from m5.objects.SystemC import SystemC_ScModule
from m5.objects.Tlm import TlmTargetSocket
from m5.params import Param
from m5.proxy import Parent


class C920TlmPrintMem(SystemC_ScModule):
    type = "C920TlmPrintMem"
    cxx_class = "sc_gem5::C920TlmPrintMem"
    cxx_header = "systemc/tlm_bridge/c920_tlm_print_mem.hh"

    tlm = TlmTargetSocket(64, "TLM target socket for C920 print memory")
    system = Param.System(Parent.any, "system")
