/*
 * Copyright 2026
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include "systemc/tlm_bridge/c920_tlm_print_mem.hh"

namespace sc_gem5
{

C920TlmPrintMem::C920TlmPrintMem(
    const Params &params, const sc_core::sc_module_name &name) :
    sc_core::sc_module(name),
    bus("bus"),
    target("target", params.system),
    wrapper(bus.target_socket[0], std::string(this->name()) + ".tlm",
            gem5::InvalidPortID)
{
    bus.initiator_socket[0].bind(target.socket);
}

gem5::Port &
C920TlmPrintMem::gem5_getPort(const std::string &if_name, int idx)
{
    if (if_name == "tlm") {
        return wrapper;
    }

    return sc_core::sc_module::gem5_getPort(if_name, idx);
}

} // namespace sc_gem5

sc_gem5::C920TlmPrintMem *
gem5::C920TlmPrintMemParams::create() const
{
    return new sc_gem5::C920TlmPrintMem(
        *this, sc_core::sc_module_name(name.c_str()));
}
