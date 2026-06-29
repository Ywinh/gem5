# RISC-V 玄铁扩展指令接入指南

## 1. 文档目的

该文档总结出一套后续可复用的方法，说明如果还要继续在 gem5 里加入玄铁风格的 RISC-V 扩展指令，应该怎么做。

文档分成两部分：

1. 前半部分先给出普适的接入建议和工作流程。
2. 后半部分再用一组已经落地的玄铁扩展指令作为例子，说明这些建议在代码里具体会落到哪些文件、哪些实现点上。

本文假设读者已经知道目标指令的 spec，但还不熟悉 gem5 的 RISC-V ISA 生成链路。

## 2. 后续接入扩展指令的普适建议

如果后面还要继续加入玄铁扩展指令，建议先记住下面几条原则。

### 2.1 先把 spec 拆成编码路径，再去改 `decoder.isa`

不要一上来就直接在 `decoder.isa` 里试写分支。应该先把指令编码拆成：

- `opcode[6:0]`
- `funct3`
- `funct7`
- `rd`
- `rs1`
- `rs2`
- 以及其他受约束位

然后再把它映射成 gem5 译码树里会用到的字段名，例如：

- `QUADRANT`
- `OPCODE5`
- `FUNCT3`
- `RD`
- `RS1`
- `RS2`
- `FUNCT7`

### 2.2 优先复用现有 format 和基类，只有必要时才扩新骨架

gem5 的 RISC-V 指令接入链路本来就有不少现成抽象，后续扩展时应尽量复用：

- 纯寄存器运算优先考虑 `ROp`
- 单立即数寄存器运算优先考虑 `IOp`
- 系统/序列化类优先考虑 `SystemOp`
- 普通基址访存优先考虑 `Load` / `Store`

只有在下面这些场景，才建议额外新增一层基类或 format：

- 指令需要保存现有模板拿不到的额外编码字段
- 指令需要专门的反汇编格式
- 多条新指令共享同一种特殊语义骨架
- 地址计算或操作数组织方式和已有模板明显不同

换句话说，应该尽量让“新加的代码只表达新需求”，而不是为了写起来顺手就复制出一套平行基础设施。

### 2.3 不要轻易绕开 gem5 现有异常路径

如果一条扩展指令本质上仍然是普通算术或普通访存，就尽量复用 gem5 已有的执行与异常机制。特别是访存类指令，不要轻易自己手写 page fault、access fault、alignment fault 路径，除非语义确实和普通 `Load` / `Store` 已经不同。

通常更好的做法是：

- 自定义真正不同的那一小部分，例如 EA 计算方式
- 其余部分继续复用 gem5 的普通访存路径

这样做的好处是行为更稳定，也更容易和后续 gem5 代码保持一致。

### 2.4 提前约定非法输入、不规范输入如何处理

spec 里常见三类描述：

- `illegal`
- `reserved`
- `unpredictable`

对模拟器来说，`illegal` 最直接；而 `unpredictable` 如果放着不管，后面会在调试和对比时引入很多不确定性。因此建议在接入时就明确一个稳定策略，并在文档里写清楚。即使这个策略不是唯一可能的实现，也应当保证：

- 行为稳定
- 容易解释
- 容易复现

### 2.5 反汇编不要最后再补

后续调试扩展指令时，trace 和反汇编可读性非常关键。如果一条指令语义写对了、但是反汇编格式不对，那么后面做 spike/hardware 对比时会非常痛苦。

因此接入时应同步考虑：

- 现有基类能不能直接打印出正确格式
- 如果不能，是否需要单独实现 `generateDisassembly()`

### 2.6 用最小闭环验证，不要只看能不能编过

最少应覆盖三层验证：

1. `scons build/RISCV/gem5.opt` 是否能通过
2. 指令是否能被正确译码并执行
3. trace / 反汇编 / 异常路径是否符合预期

只编译通过，通常只能说明 `.isa` 语法和 C++ 符号大体没错，不能证明指令已经真正接进来了。

