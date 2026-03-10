"""
XuanTie C920 Functional Unit definitions for gem5 O3CPU.

Latencies sourced from the C910/C920 User Manual (xrvm, 2025-01-24),
Chapter 3 instruction timing tables.

C920 execution units:
  IU  - ALU, MULT, DIV, BJU
  FPU - FALU, FMAU, FDSU
  LSU - Load/Store (2 ports)

With 3-issue width the FU counts are set so the pipeline is never
artificially starved.

gem5 FUDesc parameters (src/cpu/FuncUnit.py):
  opList   : list of OpDesc (opClass, opLat, pipelined, ...)
  count    : number of copies of this functional unit

gem5 OpDesc parameters:
  opClass  : operation class name (e.g. "IntAlu")
  opLat    : operation latency in cycles            [default: 1]
  pipelined: whether the FU is fully pipelined      [default: True]
"""

from m5.objects import *


# ---------------------------------------------------------------------------
# Integer ALU - 1 cycle latency (Table 3.1)
# C920 has ALU + BJU; model as 2 ALU units to allow branch + ALU in parallel
# ---------------------------------------------------------------------------
class C920_IntALU(FUDesc):
    opList = [
        OpDesc(opClass="IntAlu", opLat=1, pipelined=True),
    ]
    count = 2


# ---------------------------------------------------------------------------
# Integer Multiply / Divide (Table 3.2)
#   MUL/MULW/MULH*: 4 cycles, pipelined
#   DIV/DIVU:  3-20 cycles, NOT pipelined (use worst-case 20)
#   DIVW/DIVUW: 3-12 cycles, NOT pipelined
# ---------------------------------------------------------------------------
class C920_IntMultDiv(FUDesc):
    opList = [
        OpDesc(opClass="IntMult", opLat=4, pipelined=True),
        OpDesc(opClass="IntDiv", opLat=20, pipelined=False),
    ]
    count = 1


# ---------------------------------------------------------------------------
# Scalar Floating-Point ALU (Table 3.4 - FALU)
#   FADD.S/FSUB.S: 3 cycles
#   FP compare: 3+1 cycles (cross-domain result), model as 3
#   FP convert: 3 cycles
#   FP sign-inject/misc: 3 cycles
# ---------------------------------------------------------------------------
class C920_FP_ALU(FUDesc):
    opList = [
        OpDesc(opClass="FloatAdd", opLat=3, pipelined=True),
        OpDesc(opClass="FloatCmp", opLat=3, pipelined=True),
        OpDesc(opClass="FloatCvt", opLat=3, pipelined=True),
        OpDesc(opClass="FloatMisc", opLat=3, pipelined=True),
    ]
    count = 1


# ---------------------------------------------------------------------------
# Scalar Floating-Point Multiply / Divide / Sqrt (Table 3.4 - FMAU + FDSU)
#   FMUL.S: 4 cycles, pipelined
#   FMADD.S/FMSUB.S/FNMADD.S/FNMSUB.S: 5 cycles, pipelined
#   FDIV.S: 4-10 cycles, NOT pipelined (use worst-case 10)
#   FSQRT.S: 4-10 cycles, NOT pipelined (use worst-case 10)
# ---------------------------------------------------------------------------
class C920_FP_MultDiv(FUDesc):
    opList = [
        OpDesc(opClass="FloatMult", opLat=4, pipelined=True),
        OpDesc(opClass="FloatMultAcc", opLat=5, pipelined=True),
        OpDesc(opClass="FloatDiv", opLat=10, pipelined=False),
        OpDesc(opClass="FloatSqrt", opLat=10, pipelined=False),
    ]
    count = 1


# ---------------------------------------------------------------------------
# SIMD / Vector Unit
# C920 supports RV64V (128-bit VLEN). Exact per-instruction vector
# latency is not fully specified in the manual; use representative
# values matching scalar equivalents where possible.
# ---------------------------------------------------------------------------
class C920_SIMD(FUDesc):
    opList = [
        OpDesc(opClass="SimdAdd", opLat=1, pipelined=True),
        OpDesc(opClass="SimdAddAcc", opLat=1, pipelined=True),
        OpDesc(opClass="SimdAlu", opLat=1, pipelined=True),
        OpDesc(opClass="SimdCmp", opLat=1, pipelined=True),
        OpDesc(opClass="SimdCvt", opLat=3, pipelined=True),
        OpDesc(opClass="SimdMisc", opLat=1, pipelined=True),
        OpDesc(opClass="SimdMult", opLat=4, pipelined=True),
        OpDesc(opClass="SimdMultAcc", opLat=4, pipelined=True),
        OpDesc(opClass="SimdMatMultAcc", opLat=4, pipelined=True),
        OpDesc(opClass="SimdShift", opLat=1, pipelined=True),
        OpDesc(opClass="SimdShiftAcc", opLat=1, pipelined=True),
        OpDesc(opClass="SimdDiv", opLat=10, pipelined=False),
        OpDesc(opClass="SimdSqrt", opLat=10, pipelined=False),
        OpDesc(opClass="SimdFloatAdd", opLat=3, pipelined=True),
        OpDesc(opClass="SimdFloatAlu", opLat=3, pipelined=True),
        OpDesc(opClass="SimdFloatCmp", opLat=3, pipelined=True),
        OpDesc(opClass="SimdFloatCvt", opLat=3, pipelined=True),
        OpDesc(opClass="SimdFloatDiv", opLat=10, pipelined=False),
        OpDesc(opClass="SimdFloatMisc", opLat=3, pipelined=True),
        OpDesc(opClass="SimdFloatMult", opLat=4, pipelined=True),
        OpDesc(opClass="SimdFloatMultAcc", opLat=5, pipelined=True),
        OpDesc(opClass="SimdFloatMatMultAcc", opLat=5, pipelined=True),
        OpDesc(opClass="SimdFloatSqrt", opLat=10, pipelined=False),
        OpDesc(opClass="SimdReduceAdd", opLat=1, pipelined=True),
        OpDesc(opClass="SimdReduceAlu", opLat=1, pipelined=True),
        OpDesc(opClass="SimdReduceCmp", opLat=1, pipelined=True),
        OpDesc(opClass="SimdFloatReduceAdd", opLat=3, pipelined=True),
        OpDesc(opClass="SimdFloatReduceCmp", opLat=3, pipelined=True),
        OpDesc(opClass="SimdExt", opLat=1, pipelined=True),
        OpDesc(opClass="SimdFloatExt", opLat=1, pipelined=True),
        OpDesc(opClass="SimdConfig", opLat=1, pipelined=True),
        OpDesc(opClass="SimdAes", opLat=1, pipelined=True),
        OpDesc(opClass="SimdAesMix", opLat=1, pipelined=True),
        OpDesc(opClass="SimdSha1Hash", opLat=1, pipelined=True),
        OpDesc(opClass="SimdSha1Hash2", opLat=1, pipelined=True),
        OpDesc(opClass="SimdSha256Hash", opLat=1, pipelined=True),
        OpDesc(opClass="SimdSha256Hash2", opLat=1, pipelined=True),
        OpDesc(opClass="SimdShaSigma2", opLat=1, pipelined=True),
        OpDesc(opClass="SimdShaSigma3", opLat=1, pipelined=True),
    ]
    count = 1


