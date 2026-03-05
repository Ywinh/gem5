# 导入m5库
import m5

# 导入所有SimObjects
from m5.objects import *

from gem5.components.cachehierarchies.classic.abstract_classic_cache_hierarchy import (
    AbstractClassicCacheHierarchy,
)


# for I-Cache prefetcher
class L1ICachePrefetcher(TaggedPrefetcher):
    def __init__(self):
        super().__init__()

        self.on_miss = True
        self.on_read = True
        self.on_write = False
        self.on_data = False
        self.on_inst = True
        self.prefetch_on_access = False
        self.prefetch_on_pf_hit = False  # 不在预取命中时触发
        self.latency = 1  # 预取请求生成的延迟

        self.degree = 1  # 每次预取 1 个 Cache Line (实现 "Next-Line")
        self.block_size = 4096  # Cache Line 大小 (字节)


class L1DCachePrefetcher(StridePrefetcher):
    def __init__(self):
        super().__init__()

        self.on_inst = False
        self.on_data = True

        self.on_miss = True  # 仅在 Cache Miss 时触发
        self.on_read = True
        self.on_write = True
        self.prefetch_on_access = False
        self.prefetch_on_pf_hit = False  # 不在预取命中时触发

        # -----------------------------------------------------------------
        # 3. 预取行为 (User Requirement: 连续下一行, 预取缓冲)
        self.degree = 1
        self.distance = 0
        self.queue_size = 4
        self.latency = 1

        # -----------------------------------------------------------------
        # 4. 算法激进程度优化
        # Stride 预取器默认需要"学习"并积累置信度。
        # 为了让它表现得像纯粹的 "Next-Line" 且反应迅速，我们可以调整置信度参数：
        # initial_confidence(4) >= confidence_threshold(50%) -> 默认即可立即触发。
        # 如果想更激进，可以将阈值设为 0。
        self.confidence_threshold = 50


class L1ICache(Cache):
    def __init__(self, size):
        super().__init__()
        self.size = size  # 8KB/16KB/32KB/64KB
        self.assoc = 2
        self.replacement_policy = FIFORP()

        self.sequential_access = False  # False表示tag和data访问是并行的
        self.tag_latency = 1
        self.data_latency = 1
        self.response_latency = 2

        self.mshrs = 4  # 不能为0
        self.tgts_per_mshr = (
            4  # 每一个mshr可以接受多少个target，这个参数其实是乱设置的
        )

        self.is_read_only = True
        # writeback_clean = false 这个参数为True时，表示L2与L1完全没有交集，L2是L1的victim Cache
        self.write_allocator = NULL
        self.prefetcher = L1ICachePrefetcher()
        self.clusivity = "mostly_incl"


class L1DCacheWriteAllocator(WriteAllocator):
    def __init__(self):
        super().__init__()
        """
        硬件906写分配策略：
        - 连续3条cacheline的存储操作后 → 切换到写不分配模式

        gem5的WriteAllocator模式转换：
        ALLOCATE → COALESCE (达到coalesce_limit条cacheline)
                 → NO_ALLOCATE (达到no_allocate_limit条cacheline)

        配置说明：
        - coalesce_limit: cacheline数量（不是字节数）
        - no_allocate_limit: cacheline数量（不是字节数）
        - 设置为相同值可以跳过COALESCE模式，直接进入NO_ALLOCATE
        """
        self.coalesce_limit = 3  # 3条cacheline
        self.no_allocate_limit = 3  # 3条cacheline后立即切换到no-allocate
        self.delay_threshold = 8  # 延迟周期数


class L1DCache(Cache):
    def __init__(self, size):
        super().__init__()
        self.size = size  # 8KB/16KB/32KB/64KB
        self.assoc = 4
        self.replacement_policy = FIFORP()

        self.sequential_access = False  # False表示tag和data访问是并行的
        self.tag_latency = 1
        self.data_latency = 1
        self.response_latency = 1  # 修改了没什么变化

        self.mshrs = 4
        self.tgts_per_mshr = 4
        self.is_read_only = False

        self.write_allocator = L1DCacheWriteAllocator()
        self.prefetcher = L1DCachePrefetcher()