## 3. gem5 中 RISC-V 指令是怎么进来的

后续继续接入扩展指令时，最重要的是先理解 gem5 的接入链路。

### 3.1 取指与译码入口

入口在：

- `src/arch/riscv/decoder.cc`

核心过程是：

1. `moreBytes()` 把内存中的机器码拼进 `emi.instBits`
2. `decode(PCStateBase&)` 再把 `rv_type`、`vl`、`vtype` 这类上下文信息塞进 `emi`
3. 最后调用生成出来的 `decodeInst(emi)`

这里的 `emi` 类型就是 `ExtMachInst`。

### 3.2 位字段提取

位字段的运行时定义在：

- `src/arch/riscv/types.hh`

例如：

- `quadRant = inst[1:0]`
- `opcode5 = inst[6:2]`
- `rd = inst[11:7]`
- `funct3 = inst[14:12]`
- `rs1 = inst[19:15]`
- `rs2 = inst[24:20]`
- `funct7 = inst[31:25]`

而 `.isa` 文件里使用的字段名，声明在：

- `src/arch/riscv/isa/bitfields.isa`

例如：

- `def bitfield QUADRANT <1:0>;`
- `def bitfield OPCODE5 <6:2>;`
- `def bitfield FUNCT3 <14:12>;`

如果后续扩展指令需要新的编码字段名，通常就要同时考虑这两个文件。

### 3.3 ISA 描述文件的展开顺序

总入口在：

- `src/arch/riscv/isa/main.isa`

它会依次包含：

1. `includes.isa`
2. `bitfields.isa`
3. `operands.isa`
4. `templates/templates.isa`
5. `formats/formats.isa`
6. `decoder.isa`

真正的译码树写在：

- `src/arch/riscv/isa/decoder.isa`

因此如果你新增了：

- 新基类
- 新 format
- 新 bitfield

就必须确认它们都已经通过这条 include 链路接进来了。

## 4. 后续接入玄铁扩展指令的推荐流程

下面是一套比较稳妥的工作流程。

### 4.1 先确定它落在哪个 opcode 大类

先根据 spec 写出：

- `opcode[6:0]`
- `funct3`
- `funct7`
- 以及其他约束位

再手工推导出它在 gem5 里的译码路径。只有这一步清楚了，才能准确判断是挂到现有分支里，还是要新开一段 decode 树。

### 4.2 判断它更像哪一类已有指令

先判断语义类型，再决定选哪种现成模板：

- 纯寄存器算术：优先 `ROp`
- 单立即数寄存器类：优先 `IOp`
- 系统/序列化类：优先 `SystemOp`
- 普通基址加载/存储：优先 `Load` / `Store`
- 位操作但字段特殊：考虑扩一个类似 `ExtOp` 的小骨架
- 特殊地址计算访存：考虑扩一个类似 `ShiftLoad` 的小骨架

### 4.3 只有在必要时才补新 bitfield

如果 spec 使用的字段正好能复用已有定义，例如某些 `funct` 子字段或现有立即数字段，那就优先复用。

只有在下面两种情况才建议新增 bitfield：

- 当前字段名不足以表达指令编码含义
- 后续实现和阅读都会因为新字段名明显更清楚

新增 bitfield 时，一般要同时考虑：

- `src/arch/riscv/types.hh`
- `src/arch/riscv/isa/bitfields.isa`

### 4.4 决定是否要新增指令基类或 format

只有在确实有共性需求时，才建议新增：

- `src/arch/riscv/insts/*.hh`
- `src/arch/riscv/insts/*.cc`
- `src/arch/riscv/isa/formats/*.isa`

常见触发条件包括：

- 多条新指令都需要携带相同的额外字段
- 多条新指令共享一套特殊反汇编格式
- 现有 format 很难表达新的操作数布局

如果新增了 `.cc` 文件，还要同步接到：

