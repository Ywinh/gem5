from m5.objects import *


class MyBranchPredictor(BiModeBP):
    # def __init__(self):
    #     super().__init__()
    # 分支历史表：使用 BiModeBP (BI-MODE 策略)
    # 8Kb 配置：globalPredictorSize=4096 (4096 * 2 bits = 8Kb)
    # 16Kb 配置：globalPredictorSize=8192 (8192 * 2 bits = 16Kb)
    # 这里选择 8Kb；如需 16Kb，改为 8192
    globalPredictorSize = 4096  # 8Kb
    globalCtrBits = 2  # 2-bit counters
    choicePredictorSize = 4096  # 匹配 globalPredictorSize
    choiceCtrBits = 2

    # BTB: 16 表项，全相联
    btb = SimpleBTB(
        numEntries=16, associativity=16, tagBits=16  # 全相联  # 默认 16 bits
    )

    # RAS: 4 层
    ras = ReturnAddrStack(numEntries=4)

    # 间接分支跳转预测器: null
    indirectBranchPred = NULL

    instShiftAmt = 2  # riscv
