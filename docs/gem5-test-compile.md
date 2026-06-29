# gem5 测试程序编译说明

## 1. 说明

本文档说明在进行 C920 性能测试时，如何构造 gem5 与硬件仿真可共用的测试程序。该测试程序主要用于性能对比；如果当前没有这类对比需求，可以跳过本文档。

gem5 对这类通用测试程序的基本要求如下：

- 最终产物需要是 `ELF`
- 程序需要能够以 bare-metal 方式运行
- 如果程序中使用了工具链特有的 CSR，且 gem5 尚未支持这些 CSR，需要先在 gem5 中补充识别，否则运行时会报错

## 2. Get Started

### 2.1 获取参考源码

下面的参考源码位于外网仓库，当前没有同步到内网。它本身只是一个简单参考，主要用于说明 `Makefile` 的修改方式。

```bash
git clone https://github.com/Ywinh/gem5-resources.git
git checkout develop
cd src/simple
```

### 2.2 安装编译工具链

需要先安装 RISC-V GNU toolchain 或玄铁 toolchain。

#### 2.2.1 RISC-V GNU toolchain

仓库地址：

- <https://github.com/riscv-collab/riscv-gnu-toolchain>

说明：

- 需要确认工具链支持 32 位编译
- 需要支持 `-march=rv32imf -mabi=ilp32f` 这一类编译选项

#### 2.2.2 玄铁 toolchain

可以直接从官网下载编译好的二进制版本，安装后即可使用。根据需要选择 32 位或 64 位工具链。

下载地址：

- <https://www.xrvm.cn/community/download?id=4460156621967921152>

### 2.3 编译自己的程序

步骤如下：

1. 在 `src/simple` 目录下编写自己的 `.c` 文件。
2. 通过 `make` 生成 bare-metal 程序。

示例命令：

```bash
make ISA=riscv BARE_INS=my_coremark bare \
  CCFLAGS_ISA="-march=rv32imf -mabi=ilp32f"
```

常见用法：

- 编译 32 位程序

```bash
make ISA=riscv BARE_INS=my_coremark bare \
  CCFLAGS_ISA="-march=rv32imf -mabi=ilp32f"
```

- 编译 64 位程序

```bash
make ISA=riscv BARE_INS=920_test_compact bare \
  CCFLAGS_ISA="-march=rv64imf -mabi=lp64f"
```

其中：

- `-march`
- `-mabi`

都可以根据目标程序实际需求调整。

## 3. Case

可用测试程序来源主要有两类：

1. 本仓库 `gem5/case/` 目录下已有一些现成 case 可直接使用。
2. gem5 官方也提供了一些现成 case，可从 <https://resources.gem5.org/> 获取。

## 4. Bootloader 需要额外做的事情

> 以下寄存器不是标准 RISC-V ISA 原生 CSR，而是玄铁扩展寄存器。
> 如果测试程序中使用了这些寄存器，而 gem5 还没有支持，运行时会报“不认识该寄存器”的错误。
> 因此需要先在 gem5 中补充识别；现阶段通常只需要做到“可识别”即可，功能是否完全实现可以后续再补。

### 4.1 在程序开头配置玄铁相关控制寄存器

由于玄铁某些特性需要先打开控制寄存器才能生效，例如 prefetcher、cache 等，因此测试程序开头通常需要加入一段初始化汇编。具体寄存器配置应以手册为准，例如：

```asm
li x3, 0x70013
csrs mcor, x3

# enable write allocate
# li x3, 0x4
# csrs 0x7c1, x3
li x3, 0x11ff
csrs mhcr, x3

# enable lbuf, way_pred, data_cache_prefetch, amr
# li x3, 0x7e30c
# csrs 0x7c5, x3
li x3, 0x6e30c
csrs mhint, x3

li x3, 0x6b8000
csrs mxstatus, x3

li x3, 0xe0000009
csrs mccr2, x3
```

### 4.2 在程序开头配置性能计数器

如果需要 dump 指定性能计数器，也需要在程序开头完成配置。具体事件编号应参考 C920 手册，例如：

```asm
# performance counter
# 前端 / 分支 11 个
li x3, 0x1
csrs 0x323, x3      # mhpmcnt3  L1 ICache Access

li x3, 0x2
csrs 0x324, x3      # mhpmcnt4  L1 ICache Miss

li x3, 0x3
csrs 0x325, x3      # mhpmcnt5  I-UTLB Miss

li x3, 0x5
csrs 0x326, x3      # mhpmcnt6  JTLB Miss

li x3, 0x6
csrs 0x327, x3      # mhpmcnt7  Conditional Branch Mispredict

li x3, 0x7
csrs 0x328, x3      # mhpmcnt8  Conditional Branch

li x3, 0x8
csrs 0x329, x3      # mhpmcnt9  Indirect Branch Mispredict

li x3, 0x9
csrs 0x32a, x3      # mhpmcnt10 Indirect Branch

li x3, 0x1b
csrs 0x32b, x3      # mhpmcnt11 IFU Branch Target Mispred

li x3, 0x1c
csrs 0x32c, x3      # mhpmcnt12 IFU Branch Target Instruction

li x3, 0x27
csrs 0x32d, x3      # mhpmcnt13 Stalled Cycles Frontend

# 后端 / 访存 14 个
li x3, 0x4
csrs 0x32e, x3      # mhpmcnt14 D-UTLB Miss

li x3, 0xa
csrs 0x32f, x3      # mhpmcnt15 LSU Spec Fail

li x3, 0xb
csrs 0x330, x3      # mhpmcnt16 Store Instruction

li x3, 0xc
csrs 0x331, x3      # mhpmcnt17 L1 DCache Load Access

li x3, 0xd
csrs 0x332, x3      # mhpmcnt18 L1 DCache Load Miss

li x3, 0xe
csrs 0x333, x3      # mhpmcnt19 L1 DCache Store Access

li x3, 0xf
csrs 0x334, x3      # mhpmcnt20 L1 DCache Store Miss

li x3, 0x10
csrs 0x335, x3      # mhpmcnt21 L2 Load Access

li x3, 0x11
csrs 0x336, x3      # mhpmcnt22 L2 Load Miss

li x3, 0x12
csrs 0x337, x3      # mhpmcnt23 L2 Store Access

li x3, 0x13
csrs 0x338, x3      # mhpmcnt24 L2 Store Miss

li x3, 0x17
csrs 0x339, x3      # mhpmcnt25 LSU Cross 4K Stall

li x3, 0x18
csrs 0x33a, x3      # mhpmcnt26 LSU Other Stall

li x3, 0x28
csrs 0x33b, x3      # mhpmcnt27 Stalled Cycles Backend

# 指令 mix 4 个
li x3, 0x1d
csrs 0x33c, x3      # mhpmcnt28 ALU Instruction

li x3, 0x1e
csrs 0x33d, x3      # mhpmcnt29 LDST Instruction

li x3, 0x1f
csrs 0x33e, x3      # mhpmcnt30 Vector SIMD Instruction

li x3, 0x2a
csrs 0x33f, x3      # mhpmcnt31 Floating Point Instruction
```
