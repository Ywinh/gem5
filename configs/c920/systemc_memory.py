"""
SystemC-backed memory systems for C920 validation and bridge timing studies.
"""

from typing import (
    List,
    Sequence,
    Tuple,
)

from m5.objects import (
    AddrRange,
    C920TlmPrintMem,
    C920TlmSimpleMem,
    Gem5ToTlmBridge64,
    MemCtrl,
    MemInterface,
    Port,
    Root,
    SimpleMemory,
    SystemC_Kernel,
)
from m5.util.convert import toMemorySize

from gem5.components.boards.abstract_board import AbstractBoard
from gem5.components.memory.abstract_memory_system import AbstractMemorySystem
from gem5.utils.override import overrides


class _C920SystemcMemoryBase(AbstractMemorySystem):
    """
    Common glue for gem5->TLM bridge based memories used by the C920 configs.

    A tiny gem5 SimpleMemory is kept unconnected so SE mode still has a physmem
    object and a physical page pool. The actual memory contents live only in
    the SystemC target; timing and functional traffic both go through the
    bridge into that single storage instance.
    """

    def __init__(self, size: str, target) -> None:
        super().__init__()

        self._size = toMemorySize(size)
        self._mem_range = None

        self.bridge = Gem5ToTlmBridge64()
        self.target = target
        self.backing = SimpleMemory(latency="1ps", bandwidth="1TiB/s")

        self.bridge.tlm = self.target.tlm

    @overrides(AbstractMemorySystem)
    def _pre_instantiate(self, root: Root) -> None:
        root.systemc_kernel = SystemC_Kernel()

    @overrides(AbstractMemorySystem)
    def incorporate_memory(self, board: AbstractBoard) -> None:
        pass

    @overrides(AbstractMemorySystem)
    def get_mem_ports(self) -> Sequence[Tuple[AddrRange, Port]]:
        if self._mem_range is None:
            raise Exception(
                "Memory range must be set before requesting ports."
            )

        return [(self._mem_range, self.bridge.gem5)]

    @overrides(AbstractMemorySystem)
    def get_memory_controllers(self) -> List[MemCtrl]:
        return [self.backing]

    @overrides(AbstractMemorySystem)
    def get_mem_interfaces(self) -> List[MemInterface]:
        return []

    @overrides(AbstractMemorySystem)
    def get_size(self) -> int:
        return self._size

    @overrides(AbstractMemorySystem)
    def set_memory_range(self, ranges: List[AddrRange]) -> None:
        if len(ranges) != 1 or ranges[0].size() != self._size:
            raise Exception(
                "C920 SystemC memory requires a single range matching the "
                "configured memory size."
            )

        self._mem_range = ranges[0]
        self.bridge.addr_ranges = [self._mem_range]
        self.backing.range = self._mem_range

        if hasattr(self.target, "range"):
            self.target.range = self._mem_range

    @overrides(AbstractMemorySystem)
    def get_uninterleaved_range(self) -> List[AddrRange]:
        if self._mem_range is None:
            raise Exception("Memory range must be set before querying ranges.")

        return [self._mem_range]


class C920SystemcPrintMemory(_C920SystemcMemoryBase):
    """
    Print every bridged request while mirroring data into gem5 physmem.
    """

    def __init__(self, size: str = "1GiB") -> None:
        super().__init__(size=size, target=C920TlmPrintMem())


class C920SystemcSimpleMemory(_C920SystemcMemoryBase):
    """
    SystemC memory with SimpleMemory-like timing controls for bridge studies.
    """

    def __init__(
        self,
        size: str = "1GiB",
        latency: str = "30ns",
        latency_var: str = "0ns",
        bandwidth: str = "12.8GiB/s",
    ) -> None:
        super().__init__(
            size=size,
            target=C920TlmSimpleMem(
                latency=latency,
                latency_var=latency_var,
                bandwidth=bandwidth,
            ),
        )
