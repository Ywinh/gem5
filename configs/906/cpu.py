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

    # ====================================================================
    # Fetch 配置 - 906每次取2条指令（8字节）
    # ====================================================================
    fetch1FetchLimit = 1  # 同时最多1个fetch请求

    # 关键配置：每次只fetch 8字节（2条RV32指令）
    fetch1LineSnapWidth = 8  # 按8字节对齐
    fetch1LineWidth = 8  # 每次最多fetch 8字节

    # 减小inputBuffer，避免过度缓存
    fetch2InputBufferSize = 2  # 最多缓存2个8字节line

    # ====================================================================
    # Decode/Execute 配置 - 单发射
    # ====================================================================
    decodeInputWidth = 1
    executeInputWidth = 1
    executeIssueLimit = 1
    executeMemoryIssueLimit = 1
    executeCommitLimit = 1
    executeMemoryCommitLimit = 1
    executeAllowEarlyMemoryIssue = (
        True  # 开启之后就类似non-blocking LSQ了，可以更早地发出memory指令
    )

    # ====================================================================
    # LSQ (Load-Store Queue) 配置 - 硬件906有4个store buffer
    # ====================================================================
    executeLSQStoreBufferSize = 4  # Store buffer大小：4个entries
    executeLSQMaxStoreBufferStoresPerCycle = 2  # 每周期最多2个store drain
    executeLSQRequestsQueueSize = 8  # Request queue大小
    executeLSQTransfersQueueSize = 8  # Transfer queue大小
    executeMaxAccessesInMemory = 4  # 同时在memory system中的最大访问数

    branchPred = MyBranchPredictor()
    executeFuncUnits = C906FUPool()


class C906Core(BaseCPUCore):
    def __init__(
        self,
        core_id,
    ):
        super().__init__(core=Custom906CPU(cpu_id=core_id), isa=ISA.RISCV)
        self.core.isa[0].enable_rvv = False
        self.core.isa[0].riscv_type = "RV32"
