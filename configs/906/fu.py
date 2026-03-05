from m5.objects import *
from m5.params import *

# todo：说明修改了哪些，为什么修改；不要的fu可以pass或者去掉？


class C906IntFU(MinorDefaultIntFU):
    opClasses = minorMakeOpClassSet(["IntAlu"])
    timings = [MinorFUTiming(description="Int", srcRegsRelativeLats=[0])]
    issueLat = 1
    opLat = 1  # modify


class C906IntMulFU(MinorDefaultIntMulFU):
    opClasses = minorMakeOpClassSet(["IntMult"])
    timings = [MinorFUTiming(description="Mul", srcRegsRelativeLats=[0])]
    issueLat = 1
    opLat = 1


class C906IntDivFU(MinorDefaultIntDivFU):
    opClasses = minorMakeOpClassSet(["IntDiv"])
    issueLat = 9
    opLat = 9


class C906FloatFU(MinorDefaultFloatSimdFU):  # modify
    opClasses = minorMakeOpClassSet(
        [
            "FloatAdd",
            "FloatCmp",
            "FloatCvt",
            "FloatMisc",
            "FloatMult",
            "FloatMultAcc",
            "FloatDiv",
            "FloatSqrt",
        ]
    )

    timings = [
        MinorFUTiming(description="FloatSimd", srcRegsRelativeLats=[1])
    ]  # 如果有旁路，允许偷跑一周期 3-1 = 2
    opLat = 3


class C906SimdFU(MinorDefaultFloatSimdFU):
    opClasses = minorMakeOpClassSet(
        [
            "SimdAdd",
            "SimdAddAcc",
            "SimdAlu",
            "SimdCmp",
            "SimdCvt",
            "SimdMisc",
            "SimdMult",
            "SimdMultAcc",
            "SimdMatMultAcc",
            "SimdShift",
            "SimdShiftAcc",
            "SimdDiv",
            "SimdSqrt",
            "SimdFloatAdd",
            "SimdFloatAlu",
            "SimdFloatCmp",
            "SimdFloatCvt",
            "SimdFloatDiv",
            "SimdFloatMisc",
            "SimdFloatMult",
            "SimdFloatMultAcc",
            "SimdFloatMatMultAcc",
            "SimdFloatSqrt",
            "SimdReduceAdd",
            "SimdReduceAlu",
            "SimdReduceCmp",
            "SimdFloatReduceAdd",
            "SimdFloatReduceCmp",
            "SimdAes",
            "SimdAesMix",
            "SimdSha1Hash",
            "SimdSha1Hash2",
            "SimdSha256Hash",
            "SimdSha256Hash2",
            "SimdShaSigma2",
            "SimdShaSigma3",
            "Matrix",
            "MatrixMov",
            "MatrixOP",
            "SimdExt",
            "SimdFloatExt",
            "SimdFloatCvt",
            "SimdConfig",
        ]
    )

    timings = [MinorFUTiming(description="FloatSimd", srcRegsRelativeLats=[2])]
    opLat = 6


class C906PredFU(MinorDefaultPredFU):
    opClasses = minorMakeOpClassSet(["SimdPredAlu"])
    timings = [MinorFUTiming(description="Pred", srcRegsRelativeLats=[2])]
    opLat = 3


class C906MemReadFU(MinorDefaultMemFU):
    opClasses = minorMakeOpClassSet(
        [
            "MemRead",
            "FloatMemRead",
            "SimdUnitStrideLoad",
            "SimdUnitStrideMaskLoad",
            "SimdStridedLoad",
            "SimdIndexedLoad",
            "SimdUnitStrideFaultOnlyFirstLoad",
            "SimdWholeRegisterLoad",
        ]
    )
    timings = [
        MinorFUTiming(
            description="Mem",
            srcRegsRelativeLats=[1],
            extraAssumedLat=1,  # "For mem refs, if this is 0, the result's time is marked as unpredictable and no forwarding can take place."
        )
    ]
    issueLat = 1
    opLat = 1  # modify cacheable load >= 2 cycles：oplat + extraAssumedLat


class C906MemWriteFU(MinorDefaultMemFU):
    opClasses = minorMakeOpClassSet(
        [
            "MemWrite",
            "FloatMemWrite",
            "SimdUnitStrideStore",
            "SimdUnitStrideMaskStore",
            "SimdStridedStore",
            "SimdIndexedStore",
            "SimdWholeRegisterStore",
        ]
    )
    timings = [
        MinorFUTiming(
            description="Mem", srcRegsRelativeLats=[1], extraAssumedLat=1
        )
    ]
    issueLat = 1
    opLat = 1  # cacheable store = 1 cycle


class C906MiscFU(MinorDefaultMiscFU):
    opClasses = minorMakeOpClassSet(["IprAccess", "InstPrefetch"])
    opLat = 1


class C906FUPool(MinorFUPool):
    funcUnits = [
        C906IntFU(),
        C906IntFU(),
        C906IntMulFU(),
        C906IntDivFU(),
        C906FloatFU(),
        C906SimdFU(),
        C906PredFU(),
        C906MemReadFU(),
        C906MemWriteFU(),
        C906MiscFU(),
    ]
