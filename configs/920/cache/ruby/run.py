# 导入m5库
from Ruby_two_level_cache import MESITwoLevelCacheHierarchy

import m5

# 导入所有SimObjects
from m5.objects import *

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.boards.test_board import TestBoard
from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import (
    PrivateL1CacheHierarchy,
)
from gem5.components.memory.multi_channel import DualChannelDDR4_2400
from gem5.components.memory.single_channel import SingleChannelDDR3_1600
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.linear_generator import LinearGenerator
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.isas import ISA
from gem5.resources.resource import obtain_resource
from gem5.simulate.simulator import Simulator

board = TestBoard(
    generator=LinearGenerator(
        num_cores=1, block_size=4, max_addr=2**22, rd_perc=75
    ),
    cache_hierarchy=MESITwoLevelCacheHierarchy(
        l1d_size="32KiB",
        l1d_assoc=2,
        l1i_size="32KiB",
        l1i_assoc=2,
        l2_size="256KiB",
        l2_assoc=16,
        num_l2_banks=8,
    ),
    memory=DualChannelDDR4_2400(size="2GiB"),
    clk_freq="3GHz",
)

sim = Simulator(board)
sim.run()

# memory = SingleChannelDDR3_1600("1GiB")

# # By default, use Atomic CPU
# cpu_type = CPUTypes.MINOR

# # Uncomment for steps 2 and 3
# # cpu_type = CPUTypes.TIMING

# # Note: O3CPU is the only CPU here that is modeled off of a real CPU
# # Uncomment and look at this cpu_type at home for fun!
# # cpu_type = CPUTypes.O3

# processor = SimpleProcessor(cpu_type=cpu_type, isa=ISA.RISCV, num_cores=1)

# board = SimpleBoard(
#     clk_freq="3GHz",
#     processor=processor,
#     memory=memory,
#     cache_hierarchy=MESITwoLevelCacheHierarchy(
#         l1d_size="32kB",
#         l1d_assoc=2,
#         l1i_size="32kB",
#         l1i_assoc=2,
#         l2_size="256kB",
#         l2_assoc=16,
#         num_l2_banks=8,
#     )
# )

# # Resources can be found at
# # https://resources.gem5.org/
# # riscv-matrix-multiply is obtained from
# # https://resources.gem5.org/resources/riscv-getting-started-benchmark-suite?version=1.0.0

# # workload = obtain_resource("riscv-matrix-multiply-run")
# # board.set_workload(workload)

# binary = obtain_resource("riscv-hello")
# board.set_se_binary_workload(binary)
# simulator = Simulator(board=board)
# simulator.run()
