"""
XuanTie C920 O3CPU core configuration for gem5.

Architecture summary (Manual Chapter 1-2 + C910 RTL verification):
  - RV64GCV, 9-12 stage pipeline
  - 3-issue, 8-retire, out-of-order superscalar (Manual §1.2.2)
  - IU (ALU/MULT/DIV/BJU) + FPU (FALU/FMAU/FDSU) + LSU
  - 128-bit VLEN vector unit (C920)

C910 RTL verified parameters:
  - ROB: 64 entries (ct_rtu_rob.v: entry0-63)
  - Dispatch: 4-wide in C910 (create0/1/2/3)
  - Retire: 3-wide in C910 (inst0/1/2)
  - LQ: 16 entries (ct_lsu_lq.v: parameter LQ_ENTRY=16)
  - SQ: 12 entries (ct_lsu_sq.v: parameter SQ_ENTRY=12)
  - WMB: 8 entries (ct_lsu_wmb.v: parameter WMB_ENTRY=8)
  - Issue Queues: AIQ0=8, AIQ1=8, BIQ=12, LSIQ=12, SDIQ=12, VIQ0=8, VIQ1=8
  - Physical Int Regs: 96 (ct_rtu_pst_preg.v: preg0-95)
  - Physical Vec/FP Regs: 64 (ct_rtu_pst_vreg.v: vreg0-63)
  - Physical Ereg: 32 (ct_rtu_pst_ereg.v: ereg0-31)

NOTE: C920 manual says "3-issue 8-retire" while C910 RTL shows "4-dispatch
3-retire". Pipeline widths use the C920 manual values. Structure sizes
(ROB/LQ/SQ/IQ/regs) use C910 RTL values since C920 is architecturally
similar and the manual does not specify these.

Pipeline mapping to gem5 O3CPU stages:
  IFU  (3 stages) -> fetchToDecodeDelay = 3
  IDU  (2 stages) -> decodeToRenameDelay = 2
  Rename/Dispatch  -> renameToIEWDelay = 2
  Issue/Execute    -> issueToExecuteDelay = 1
  Writeback/Commit -> iewToCommitDelay = 1
  Total: 3+2+2+1+1 = 9 stages minimum (matches manual "9~12 stages")

Default sources:
  BaseO3CPU -> src/cpu/o3/BaseO3CPU.py
"""

from bpu import C920_BranchPredictor
from fu import C920FUPool

from m5.objects import *

from gem5.components.processors.base_cpu_core import BaseCPUCore
from gem5.isas import ISA