- `src/arch/riscv/insts/SConscript`

如果新增了基类给 `.isa` 使用，还要同步接到：

- `src/arch/riscv/isa/includes.isa`

### 4.5 把语义尽量写在最小必要层

原则是“在哪里差异最小，就在哪里改”：

- 纯算术语义，尽量直接落在 `decoder.isa`
- 特殊反汇编，尽量落在新基类
- 特殊 EA 计算，尽量落在访存 format 或专门访存基类

不要为了实现一条指令，把整条执行路径都复制一份。

### 4.6 在 `decoder.isa` 里补译码入口

这里要做的事情其实很明确：

1. 找到正确的上层 decode 分支
2. 按字段约束逐层补进去
3. 最后生成对应指令对象

读 `decoder.isa` 的方法，本质上就是把它看成一个层层嵌套的 `switch/case`。例如：

```isa
0x02: decode FUNCT3 {
    0x0: decode RD {
        0x00: decode RS1 {
            0x00: decode FUNCT7 {
                0x00: decode RS2 {
                    0x18: sync(...)
```

它要读成：

1. 外层已经命中了 `OPCODE5 == 0x02`
2. 再要求 `FUNCT3 == 0x0`
3. 再要求 `RD == 0`
4. 再要求 `RS1 == 0`
5. 再要求 `FUNCT7 == 0`
6. 再要求 `RS2 == 0x18`
7. 这时生成 `sync` 指令对象

### 4.7 明确异常和非法编码策略

扩展指令接入时，建议显式回答下面几个问题：

- 哪些输入应当抛 `IllegalInstFault`
- 哪些输入可以复用已有 fault path
- 对 `unpredictable` 是否主动收敛为某种固定行为

最好在代码和文档中都把这个策略写出来，不要留给后来的人猜。

### 4.8 编译并做最小闭环验证

至少要先过：

```bash
scons -j4 build/RISCV/gem5.opt
```

需要重点关注两类问题：

1. ISA 生成阶段错误
   - 常见于 `.isa` 语法、format 注册、include 关系
2. C++ 编译阶段错误
   - 常见于新基类没加入 `SConscript`
   - 或 include 没接进 `includes.isa`

之后再用最小 bare-metal 程序或定向测试验证：

- 是否真的译码到新指令
- 语义是否正确
- 反汇编是否正确
- 异常路径是否符合预期

## 5. 什么时候需要改哪些文件

后续扩展时，可以先用下面这张表判断改动范围。

| 场景 | 常见需要修改的文件 |
| --- | --- |
| 只是给现有译码树补一条普通寄存器运算指令 | `src/arch/riscv/isa/decoder.isa` |
| 需要新增编码字段名 | `src/arch/riscv/types.hh`、`src/arch/riscv/isa/bitfields.isa` |
| 需要专门的反汇编格式或共享小骨架 | `src/arch/riscv/insts/*.hh`、`src/arch/riscv/insts/*.cc`、`src/arch/riscv/isa/includes.isa`、`src/arch/riscv/insts/SConscript` |
| 需要新增 ISA format | `src/arch/riscv/isa/formats/*.isa` |
| 需要特殊访存地址计算 | `src/arch/riscv/isa/formats/mem.isa`，必要时还包括 `src/arch/riscv/insts/mem.hh`、`src/arch/riscv/insts/mem.cc` |
| 需要 trace/反汇编可读 | 优先检查已有基类是否够用，不够时补 `generateDisassembly()` |

## 6. 推荐检查清单

每加一条扩展指令，建议过一遍下面这张表：

- 编码路径是否已经手算成 `QUADRANT -> OPCODE5 -> ...`
- 新字段是否真的需要补到 `types.hh` 和 `bitfields.isa`
- 选的 format 是否是最小可复用方案
- 是否复用了现有异常路径
- 反汇编是否符合 spec 语法
- 对非法输入或不规范输入是否有确定策略
- 是否已经接进 `includes.isa` 和 `SConscript`
- 是否通过了 `build/RISCV/gem5.opt` 编译
- 是否做过至少一次最小运行验证

