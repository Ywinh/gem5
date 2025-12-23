# 导入m5库
import m5

# 导入所有SimObjects
from m5.objects import *

from gem5.components.cachehierarchies.classic.abstract_classic_cache_hierarchy import (
    AbstractClassicCacheHierarchy,
)


class L1IcachePrefetcher(StridePrefetcher):
    def __init__(self):
        super().__init__()
        # -----------------------------------------------------------------
        # 1. 核心修正 (基于 Prefetcher.py 源码)
        # 源码中 StridePrefetcher 类定义里写死了 `on_inst = False`。
        # 因为我们是用在 I-Cache，必须显式将其改为 True，否则预取器无法感知指令流。
        self.on_inst = True
        self.on_data = False  # I-Cache 不涉及数据访问，显式关闭以防万一

        # -----------------------------------------------------------------
        # 2. 触发策略 (User Requirement: 访问缺失时触发)
        self.on_miss = True  # 仅在 Cache Miss 时触发
        self.on_read = True  # 响应 Read Miss (指令获取属于 Read)
        self.on_write = False  # I-Cache 不会有 Write 操作
        self.prefetch_on_access = False  # 不要每次访问都触发，仅 Miss 触发

        # -----------------------------------------------------------------
        # 3. 预取行为 (User Requirement: 连续下一行, 预取缓冲)
        self.degree = 1  # 每次预取 1 个 Cache Line (实现 "Next-Line")
        self.distance = 0  # 紧邻当前缺失行的下一行 (无跨步跳跃)
        self.queue_size = 4  # 对应 "预取缓冲器"，设置大小为 4 (可按需调整)
        self.latency = 1  # 预取请求生成的延迟

        # -----------------------------------------------------------------
        # 4. 算法激进程度优化
        # Stride 预取器默认需要"学习"并积累置信度。
        # 为了让它表现得像纯粹的 "Next-Line" 且反应迅速，我们可以调整置信度参数：
        # initial_confidence(4) >= confidence_threshold(50%) -> 默认即可立即触发。
        # 如果想更激进，可以将阈值设为 0。
        self.confidence_threshold = 50

        # -----------------------------------------------------------------
        # 5. 地址与页边界 (User Requirement: 同一页面)
        self.use_virtual_addresses = False  # 使用物理地址
        # gem5 的 StridePrefetcher 内部逻辑默认会检查页边界 (Page Boundary)，
        # 防止跨页预取导致 Page Fault 或安全问题，无需额外参数配置。


class L1DcachePrefetcher(StridePrefetcher):
    def __init__(self):
        super().__init__()
        # -----------------------------------------------------------------
        # 1. 核心修正 (基于 Prefetcher.py 源码)
        # 源码中 StridePrefetcher 类定义里写死了 `on_inst = False`。
        # 因为我们是用在 I-Cache，必须显式将其改为 True，否则预取器无法感知指令流。
        self.on_inst = False
        self.on_data = True

        # -----------------------------------------------------------------
        # 2. 触发策略 (User Requirement: 访问缺失时触发)
        self.on_miss = True  # 仅在 Cache Miss 时触发
        self.on_read = True
        self.on_write = True
        self.prefetch_on_access = False  # 不要每次访问都触发，仅 Miss 触发

        # -----------------------------------------------------------------
        # 3. 预取行为 (User Requirement: 连续下一行, 预取缓冲)
        self.degree = 1  # 每次预取 1 个 Cache Line (实现 "Next-Line")
        self.distance = 0  # 紧邻当前缺失行的下一行 (无跨步跳跃)
        self.queue_size = 4  # 对应 "预取缓冲器"，设置大小为 4 (可按需调整)
        self.latency = 1  # 预取请求生成的延迟

        # -----------------------------------------------------------------
        # 4. 算法激进程度优化
        # Stride 预取器默认需要"学习"并积累置信度。
        # 为了让它表现得像纯粹的 "Next-Line" 且反应迅速，我们可以调整置信度参数：
        # initial_confidence(4) >= confidence_threshold(50%) -> 默认即可立即触发。
        # 如果想更激进，可以将阈值设为 0。
        self.confidence_threshold = 0

        # -----------------------------------------------------------------
        # 5. 地址与页边界 (User Requirement: 同一页面)
        self.use_virtual_addresses = False  # 使用物理地址
        # gem5 的 StridePrefetcher 内部逻辑默认会检查页边界 (Page Boundary)，
        # 防止跨页预取导致 Page Fault 或安全问题，无需额外参数配置。


class L1Icache(Cache):
    def __init__(self, size):
        # MSHR没有设置
        super().__init__()
        self.size = size  # 32K/64K
        self.assoc = 2
        self.replacement_policy = FIFORP()
        self.tag_latency = 1
        self.data_latency = 1
        self.response_latency = 1
        self.mshrs = 4  # 不能为0
        # tgts_per_mshr 不懂
        self.tgts_per_mshr = 1
        self.is_read_only = True
        # writeback_clean = false 这个参数为True时，表示L2与L1完全没有交集，L2是L1的垃圾桶？
        self.write_allocator = NULL
        self.prefetcher = L1IcachePrefetcher()
        self.clusivity = "mostly_incl"


