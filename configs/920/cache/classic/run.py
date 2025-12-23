# 导入m5库
# from gem5.components.cachehierarchies.ruby import mesi_two_level_cache_hierarchy
from cache import L1PrivateL2SharedCacheHierarchy

import m5

# 导入所有SimObjects
from m5.objects import *

from gem5.components.boards.test_board import TestBoard
from gem5.components.memory.multi_channel import DualChannelDDR4_2400

# 使用 LinearGenerator 的话，代码如下：
from gem5.components.processors.linear_generator import LinearGenerator
from gem5.simulate.simulator import Simulator

# 使用 ComplexGenerator 和自定义的 FIFOgen 脚本
# from gem5.components.processors.complex_generator import ComplexGenerator
# from FIFOgen import returning_sequence
# gen = ComplexGenerator(num_cores=1)
# gen.set_traffic_from_python_generator(returning_sequence)


gen = LinearGenerator(
    num_cores=1,
    duration="1ms",
    rate="10MiB/s",
    block_size=4,
    max_addr=2**15,
    data_limit=2**15,
    rd_perc=50,
)

board = TestBoard(
    generator=gen,
    cache_hierarchy=L1PrivateL2SharedCacheHierarchy(
        l1d_size="32KiB",
        l1i_size="32KiB",
        l2_size="256KiB",
    ),
    memory=DualChannelDDR4_2400(size="2GiB"),
    clk_freq="3GHz",
)

sim = Simulator(board)
sim.run()