## 7. 示例：以一组 `custom-0` 玄铁扩展指令为例

下面不再按“某次改动”叙述，而是把已经接入的一组玄铁扩展指令当作示例，说明前面的方法是如何落地的。

### 7.1 示例指令

本例使用以下几条已经接入的指令：

- `sync`
- `mveqz`
- `mvnez`
- `mulaw`
- `ext`
- `extu`
- `lrw`

这些指令都落在同一个编码大类下：

- `opcode[6:0] = 0001011`
- `QUADRANT = 0x3`
- `OPCODE5 = 0x02`

也就是说，它们都属于 gem5 RISC-V 译码树中 `custom-0` 这一支。

### 7.2 本例为什么需要改这些文件

#### 7.2.1 位字段定义

- `src/arch/riscv/types.hh`
- `src/arch/riscv/isa/bitfields.isa`

这里补了：

- `imm1 = inst[31:26]`
- `imm2 = inst[25:20]`

原因是 `ext/extu` 需要显式访问两个 6-bit 立即数字段。这个例子说明：如果后续新指令确实需要更直接的编码字段表达，那么增加 bitfield 是合理的。

#### 7.2.2 自定义双立即数字段指令基类

- `src/arch/riscv/insts/ext.hh`
- `src/arch/riscv/insts/ext.cc`
- `src/arch/riscv/isa/includes.isa`
- `src/arch/riscv/insts/SConscript`

这里新增了 `ExtOp`：

- 保存 `imm1` 和 `imm2`
- 提供 `ext rd, rs1, imm1, imm2` 这种反汇编格式

这个例子说明：如果多条新指令共享同一种额外字段组织方式和反汇编格式，单独抽一个小基类是值得的。

#### 7.2.3 ISA 生成格式

- `src/arch/riscv/isa/formats/bs.isa`

这里新增了 `ExtOp` format，用来生成基于 `ExtOp` 的指令类。这个例子说明：当已有 format 很难自然表达新的操作数组织方式时，可以新增 format，但范围应尽量收敛。

#### 7.2.4 译码入口

- `src/arch/riscv/isa/decoder.isa`

这里在 `OPCODE5 == 0x02` 下新增了：

- `sync`
- `mveqz`
- `mvnez`
- `mulaw`
- `ext`
- `extu`
- `lrw`

这部分对应的是“先确定编码路径，再回填译码树”的标准流程。

#### 7.2.5 `lrw` 的访存格式与反汇编

- `src/arch/riscv/isa/formats/mem.isa`
- `src/arch/riscv/insts/mem.hh`
- `src/arch/riscv/insts/mem.cc`

这里新增了：

- `ShiftLoad` format
- `ShiftedAddrLoad` 类

它们服务于这类地址形态：

```text
EA = rs1 + (rs2 << imm2)
```

并让 `lrw` 的反汇编输出保持为：

```asm
lrw rd, rs1, rs2, imm2
```

这个例子说明：如果访存指令真正特殊的只是 EA 计算，而不是整条访存机制，那么最好只把“特殊 EA”抽出来，其他路径继续复用普通 `Load`。

### 7.3 本例中每类指令是怎么映射语义的

#### 7.3.1 `sync`

当前实现方式：

- 挂在 `SystemOp`
- 执行代码块为空
- 加了 `IsSerializeBefore` 和 `IsSerializeAfter`

因此它当前等价于一个“序列化 nop”。这个例子说明：如果某条指令当前最关键的语义是顺序约束，而不是可见数据变换，那么可以先把顺序语义稳定接进去，再看是否需要继续补完整门控逻辑。

#### 7.3.2 `mveqz`

语义：

```text
if (rs2 == 0)
    rd = rs1
else
    rd 保持不变
```

实现方式：

- 挂在 `ROp`
- 让 `Rd` 同时参与读写

