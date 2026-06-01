/*
 * Copyright 2026
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <algorithm>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <iostream>

#include "c920_memory.hh"

C920SimpleMemoryTarget::C920SimpleMemoryTarget(
    sc_core::sc_module_name name, const gem5::AddrRange &range,
    gem5::Tick latency, gem5::Tick latencyVar, double bandwidth,
    bool verbose) :
    sc_core::sc_module(name),
    socket("socket"),
    responseInProgress(false),
    peq(this, &C920SimpleMemoryTarget::peq_cb),
    range(range),
    storage(range.size(), 0),
    latencyTicks(latency),
    latencyVarTicks(latencyVar),
    bandwidthTicksPerByte(bandwidth),
    busyUntil(sc_core::SC_ZERO_TIME),
    rng(gem5::Random::genRandom()),
    verbose(verbose)
{
    socket.register_b_transport(this, &C920SimpleMemoryTarget::b_transport);
    socket.register_transport_dbg(
        this, &C920SimpleMemoryTarget::transport_dbg);
    socket.register_nb_transport_fw(
        this, &C920SimpleMemoryTarget::nb_transport_fw);
    socket.register_get_direct_mem_ptr(
        this, &C920SimpleMemoryTarget::get_direct_mem_ptr);
}

void
C920SimpleMemoryTarget::b_transport(
    transaction_type &trans, sc_core::sc_time &delay)
{
    execute_transaction(trans);
    if (trans.get_response_status() == tlm::TLM_OK_RESPONSE) {
        delay += responseLatency();
    }
}

unsigned int
C920SimpleMemoryTarget::transport_dbg(transaction_type &trans)
{
    execute_transaction(trans);
    if (trans.get_response_status() != tlm::TLM_OK_RESPONSE) {
        return 0;
    }

    return trans.get_data_length();
}

C920SimpleMemoryTarget::sync_enum_type
C920SimpleMemoryTarget::nb_transport_fw(
    transaction_type &trans, phase_type &phase, sc_core::sc_time &delay)
{
    peq.notify(trans, phase, delay);
    return tlm::TLM_ACCEPTED;
}

bool
C920SimpleMemoryTarget::get_direct_mem_ptr(
    transaction_type &, tlm::tlm_dmi &)
{
    return false;
}

void
C920SimpleMemoryTarget::peq_cb(
    transaction_type &trans, const phase_type &phase)
{
    if (phase == tlm::BEGIN_REQ) {
        trans.acquire();
        sc_core::sc_time acceptDelay = sc_core::SC_ZERO_TIME;

        if (busyUntil > sc_core::sc_time_stamp()) {
            acceptDelay = busyUntil - sc_core::sc_time_stamp();
        }

        busyUntil = std::max(busyUntil, sc_core::sc_time_stamp()) +
            payloadDuration(trans.get_data_length());
        peq.notify(trans, tlm::END_REQ, acceptDelay);
        return;
    }

    if (phase == tlm::END_REQ) {
        send_end_req(trans);
        execute_transaction(trans);
        peq.notify(trans, tlm::BEGIN_RESP, responseLatency());
        return;
    }

    if (phase == tlm::BEGIN_RESP) {
        if (responseInProgress) {
            pendingResponses.push_back(&trans);
        } else {
            send_response(trans);
        }
        return;
    }

    if (phase == tlm::END_RESP) {
        if (!responseInProgress) {
            SC_REPORT_FATAL(
                "C920ExternalSystemcSimpleMem",
                "Illegal END_RESP received by target");
        }

        responseInProgress = false;
        trans.release();

        if (!pendingResponses.empty()) {
            auto *next = pendingResponses.front();
            pendingResponses.pop_front();
            send_response(*next);
        }
        return;
    }

    SC_REPORT_FATAL(
        "C920ExternalSystemcSimpleMem",
        "Illegal phase received by target PEQ");
}

void
C920SimpleMemoryTarget::send_end_req(transaction_type &trans)
{
    phase_type phase = tlm::END_REQ;
    sc_core::sc_time delay = sc_core::SC_ZERO_TIME;
    sync_enum_type status = socket->nb_transport_bw(trans, phase, delay);

    if (status != tlm::TLM_ACCEPTED) {
        SC_REPORT_FATAL(
            "C920ExternalSystemcSimpleMem",
            "Unexpected status after sending END_REQ");
    }
}

void
C920SimpleMemoryTarget::send_response(transaction_type &trans)
{
    responseInProgress = true;

    phase_type phase = tlm::BEGIN_RESP;
    sc_core::sc_time delay = sc_core::SC_ZERO_TIME;
    sync_enum_type status = socket->nb_transport_bw(trans, phase, delay);

    if (status == tlm::TLM_COMPLETED ||
        (status == tlm::TLM_UPDATED && phase == tlm::END_RESP)) {
        responseInProgress = false;
        trans.release();

        if (!pendingResponses.empty()) {
            auto *next = pendingResponses.front();
            pendingResponses.pop_front();
            peq.notify(*next, tlm::BEGIN_RESP, delay);
        }
    } else if (status != tlm::TLM_ACCEPTED) {
        SC_REPORT_FATAL(
            "C920ExternalSystemcSimpleMem",
            "Unexpected status after sending BEGIN_RESP");
    }
}

void
C920SimpleMemoryTarget::execute_transaction(transaction_type &trans)
{
    checkTransaction(trans);
    if (trans.get_response_status() != tlm::TLM_INCOMPLETE_RESPONSE) {
        return;
    }

    if (verbose) {
        reportTransaction(trans);
    }

    const auto offset = trans.get_address() - range.start();
    auto *storagePtr = storage.data() + offset;
    auto *data = trans.get_data_ptr();
    const auto len = trans.get_data_length();

    switch (trans.get_command()) {
      case tlm::TLM_READ_COMMAND:
        if (data && len != 0) {
            std::memcpy(data, storagePtr, len);
        }
        break;

      case tlm::TLM_WRITE_COMMAND:
        if (data && len != 0) {
            std::memcpy(storagePtr, data, len);
        }
        break;

      case tlm::TLM_IGNORE_COMMAND:
        break;

      default:
        trans.set_response_status(tlm::TLM_COMMAND_ERROR_RESPONSE);
        return;
    }

    trans.set_dmi_allowed(false);
    trans.set_response_status(tlm::TLM_OK_RESPONSE);
}

void
C920SimpleMemoryTarget::checkTransaction(transaction_type &trans)
{
    trans.set_response_status(tlm::TLM_INCOMPLETE_RESPONSE);

    const auto start = trans.get_address();
    const auto len = trans.get_data_length();
    const auto end = start + len;

    if (start < range.start() || end > range.end()) {
        trans.set_response_status(tlm::TLM_ADDRESS_ERROR_RESPONSE);
        return;
    }

    if (trans.get_byte_enable_ptr() != nullptr) {
        trans.set_response_status(tlm::TLM_BYTE_ENABLE_ERROR_RESPONSE);
        return;
    }

    if (trans.get_streaming_width() < len) {
        trans.set_response_status(tlm::TLM_BURST_ERROR_RESPONSE);
        return;
    }
}

void
C920SimpleMemoryTarget::reportTransaction(const transaction_type &trans) const
{
    const char *cmd = "IGNORE";
    if (trans.get_command() == tlm::TLM_READ_COMMAND) {
        cmd = "READ";
    } else if (trans.get_command() == tlm::TLM_WRITE_COMMAND) {
        cmd = "WRITE";
    }

    std::ios oldState(nullptr);
    oldState.copyfmt(std::cout);
    std::cout << "[C920ExternalSystemcSimpleMem] @" << sc_core::sc_time_stamp()
              << ' ' << cmd << " addr=0x" << std::hex << trans.get_address()
              << std::dec << " len=" << trans.get_data_length() << '\n';
    std::cout.copyfmt(oldState);
}

sc_core::sc_time
C920SimpleMemoryTarget::payloadDuration(unsigned int len) const
{
    if (len == 0) {
        return sc_core::SC_ZERO_TIME;
    }

    const auto ticks = static_cast<gem5::Tick>(
        std::ceil(static_cast<double>(len) * bandwidthTicksPerByte));
    return sc_core::sc_time::from_value(ticks);
}

sc_core::sc_time
C920SimpleMemoryTarget::responseLatency() const
{
    gem5::Tick ticks = latencyTicks;
    if (latencyVarTicks != 0) {
        ticks += rng->random<gem5::Tick>(0, latencyVarTicks);
    }

    return sc_core::sc_time::from_value(ticks);
}
