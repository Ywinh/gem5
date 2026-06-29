# gem5 C920 文档总览

## 1. 背景介绍

**做处理器相关工作时，常见工具大致可以分成几类：**
* RTL 仿真器：例如 VCS、Xcelium、Questa。直接运行 Verilog/SystemVerilog/VHDL，关注的是寄存器传输级行为是否正确，信号在每个时钟周期怎么变化
* ISA / 功能级模拟器：例如 Spike。主要回答“这条指令执行后，架构状态对不对”，重点是 ISA 正确性，不强调 cache、流水线、乱序、总线延迟等微结构细节
* 系统仿真 / 架构仿真器：例如 gem5。既可以在 ISA 层面运行程序，也可以进一步建模 CPU 微结构、cache、memory、设备，甚至运行一个完整系统
* 高速功能模拟 / 虚拟平台：例如 QEMU。核心目标通常是“尽快跑起来”，适合软件 bring-up、OS 启动、驱动联调，对时序和微结构细节建模较弱

**仿真器和硬件仿真vcs等区别：**
* VCS 这类工具的输入是 RTL，它仿真的对象是真实硬件实现本身。
  * 精度高，适合验证设计正确性
  * 但速度通常很慢，尤其是跑稍大一点的软件负载时成本很高
* gem5 的输入不是 RTL，而是一个“抽象后的硬件模型”。
  * 你不需要把整个 CPU 用 RTL 写出来，而是用 gem5 提供的 CPU、cache、memory、device 框架去描述目标系统
  * 它更像“可编程的架构级/微结构级仿真平台”

**所以两者的差别可以概括为：**
* VCS 更接近“验证一个已经存在的硬件实现”
* gem5 更接近“构造一个可调参数的硬件模型，并观察它运行软件时的行为”
* 在实际运行时，gem5 的运行速度与 vcs 差了大概三个数量级

本项目的目标是在 gem5 中建模玄铁 C920。C920 是一个乱序超标量处理器，当前模型聚焦于核心、cache 和 memory 三部分，并结合 gem5 的 Python 配置能力完成系统组装与参数校准。

**为什么选 gem5，而不是 Spike、QEMU 等？**
和本项目的目标有关系，我们的目标是尽可能建模一个比较精确的CPU，这件事决定了工具选择。

* 为什么不用 Spike
  * Spike 的优势是：简洁、功能正确性强、很适合做 ISA 参考模型
  * 但它主要是 ISA functional simulator，更适合回答：指令语义对不对、CSR 行为对不对、程序最终结果对不对
  * 它对 CPU 微架构建模不精细，只是一个能跑程序指令的程序
  * 所以 Spike 很适合当 golden model 做功能对比，但不适合做我们这种 CPU 建模主平台。
* 为什么不用 QEMU
  * QEMU 的优势是：跑得快、很适合 bring-up 软件、很适合启动 OS、调驱动、跑应用
  * 但它更偏“功能级虚拟平台”，主要目标是：执行 guest code、模拟外设和系统环境，也就是系统级别的模拟

为什么 gem5 更适合当前目标
* 比 Spike 更强的地方在于：它能建模微结构和 memory hierarchy
* 比 QEMU 更强的地方在于：它能提供更有解释力的性能模型
* 比 VCS 更现实的地方在于：它可以在可接受的时间里跑更复杂的软件负载

**为什么只编译一次，就能配置不同 CPU**
> 不是可执行文件每次都变了，而是“同一个二进制里已经包含了很多模型”
gem5.opt 编译出来之后，本质上是一个大的仿真器二进制。这个二进制里已经包含了很多：CPU 模型、cache 模型、memory 模型、bus / device / board 模型，以及这些模型对应的参数定义

所以换 CPU并不是重新生成了一个新可执行文件，而是：仍然运行同一个 gem5.opt,只是启动时选择实例化不同的 CPU 类和参数

例如同样一个 gem5.opt，你可以在 Python 配置脚本里选择：TimingSimpleCPU、MinorCPU、O3CPU等

这就像：执行文件是“工厂”，Python 配置是“订单”每次运行时根据订单装配不同机器，所以不是“二进制每次变了”，而是“二进制支持的部件已经编进去，运行时选择不同组合”。

**Python 配置、实例化之间是什么关系**

正常流程是：Python 配置脚本先构造对象树，然后调用 m5.instantiate() 完成实例化。config.ini 是实例化后导出的“最终配置快照”，也就是说，config.ini 更像“结果记录”，不是平时驱动实例化的输入文件。

Python 配置脚本到底在做什么？在 gem5 里，Python 脚本不是简单写文本配置，它实际上是在：
* 创建 SimObject
* 设置参数
* 连接端口
* 组装 board / cpu / cache / memory 的拓扑关系