class C920_PredALU(FUDesc):
    opList = [
        OpDesc(opClass="SimdPredAlu", opLat=1, pipelined=True),
    ]
    count = 1


class C920_Matrix(FUDesc):
    opList = [
        OpDesc(opClass="Matrix", opLat=1, pipelined=True),
        OpDesc(opClass="MatrixMov", opLat=1, pipelined=True),
        OpDesc(opClass="MatrixOP", opLat=1, pipelined=True),
    ]
    count = 1


# ---------------------------------------------------------------------------
# Load / Store ports
# C920 LSU supports 1 load + 1 store per cycle (Section 2.2.4).
# Memory op latency in the FU is 1 cycle; actual cache latency is
# handled by the cache model separately.
# ---------------------------------------------------------------------------
class C920_ReadPort(FUDesc):
    opList = [
        OpDesc(opClass="MemRead", opLat=1, pipelined=True),
        OpDesc(opClass="FloatMemRead", opLat=1, pipelined=True),
        OpDesc(opClass="SimdUnitStrideLoad", opLat=1, pipelined=True),
        OpDesc(opClass="SimdUnitStrideMaskLoad", opLat=1, pipelined=True),
        OpDesc(opClass="SimdUnitStrideSegmentedLoad", opLat=1, pipelined=True),
        OpDesc(opClass="SimdStridedLoad", opLat=1, pipelined=True),
        OpDesc(opClass="SimdIndexedLoad", opLat=1, pipelined=True),
        OpDesc(
            opClass="SimdUnitStrideFaultOnlyFirstLoad",
            opLat=1,
            pipelined=True,
        ),
        OpDesc(
            opClass="SimdUnitStrideSegmentedFaultOnlyFirstLoad",
            opLat=1,
            pipelined=True,
        ),
        OpDesc(opClass="SimdWholeRegisterLoad", opLat=1, pipelined=True),
        OpDesc(opClass="SimdStrideSegmentedLoad", opLat=1, pipelined=True),
    ]
    count = 1


class C920_WritePort(FUDesc):
    opList = [
        OpDesc(opClass="MemWrite", opLat=1, pipelined=True),
        OpDesc(opClass="FloatMemWrite", opLat=1, pipelined=True),
        OpDesc(opClass="SimdUnitStrideStore", opLat=1, pipelined=True),
        OpDesc(opClass="SimdUnitStrideMaskStore", opLat=1, pipelined=True),
        OpDesc(
            opClass="SimdUnitStrideSegmentedStore", opLat=1, pipelined=True
        ),
        OpDesc(opClass="SimdStridedStore", opLat=1, pipelined=True),
        OpDesc(opClass="SimdIndexedStore", opLat=1, pipelined=True),
        OpDesc(opClass="SimdWholeRegisterStore", opLat=1, pipelined=True),
        OpDesc(opClass="SimdStrideSegmentedStore", opLat=1, pipelined=True),
    ]
    count = 1


# ---------------------------------------------------------------------------
# IPR (Internal Processor Register) access
# ---------------------------------------------------------------------------
class C920_IprPort(FUDesc):
    opList = [
        OpDesc(opClass="IprAccess", opLat=3, pipelined=False),
    ]
    count = 1


# ---------------------------------------------------------------------------
# Aggregate FU Pool
# ---------------------------------------------------------------------------
class C920FUPool(FUPool):
    FUList = [
        C920_IntALU(),  # 2x integer ALU (includes BJU)
        C920_IntMultDiv(),  # 1x integer multiply/divide
        C920_FP_ALU(),  # 1x FP add/cmp/cvt (FALU)
        C920_FP_MultDiv(),  # 1x FP mul/div/sqrt (FMAU+FDSU)
        C920_SIMD(),  # 1x vector/SIMD unit
        C920_PredALU(),  # 1x predicate ALU
        C920_Matrix(),  # 1x matrix unit
        C920_ReadPort(),  # 1x load port
        C920_WritePort(),  # 1x store port
        C920_IprPort(),  # 1x IPR access port
    ]
