/*
 * Copyright 2026
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef __UTIL_TLM_EXAMPLES_C920_SIMPLE_MEM_C920_MEMORY_HH__
#define __UTIL_TLM_EXAMPLES_C920_SIMPLE_MEM_C920_MEMORY_HH__

#include <tlm_utils/peq_with_cb_and_phase.h>
#include <tlm_utils/simple_target_socket.h>

#include <deque>
#include <systemc>
#include <tlm>
#include <vector>

#include "base/addr_range.hh"
#include "base/random.hh"

class C920SimpleMemoryTarget : public sc_core::sc_module
{
  public:
    using transaction_type = tlm::tlm_generic_payload;
    using phase_type = tlm::tlm_phase;
    using sync_enum_type = tlm::tlm_sync_enum;

    tlm_utils::simple_target_socket<C920SimpleMemoryTarget> socket;

    SC_HAS_PROCESS(C920SimpleMemoryTarget);
    C920SimpleMemoryTarget(
        sc_core::sc_module_name name, const gem5::AddrRange &range,
        gem5::Tick latency, gem5::Tick latencyVar, double bandwidth,
        bool verbose);

    void b_transport(transaction_type &trans, sc_core::sc_time &delay);
    unsigned int transport_dbg(transaction_type &trans);
    sync_enum_type nb_transport_fw(
        transaction_type &trans, phase_type &phase, sc_core::sc_time &delay);
    bool get_direct_mem_ptr(transaction_type &trans, tlm::tlm_dmi &dmi_data);

  private:
    bool responseInProgress;
    std::deque<transaction_type *> pendingResponses;
    tlm_utils::peq_with_cb_and_phase<C920SimpleMemoryTarget> peq;

    gem5::AddrRange range;
    std::vector<unsigned char> storage;
    gem5::Tick latencyTicks;
    gem5::Tick latencyVarTicks;
    double bandwidthTicksPerByte;
    sc_core::sc_time busyUntil;
    gem5::Random::RandomPtr rng;
    bool verbose;

    void peq_cb(transaction_type &trans, const phase_type &phase);
    void send_end_req(transaction_type &trans);
    void send_response(transaction_type &trans);
    void execute_transaction(transaction_type &trans);

    void checkTransaction(transaction_type &trans);
    void reportTransaction(const transaction_type &trans) const;
    sc_core::sc_time payloadDuration(unsigned int len) const;
    sc_core::sc_time responseLatency() const;
};

#endif