例如脚本里写：
```
processor = C920Processor(num_cores=1)
cache_hierarchy = C920CacheHierarchy(...)
memory = SingleChannelDDR4_2400("1GB")
board = C920BareMetalBoard(...)
```

为什么 Python 能控制 C++ 对象
* 因为 gem5 在编译时会把大量 C++ SimObject 通过绑定机制暴露给 Python。所以 Python 里写的那些类，背后通常都对应到 C++ 里的真实 SimObject 类型和参数定义。
* 可以理解成：C++ 提供“模型实现”,Python 提供“组装方式”

m5.instantiate() 时发生了什么，当调用 m5.instantiate() 时，gem5 会做几件关键事情：
* 检查 Python 侧对象树和参数是否完整，将这些对象和参数传给 C++ 侧
* 在 C++ 侧真正创建对应的 SimObject 实例
* 建立端口连接、层次关系和运行时状态


gem5 本质上是一个事件驱动模拟器，时间单位是 `tick`。它通过 `pybind` 将大量 SimObject 暴露给 Python，因此很多建模工作首先不是改 C++ 源码，而是理解如何通过配置文件实例化 CPU、cache、memory 和 board，并通过参数调整尽量逼近目标硬件行为。对于 gem5 原生微结构与待建模 CPU 之间无法完全对齐的部分，当前策略是优先通过参数映射减小误差，而不是一开始就重写底层实现。

## 2. 项目概述

- 建模对象：玄铁 C920
- 核心模型：基于 gem5 `RiscvO3CPU`
- cache 层次：私有 `L1I/L1D` + 共享 `L2`
- 运行模式：以 bare-metal 方式运行裸机程序
- memory backend：支持 gem5 DDR4、近零时延 DDR4、`SimpleMemory`、SystemC/TLM memory

