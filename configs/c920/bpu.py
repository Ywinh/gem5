"""
XuanTie C920 Branch Predictor configuration for gem5 O3CPU.

Architecture details (Manual §7.2 + C910 RTL verification):
  - BI-MODE direction predictor, 64Kb total storage  (§7.2.4)
  - BTB: 1024 entries, 4-way, 10-bit tag, 20-bit target (RTL: ct_ifu_btb.v)
  - BHT: Pre array 1024×64 (direction), Sel array 128×16 (choice), 22-bit GHR
  - RAS: 12 IFU entries + 6 RTU entries (RTL: ct_ifu_ras.v)
  - Indirect BTB: 256 entries, direct-mapped (RTL: ct_ifu_ind_btb.v)
  - L0 BTB: 16 entries fully-assoc (RTL: ct_ifu_l0_btb.v, no gem5 equivalent)

gem5 BiModeBP mapping:
  Pre array (1024×64 bits) holds taken + not-taken direction tables:
    1024 × 64 / 2 tables / 2-bit counters = 16384 entries per direction table
    → globalPredictorSize = 16384
  Sel array (128×16 bits) holds choice table:
    128 × 16 / 2-bit counters = 1024 entries
    → choicePredictorSize = 1024

Default sources:
  SimpleBTB         -> src/cpu/pred/BranchPredictor.py : SimpleBTB
  ReturnAddrStack   -> src/cpu/pred/BranchPredictor.py : ReturnAddrStack
  SimpleIndirectPredictor -> src/cpu/pred/BranchPredictor.py
  BiModeBP          -> src/cpu/pred/BranchPredictor.py : BiModeBP
  BranchPredictor   -> src/cpu/pred/BranchPredictor.py : BranchPredictor (abstract base)
"""

from m5.objects import *


# ---------------------------------------------------------------------------
# BTB (Branch Target Buffer)
# RTL verified: ct_ifu_btb.v
#   - 2 banks × 512 entries = 1024 total
#   - 4-way set-associative (way0-way3)
#   - Tag[9:0] = {vpc[19:13], vpc[2:0]}  → 10-bit tag
#   - target_pc[19:0]                     → 20-bit target
#   - way_pred[1:0]                       → 2-bit way predictor
#
# SimpleBTB defaults (src/cpu/pred/BranchPredictor.py):
#   numEntries     = 4096
#   tagBits        = 16
#   instShiftAmt   = Parent.instShiftAmt
#   associativity  = 1
#   btbReplPolicy  = LRURP()
#   btbIndexingPolicy = BTBSetAssociative(...)
# ---------------------------------------------------------------------------
class C920_BTB(SimpleBTB):
    numEntries = 1024  # RTL: 2 banks × 512 = 1024 [default: 4096]
    tagBits = 10  # RTL: Tag[9:0] = 10 bits [default: 16]
    instShiftAmt = (
        1  # RV64C: min 2-byte instructions -> shift 1 [default: Parent]
    )
    associativity = 4  # RTL: way0-way3 = 4-way [default: 1]
    btbReplPolicy = LRURP()  # LRU replacement [default: LRURP()]


# ---------------------------------------------------------------------------
# Branch Direction Predictor (BI-MODE)
# RTL verified: ct_ifu_bht.v, ct_ifu_bht_pre_array.v, ct_ifu_bht_sel_array.v
#   - Pre array: ct_spsram_1024x64 → 1024 × 64-bit rows
#     Contains both taken & not-taken direction tables
#     Effective entries: 1024 × 64 / 2 / 2-bit = 16384 per direction table
#   - Sel array: ct_spsram_128x16 → 128 × 16-bit rows
#     Choice predictor: 128 × 16 / 2-bit = 1024 entries
#   - GHR: vghr[21:0] = 22-bit global history register
#   - 2-bit saturating counters
#   - Write buffer: 4 entries for update coalescing
#
# BiModeBP defaults (src/cpu/pred/BranchPredictor.py):
#   globalPredictorSize = 8192
#   globalCtrBits       = 2
#   choicePredictorSize = 8192
#   choiceCtrBits       = 2
#
# BranchPredictor base defaults:
#   instShiftAmt         = 0
#   speculativeHistUpdate = True
#   requiresBTBHit       = False
#   btb                  = SimpleBTB()
#   ras                  = ReturnAddrStack()
#   indirectBranchPred   = SimpleIndirectPredictor()
#   takenOnlyHistory     = False
#
# ReturnAddrStack defaults:
#   numEntries = 16
#
# SimpleIndirectPredictor defaults:
#   indirectHashGHR      = True
#   indirectHashTargets  = True
#   indirectSets         = 256
#   indirectWays         = 2
#   indirectTagSize      = 16
#   indirectPathLength   = 3
#   speculativePathLength = 256
#   indirectGHRBits      = 13
#   instShiftAmt         = Parent.instShiftAmt
# ---------------------------------------------------------------------------
class C920_BranchPredictor(BiModeBP):
    # --- BiModeBP-specific (RTL verified) ---
    globalPredictorSize = (
        16384  # RTL: 1024×64 pre array / 2 / 2bit = 16384 [default: 8192]
    )
    globalCtrBits = 2  # RTL: 2-bit saturating counters [default: 2]
    choicePredictorSize = (
        1024  # RTL: 128×16 sel array / 2bit = 1024 [default: 8192]
    )
    choiceCtrBits = 2  # RTL: 2-bit saturating counters [default: 2]

    # --- BranchPredictor base ---
    instShiftAmt = 1  # RV64C min 2-byte insn -> shift 1 [default: 0]
    speculativeHistUpdate = True  # speculative GHR update [default: True]
    requiresBTBHit = False  # no BTB-hit requirement [default: False]
    takenOnlyHistory = False  # use all branches in GHR [default: False]

    # --- BTB (RTL verified) ---
    btb = C920_BTB()

    # --- RAS (RTL verified: ct_ifu_ras.v) ---
    # RTL: 12 IFU entries (speculative) + 6 RTU entries (architectural recovery)
    # gem5 RAS models the speculative part; recovery is handled internally.
    ras = ReturnAddrStack(
        numEntries=12,  # RTL: 12 IFU entries [default: 16]
    )

    # --- Indirect Branch Predictor (RTL verified: ct_ifu_ind_btb.v) ---
    # RTL: ct_spsram_256x23 → 256 entries, 8-bit index, direct-mapped
    #   Data format: {vld, priv_mode[1:0], target[19:0]} = 23 bits
    #   Index hash uses path history (4 × 8-bit path registers)
    indirectBranchPred = SimpleIndirectPredictor(
        indirectHashGHR=True,  # RTL uses GHR hashing [default: True]
        indirectHashTargets=True,  # RTL uses path history hashing [default: True]
        indirectSets=256,  # RTL: 256 entries [default: 256]
        indirectWays=1,  # RTL: direct-mapped [default: 2]
        indirectTagSize=16,  # tag for disambiguation [default: 16]
        indirectPathLength=4,  # RTL: 4 path registers [default: 3]
        speculativePathLength=256,  # spec path buffer depth [default: 256]
        indirectGHRBits=8,  # RTL: bht_ind_btb_rtu_ghr[7:0] = 8-bit [default: 13]
    )
