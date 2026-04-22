/*
 * Copyright 2026
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef __SYSTEMC_TLM_BRIDGE_C920_TLM_PRINT_MEM_HH__
#define __SYSTEMC_TLM_BRIDGE_C920_TLM_PRINT_MEM_HH__

#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <string>

#include "mem/physical.hh"
#include "params/C920TlmPrintMem.hh"
#include "sim/system.hh"
#include "systemc/ext/core/sc_module.hh"
#include "systemc/ext/core/sc_module_name.hh"

#include "systemc/ext/systemc"
#include "systemc/ext/tlm"
#include "systemc/ext/tlm_utils/peq_with_get.h"
#include "systemc/ext/tlm_utils/simple_initiator_socket.h"
#include "systemc/ext/tlm_utils/simple_target_socket.h"
#include "systemc/tlm_port_wrapper.hh"

namespace sc_gem5
{

template <unsigned int BITWIDTH, int NR_OF_INITIATORS, int NR_OF_TARGETS>
class SimpleBusAT : public sc_core::sc_module
{
  public:
    typedef tlm::tlm_generic_payload transaction_type;
    typedef tlm::tlm_phase phase_type;
    typedef tlm::tlm_sync_enum sync_enum_type;
    typedef tlm_utils::simple_target_socket_tagged<SimpleBusAT, BITWIDTH>
        target_socket_type;
    typedef tlm_utils::simple_initiator_socket_tagged<SimpleBusAT, BITWIDTH>
        initiator_socket_type;

    target_socket_type target_socket[NR_OF_INITIATORS];
    initiator_socket_type initiator_socket[NR_OF_TARGETS];

    SC_HAS_PROCESS(SimpleBusAT);
    explicit SimpleBusAT(sc_core::sc_module_name name) :
        sc_core::sc_module(name),
        mRequestPEQ("request_peq"),
        mResponsePEQ("response_peq")
    {
        for (int i = 0; i < NR_OF_INITIATORS; ++i) {
            target_socket[i].register_nb_transport_fw(
                this, &SimpleBusAT::initiatorNBTransport, i);
            target_socket[i].register_transport_dbg(
                this, &SimpleBusAT::transportDebug, i);
            target_socket[i].register_get_direct_mem_ptr(
                this, &SimpleBusAT::getDMIPointer, i);
        }

        for (int i = 0; i < NR_OF_TARGETS; ++i) {
            initiator_socket[i].register_nb_transport_bw(
                this, &SimpleBusAT::targetNBTransport, i);
            initiator_socket[i].register_invalidate_direct_mem_ptr(
                this, &SimpleBusAT::invalidateDMIPointers, i);
        }

        SC_THREAD(requestThread);
        SC_THREAD(responseThread);
    }

    unsigned int
    decode(const sc_dt::uint64 &) const
    {
        return 0;
    }

    sc_dt::uint64
    getAddressMask(unsigned int) const
    {
        return ~static_cast<sc_dt::uint64>(0);
    }

    sync_enum_type
    initiatorNBTransport(
        int initiator_id, transaction_type &trans, phase_type &phase,
        sc_core::sc_time &t)
    {
        if (phase == tlm::BEGIN_REQ) {
            trans.acquire();
            addPendingTransaction(trans, nullptr, initiator_id);
            mRequestPEQ.notify(trans, t);
            return tlm::TLM_ACCEPTED;
        }

        if (phase == tlm::END_RESP) {
            mEndResponseEvent.notify(t);
            return tlm::TLM_COMPLETED;
        }

        SC_REPORT_FATAL(name(), "Illegal phase received from initiator");
        return tlm::TLM_COMPLETED;
    }

    sync_enum_type
    targetNBTransport(
        int, transaction_type &trans, phase_type &phase, sc_core::sc_time &t)
    {
        if (phase != tlm::END_REQ && phase != tlm::BEGIN_RESP) {
            SC_REPORT_FATAL(name(), "Illegal phase received from target");
        }

        mEndRequestEvent.notify(t);
        if (phase == tlm::BEGIN_RESP) {
            mResponsePEQ.notify(trans, t);
        }

        return tlm::TLM_ACCEPTED;
    }

    unsigned int
    transportDebug(int, transaction_type &trans)
    {
        const unsigned int port_id = decode(trans.get_address());
        assert(port_id < NR_OF_TARGETS);
        initiator_socket_type *decode_socket = &initiator_socket[port_id];
        trans.set_address(trans.get_address() & getAddressMask(port_id));
        return (*decode_socket)->transport_dbg(trans);
    }

    bool
    getDMIPointer(int, transaction_type &trans, tlm::tlm_dmi &dmi_data)
    {
        const unsigned int port_id = decode(trans.get_address());
        assert(port_id < NR_OF_TARGETS);
        initiator_socket_type *decode_socket = &initiator_socket[port_id];
        trans.set_address(trans.get_address() & getAddressMask(port_id));
        return (*decode_socket)->get_direct_mem_ptr(trans, dmi_data);
    }

    void
    invalidateDMIPointers(
        int, sc_dt::uint64 start_range, sc_dt::uint64 end_range)
    {
        for (int i = 0; i < NR_OF_INITIATORS; ++i) {
            target_socket[i]->invalidate_direct_mem_ptr(
                start_range, end_range);
        }
    }

  private:
    struct ConnectionInfo
    {
        target_socket_type *from;
        initiator_socket_type *to;
    };

    typedef std::map<transaction_type *, ConnectionInfo> PendingTransactions;
    typedef typename PendingTransactions::iterator PendingTransactionsIterator;

    void
    addPendingTransaction(
        transaction_type &trans, initiator_socket_type *to, int initiator_id)
    {
        const ConnectionInfo info = {&target_socket[initiator_id], to};
        assert(
            mPendingTransactions.find(&trans) ==
            mPendingTransactions.end());
        mPendingTransactions[&trans] = info;
    }

    void
    requestThread()
    {
        while (true) {
            wait(mRequestPEQ.get_event());

            transaction_type *trans;
            while ((trans = mRequestPEQ.get_next_transaction()) != nullptr) {
                const unsigned int port_id = decode(trans->get_address());
                assert(port_id < NR_OF_TARGETS);
                initiator_socket_type *decode_socket =
                    &initiator_socket[port_id];
                trans->set_address(
                    trans->get_address() & getAddressMask(port_id));

                PendingTransactionsIterator it =
                    mPendingTransactions.find(trans);
                assert(it != mPendingTransactions.end());
                it->second.to = decode_socket;

                phase_type phase = tlm::BEGIN_REQ;
                sc_core::sc_time t = sc_core::SC_ZERO_TIME;

                switch ((*decode_socket)->nb_transport_fw(*trans, phase, t)) {
                  case tlm::TLM_ACCEPTED:
                  case tlm::TLM_UPDATED:
                    if (phase == tlm::BEGIN_REQ) {
                        wait(mEndRequestEvent);
                    } else if (phase == tlm::END_REQ) {
                        wait(t);
                    } else if (phase == tlm::BEGIN_RESP) {
                        mResponsePEQ.notify(*trans, t);
                        continue;
                    } else {
                        SC_REPORT_FATAL(
                            name(),
                            "Unexpected phase while processing request");
                    }

                    if (it->second.from) {
                        phase = tlm::END_REQ;
                        t = sc_core::SC_ZERO_TIME;
                        (*it->second.from)->nb_transport_bw(*trans, phase, t);
                    }
                    break;

                  case tlm::TLM_COMPLETED:
                    mResponsePEQ.notify(*trans, t);
                    it->second.to = nullptr;
                    wait(t);
                    break;

                  default:
                    SC_REPORT_FATAL(
                        name(), "Unsupported TLM sync return value");
                }
            }
        }
    }

    void
    responseThread()
    {
        while (true) {
            wait(mResponsePEQ.get_event());

            transaction_type *trans;
            while ((trans = mResponsePEQ.get_next_transaction()) != nullptr) {
                PendingTransactionsIterator it =
                    mPendingTransactions.find(trans);
                assert(it != mPendingTransactions.end());

                phase_type phase = tlm::BEGIN_RESP;
                sc_core::sc_time t = sc_core::SC_ZERO_TIME;

                target_socket_type *initiator_socket = it->second.from;
                assert(initiator_socket != nullptr);
                it->second.from = nullptr;

                switch (
                    (*initiator_socket)->nb_transport_bw(*trans, phase, t)) {
                  case tlm::TLM_COMPLETED:
                    wait(t);
                    break;

                  case tlm::TLM_ACCEPTED:
                  case tlm::TLM_UPDATED:
                    wait(mEndResponseEvent);
                    break;

                  default:
                    SC_REPORT_FATAL(
                        name(), "Unsupported TLM response return value");
                }

                if (it->second.to) {
                    phase = tlm::END_RESP;
                    t = sc_core::SC_ZERO_TIME;
                    sync_enum_type result =
                        (*it->second.to)->nb_transport_fw(*trans, phase, t);
                    assert(result == tlm::TLM_COMPLETED);
                    (void)result;
                }

                mPendingTransactions.erase(it);
                trans->release();
            }
        }
    }

    PendingTransactions mPendingTransactions;
    tlm_utils::peq_with_get<transaction_type> mRequestPEQ;
    sc_core::sc_event mEndRequestEvent;
    tlm_utils::peq_with_get<transaction_type> mResponsePEQ;
    sc_core::sc_event mEndResponseEvent;
};

class C920PrintTarget : public sc_core::sc_module
{
  public:
    typedef tlm::tlm_generic_payload transaction_type;
    typedef tlm::tlm_phase phase_type;
    typedef tlm::tlm_sync_enum sync_enum_type;

    tlm_utils::simple_target_socket<C920PrintTarget, 64> socket;

    SC_HAS_PROCESS(C920PrintTarget);
    C920PrintTarget(sc_core::sc_module_name name, gem5::System *system) :
        sc_core::sc_module(name), socket("socket"), system(system)
    {
        assert(system != nullptr);
        socket.register_nb_transport_fw(this, &C920PrintTarget::nbTransportFw);
        socket.register_b_transport(this, &C920PrintTarget::bTransport);
        socket.register_transport_dbg(this, &C920PrintTarget::transportDebug);
        socket.register_get_direct_mem_ptr(
            this, &C920PrintTarget::getDMIPointer);
    }

    sync_enum_type
    nbTransportFw(
        transaction_type &trans, phase_type &phase, sc_core::sc_time &)
    {
        if (phase == tlm::END_RESP) {
            return tlm::TLM_COMPLETED;
        }

        if (phase != tlm::BEGIN_REQ) {
            SC_REPORT_FATAL(name(), "Print target received an illegal phase");
        }

        executeTransaction(trans);
        phase = tlm::END_RESP;
        return tlm::TLM_COMPLETED;
    }

    void
    bTransport(transaction_type &trans, sc_core::sc_time &)
    {
        executeTransaction(trans);
    }

    unsigned int
    transportDebug(transaction_type &trans)
    {
        executeTransaction(trans);
        return trans.get_data_length();
    }

    bool
    getDMIPointer(transaction_type &, tlm::tlm_dmi &)
    {
        return false;
    }

  private:
    gem5::System *system;

    static const char *
    commandToString(tlm::tlm_command cmd)
    {
        switch (cmd) {
          case tlm::TLM_READ_COMMAND:
            return "READ";
          case tlm::TLM_WRITE_COMMAND:
            return "WRITE";
          case tlm::TLM_IGNORE_COMMAND:
            return "IGNORE";
          default:
            return "UNKNOWN";
        }
    }

    static std::string
    formatData(const transaction_type &trans)
    {
        const unsigned char *data = trans.get_data_ptr();
        if (!data || trans.get_data_length() == 0) {
            return "-";
        }

        std::ostringstream os;
        os << std::hex << std::setfill('0');

        const unsigned int bytes = std::min(trans.get_data_length(), 8U);
        for (unsigned int i = 0; i < bytes; ++i) {
            if (i != 0) {
                os << ' ';
            }
            os << std::setw(2) << static_cast<unsigned int>(data[i]);
        }

        if (trans.get_data_length() > bytes) {
            os << " ...";
        }

        return os.str();
    }

    void
    backingStoreAccess(transaction_type &trans)
    {
        unsigned char *data = trans.get_data_ptr();
        const auto data_length = trans.get_data_length();
        const gem5::Addr start = trans.get_address();
        const gem5::Addr end = start + data_length;

        uint8_t *host = nullptr;
        for (const auto &entry : system->getPhysMem().getBackingStore()) {
            if (start >= entry.range.start() && end <= entry.range.end()) {
                host = entry.pmem + (start - entry.range.start());
                break;
            }
        }

        if (!host && data_length != 0) {
            trans.set_response_status(tlm::TLM_ADDRESS_ERROR_RESPONSE);
            return;
        }

        switch (trans.get_command()) {
          case tlm::TLM_READ_COMMAND:
            if (data && data_length != 0) {
                std::memcpy(data, host, data_length);
            }
            break;

          case tlm::TLM_WRITE_COMMAND:
            if (data && data_length != 0) {
                std::memcpy(host, data, data_length);
            }
            break;

          case tlm::TLM_IGNORE_COMMAND:
            break;

          default:
            trans.set_response_status(tlm::TLM_COMMAND_ERROR_RESPONSE);
            return;
        }

        trans.set_response_status(tlm::TLM_OK_RESPONSE);
    }

    void
    executeTransaction(transaction_type &trans)
    {
        if (trans.get_byte_enable_ptr() != nullptr) {
            trans.set_response_status(tlm::TLM_BYTE_ENABLE_ERROR_RESPONSE);
            return;
        }

        backingStoreAccess(trans);
        if (trans.get_response_status() != tlm::TLM_OK_RESPONSE) {
            return;
        }

        std::cout << "[C920TlmPrintMem] @" << sc_core::sc_time_stamp()
                  << " cmd=" << commandToString(trans.get_command())
                  << " addr=0x" << std::hex << trans.get_address()
                  << " len=" << std::dec << trans.get_data_length()
                  << " data=" << formatData(trans) << std::endl;

        trans.set_dmi_allowed(false);
    }
};

class C920TlmPrintMem : public sc_core::sc_module
{
  public:
    typedef gem5::C920TlmPrintMemParams Params;

    gem5::Port &
    gem5_getPort(const std::string &if_name, int idx = -1) override;

    C920TlmPrintMem(const Params &params, const sc_core::sc_module_name &name);

  private:
    SimpleBusAT<64, 1, 1> bus;
    C920PrintTarget target;
    sc_gem5::TlmTargetWrapper<64> wrapper;
};

} // namespace sc_gem5

#endif // __SYSTEMC_TLM_BRIDGE_C920_TLM_PRINT_MEM_HH__
