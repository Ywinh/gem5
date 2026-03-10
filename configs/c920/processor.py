"""
XuanTie C920 Processor wrapper for gem5 stdlib.
Supports 1-4 cores (C910/C920MP supports 1~4 cores per cluster).
"""

from cpu import C920Core

from gem5.components.processors.base_cpu_processor import BaseCPUProcessor
from gem5.components.processors.cpu_types import CPUTypes


class C920Processor(BaseCPUProcessor):

    def __init__(self, num_cores: int = 1) -> None:
        self._cpu_type = CPUTypes.O3
        super().__init__(cores=[C920Core(core_id=i) for i in range(num_cores)])
