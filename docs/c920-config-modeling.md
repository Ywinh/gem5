# C920 配置建模

## 1. 背景
C920 相关配置的目标，是在 gem5 中建立一套可运行、可校准、可扩展的玄铁高性能核模型，以及 gem5 与 SystemC/TLM 的外部内存联动。这里的重点不是逐级复刻 RTL，而是保留对行为影响最大的微结构约束，使模拟结果在趋势上具备解释力。

当前仓库中与 C920 有关的实现分成两条线：

- `configs/920` 主要承担早期探索，包括 classic cache、banked L2、Ruby two-level 和流量发生器试验。
- `configs/c920` 是后续收敛后的主路径，围绕真实 workload、bare-metal 运行和多种 memory backend 进行了整理。

## 2. 总体大纲

1. 配置组织与演进路径
2. 核心模型与流水线参数
3. 结构规模与代理来源
4. 前端能力与分支预测
5. 执行资源与功能单元
6. Cache 层次、地址空间与内存后端
7. 关键文件与当前限制

## 3. 设计意图

- 根据 C920 特性，采用 `RiscvO3CPU` 作为底层骨架，建模为支持乱序执行
- 对 920 公开手册可直接确认的参数，尽量直接映射到配置中；对手册未公开但 gem5 必须显式给出的内部结构，使用与 C920 架构接近的 C910 RTL 规模做代理近似，并在实现中明确标注来源（920 RTL没有公开，它相比 910 只是多了 vector 指令，其他都相同因此可以参考）
- 将 `classic cache` 作为主路径，不直接以 Ruby 为默认方案，是为了降低系统组装复杂度，优先打通 workload、cache 和外部 memory backend 的联动链路。Ruby 相比 classic cache 支持更多缓存一致性的协议
- 对于外部与 Systemc/TLM 集成来说，gem5通过一个transactor，将 ddr 与写 fifo 路由到transactor上面，再由transactor发到外部systemc模块

## 4. 核心实现

### 4.1 配置组织与主入口

主入口位于 `configs/c920/run.py`。脚本负责统一解析核心数、频率、cache 容量、memory backend、最大 tick 数和多 system 实例等参数，并最终组装 `board + processor + cache_hierarchy + memory + workload`。这里的设计重点不是单纯把对象连起来，而是把后续最常用的实验口径封装为一个统一入口，避免不同脚本各自维护一套隐含假设。

实现上，当前默认运行参数由 `run.py` 而不是类定义默认值决定：

- `1` 核
- `1GHz`
- `L1I=32KiB`
- `L1D=32KiB`
- `L2=256KiB`
- `mem-size=1GB`

### 4.2 核心模型与流水线参数

gem5 流水线分为 Fetch -> Decode -> Rename -> IEW(Issue->Exe->Writeback) -> Commit
而玄铁 C920 则是 Fecth(3 stages) -> Decode & Issue (4) -> Exe(1~4) -> WB(1)

核心定义位于 `configs/c920/cpu.py`。当前模型基于 `RiscvO3CPU`，并显式设置 stage delay、前后端宽度、ROB、IQ、LSQ 和物理寄存器规模。流水线被映射为 `IFU(3) -> IDU(2) -> Rename/Dispatch(2) -> IEW(1) -> Commit(1)`，分别体现为：

- `fetchToDecodeDelay=3`
- `decodeToRenameDelay=2`
- `renameToIEWDelay=2`
- `issueToExecuteDelay=1`
- `iewToCommitDelay=1`

这样做的目的，是在 gem5 O3 的抽象框架下保留“前端不浅、乱序路径存在排队和反馈、最短流水级数约在 9 级量级”的基本特征。

吞吐宽度方面，当前设置为：

- `fetch/decode/rename/dispatch/issue = 3`
- `commit = 8`
- `wb = 8`
- `fetchBufferSize = 16`

这一组参数直接表达了“3 发射、8 退休、128-bit 取指”的设计意图，是整套模型最核心的吞吐边界。

### 4.3 结构规模与代理来源

ROB、IQ、LSQ 和物理寄存器规模位于 `configs/c920/cpu.py`。当前使用：

- `numROBEntries=64`
- `numIQEntries=52`
- `LQEntries=16`
- `SQEntries=12`
- `numPhysIntRegs=96`
- `numPhysFloatRegs=96`
- `numPhysVecRegs=96`

其中，ROB/LQ/SQ/IQ 规模主要依据 C910 RTL 可见结构进行代理映射，而不是来自 C920 手册的逐项公开参数。

这里的关键设计意图有两层：

- 这些结构值用于控制乱序窗口大小、cache miss 隐藏能力和资源竞争强度，比沿用 gem5 默认值更接近目标核量级。
- 浮点和向量物理寄存器并不是在宣称真实硬件各有 `96` 个，而是为满足 gem5 O3 的资源安全条件所做的工程化填充，避免极端 workload 下出现模拟器层面的资源死锁或异常悲观行为。

### 4.4 RVV 与 ISA 扩展

RVV 相关设置同样在 `configs/c920/cpu.py`。当前开启与920对齐，但是未使用

- `enable_rvv=True`
- `vlen=128`

这意味着该模型从一开始就把 C920 视为具备向量扩展能力的核心，而不是单纯的 `RV64GC` 核。后续任何向量 workload、向量寄存器压力、向量访存和 vector FU 延迟的实验，都是建立在这一假设上的。

### 4.5 分支预测与前端能力

