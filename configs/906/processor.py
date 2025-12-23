from cpu import C906Core

from m5.util import warn

from gem5.components.boards.abstract_board import AbstractBoard
from gem5.components.boards.mem_mode import MemMode
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.utils.override import overrides


class C906Processor(BaseCPUProcessor):
    """
    A C906Processor contains a number of cores of Custom906CPU.
    """

    def __init__(
        self,
        is_fs: bool,
    ) -> None:
        self._cpu_type = CPUTypes.MINOR
        super().__init__(cores=self._create_cores(is_fs))

    def _create_cores(self, is_fs: bool):
        if is_fs:
            num_cores = 4
        else:
            num_cores = 1
        return [C906Core(core_id=i) for i in range(num_cores)]
