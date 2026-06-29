"""
XuanTie C920 cache hierarchy: Private L1I + L1D per core, shared L2.

Topology (Manual Section 7.1, 7.4):
  Core0 ─┬─ L1I (64KB) ─┐
          └─ L1D (64KB) ─┼─ L2 (512KB, shared, inclusive) ─── Memory
  Core1 ─┬─ L1I (64KB) ─┤
          └─ L1D (64KB) ─┘
"""

from typing import Optional

from cache import (
    C920_L1DCache,
    C920_L1ICache,
    C920_L2Cache,
)

from m5.objects import (
    AddrRange,
    BadAddr,
    BaseXBar,
    Cache,
    ExternalSlave,
    L2XBar,
    Port,
    SystemXBar,
)

from gem5.components.boards.abstract_board import AbstractBoard
from gem5.components.cachehierarchies.abstract_cache_hierarchy import (
    AbstractCacheHierarchy,
)
from gem5.components.cachehierarchies.classic.abstract_classic_cache_hierarchy import (
    AbstractClassicCacheHierarchy,
)
from gem5.isas import ISA
from gem5.utils.override import *


class C920CacheHierarchy(AbstractClassicCacheHierarchy):
    """
    Private L1 I/D caches + shared inclusive L2.
    """

    def _get_default_membus(self) -> SystemXBar:
        membus = SystemXBar(width=64)
        membus.badaddr_responder = BadAddr()
        membus.default = membus.badaddr_responder.pio
        return membus

    def __init__(
        self,
        l1i_size: str = "64KiB",
        l1d_size: str = "64KiB",
        l2_size: str = "512KiB",
        membus: Optional[BaseXBar] = None,
        fifo_port_data: Optional[str] = "transactor",
        fifo_base: int = 0x0A082000,
        fifo_size: int = 0x88,
    ) -> None:
        super().__init__()
        self.membus = membus if membus else self._get_default_membus()
        self._l1i_size = l1i_size
        self._l1d_size = l1d_size
        self._l2_size = l2_size
        self._fifo_port_data = fifo_port_data
        self._fifo_range = AddrRange(fifo_base, size=fifo_size)

    @overrides(AbstractClassicCacheHierarchy)
    def get_mem_side_port(self) -> Port:
        return self.membus.mem_side_ports

    @overrides(AbstractClassicCacheHierarchy)
    def get_cpu_side_port(self) -> Port:
        return self.membus.cpu_side_ports

    @overrides(AbstractCacheHierarchy)
    def incorporate_cache(self, board: AbstractBoard) -> None:
        board.connect_system_port(self.membus.cpu_side_ports)

        for _, port in board.get_mem_ports():
            self.membus.mem_side_ports = port

        if self._fifo_port_data is not None:
            self.fifo_tlm = ExternalSlave(
                port_type="tlm_slave",
                port_data=self._fifo_port_data,
            )
            self.fifo_tlm.addr_ranges = [self._fifo_range]
            self.membus.mem_side_ports = self.fifo_tlm.port

        self.l2bus = L2XBar()

        self.l2cache = C920_L2Cache(size=self._l2_size)
        self.l2cache.cpu_side = self.l2bus.mem_side_ports
        self.l2cache.mem_side = self.membus.cpu_side_ports

        num_cores = board.get_processor().get_num_cores()

        self.l1icaches = [
            C920_L1ICache(size=self._l1i_size) for _ in range(num_cores)
        ]
        self.l1dcaches = [
            C920_L1DCache(size=self._l1d_size) for _ in range(num_cores)
        ]

        if board.has_coherent_io():
            self._setup_io_cache(board)

        for i, cpu in enumerate(board.get_processor().get_cores()):
            cpu.connect_icache(self.l1icaches[i].cpu_side)
            cpu.connect_dcache(self.l1dcaches[i].cpu_side)

            self.l1icaches[i].mem_side = self.l2bus.cpu_side_ports
            self.l1dcaches[i].mem_side = self.l2bus.cpu_side_ports

            if board.get_processor().get_isa() == ISA.X86:
                int_req_port = self.membus.mem_side_ports
                int_resp_port = self.membus.cpu_side_ports
                cpu.connect_interrupt(int_req_port, int_resp_port)
            else:
                cpu.connect_interrupt()

    def _setup_io_cache(self, board: AbstractBoard) -> None:
        self.iocache = Cache(
            assoc=8,
            tag_latency=50,
            data_latency=50,
            response_latency=50,
            mshrs=20,
            size="1KiB",
            tgts_per_mshr=12,
            addr_ranges=board.mem_ranges,
        )
        self.iocache.mem_side = self.membus.cpu_side_ports
        self.iocache.cpu_side = board.get_mem_side_coherent_io_port()
