# C920 Configuration

`configs/c920` 提供了一套基于 gem5 stdlib 的玄铁 C920 配置，当前面向
RISC-V `SE` 模式使用。目录里的配置把 C920 组织成：

- `RiscvO3CPU` 风格的 C920 OoO 核心模型
- 自定义分支预测器和功能单元池
- 私有 L1I/L1D + 共享 L2 的 classic cache 层次
- 多种内存后端
  - gem5 DDR4
  - 近似零时延 DDR4
  - gem5 `SimpleMemory`
  - 通过 `Gem5ToTlmBridge` 连接的 SystemC memory

默认入口脚本是 [run.py](/home/yinjianhui/gem5/configs/c920/run.py)。

## Directory Overview

- [run.py](/home/yinjianhui/gem5/configs/c920/run.py)
  顶层运行入口。负责解析命令行参数，组装 board / processor / cache /
  memory，并设置 SE binary workload。

- [processor.py](/home/yinjianhui/gem5/configs/c920/processor.py)
  `C920Processor` 封装。负责按核数创建 `C920Core` 列表，当前固定使用 O3
  类型核心。

- [cpu.py](/home/yinjianhui/gem5/configs/c920/cpu.py)
  `C920_O3CPU` 的主要参数配置，包括流水级间延迟、发射/退休宽度、ROB/IQ/LSQ
  大小、物理寄存器数量、RVV 使能和 VLEN 设置。

- [bpu.py](/home/yinjianhui/gem5/configs/c920/bpu.py)
  C920 分支预测近似模型，包括 BTB、Bi-Mode 方向预测器、RAS 和间接分支预测器。

- [fu.py](/home/yinjianhui/gem5/configs/c920/fu.py)
  功能单元池定义，覆盖整数、浮点、SIMD/Vector、Load/Store、IPR 等执行资源和
  操作延迟。

- [cache.py](/home/yinjianhui/gem5/configs/c920/cache.py)
  cache 和 prefetcher 细节配置，包含 L1I、L1D、L2 以及 I/D/L2 prefetcher。

- [cache_hierarchy.py](/home/yinjianhui/gem5/configs/c920/cache_hierarchy.py)
  classic cache 拓扑。当前是每核私有 `L1I + L1D`，所有核心共享一颗 L2。

- [systemc_memory.py](/home/yinjianhui/gem5/configs/c920/systemc_memory.py)
  C920 专用 SystemC memory 封装，提供两种通过 TLM bridge 接入的内存模式：
  `systemc-print-mem` 和 `systemc-simple-mem`。

- [README.md](/home/yinjianhui/gem5/configs/c920/README.md)
  本说明文档。

## Default Configuration

不带额外参数时，[run.py](/home/yinjianhui/gem5/configs/c920/run.py) 的默认行为是：

- ISA: RISC-V
- 模式: SE mode
- 核心数: 1
- 时钟: `1GHz`
- 核心模型: `C920Processor -> C920Core -> C920_O3CPU`
- 向量支持: RVV enabled，`VLEN=128`
- Cache:
  - L1I: `32KiB`
  - L1D: `32KiB`
  - L2: `256KiB`
- Memory:
  - `SingleChannelDDR4_2400`
  - 大小 `1GB`
- Workload:
  - 如果未指定 `--binary`，默认尝试获取 gem5 resource `riscv-hello`

## Build

建议从仓库根目录运行。一个最小构建命令示例如下：

```bash
scons build/RISCV/gem5.opt -j"$(nproc)"
```

如果你准备使用 `--systemc-simple-mem` 或 `--systemc-print-mem`，需要确保当前
`build/RISCV/gem5.opt` 已包含本仓库里的 SystemC/TLM bridge 相关对象。

## How To Run

以下命令都假设当前工作目录是仓库根目录 `/home/yinjianhui/gem5`。

### 1. 运行默认 hello

```bash
build/RISCV/gem5.opt configs/c920/run.py
```

这会使用默认的 1 核 C920、默认 cache、默认 DDR4 memory，并运行
`riscv-hello` resource。