class C920_O3CPU(RiscvO3CPU):

    # ==================================================================
    # Activity tracking
    # ==================================================================
    activity = 0  # initial activity count [default: 0]

    # ==================================================================
    # Cache port limits
    # ==================================================================
    cacheStorePorts = 200  # max store port bandwidth [default: 200]
    cacheLoadPorts = 200  # max load port bandwidth [default: 200]

    # ==================================================================
    # Pipeline stage delays (forward path)
    #
    # C920 pipeline: IFU(3) -> IDU(2) -> Rename/Dispatch(2) -> IEW(1) -> Commit(1)
    # ==================================================================
    fetchToDecodeDelay = 3  # IFU: ~3 stages [default: 1]
    decodeToRenameDelay = 2  # IDU: ~2 stages [default: 1]
    renameToIEWDelay = 2  # dispatch + IQ scheduling [default: 2]
    issueToExecuteDelay = 1  # within IEW stage [default: 1]
    iewToCommitDelay = 1  # writeback -> ROB [default: 1]
    renameToROBDelay = 1  # rename -> ROB entry alloc [default: 1]

    # ==================================================================
    # Pipeline stage delays (feedback / backward path)
    # Kept at minimum 1 cycle for OoO core.
    # ==================================================================
    decodeToFetchDelay = 1  # [default: 1]
    renameToFetchDelay = 1  # [default: 1]
    iewToFetchDelay = 1  # [default: 1]
    commitToFetchDelay = 1  # [default: 1]
    renameToDecodeDelay = 1  # [default: 1]
    iewToDecodeDelay = 1  # [default: 1]
    commitToDecodeDelay = 1  # [default: 1]
    iewToRenameDelay = 1  # [default: 1]
    commitToRenameDelay = 1  # [default: 1]
    commitToIEWDelay = 1  # [default: 1]

    # ==================================================================
    # Pipeline widths
    # Manual §1.2.2: "3发射8退休" → 3-issue, 8-retire
    # C910 RTL: 4-dispatch, 3-retire (different from C920 manual!)
    # Using C920 manual values here.
    # ==================================================================
    fetchWidth = 3  # C920 manual: 3 instructions/cycle [default: 8]
    fetchBufferSize = 16  # 128-bit fetch = 16 bytes [default: 64]
    fetchQueueSize = 16  # fetch queue depth [default: 32]

    decodeWidth = 3  # 3-wide decode [default: 8]
    renameWidth = 3  # 3-wide rename [default: 8]
    dispatchWidth = 3  # 3-wide dispatch to IQ [default: 8]
    issueWidth = 3  # 3-wide issue from IQ [default: 8]
    wbWidth = 8  # 8-wide writeback [default: 8]
    commitWidth = 8  # C920 manual: 8-wide retire [default: 8]
    squashWidth = 8  # squash bandwidth [default: 8]

    # ==================================================================
    # ROB (Reorder Buffer)
    # RTL verified: ct_rtu_rob.v has entry0-63 = 64 entries
    # IID width = 7 bits → max 128 entries possible, but only 64 instantiated
    # ==================================================================
    numRobs = 1  # single ROB [default: 1]
    numROBEntries = 64  # RTL: 64 entries [default: 192]

    # ==================================================================
    # Instruction Queue
    # RTL verified: C910 has separate IQs:
    #   AIQ0=8, AIQ1=8, BIQ=12, LSIQ=12, SDIQ=12 (scalar total=52)
    #   VIQ0=8, VIQ1=8 (vector total=16)
    # gem5 uses unified IQ → sum of scalar IQs as approximation
    # ==================================================================
    numIQEntries = 52  # RTL: scalar IQ total = 8+8+12+12+12 [default: 64]

    # ==================================================================
    # Load/Store Queue
    # RTL verified: ct_lsu_lq.v (LQ_ENTRY=16), ct_lsu_sq.v (SQ_ENTRY=12)
    # ==================================================================
    LQEntries = 16  # RTL: LQ_ENTRY = 16 [default: 32]
    SQEntries = 12  # RTL: SQ_ENTRY = 12 [default: 32]
    LSQDepCheckShift = 4  # addr shift for dep check [default: 4]
    LSQCheckLoads = True  # check loads for violations [default: True]
    store_set_clear_period = (
        250000  # clear store-set predictor [default: 250000]
    )
    LFSTSize = 1024  # last-fetched-store table [default: 1024]
    SSITSize = "1024"  # store-set ID table size [default: "1024"]
    SSITAssoc = 1  # SSIT associativity [default: 1]

    # ==================================================================
    # Physical Register File sizes
    # RTL verified:
    #   ct_rtu_pst_preg.v: preg0-95 → 96 physical int regs
    #   ct_rtu_pst_vreg.v: vreg0-63 → 64 physical vec/float regs
    #   ct_rtu_pst_ereg.v: ereg0-31 → 32 extra status regs
    #
    # gem5 requires numPhysRegs >= numROBEntries + numArchRegs.
    # RISC-V: 32 int + 32 float + 32 vec arch registers.
    #   Int:   96 >= 64 + 32 ✓
    #   Float: 64 < 64 + 32 (need padding for gem5 safety → use 96)
    #   Vec:   64 < 64 + 32 (need padding for gem5 safety → use 96)
    # Note: C910 shares float/vec in one vreg file. gem5 has separate
    # files, so we pad to avoid deadlock in worst-case all-FP workloads.
    # ==================================================================
    numPhysIntRegs = 96  # RTL: 96 pregs [default: 256]
    numPhysFloatRegs = 96  # RTL: 64 vregs, padded for gem5 [default: 256]
    numPhysVecRegs = 96  # RTL: 64 vregs, padded for gem5 [default: 256]
    numPhysVecPredRegs = 32  # predicate regs [default: 32]
    numPhysMatRegs = 2  # matrix regs [default: 2]
    numPhysCCRegs = 0  # RISC-V has no CC regs [default: 0]

    # ==================================================================
    # Functional units and branch predictor
    # ==================================================================
    fuPool = C920FUPool()
    branchPred = C920_BranchPredictor()

    # ==================================================================
    # Trap handling
    # ==================================================================
    trapLatency = 13  # trap processing latency [default: 13]
    fetchTrapLatency = 1  # fetch-side trap latency [default: 1]

    # ==================================================================
    # Communication buffers
    # ==================================================================
    backComSize = 5  # backward comm buffer depth [default: 5]
    forwardComSize = 5  # forward comm buffer depth [default: 5]

    # ==================================================================
    # SMT (Single-thread, no SMT on C920)
    # ==================================================================
    smtNumFetchingThreads = 1  # [default: 1]
    smtFetchPolicy = "RoundRobin"  # [default: "RoundRobin"]
    smtLSQPolicy = "Partitioned"  # [default: "Partitioned"]
    smtLSQThreshold = 100  # [default: 100]
    smtIQPolicy = "Partitioned"  # [default: "Partitioned"]
    smtIQThreshold = 100  # [default: 100]
    smtROBPolicy = "Partitioned"  # [default: "Partitioned"]
    smtROBThreshold = 100  # [default: 100]
    smtCommitPolicy = "RoundRobin"  # [default: "RoundRobin"]

    # ==================================================================
    # Memory model
    # ==================================================================
    needsTSO = False  # RISC-V uses RVWMO, not TSO [default: False]

    # ==================================================================
    # Load response throttling
    # ==================================================================
    recvRespThrottling = False  # no throttling [default: False]
    recvRespMaxCachelines = 1  # [default: 1]
    recvRespBufferSize = 64  # [default: 64]


class C920Core(BaseCPUCore):
    """Wraps C920_O3CPU for use with gem5 stdlib SimpleBoard."""

    def __init__(self, core_id):
        super().__init__(core=C920_O3CPU(cpu_id=core_id), isa=ISA.RISCV)
        self.core.isa[0].enable_rvv = True  # enable RVV (§1.2.2)
        self.core.isa[0].vlen = 128  # VLEN=128 bits (§4.5)
        self.core.isa[0].riscv_type = "RV32"