class L1DcacheWriteAllocator(WriteAllocator):
    def __init__(self):
        super().__init__()
        # 920 only support write-allocate and write-noallocate but gem5 have 3 write mode:
        # 1. write-allocate 2. write-coalesce 3. write-noallocate
        # so set coalesce_limit = no_allocate_limit to change to 2 mode in gem5
        # 目前暂时把limit设得很大，使得一直处于写分配模式； 后续需要玄铁参数具体需要多少个cacheline开启写不分配
        self.coalesce_limit = 10000
        self.no_allocate_limit = 10000
        self.delay_threshold = 8


# Dcache需要一致性协议，可能得用rubycache
# classic cache 默认使用 MOESI 一致性协议
class L1Dcache(Cache):
    def __init__(self, size):
        super().__init__()
        self.size = size  # 32K/64K
        self.assoc = 2
        self.replacement_policy = FIFORP()
        self.tag_latency = 1
        self.data_latency = 1
        self.response_latency = 1
        self.mshrs = 4
        # tgts_per_mshr 不懂
        self.tgts_per_mshr = 1
        self.is_read_only = False
        self.write_allocator = L1DcacheWriteAllocator()
        self.prefetcher = L1DcachePrefetcher()


class L2cache(Cache):
    def __init__(self, size):
        super().__init__()
        self.size = size  # 32K/64K
        self.assoc = 8
        self.replacement_policy = FIFORP()
        # L2：下面每个latency都是setup latency + data_latency，玄铁可配置
        self.tag_latency = 2
        self.data_latency = 2
        self.response_latency = 2
        self.mshrs = 4
        # tgts_per_mshr 不懂
        self.tgts_per_mshr = 1
        self.is_read_only = False
        # prefetcher 和 writeAllocator暂时用L1Dcache的东西
        # self.write_allocator = L1DcacheWriteAllocator() # 使用L1的
        # self.prefetcher = L1DcachePrefetcher()


class L2CacheBank(Cache):
    """
    Bank L2 Cache, only handles requests to a portion of the total address space.
    """

    def __init__(
        self,
        banksize: str,
        bankid: int = 0,
        assoc: int = 16,
        tag_latency: int = 3,
        data_latency: int = 3,
        response_latency: int = 0,
        mshrs: int = 3,
        tgts_per_mshr: int = 1,
        writeback_clean: bool = False,
        clusivity: Clusivity = "mostly_incl",
        warmup_percentage: int = 100,
        PrefetcherCls: Type[BasePrefetcher] = StridePrefetcher,
    ):
        super().__init__()
        self.size = banksize
        self.assoc = assoc
        self.tag_latency = tag_latency
        self.data_latency = data_latency
        self.response_latency = response_latency
        self.mshrs = mshrs
        self.tgts_per_mshr = tgts_per_mshr
        self.writeback_clean = writeback_clean
        self.clusivity = clusivity
        self.prefetcher = PrefetcherCls()
        self.addr_ranges = AddrRange(
            0x00000000 + bankid * 0x40000,
            0x00000000 + (bankid + 1) * 0x40000 - 1,
        )  # Example address range per bank
        self.warmup_percentage = warmup_percentage


class L1PrivateL2SharedCacheHierarchy(AbstractClassicCacheHierarchy):
    def __init__(self, l1i_size: str, l1d_size: str, l2_size: str) -> None:
        AbstractClassicCacheHierarchy.__init__(self=self)
        self.membus = SystemXBar(width=64)
        self._l1i_size = l1i_size
        self._l1d_size = l1d_size
        self._l2_size = l2_size

    def get_mem_side_port(self) -> Port:
        return self.membus.mem_side_ports

    def get_cpu_side_port(self) -> Port:
        return self.membus.cpu_side_ports

    def incorporate_cache(self, board: AbstractBoard) -> None:
        # Set up the system port for functional access from the simulator.
        board.connect_system_port(self.membus.cpu_side_ports)

        for cntr in board.get_memory().get_memory_controllers():
            cntr.port = self.membus.mem_side_ports

        self.l1icaches = [
            L1Icache(size=self._l1i_size)
            for i in range(board.get_processor().get_num_cores())
        ]

        self.l1dcaches = [
            L1Dcache(size=self._l1d_size)
            for i in range(board.get_processor().get_num_cores())
        ]

        # self.l2cache = L2cache(size=self._l2_size)
        self.l2caches = [
            L2CacheBank(banksize=self._l2_size, bankid=i) for i in range(3)
        ]

        cpu_side = [bank.cpu_side for bank in self.l2caches]
        mem_side = [bank.mem_side for bank in self.l2caches]

        self.l2XBar = L2XBar()

        for i, cpu in enumerate(board.get_processor().get_cores()):

            cpu.connect_icache(self.l1icaches[i].cpu_side)
            cpu.connect_dcache(self.l1dcaches[i].cpu_side)

            self.l1icaches[i].mem_side = self.l2XBar.cpu_side_ports
            self.l1dcaches[i].mem_side = self.l2XBar.cpu_side_ports

            int_req_port = self.membus.mem_side_ports
            int_resp_port = self.membus.cpu_side_ports
            cpu.connect_interrupt(int_req_port, int_resp_port)

        # self.l2XBar.mem_side_ports = self.l2cache.cpu_side
        self.l2XBar.mem_side_ports = cpu_side

        # self.membus.cpu_side_ports = self.l2cache.mem_side
        self.membus.cpu_side_ports = mem_side