分支预测实现位于 `configs/c920/bpu.py`。BTB 当前建模为：

- `1024` 项
- `4` 路
- `10-bit tag`

方向预测器使用 `BiModeBP`，并根据 RTL 规模推导出：

- `globalPredictorSize=16384`
- `choicePredictorSize=1024`

此外还配置了：

- `12` 项 RAS
- `256` 项 direct-mapped 的间接分支预测器

### 4.6 功能单元与执行资源

功能单元定义位于 `configs/c920/fu.py`。当前 `C920FUPool` 包含：

- 两路整数 ALU
- 一路整数乘除
- 一路标量浮点 ALU
- 一路浮点乘除
- 一路 SIMD/Vector 单元
- 一路 predicate ALU
- 一路 matrix 单元
- 一路读端口
- 一路写端口
- 一路 IPR 访问端口

这里的设计重点，是把“执行资源分工明确”这件事体现在 gem5 中，而不是只调宽 `issueWidth`，各个FU的延迟可以通过920手册获取。例如：

- 整数乘法设为 `4` cycle
- 整数除法设为非流水的 `20` cycle
- 浮点加法为 `3` cycle
- 浮点乘法为 `4` cycle
- FMA 为 `5` cycle

### 4.7 Cache 层次与预取策略

cache 与预取逻辑位于 `configs/c920/cache.py`，拓扑位于 `configs/c920/cache_hierarchy.py`。与920对齐，当前主路径采用“每核私有 L1I/L1D + 共享 L2”的 classic cache 层次。一致性协议

具体参数上：

- L1I 为 `2-way`、`1/1/1` 延迟、`mshrs=4`、`tgts_per_mshr=8`
- L1D 为 `2-way`、`2/2/1` 延迟、`mshrs=8`、`tgts_per_mshr=2`
- L2 为 `16-way`、`3/5/2` 延迟、`mshrs=16`、`tgts_per_mshr=12`

这组参数不是为了逐级对齐某个绝对时钟值，而是为了构造合理的层次关系：

- L1I 更轻更快
- L1D 更敏感于 load-use 路径
- L2 作为共享容量层明显更慢但并发更强

预取策略同样被显式建模：

- I-Cache 使用 next-line 风格预取器
- D-Cache 使用 stride 预取器
- L2 使用 stride 预取器

设计意图是用较低复杂度保留“前端顺序取指预取、数据流预取和下层容量预取”的基本差异。

### 4.8 地址空间、MMIO 与内存后端

板级封装位于 `configs/c920/run.py`。`C920BareMetalBoard` 会把内存映射到 `0x80000000`，并使用 `RiscvBareMetal` 方式加载 workload。与此同时，`FIFO_BASE=0x0A082000` 的地址窗口被配置为 PMA `uncacheable`。这使得该配置不仅能承载纯 CPU/cache 实验，也能处理固定 MMIO 地址和外部 FIFO/TLM endpoint 的联动场景。

内存后端支持：

- 标准 DDR4
- 近零时延 DDR4
- gem5 `SimpleMemory`
- SystemC print memory
- SystemC simple memory
- external SystemC simple memory

这部分的设计重点是让同一套核心和 cache 模型能够挂接不同内存后端，从而分别服务于真实性能路径、参数扫描、bridge 调试和外部 SystemC 进程协同运行。

## 5. 关键文件

- `configs/c920/run.py`：主入口，负责运行模式、地址空间、memory backend 和 workload 组装。
- `configs/c920/cpu.py`：O3 核心模型，定义流水线、宽度、ROB/IQ/LSQ、寄存器规模和 RVV。
- `configs/c920/bpu.py`：BTB、BiModeBP、RAS 和间接分支预测器的配置。
- `configs/c920/fu.py`：功能单元池和主要执行延迟。
- `configs/c920/cache.py`：L1I/L1D/L2 参数以及预取器配置。
- `configs/c920/cache_hierarchy.py`：classic cache 拓扑和 FIFO `ExternalSlave` 接入。
- `configs/c920/processor.py`：多核 `C920Processor` 封装。
- `configs/c920/systemc_memory.py`：SystemC/TLM memory 封装。
- `configs/920/c920.py`：早期 C920 试验入口。
- `configs/920/cache/classic/cache.py`：classic cache 探索实现。
- `configs/920/cache/ruby/run.py`：Ruby two-level 试验入口。

## 6. 已知限制

- 当前 O3CPU 配置是“微结构近似模型”，不是 C920 RTL 的 cycle-accurate 复刻。
- ROB、IQ、LQ、SQ 以及部分寄存器规模使用了 C910 RTL 代理值，适合作为量级近似，不应直接视为 C920 官方公开参数。
- 向量功能单元的延迟仍属于代表性建模，尚未对所有 RVV 指令逐项校准。
- classic cache 无法完整表达真实 cache 内部的 bank、仲裁、coherence 细节和专用控制逻辑，因此更适合做主路径实验，而不是替代更细粒度协议模型。
- 前端预测虽然已经做了规模化近似，但 L0 BTB 等结构在 gem5 中没有直接等价实现。
- `configs/c920/README.md` 中仍有部分描述偏向旧的 SE 口径，而当前 `configs/c920/run.py` 实际上已经按 bare-metal/full-system 路径组织，两者需要以后者为准。
- 多 system 模式当前不支持 `systemc-print-mem`、`systemc-simple-mem` 和 `external-systemc-simple-mem` 组合。
- 后期如果gem5持续更新，为了更加精准的建模可能需要与上游同步
