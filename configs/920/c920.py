# 导入m5库
# from gem5.components.cachehierarchies.ruby import mesi_two_level_cache_hierarchy
from cache import L1PrivateL2SharedCacheHierarchy

import m5

# 导入所有SimObjects
from m5.objects import *

from gem5.components.boards.test_board import TestBoard
from gem5.components.memory.multi_channel import DualChannelDDR4_2400
from gem5.components.processors.linear_generator import LinearGenerator
from gem5.simulate.simulator import Simulator

board = TestBoard(
    generator=LinearGenerator(num_cores=1, max_addr=2**22, rd_perc=75),
    cache_hierarchy=L1PrivateL2SharedCacheHierarchy(
        l1d_size="32KiB",
        l1i_size="32KiB",
        l2_size="256KiB",
    ),
    memory=DualChannelDDR4_2400(size="2GB"),
    clk_freq="3GHz",
)

sim = Simulator(board)
sim.run()


# system = System()

# system.clk_domain = SrcClockDomain()
# system.clk_domain.clock = '1GHz'
# system.clk_domain.voltage_domain = VoltageDomain() #不关心系统功耗，使用电压与默认选项


# L1 Dcache和L2 cache一致性协议配置，L1 Icache单独配置，因为不需要 write cache
# 为每一个core创建一个L1 cache
# 根据banks数目，创建多个 L2 缓存控制器实例。这些 L2 块共同组成了逻辑上的共享 L2 缓存
# cache_hierarchy = MESITwoLevelCacheHierarchy(
#     l1d_size="32kB",
#     l1d_assoc=2,
#     l1i_size="32kB",
#     l1i_assoc=2,
#     l2_size="256kB",
#     l2_assoc=16,
#     num_l2_banks=8,
# )
