from bpu import MyBranchPredictor
from fu import C906FUPool

import m5
from m5.objects import *
from m5.objects import BaseMinorCPU
from m5.params import *

from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.isas import ISA


class Custom906CPU(RiscvMinorCPU):
    # def __init__(self):
    #     super().__init__()
    # todo：写一个修改了哪些参数，为什么修改的说明

    # buffersize 只要 >= 2 都可以接受
    fetch1FetchLimit = 1
    decodeInputWidth = 2
    executeInputWidth = 2
    executeIssueLimit = 1
    executeMemoryIssueLimit = 1
    executeCommitLimit = 1
    executeMemoryCommitLimit = 1
    executeAllowEarlyMemoryIssue = False
    # lsq?

    branchPred = MyBranchPredictor()
    executeFuncUnits = C906FUPool()


class C906Core(BaseCPUCore):
    def __init__(
        self,
        core_id,
    ):
        super().__init__(core=Custom906CPU(cpu_id=core_id), isa=ISA.RISCV)
        self.core.isa[0].enable_rvv = False
