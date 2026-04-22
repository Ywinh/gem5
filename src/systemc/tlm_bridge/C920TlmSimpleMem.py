from m5.objects.SystemC import SystemC_ScModule
from m5.objects.Tlm import TlmTargetSocket
from m5.params import Param


class C920TlmSimpleMem(SystemC_ScModule):
    type = "C920TlmSimpleMem"
    cxx_class = "sc_gem5::C920TlmSimpleMem"
    cxx_header = "systemc/tlm_bridge/c920_tlm_simple_mem.hh"

    tlm = TlmTargetSocket(
        64, "TLM target socket for C920 SystemC simple memory"
    )
    range = Param.AddrRange(
        "128MiB", "Address range served by the SystemC memory"
    )
    latency = Param.Latency("30ns", "Request to response latency")
    latency_var = Param.Latency("0ns", "Request to response latency variance")
    bandwidth = Param.MemoryBandwidth(
        "12.8GiB/s", "Combined read and write bandwidth"
    )