### 2. 运行本地 RISC-V binary

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary tests/test-progs/hello/bin/riscv/linux/hello
```

离线环境更推荐这种方式，因为它不依赖 `obtain_resource(...)`。

### 3. 调整核心数、时钟和 cache 大小

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary ./your_riscv_binary \
  --num-cores 4 \
  --clock 2GHz \
  --l1i-size 64KiB \
  --l1d-size 64KiB \
  --l2-size 1MiB
```

### 4. 调整主存大小

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary ./your_riscv_binary \
  --mem-size 2GB
```

### 5. 切换 memory mode

`run.py` 的 memory mode 是互斥的，一次只能选一个。

#### 标准 gem5 DDR4

默认就是标准 gem5 DDR4，不需要额外参数：

```bash
build/RISCV/gem5.opt configs/c920/run.py --binary ./your_riscv_binary
```

#### 近似零时延 DDR4

保留 DDR4 controller / interface 路径，但把 DRAM timing 压到接近零：

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary ./your_riscv_binary \
  --zero-dram-latency
```

这个模式适合把实验重点放在 core 和 cache 上，而弱化 DRAM 时序影响。

#### gem5 SimpleMemory

使用 gem5 自带 `SimpleMemory`，并显式控制延迟和带宽：

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary ./your_riscv_binary \
  --gem5-simple-mem \
  --simple-mem-latency 30ns \
  --simple-mem-latency-var 0ns \
  --simple-mem-bandwidth 12.8GiB/s
```

#### SystemC Simple Memory

通过 `Gem5ToTlmBridge64` 把 gem5 memory traffic 送到 SystemC 侧
`C920TlmSimpleMem`：

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary ./your_riscv_binary \
  --systemc-simple-mem \
  --simple-mem-latency 50ns \
  --simple-mem-latency-var 10ns \
  --simple-mem-bandwidth 8GiB/s
```

这个模式下，实际 memory contents 保存在 SystemC target 的内部 storage 里。

#### SystemC Print Memory

通过 bridge 把访问发到一个 SystemC print target。该 target 会打印每个请求，
同时把数据镜像到 gem5 physmem backing store，便于做连通性和 functional 路径调试：

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary ./your_riscv_binary \
  --systemc-print-mem \
  --max-ticks 100000
```

这个模式主要用于调试，不是一个真实的 SystemC DRAM model。

### 6. 限制仿真 tick 数

```bash
build/RISCV/gem5.opt configs/c920/run.py \
  --binary ./your_riscv_binary \
  --max-ticks 1000000
```

这对于短时间 SystemC bridge 验证、接口冒烟测试和快速回归很有用。

## Command-Line Options Summary

- `--binary`
  本地 RISC-V ELF 路径。未指定时使用默认 `riscv-hello` resource。

- `--num-cores`
  C920 核数，允许 `1` 到 `4`。

- `--clock`
  board 时钟频率，例如 `1GHz`、`2GHz`。

- `--l1i-size`, `--l1d-size`, `--l2-size`
  cache 容量参数。

- `--mem-size`
  主存大小。

- `--zero-dram-latency`
  近似零时延 DDR4。

- `--gem5-simple-mem`
  使用 gem5 `SimpleMemory`。

- `--systemc-simple-mem`
  使用通过 TLM bridge 接入的 SystemC simple memory。

- `--systemc-print-mem`
  使用打印型 SystemC memory target，并镜像到 gem5 physmem。

- `--simple-mem-latency`
  `SimpleMemory` / `systemc-simple-mem` 的固定延迟。

- `--simple-mem-latency-var`
  `SimpleMemory` / `systemc-simple-mem` 的延迟扰动范围。

- `--simple-mem-bandwidth`
  `SimpleMemory` / `systemc-simple-mem` 的总带宽。

- `--max-ticks`
  最大仿真 tick 数。

## Notes

- 这个目录当前主要面向 `SE` 模式，不是完整的 `FS` 板级平台。
- 默认 workload 依赖 gem5 resource；在离线环境下请优先使用 `--binary`。
- `run.py` 使用本目录下的本地模块导入，因此建议始终从仓库根目录调用：

```bash
build/RISCV/gem5.opt configs/c920/run.py ...
```
