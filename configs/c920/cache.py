"""
XuanTie C920 Cache hierarchy configuration for gem5 classic caches.

Architecture details (Manual Chapter 7):

L1 I-Cache (Section 7.2):
  - 64KB, 2-way set-associative, 64B line
  - VIPT (gem5 classic cache is effectively PIPT, acceptable approximation)
  - 128-bit fetch interface
  - I-Cache prefetcher (MHINT.IPLD), modeled as next-line prefetch

L1 D-Cache (Section 7.3):
  - 64KB, 2-way set-associative, 64B line
  - PIPT
  - MESI coherence (classic cache uses a simplified snooping protocol)
  - 8 stride prefetchers (Section 7.5.2, stride <= 32 cachelines)
  - Store write-allocate with configurable write-no-allocate (MHINT.AMR)

L2 Cache (Section 7.4):
  - 512KB (user-selected), 16-way set-associative, 64B line
  - PIPT
  - Inclusive of L1 D-Cache
  - MOESI coherence (classic cache approximation)
  - L2 prefetcher present (Section 7.5.4)
  - Configurable TAG/DATA RAM latency (Section 7.4.4)

Load-to-use latency:
  Manual states cacheable LOAD >= 3 cycles.  In gem5 O3CPU this is
  composed of: cache tag_latency + data_latency (parallel or sequential)
  + pipeline stage delays.  We set L1D tag=2, data=2 (parallel) so
  that the total through the cache is ~2 cycles, with the remaining
  cycle(s) coming from issue-to-execute pipeline delay.

Default sources:
  BasePrefetcher    -> src/mem/cache/prefetch/Prefetcher.py
  QueuedPrefetcher  -> src/mem/cache/prefetch/Prefetcher.py
  TaggedPrefetcher  -> src/mem/cache/prefetch/Prefetcher.py
  StridePrefetcher  -> src/mem/cache/prefetch/Prefetcher.py
  BaseCache / Cache -> src/mem/cache/Cache.py
  WriteAllocator    -> src/mem/cache/Cache.py
"""

from m5.objects import *

# ===========================================================================
# Prefetchers
# ===========================================================================


class C920_ICachePrefetcher(TaggedPrefetcher):
    """
    Next-line prefetcher for I-Cache (Section 7.5.1, MHINT.IPLD).

    TaggedPrefetcher adds:
      degree = 2  (number of prefetches to generate)

    QueuedPrefetcher defaults:
      latency     = 1
      queue_size  = 32
      max_prefetch_requests_with_pending_translation = 32
      queue_squash = True
      queue_filter = True
      cache_snoop  = False
      tag_prefetch = True
      throttle_control_percentage = 0

    BasePrefetcher defaults:
      block_size           = Parent.cache_line_size
      on_miss              = False
      on_read              = True
      on_write             = True
      on_data              = True
      on_inst              = True
      prefetch_on_access   = False
      prefetch_on_pf_hit   = True
      use_virtual_addresses = False
      page_bytes           = "4KiB"
    """

    # --- BasePrefetcher ---
    on_miss = True  # only prefetch on miss [default: False]
    on_read = False  # notify on reads [default: True]
    on_write = False  # I-Cache is read-only [default: True]
    on_data = False  # not for data accesses [default: True]
    on_inst = True  # for instruction accesses [default: True]
    prefetch_on_access = (
        False  # only on miss, not every access [default: False]
    )
    prefetch_on_pf_hit = False  # no cascade on prefetch-hit [default: True]
    use_virtual_addresses = False  # use physical addresses [default: False]

    # --- QueuedPrefetcher ---
    latency = 1  # prefetch generation latency [default: 1]
    queue_size = 32  # max queued prefetches [default: 32]
    max_prefetch_requests_with_pending_translation = 32  # [default: 32]
    queue_squash = True  # squash on demand access [default: True]
    queue_filter = True  # filter redundant prefetches [default: True]
    cache_snoop = False  # no cache snooping [default: False]
    tag_prefetch = True  # tag with generating PC [default: True]
    throttle_control_percentage = 0  # no throttle [default: 0]

    # --- TaggedPrefetcher ---
    degree = 1  # next-line: 1 prefetch per trigger [default: 2]


