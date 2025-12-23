from private_l1_cache_hierarchy import PrivateL1CacheHierarchy
from processor import C906Processor

import m5
from m5.objects import *

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.resources.resource import (
    BinaryResource,
    obtain_resource,
)
from gem5.simulate.simulator import Simulator

cache_hierarchy = PrivateL1CacheHierarchy(
    l1d_size="32kB",
    l1i_size="32kB",
)

memory = SingleChannelDDR4_2400("1GB")

processor = C906Processor(is_fs=False)  # 使用自定义的 CPU 类

board = SimpleBoard(
    clk_freq="1GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# run 1
# workload = obtain_resource("riscv-matrix-multiply-run")
# board.set_workload(workload)

# run 2
# binary = obtain_resource("riscv-hello")
# board.set_se_binary_workload(binary)

# run 3


board.set_se_binary_workload(
    binary=BinaryResource(
        local_path="/home/yinjianhui/gem5-resources/src/simple/out/riscv/user/hello.out"
    )
)

simulator = Simulator(board=board)

simulator.run()

print("Simulation Done")
