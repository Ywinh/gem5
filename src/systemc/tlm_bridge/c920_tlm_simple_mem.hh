/*
 * Copyright 2026
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#ifndef __SYSTEMC_TLM_BRIDGE_C920_TLM_SIMPLE_MEM_HH__
#define __SYSTEMC_TLM_BRIDGE_C920_TLM_SIMPLE_MEM_HH__

#include <cmath>
#include <cstdint>
#include <cstring>
#include <deque>
#include <vector>

#include "base/addr_range.hh"
#include "base/random.hh"
#include "params/C920TlmSimpleMem.hh"
#include "systemc/ext/core/sc_module.hh"
#include "systemc/ext/core/sc_module_name.hh"

#include "systemc/ext/systemc"
#include "systemc/ext/tlm"
#include "systemc/ext/tlm_utils/peq_with_cb_and_phase.h"
#include "systemc/ext/tlm_utils/simple_target_socket.h"
#include "systemc/tlm_port_wrapper.hh"

namespace sc_gem5
{

class C920SimpleMemoryTarget : public sc_core::sc_module
{
  public:
    using transaction_type = tlm::tlm_generic_payload;
    using phase_type = tlm::tlm_phase;
    using sync_enum_type = tlm::tlm_sync_enum;

    tlm_utils::simple_target_socket<C920SimpleMemoryTarget, 64> socket;

    SC_HAS_PROCESS(C920SimpleMemoryTarget);
    C920SimpleMemoryTarget(
        sc_core::sc_module_name name, const gem5::AddrRange &range,
        gem5::Tick latency,
        gem5::Tick latencyVar, double bandwidth);

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

    void peq_cb(transaction_type &trans, const phase_type &phase);
    void send_end_req(transaction_type &trans);
    void send_response(transaction_type &trans);
    void execute_transaction(transaction_type &trans);

    void checkTransaction(transaction_type &trans);
    sc_core::sc_time payloadDuration(unsigned int len) const;
    sc_core::sc_time responseLatency() const;
};

class C920TlmSimpleMem : public sc_core::sc_module
{
  public:
    using Params = gem5::C920TlmSimpleMemParams;

    gem5::Port &
    gem5_getPort(const std::string &if_name, int idx = -1) override;

    C920TlmSimpleMem(
        const Params &params, const sc_core::sc_module_name &name);

  private:
    C920SimpleMemoryTarget target;
    sc_gem5::TlmTargetWrapper<64> wrapper;
};

} // namespace sc_gem5

#endif // __SYSTEMC_TLM_BRIDGE_C920_TLM_SIMPLE_MEM_HH__