class C920_DCachePrefetcher(StridePrefetcher):
    """
    Stride prefetcher for D-Cache (Section 7.5.2).

    Hardware has 8 stride prefetchers with stride <= 32 cachelines.
    gem5 StridePrefetcher models a single stride table; we configure it
    to approximate the hardware behavior.

    StridePrefetcher adds:
      on_inst                  = False  (overrides base default True)
      confidence_counter_bits  = 3
      initial_confidence       = 4
      confidence_threshold     = 50
      use_requestor_id         = True
      use_cache_line_address   = True
      degree                   = 4

    QueuedPrefetcher defaults: (same as above)
    BasePrefetcher defaults:   (same as above)
    """

    # --- BasePrefetcher ---
    on_miss = True  # trigger on D-Cache miss [default: False]
    on_read = True  # notify on reads [default: True]
    on_write = True  # notify on writes [default: True]
    on_data = True  # for data accesses [default: True]
    on_inst = False  # not for instructions [StridePrefetcher default: False]
    prefetch_on_access = (
        True  # also prefetch on hits (aggressive) [default: False]
    )
    prefetch_on_pf_hit = False  # no cascade on prefetch-hit [default: True]
    use_virtual_addresses = False  # use physical addresses [default: False]

    # --- QueuedPrefetcher ---
    latency = 1  # [default: 1]
    queue_size = 16  # moderate queue depth [default: 32]
    max_prefetch_requests_with_pending_translation = 32  # [default: 32]
    queue_squash = True  # [default: True]
    queue_filter = True  # [default: True]
    cache_snoop = False  # [default: False]
    tag_prefetch = True  # [default: True]
    throttle_control_percentage = 0  # [default: 0]

    # --- StridePrefetcher ---
    degree = 4  # 4 prefetches per trigger [default: 4]
    confidence_counter_bits = 3  # 3-bit confidence counter [default: 3]
    initial_confidence = 4  # starting confidence [default: 4]
    confidence_threshold = 50  # threshold to generate prefetch [default: 50]
    use_requestor_id = True  # per-requestor history [default: True]
    use_cache_line_address = (
        True  # operate on cacheline addresses [default: True]
    )


class C920_L2Prefetcher(StridePrefetcher):
    """
    L2 prefetcher (Section 7.5.4).
    Configured conservatively to avoid excessive bandwidth usage.
    """

    # --- BasePrefetcher ---
    on_miss = True  # trigger on L2 miss [default: False]
    on_read = True  # [default: True]
    on_write = False  # no prefetch on writes to L2 [default: True]
    on_data = True  # [default: True]
    on_inst = False  # [StridePrefetcher default: False]
    prefetch_on_access = True  # also on hits [default: False]
    prefetch_on_pf_hit = False  # [default: True]
    use_virtual_addresses = False  # [default: False]

    # --- QueuedPrefetcher ---
    latency = 1  # [default: 1]
    queue_size = 8  # smaller queue for L2 [default: 32]
    max_prefetch_requests_with_pending_translation = 32  # [default: 32]
    queue_squash = True  # [default: True]
    queue_filter = True  # [default: True]
    cache_snoop = False  # [default: False]
    tag_prefetch = True  # [default: True]
    throttle_control_percentage = 0  # [default: 0]

    # --- StridePrefetcher ---
    degree = 2  # conservative: 2 prefetches [default: 4]
    confidence_counter_bits = 3  # [default: 3]
    initial_confidence = 4  # [default: 4]
    confidence_threshold = 50  # [default: 50]
    use_requestor_id = True  # [default: True]
    use_cache_line_address = True  # [default: True]


# ===========================================================================
# Caches
#
# BaseCache defaults (src/mem/cache/Cache.py):
#   size               = (required)
#   assoc              = (required)
#   tag_latency        = (required)
#   data_latency       = (required)
#   response_latency   = (required)
#   warmup_percentage  = 0
#   max_miss_count     = 0
#   mshrs              = (required)
#   demand_mshr_reserve = 1
#   tgts_per_mshr      = (required)
#   write_buffers      = 8
#   is_read_only       = False
#   prefetcher         = NULL
#   tags               = BaseSetAssoc()
#   replacement_policy = LRURP()
#   partitioning_manager = NULL
#   compressor         = NULL
#   replace_expansions = True
#   move_contractions  = True
#   sequential_access  = False
#   addr_ranges        = [AllMemory]
#   writeback_clean    = False
#   clusivity          = "mostly_incl"
#   write_allocator    = NULL
# ===========================================================================


class C920_L1ICache(Cache):
    """
    L1 Instruction Cache: 64KB, 2-way, 64B line (§7.2).
    Tag and data accessed in parallel (sequential_access=False).
    """

    def __init__(self, size="32KiB"):
        super().__init__()

        # --- Capacity ---
        self.size = size  # C920: 32KB [required]
        self.assoc = 2  # C920: 2-way (§7.2.1) [required]

        # --- Latency ---
        self.tag_latency = 1  # 1-cycle tag lookup [required]
        self.data_latency = 1  # 1-cycle data access [required]
        self.response_latency = 1  # 1-cycle miss return path [required]
        self.sequential_access = False  # parallel tag+data [default: False]

        # --- MSHRs ---
        self.mshrs = 4  # max outstanding misses [required]
        self.demand_mshr_reserve = 1  # reserved for demand [default: 1]
        self.tgts_per_mshr = 8  # targets per MSHR [required]
        self.write_buffers = 8  # write buffer entries [default: 8]

        # --- Behavior ---
        self.is_read_only = True  # I-Cache is read-only [default: False]
        self.writeback_clean = True  # writeback clean to L2 [default: False]
        self.clusivity = "mostly_incl"  # inclusive [default: "mostly_incl"]

        # --- Replacement ---
        self.replacement_policy = (
            FIFORP()
        )  # LRU replacement [default: LRURP()]
        self.tags = (
            BaseSetAssoc()
        )  # set-associative tags [default: BaseSetAssoc()]

        # --- Prefetcher ---
        self.prefetcher = C920_ICachePrefetcher()

        # --- Unused/default ---
        self.warmup_percentage = 0  # [default: 0]
        self.max_miss_count = 0  # [default: 0]
        self.compressor = NULL  # no compression [default: NULL]
        self.replace_expansions = True  # [default: True]
        self.move_contractions = True  # [default: True]
        self.partitioning_manager = NULL  # [default: NULL]
        self.write_allocator = (
            NULL  # read-only, not applicable [default: NULL]
        )


