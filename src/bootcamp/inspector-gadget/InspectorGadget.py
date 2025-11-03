# from m5.objects.ClockedObject import ClockedObject
# from m5.params import *

# class InspectorGadget(SimObject):
#     type = "InspectorGadget"
#     cxx_header = "bootcamp/inspector-gadget/inspector_gadget.hh"
#     cxx_class = "gem5::InspectorGadget"

#     cpu_side_port = ResponsePort("ResponsePort to receive requests from CPU side")
#     mem_size_port = RequestPort("RequestPort to send received requests to memory side")

#     inspection_buffer_entries = Param.Int("Number of entries in the inspection buffer")
#     response_buffer_entries = Param.Int("Number of entries in the response buffer.")
