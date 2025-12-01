from m5.objects import *
from m5.SimObject import SimObject


class DemoMemory(SimObject):
    type = "DemoMemory"
    cxx_header = "bootcamp/mem_object/demo_memory.hh"
    cxx_class = "gem5::DemoMemory"

    inst_port = ResponsePort("CPU side port, receives request")
    data_port = ResponsePort("CPU side port, receives request")
    mem_side = RequestPort("Memory side port, sends requests")