参考手册：[920R1S6 pdf](https://occ-oss-prod.oss-cn-hangzhou.aliyuncs.com/resource//1737721869472/%E7%8E%84%E9%93%81C910%E4%B8%8EC920R1S6%E7%94%A8%E6%88%B7%E6%89%8B%E5%86%8C%28xrvm%29_20250124.pdf)

## 3. Build


## 4. Run

以下命令默认在仓库根目录 `/home/yinjianhui/gem5` 下执行，且使用单 system 模式。

### 4.1 运行基本 bare-metal 程序

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf
```

默认参数为：

- `1` 核
- `1GHz`
- `L1I=32KiB`
- `L1D=32KiB`
- `L2=256KiB`
- `mem-size=1GB`
- 标准 `SingleChannelDDR4_2400`

### 4.2 调整核心数、频率和 cache 容量

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf \
  --num-cores 4 \
  --clock 2GHz \
  --l1i-size 64KiB \
  --l1d-size 64KiB \
  --l2-size 1MiB
```

### 4.3 调整主存大小

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf \
  --mem-size 2GB
```

### 4.4 使用近零时延 DDR4

这个模式保留 DDR4 controller / interface 路径，但将 DRAM timing 压到接近零，更适合和不包含真实 DDR 延时的参考模型对齐。

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf \
  --zero-dram-latency
```

### 4.5 使用 gem5 SimpleMemory

这个模式适合做快速参数扫描，直接控制 memory latency 和 bandwidth。

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf \
  --gem5-simple-mem \
  --simple-mem-latency 30ns \
  --simple-mem-latency-var 0ns \
  --simple-mem-bandwidth 12.8GiB/s
```

### 4.6 使用 SystemC print memory

这个模式主要用于调试 bridge 连通性。memory request 会发往 SystemC 侧的 print target，同时数据镜像到 gem5 physmem backing store。

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf \
  --systemc-print-mem \
  --max-ticks 100000
```

### 4.7 使用 SystemC simple memory

这个模式通过 `Gem5ToTlmBridge64` 将 gem5 的 memory traffic 送到 SystemC 侧的 `C920TlmSimpleMem`。

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf \
  --systemc-simple-mem \
  --simple-mem-latency 50ns \
  --simple-mem-latency-var 10ns \
  --simple-mem-bandwidth 8GiB/s
```

### 4.8 使用 external SystemC simple memory

这个模式会让 gem5 生成外部 `tlm_slave` 所需配置，供 `util/tlm` 侧的独立 SystemC 进程使用。

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf \
  --external-systemc-simple-mem
```

### 4.9 限制仿真 tick 数

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary /path/to/your/baremetal.elf \
  --max-ticks 1000000
```

## 5. 核心功能

- 提供一套基于 `RiscvO3CPU` 的玄铁 C920 核心模型，包括流水线延迟、宽度、ROB/IQ/LSQ 和 RVV 配置。
- 提供与 C920 相匹配的分支预测器、功能单元池以及 `L1I + L1D + shared L2` 的 classic cache 层次。
- 支持多种 memory backend，包括标准 DDR4、近零时延 DDR4、gem5 `SimpleMemory` 和 SystemC/TLM memory。
- 支持 bare-metal 运行方式，包含固定物理地址映射和 FIFO/MMIO 地址窗口处理。
- 支持功能对比和性能对比所需的 trace、stats 和实验脚本基础。

## 6. 演进、开发历程

最早先从 C906 建模探索可行性，因为 C906 是顺序流水线，建模相对简单。这个阶段也比较了 `classic cache` 和 `ruby cache` 的适用性，最终优先采用 `classic cache`，因为它配置更直接，而 `ruby` 更偏重 NoC 和缓存一致性协议的建模，当前阶段还不是主需求。

最初采用的是 SE 模式，后面由于裸机程序没有页分配支持，访问会失败，因此改为 bare-metal 方式运行后解决。两者的核心区别可以概括为：

> FS bare-metal 和 SE 的区别
>
> - FS bare-metal：仍然是 FullSystem 视角，关注真实物理地址空间、MMIO、CSR、异常/中断、特权级、PMP/PMA 等。
> - SE：是 syscall emulation，建模的是 guest 进程，而不是一台完整机器。
>
> 一句话概括：FS bare-metal 建模“机器”，SE 建模“进程”。

906 建模校准之后，开始进行 C920 建模。从顺序流水线转向乱序多发射流水线，cache 也从单级扩展为 `L1 + L2`。随后进行了与硬件仿真的校准。由于参考硬件环境虽然挂了 DDR，但并没有真实 DDR 延时，因此增加了 `zero-dram-latency` 选项，用于在校准阶段弱化 DRAM timing 的影响。

在 C920 配置基本稳定后，后续工作转向将 gem5 接入内部仿真环境，用 gem5 替换原有 scalar core。这个过程涉及 gem5 与 SystemC 协同仿真的学习、讨论和实现，目前已经能够作为 `lib` 接入到 emu 中，但目前面向单 CCU 场景，2 CCU 需要 gem5 配置 two system。

## 7. 测试

建模需要同时关注功能与性能两个维度：

- 功能测试关注指令执行顺序和结果是否正确。
- 性能测试关注运行 workload 后的各类性能计数器是否与参考模型保持在可接受误差范围内。

无论是功能还是性能测试，核心方法都是让 gem5 和一个 golden model，例如 spike 或硬件仿真，运行同一份负载，然后对比执行轨迹、结果或统计计数器。

### 7.1 功能测试

功能测试主要与 spike 对比。gem5 生成一份执行 trace，再转换为与 spike 相近的格式，逐条比较下列信息：

- `pc` 是否一致
- 指令码是否一致
- 写回寄存器编号和值是否一致
- 对于访存指令，访存地址、数据和 size 是否一致

> gem5 的执行 trace 可通过 `--debug-flags=Exec` 开启。

### 7.2 性能测试

性能测试主要与硬件仿真对比。方法是将运行后生成的 `stats.txt` 中相关计数器，与硬件仿真 dump 出来的 PMU 计数器对照，例如总运行时间、cache hit/miss 次数、访存事件等。

C920 具有 `mhpmevent3-31` 共 29 个可配置事件寄存器，需要在程序开始处通过汇编进行设置，具体可参考 C920 手册第 14、15 章。例如：

```asm
li x3, 0x2
csrw mhpmevent4, x3 // mhpmcounter4 count event: L1 ICache Miss Counter
```

gem5 运行后，通常会在 `m5out/` 下生成以下文件：

1. `config.ini`：本次运行的实例化配置
2. `stats.txt`：仿真统计信息
3. `config.dot.svg`：拓扑图与内部连接关系

## 8. 相关文档索引

1. [C920 配置建模](./c920-config-modeling.md)
2. [RISC-V 扩展指令接入说明](./riscv-custom-instruction-guide.md)
3. [gem5 native SystemC 改动总结](./gem5-native-systemc-summary.md)
4. [gem5 的两种 sc 接入方式](https://zhuanlan.zhihu.com/p/2044510170361881121)


## 9. 限制

- 当前 C920 模型是基于 gem5 `RiscvO3CPU` 的近似建模，不是 RTL 级 cycle-accurate 复刻。
- ROB、IQ、LQ、SQ 和部分寄存器规模使用了 C910 RTL 代理值，适合作为量级近似，不应直接视为 C920 官方参数。
- `uncacheable` 请求仍会穿过 cache 层次，因此会带上一部分 cache 路径延迟。
- 向量相关配置已经开启，但当前主要工作负载还未围绕 RVV 做系统校准。
- `classic cache` 更适合当前主路径实验，但不能完整表达真实 cache 的 bank、仲裁和一致性协议细节。
- 当前 README 只覆盖单 system 的常用运行方式，不展开 two-system / multi-system 流程。