class C920_L1DCache(Cache):
    """
    L1 Data Cache: 64KB, 2-way, 64B line (§7.3).

    Load-to-use >= 3 cycles in total pipeline path.
    Cache access itself is max(tag, data) = 2 cycles effective
    (parallel), plus pipeline stage delays from O3CPU.
    """

    def __init__(self, size="32KiB"):
        super().__init__()

        # --- Capacity ---
        self.size = size  # C920: 32KB [required]
        self.assoc = 2  # C920: 2-way (§7.3.1) [required]

        # --- Latency ---
        self.tag_latency = 2  # 2-cycle tag lookup [required]
        self.data_latency = 2  # 2-cycle data access [required]
        self.response_latency = 1  # 1-cycle miss return path [required]
        self.sequential_access = False  # parallel tag+data [default: False]

        # --- MSHRs ---
        self.mshrs = 8  # max outstanding misses [required]
        self.demand_mshr_reserve = 1  # reserved for demand [default: 1]
        self.tgts_per_mshr = 8  # targets per MSHR [required]
        self.write_buffers = 16  # 16 write buffer entries [default: 8]

        # --- Behavior ---
        self.is_read_only = False  # D-Cache is read-write [default: False]
        self.writeback_clean = True  # writeback clean to L2 [default: False]
        self.clusivity = "mostly_incl"  # inclusive [default: "mostly_incl"]

        # --- Replacement ---
        self.replacement_policy = (
            FIFORP()
        )  # LRU replacement [default: LRURP()]
        self.tags = (
            BaseSetAssoc()
        )  # set-associative tags [default: BaseSetAssoc()]

        # --- Prefetcher ---
        self.prefetcher = C920_DCachePrefetcher()

        # --- Unused/default ---
        self.warmup_percentage = 0  # [default: 0]
        self.max_miss_count = 0  # [default: 0]
        self.compressor = NULL  # no compression [default: NULL]
        self.replace_expansions = True  # [default: True]
        self.move_contractions = True  # [default: True]
        self.partitioning_manager = NULL  # [default: NULL]
        self.write_allocator = (
            NULL  # no streaming write optimization [default: NULL]
        )


class C920_L2Cache(Cache):
    """
    L2 Cache: 512KB, 16-way, 64B line (§7.4).

    Inclusive of L1 D-Cache (§7.4.1).
    TAG RAM latency ~3 cycles, DATA RAM latency ~5 cycles (§7.4.4).
    Sequential access (tag-then-data) typical for large L2.
    """

    def __init__(self, size="256KiB"):
        super().__init__()

        # --- Capacity ---
        self.size = size  # C920: 256KB (user selected) [required]
        self.assoc = 16  # C920: 16-way (§7.4.1) [required]

        # --- Latency ---
        self.tag_latency = 3  # TAG RAM ~3 cycles (§7.4.4) [required]
        self.data_latency = 5  # DATA RAM ~5 cycles (§7.4.4) [required]
        self.response_latency = 2  # 2-cycle miss return path [required]
        self.sequential_access = True  # tag-then-data for L2 [default: False]

        # --- MSHRs ---
        self.mshrs = 16  # max outstanding misses [required]
        self.demand_mshr_reserve = 1  # reserved for demand [default: 1]
        self.tgts_per_mshr = 12  # targets per MSHR [required]
        self.write_buffers = 16  # 16 write buffer entries [default: 8]

        # --- Behavior ---
        self.is_read_only = False  # L2 is read-write [default: False]
        self.writeback_clean = (
            False  # no clean writeback to memory [default: False]
        )
        self.clusivity = (
            "mostly_incl"  # inclusive of L1 D-Cache [default: "mostly_incl"]
        )

        # --- Replacement ---
        self.replacement_policy = LRURP()  # LRU replacement [default: LRURP()]
        self.tags = (
            BaseSetAssoc()
        )  # set-associative tags [default: BaseSetAssoc()]

        # --- Prefetcher ---
        self.prefetcher = C920_L2Prefetcher()

        # --- Unused/default ---
        self.warmup_percentage = 0  # [default: 0]
        self.max_miss_count = 0  # [default: 0]
        self.compressor = NULL  # no compression [default: NULL]
        self.replace_expansions = True  # [default: True]
        self.move_contractions = True  # [default: True]
        self.partitioning_manager = NULL  # [default: NULL]
        self.write_allocator = NULL  # [default: NULL]