这说明普通寄存器条件赋值类指令，通常可以直接复用 `ROp`，不需要新增基础设施。

#### 7.3.3 `mvnez`

语义：

```text
if (rs2 != 0)
    rd = rs1
else
    rd 保持不变
```

实现方式和 `mveqz` 相同。

#### 7.3.4 `mulaw`

语义：

```text
tmp[31:0] = rd[31:0] + (rs1[31:0] * rs2[31:0])[31:0]
rd = sign_extend(tmp[31:0])
```

实现方式：

- 挂在 `ROp`
- 使用 `uint32_t` 做低 32 位乘和低 32 位加
- 最后写回到 `Rd`

这说明带有局部位宽约束的普通算术，也未必需要新 format，很多时候直接在语义代码里控制中间位宽就足够了。

#### 7.3.5 `ext`

语义：

```text
rd = sign_extend(rs1[imm1:imm2])
```

实现方式：

- 挂在 `ExtOp`
- `imm1`、`imm2` 来自新增 bitfield
- 先右移取字段，再按字段宽度做符号扩展

当前实现里：

- 如果 `imm1 >= XLEN` 或 `imm2 >= XLEN`，报 `IllegalInstFault`
- 如果 `imm1 < imm2`，也报 `IllegalInstFault`

这里最重要的经验不是语义本身，而是处理策略：spec 中把 `imm1 < imm2` 描述成 `unpredictable`，当前实现为了保证模拟器行为稳定，主动收敛成了非法指令。

#### 7.3.6 `extu`

语义：

```text
rd = zero_extend(rs1[imm1:imm2])
```

实现方式和 `ext` 类似，但最后不做符号扩展，而是零扩展。

#### 7.3.7 `lrw`

语义：

```text
addr = rs1 + (rs2 << imm2)
rd = sign_extend(mem[addr + 3 : addr])
```

实现方式：

- 挂在 `ShiftLoad`
- `ea_code` 改成 `EA = Rs1 + (Rs2 << imm2)`
- 加载部分复用普通 `Load`
- 数据部分直接使用 `Mem_sw -> Rd_sd`

这样可以自动复用现有的：

- 非对齐异常
- access fault
- page fault

这正是“只定制特殊 EA，尽量复用普通访存路径”的一个典型例子。

### 7.4 本例中的设计取舍

这个例子里有两个值得显式记录的取舍。

#### 7.4.1 `sync`

当前只是：

- 空执行体
- `IsSerializeBefore`
- `IsSerializeAfter`

没有实现：

- `mxstatus.xuantieisaee`
- `mxstatus.copinstee`

等更细的门控语义。

#### 7.4.2 `ext/extu`

对于：

```text
imm1 < imm2
```

当前实现直接抛 `IllegalInstFault`，而不是去模拟 `unpredictable`。

这两个点都说明：在第一轮接入时，可以先收敛到稳定、可解释、可调试的行为，再决定是否继续贴近更细的硬件语义。

## 8. 后续如果继续加入玄铁扩展，优先复用什么

如果后面继续加的仍然是风格相近的玄铁扩展，建议优先看看能否复用：

- `ExtOp`
- `ShiftLoad`
- 现有 `custom-0` 译码分支

如果新指令和这批指令已经不是同一种编码风格或语义骨架，就回到本文第 4 节的流程，重新判断：

- 编码路径
- format 选择
- 是否需要新 bitfield
- 是否需要新基类
- 是否需要单独异常策略

## 9. 总结

后续继续接入玄铁扩展指令时，可以把问题拆成三层：

1. 它在 gem5 的译码树里应该挂到哪里。
2. 它能不能复用现有 format、基类和异常路径。
3. 它有哪些需要显式约定的特殊语义、反汇编格式和非法输入策略。

先按这个顺序思考，再动 `decoder.isa`、`formats` 和 `insts`，通常会比直接按某次历史改动照抄更稳，也更容易把新指令接得干净。
