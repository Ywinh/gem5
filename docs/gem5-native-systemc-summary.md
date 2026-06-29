# gem5 native SystemC 改动总结

## 1. 文档目的

这份文档总结 `gem5` 中所谓 “native SystemC” 到底改了什么，重点回答四个问题：

1. `src/systemc` 和 `ext/systemc` 分别是什么。
2. `gem5` 相对原版 `SystemC 2.3.1` 改动了哪些地方。
3. 哪些部分是 `gem5` 自己重写的，哪些部分仍然主要来自 `Accellera`。
4. 如果把 `gem5` 和另一个基于原版 `SystemC 2.3.1` 的模块放到同一个进程里协同仿真，最终应该统一到哪套 `sc` 运行时。


## 2. 先给结论

### 2.1 两套东西，不要混淆

`gem5` 里和 SystemC 相关的代码实际上分成两层：

- `ext/systemc`
  - 这是一个 vendored 的 `SystemC 2.3.1` 分发版；和你手头的 `2.3.1a` 非逐文件完全一致，但主体同源。
  - 它可以单独编出 `libsystemc`。
  - 相对上游只有少量补丁，主要是构建系统、Boost 剥离和一个额外的 TLM checker。

- `src/systemc`
  - 这才是 `gem5 native SystemC`。
  - 它不是简单调用 `ext/systemc/libsystemc`，而是在 `gem5` 里自己实现了一套 `sc_core` 运行时，并把 SystemC API 接到 `gem5` 的事件队列、SimObject 生命周期、Port/TLM 连接机制上。
  - 当 `USE_SYSTEMC=y` 时，真正参与仿真的是这套实现。

### 2.2 最重要的事实

如果你把 `gem5` 和另一个“基于未改动的 SystemC 2.3.1”的模块一起编进同一个进程：

- 不能同时保留 `gem5 native SystemC` 和外部原版 `libsystemc`。
- 必须统一到一套 `sc_core`。
- 对这种场景，最稳妥的做法通常是：
  - 用外部原版 `SystemC 2.3.1` 作为唯一的 `sc` 库。
  - 把 `gem5` 构建成 `libgem5`，并关闭 native SystemC：`USE_SYSTEMC=n`。

`gem5` 自己的文档也是这样建议的：当把 `gem5` 嵌入外部 SystemC 程序时，需要关闭 `gem5` 自带的 native SystemC API 支持，以避免和 external SystemC 冲突。


## 3. 目录关系和构建关系

### 3.1 目录职责

| 路径 | 角色 | 是否是实际运行时 |
| --- | --- | --- |
| `ext/systemc` | 打包的上游 SystemC 2.3.1 分发版 | 否，默认不是 native 路径的实际运行时 |
| `src/systemc/ext/*` | native SystemC 暴露给用户代码的头文件/API 门面 | 是，native API 入口 |
| `src/systemc/core/*` | native 内核、调度器、事件、时间、进程、模块层 | 是，核心运行时 |
| `src/systemc/channel/*` | native 通道实现 | 是 |
| `src/systemc/utils/*` | native report/trace/vector 等工具实现 | 是 |
| `src/systemc/dt/*` | 数据类型实现，很多来自上游 | 部分是 |
| `src/systemc/tlm_core`、`src/systemc/tlm_utils` | TLM/TLM utility 支持 | 部分是 |
| `src/systemc/tlm_bridge/*` | `gem5` 包与 TLM socket 的桥接 | `gem5` 特有扩展 |

### 3.2 native 构建时到底 include 了谁

`src/systemc/SConscript` 做了两件很关键的事：

- 把 `SYSTEMC_HOME` 指向 `src/systemc/ext/systemc_home`
- 把 `src/systemc/ext` 加到头文件搜索路径

这意味着：

- native SystemC 使用的 `SYSTEMC_HOME` 并不是外部安装好的 SystemC。
- `src/systemc/ext/systemc_home/include/systemc` 只是一个转发头，它会继续包含 `src/systemc/systemc`。
- 也就是说，native 路径下用户代码看到的 `systemc` 头，最终落到的是 `gem5` 自己的头和实现，不是 `ext/systemc/libsystemc` 的头和实现。

顺手统计一下：

- `src/systemc/ext/systemc_home/include` 下面只有 16 个文件。
- 它更像一个兼容入口层，而不是一个完整的上游安装树。

### 3.3 `ext/systemc` 仍然能单独编出 `libsystemc`

`ext/systemc/SConscript` 会遍历 `ext/systemc/src` 并生成：

- `libsystemc.a`
- `libsystemc.so`

这个库在以下场景里会被用到：

- `util/tlm`
- `util/systemc/gem5_within_systemc`
- 任何明确想把 `gem5` 作为库嵌入外部 SystemC 程序的构建流程

但这条路径与 `USE_SYSTEMC=y` 的 native 路径是两种不同的集成方式。


## 4. `ext/systemc` 相对上游 2.3.1a 的改动

这里对比的是：

- 上游：`/home/yinjianhui/systemc-2.3.1a/src`
- `gem5` 版：`/home/yinjianhui/gem5/ext/systemc/src`

### 4.1 总体判断

`ext/systemc` 不是“大改版” SystemC。

更准确地说，它是：

- 一个重新打包的 `SystemC 2.3.1`
- 替换了上游构建系统
- 剥离了对 bundled Boost 的依赖
- 补了极少量兼容性/工程化改动

### 4.2 数量级

对比结果大致如下：

- 上游 `src` 文件数：448
- `gem5/ext/systemc/src` 文件数：360
- 共同路径下真正内容不同的公共文件：5 个
- 上游 `sysc/packages/boost` 文件数：77
- 上游 `Makefile.am`/`Makefile.in`：22 个
- `gem5` 新增 `SConscript.sc`：9 个

### 4.3 具体改动

#### 4.3.1 构建系统替换

上游的：

- `Makefile.am`
- `Makefile.in`
- Autoconf 相关布局

在 `gem5/ext/systemc` 中被替换成：

- `SConscript`
- 各子目录 `SConscript.sc`

这使 `SystemC` 可以作为 `gem5` SCons 构建的一部分统一管理。

#### 4.3.2 Boost 依赖剥离

`gem5/ext/systemc/README.gem5.md` 已明确说明：

- 移除了 SystemC 对 bundled Boost 的依赖
- 把相关调用替换为 C++11 STL

源码上可以直接看到的改动包括：

| 文件 | 改动 |
| --- | --- |
| `src/sysc/kernel/sc_boost.h` | `boost::bind/ref/cref` 换成 `std::bind/ref/cref` |
| `src/sysc/kernel/sc_cmnhdr.h` | 去掉 `boost/config.hpp` |
| `src/sysc/utils/sc_vector.h` | `enable_if/remove_const/is_same/is_const` 改用 `<type_traits>` |

同时，整个 `sysc/packages/boost` 目录在 `gem5/ext/systemc/src` 中被删掉了。

#### 4.3.3 字节序处理被工程化简化

`src/sysc/utils/sc_machine.h` 不再通过 Boost 自动探测字节序，而是直接定义：

- `SC_BOOST_LITTLE_ENDIAN`

并在注释里写明：

- “assume a build on x86”

这是一处真正可能影响运行语义的本地改动：

- 在非 x86/非小端宿主上需要额外小心。

#### 4.3.4 兼容现代编译器的小补丁

`src/systemc.h` 里把：

- `using std::gets;`

注释掉了。这是典型的现代编译器/标准库兼容修补。

#### 4.3.5 额外加入 TLM checker

`gem5/ext/systemc/src/tlm_utils` 里额外带了：

- `tlm2_base_protocol_checker.h`

这是 Doulos 的 TLM 2.0 base protocol checker，不属于原始上游 `src` 的一部分。


## 5. `src/systemc` native 实现做了什么

这部分才是本文的重点。

### 5.1 一句话概括

`src/systemc` 的工作不是“给上游 SystemC 打几个补丁”，而是：

- 自己暴露一套 SystemC/TLM 头文件接口
- 自己实现 `sc_core` 的运行时
- 把 SystemC 的时间、事件、进程和生命周期，接入 `gem5` 的事件驱动内核

### 5.2 按源码来源粗分

下面这个表是按文件头做的粗略统计。注意：

- 同一个文件可能同时包含 Google 和 Accellera 的版权声明
- 所以两列数字会有重叠
- 这张表只用来帮助判断“哪块更像重写、哪块更像移植”

| 子树 | 文件数 | 含 Google 版权的文件数 | 含 Accellera 版权的文件数 | 粗略判断 |
| --- | --- | --- | --- | --- |
| `src/systemc/core` | 49 | 49 | 0 | 基本全部是 `gem5` 自写运行时 |
| `src/systemc/channel` | 11 | 11 | 0 | 基本全部是 `gem5` 自写 |
| `src/systemc/utils` | 13 | 13 | 1 | 以 `gem5` 自写为主 |
| `src/systemc/dt` | 40 | 9 | 31 | 上游数据类型代码为主，配少量 `gem5` glue |
| `src/systemc/tlm_core` | 6 | 3 | 3 | 混合 |
| `src/systemc/tlm_utils` | 3 | 1 | 2 | 混合 |
| `src/systemc/ext` | 187 | 74 | 110 | 对外 API 门面，混合来源 |
| `src/systemc/tlm_bridge` | 18 | 6 | 0 | `gem5` 特有桥接层 |

最关键的解读是：

- `core/channel/utils` 是 native SystemC 的核心重写区。
- `dt/tlm_core/tlm_utils` 更像“把上游的可复用部分搬进来，再用 native runtime 接住”。


## 6. native SystemC 的核心改动

### 6.1 头文件入口和 API 门面被重做

native 入口不是上游 `systemc` 头，而是 `src/systemc/ext/systemc` 和 `src/systemc/ext/systemc.h`。

它们做的事包括：

- 聚合 `core/channel/dt/utils` 的 native 头
- 提供 `using` 声明，兼容常见的 SystemC 用户代码
- 通过 `systemc_home/include` 目录模拟 `SYSTEMC_HOME/include` 的外观

这层的设计目标是：

- 让用户代码 `#include <systemc>` 时，仍能得到熟悉的 API 表面
- 但 API 背后的实现已经换成 `gem5 native runtime`

### 6.2 `sc_main` 和顶层驱动方式被改掉

native 实现中：

- `sc_main` 不是由上游 SystemC 内核直接驱动
- 而是通过 `ScMainFiber` 在 `gem5` 的控制流里执行

关键点：

- `sc_start()`、`sc_pause()`、`sc_stop()` 最终都落到 `sc_gem5::scheduler`
- `sc_time_stamp()` 直接读取 `scheduler.getCurTick()`
- `sc_delta_count()` 直接读取 scheduler 的 cycle 计数

这意味着：

- 顶层仿真控制权已经从上游 `libsystemc` 转移到 `gem5` 自己的调度器
- SystemC API 只是 native runtime 暴露出来的前端

### 6.3 内核生命周期接到 `gem5::SimObject`

`sc_gem5::Kernel` 是一个真正的 `gem5::SimObject`。

它会在 `gem5` 生命周期里接收：

- `init()`
- `regStats()`
- `startup()`

然后把这些阶段映射到 SystemC 生命周期：

- `before_end_of_elaboration`
- `end_of_elaboration`
- `start_of_simulation`
- `end_of_simulation`

这和上游 SystemC 最大的不同在于：

- native SystemC 的生命周期不是一个独立内核在管
- 而是挂在 `gem5` 的对象模型和事件队列之下

### 6.4 调度器被重写为 `gem5 event queue` 适配层

`scheduler.hh` 的注释已经把设计说得很清楚：

- initialization phase
- evaluate phase
- update phase
- delta notification phase
- timed notification phase

都由 `sc_gem5::Scheduler` 映射到 `gem5::EventQueue`。

native 调度器的关键特征：

- 用 `readyEvent/pauseEvent/stopEvent/starvationEvent/maxTickEvent` 等内部事件组织 phase 顺序
- 用 `TimeSlot` 聚合同一 tick 的 timed notifications
- 把 delta cycle、pause/stop、run-to-time 都转成 `gem5::Event` 的优先级安排

这不是“包装一下上游调度器”。

这是：

- 一套独立的 phase engine
- 目标是保持尽量接近 SystemC 语义
- 但底层完全依赖 `gem5` 的事件系统

### 6.5 `sc_event` 被包成 native 事件对象

在 native 实现里：

- `sc_core::sc_event` 内部带有一个 `sc_gem5::Event *`
- 真正的 notify/cancel/triggered/parent-child bookkeeping 都在 `sc_gem5::Event` 里

native `Event` 做的事包括：

- 维护事件名字、层级、父对象
- 维护静态敏感列表和动态敏感列表
- 维护 delayed notification 的 `ScEvent`
- 在 update phase 阻止非法 immediate notify
- 处理 `notify()`、`notify(t)`、`notify_delayed()`、`cancel()`

这说明：

- native `sc_event` 已经不再是上游库里那个对象
- 而是一个 front-end handle，后端逻辑完全交给 `gem5`

### 6.6 `sc_time` 被绑定到 `gem5 tick`

`sc_time` 是 native SystemC 中改动最关键的语义点之一。

native 路径下：

- `sc_time::val` 本质上就是基于 `gem5::Tick` 的计数
- 时间单位换算依赖 `gem5::sim_clock`
- 设置非零时间时会调用 `gem5::fixClockFrequency()`

直接影响：

- `sc_time` 的真实时间基准来自 `gem5` 的时钟定义
- `sc_time_stamp()` 返回的是当前 `gem5` tick 转换后的时间
- 上游 SystemC 独立维护的时间推进机制，在 native 路径里被 `gem5` 接管

### 6.7 进程模型被重写为 `Fiber + Process` 体系

native 实现中的进程对象是：

- `sc_gem5::Process`
- `Method`
- `Thread`
- `CThread`

它们不是上游 `sc_process_b` 的原始实现，而是：

- 继承 `sc_process_b`
- 再叠加 `gem5::Fiber`
- 再由 native scheduler 调度

显著特点：

- 进程切换靠 fiber
- kill/reset 通过异常注入实现
- timeout、dynamic sensitivity、static sensitivity 都由 native Process 持有
- reset 信号传播通过 `Reset` 对象挂到 `sc_signal_in_if<bool>` 上

也就是说：

- 上游 SystemC 的进程控制语义，在这里被 `gem5` 按自己的执行模型重新落地

### 6.8 `sc_spawn`、`sc_sensitive`、`wait/next_trigger` 等过程控制被重做

这一层改动不只是 API 兼容，而是把语义绑定到 native 调度器：

- `sc_spawn` 负责创建 native `Process`
- `sc_sensitive` 在 elaboration 期构造 native 静态敏感关系
- timeout/dynamic sensitivity 最终都落到 native `Sensitivity` 和 native scheduler

还可以看到一些本地工程化决定：

- `sc_spawn_options::set_stack_size()` 会记录请求，但当前实现会 `warn_once("Ignoring request to set stack size.")`
- 这说明 API 被保留了，但行为不完全等于上游实现

### 6.9 对象层级、命名和端口绑定被重做

`sc_object`、`sc_module`、`sc_port` 在 native 路径下都带有自己的 backend：

- `sc_gem5::Object`
- `sc_gem5::Module`
- `sc_gem5::Port`

这些对象负责：

- 维护对象树
- 分配唯一名字
- 维护 parent/child objects 与 child events
- 在 `before_end_of_elaboration / end_of_elaboration / start_of_simulation / end_of_simulation` 时回调模块和 export
- 执行 `sc_module::operator()` 的端口绑定

这层改动的重要意义是：

- native SystemC 不再依赖上游内核里那套对象注册栈
- 而是在 `gem5` 里维护一份自己的层级和绑定状态

### 6.10 通道实现改成 native 行为

`src/systemc/channel` 下面的 out-of-line 实现全是 `gem5` 自写，包括：

- `sc_clock`
- `sc_event_queue`
- `sc_mutex`
- `sc_semaphore`
- `sc_signal`
- `sc_signal_resolved`
- `sc_in_resolved`
- `sc_out_resolved`
- `sc_inout_resolved`

其中几个特别值得注意：

#### `sc_clock`

- 用内部 `ClockTick` 事件周期性调度
- 每个边沿都创建一个 native `Method`
- 在 `before_end_of_elaboration()` 里把 up/down edge 安排进 scheduler

所以 `sc_clock` 的边沿驱动完全交给 `gem5` 调度。

#### `sc_signal`

- writer checking 在 native 层实现
- 多 writer / delta-cycle conflict 会通过 native report 报错
- value change / posedge / negedge event 都是 native 内部事件
- reset 传播直接依附于 signal 对 reset listener 的维护

这意味着信号写冲突检测、事件发放、reset 联动都已经脱离上游实现。

### 6.11 报告、错误码和 tracing 被本地化

native 路径里的 `utils` 不是简单调用上游 `sc_report_handler`。

它做了三件事：

- 重新声明了一套 `SC_ID_*` 报错字符串和编号表
- 用 `gem5` 语义包装异常/report 行为
- 自己实现了 tracing/VCD 输出后端

例子：

- `core/messages.cc` 定义了大量 `SC_ID_*`
- `utils/messages.cc` 定义了 `SC_ID_NOT_IMPLEMENTED_` 等 utility 层消息
- `sc_trace_file.cc` 和 `vcd.cc` 负责 trace/VCD 输出

所以即便 API 名字仍然叫 `sc_report`/`sc_trace_file`，实现也已经是 native 版本。


## 7. 哪些部分主要还是上游代码

### 7.1 数据类型层

`src/systemc/dt` 里大部分文件仍然保留了 Accellera 版权头。

这说明：

- `sc_int` / `sc_uint` / `sc_signed` / `sc_unsigned`
- `sc_bit` / `sc_logic` / `sc_bv` / `sc_lv`
- `sc_fx*`

这些数据类型的大量实现仍然来自上游，只是被 native 头和 runtime 重新接入。

### 7.2 TLM core / tlm_utils

类似地：

- `src/systemc/ext/tlm_core/*`
- `src/systemc/tlm_core/*`
- `src/systemc/ext/systemc_home/include/tlm_utils/*`
- `src/systemc/tlm_utils/*`

很多内容都还是 Accellera 来源代码。

native 改动主要体现在：

- 头文件入口改为 `gem5` 自己的 API 门面
- 少量 out-of-line `.cc` 用 native runtime 接住
- 对 `gem5` 端口和 TLM socket 做桥接

### 7.3 `sc_vector` 之类是混合式改造

有些文件既保留上游代码，也叠加 `gem5` 改造，比如：

- `src/systemc/ext/utils/sc_vector.hh`

这类文件通常属于：

- 上游逻辑大量保留
- 针对 native runtime、C++11 类型萃取、错误处理方式做局部改动


## 8. `gem5` 特有扩展

### 8.1 Python SimObject 绑定

`SystemC.py` 暴露了三类对象：

- `SystemC_Kernel`
- `SystemC_ScObject`
- `SystemC_ScModule`

这让 SystemC 对象能够在 Python 配置脚本里以 `gem5` 对象的方式出现。

注意这里不是说：

- `sc_object` 真正继承了 `gem5::SimObject`

而是说：

- Python 配置层提供了一层映射
- C++ 层仍然维持 SystemC 对象本身的类型体系

### 8.2 `gem5_getPort()` 和 Port/TLM wrapper

native `sc_module` 额外提供了：

- `gem5_getPort(const std::string &, int)`

同时还有两类 wrapper：

- `sc_port_wrapper.hh`
- `tlm_port_wrapper.hh`

它们的作用是：

- 把 `sc_port` / `sc_export` / `sc_interface`
- 以及 TLM initiator/target socket

包装成 `gem5::Port`，让 SystemC/TLM 连接可以进入 `gem5` 端口图。

这部分完全不是上游 SystemC 的概念，而是 native 集成的关键扩展。

### 8.3 `tlm_bridge`

`src/systemc/tlm_bridge` 里实现了：

- `Gem5ToTlmBridge`
- `TlmToGem5Bridge`
- 一些示例/专用模块

它们让：

- `gem5 packet`
- `TLM transaction`

能在同一 native SystemC/gem5 环境里相互转换。


## 9. 测试策略

`src/systemc/tests` 很大，统计下来大约有 3583 个文件。

目录结构里能看到：

- `1666-2011-compliance`
- `communication`
- `kernel`
- `datatypes`
- `tracing`
- `tlm`
- `multi_sockets`
- `endian_conv`

这说明 native SystemC 的目标不是做一个“最小可编译接口”，而是尽量兼容：

- SystemC kernel 行为
- datatypes
- tracing
- TLM
- 标准/历史测试集

不过这并不等价于“它和上游内核完全相同”，因为底层 runtime 已经换成了 `gem5`。


## 10. 边界、风险和已知不一致点

### 10.1 `SYSTEMC_HOME` 在 native 路径里只是转发壳

native 构建时设置的：

- `SYSTEMC_HOME=src/systemc/ext/systemc_home`

不是完整的上游安装目录。

它只是给：

- `#include <systemc>`
- `#include <tlm>`
- `#include <tlm_utils/...>`

这些常见 include 路径提供兼容外观。

如果外部工程假设这里一定是标准 SystemC 安装树，就容易误判。

### 10.2 simulation phase callbacks 看起来并没有完整实现

这里需要明确区分“源码事实”和“推断”。

源码事实：

- native `core/messages.cc` 里定义了 phase callback 相关报错字符串
- 测试目录里也有 `kernel/phase_callbacks/*` 测试

我没找到的东西：

- `register_simulation_phase_callback`
- `unregister_simulation_phase_callback`

在 native `src/systemc` 里的实现入口

因此合理推断是：

- native SystemC 至少没有完整公开这部分实现
- 这块功能应当视为 unsupported 或 incomplete，除非后续另有外部补丁

### 10.3 API 在，行为不一定完全等于上游

一些典型例子：

- `sc_spawn_options::set_stack_size()` 当前会忽略请求并告警
- `sc_clock::write()` 直接 `panic`
- process control corner cases 有一套 native 报错逻辑
- `sc_time` 明确绑定到 `gem5` tick

所以 native SystemC 更接近：

- “尽量兼容上游 API 与常见语义”

而不是：

- “逐行逐行为上游内核做 ABI 兼容”

### 10.4 不能和外部 `libsystemc` 混用

这是最重要的边界。

原因不是简单的“命名冲突”，而是：

- `sc_event`、`sc_time`、`sc_process_b`、`sc_module`、`sc_simcontext`
- 在 native 路径下都已经绑定到了不同的 backend 对象和调度体系

如果同一进程里同时放入：

- `gem5 native SystemC`
- 外部原版 `libsystemc`

会至少遇到以下风险：

- ODR 冲突
- 符号重复/符号劫持
- 同名类型背后 runtime 不一致
- 两套 scheduler/时间基准/对象注册体系同时存在

### 10.5 `gem5` 自己的嵌入式文档也要求关闭 native SystemC

`util/systemc/gem5_within_systemc/README` 和 `util/tlm/README` 都写得很明确：

- 当把 `gem5` 作为库嵌入一个外部 SystemC 程序时，要用 `USE_SYSTEMC=n`
- 因为 `gem5` 的 native SystemC 会和 external SystemC 冲突

这和前面的分析完全一致。


## 11. 对协同仿真的实际建议

### 11.1 如果你的另一个模块链接的是“未改动的 SystemC 2.3.1”

推荐方案：

- 统一到外部原版 `SystemC 2.3.1`
- 把 `gem5` 构建成 `libgem5`
- 关闭 native SystemC：`USE_SYSTEMC=n`

原因：

- 这样进程内只有一套 `sc_core`
- 你的外部模块无需重写到 `gem5 native SystemC`
- 这是 `gem5` 自己提供的官方嵌入路径

### 11.2 不要默认把 `util/tlm` 链到 `gem5/ext/systemc/libsystemc`

虽然 `util/tlm` 默认会去构建并依赖 `ext/systemc/libsystemc`，但如果你的目标是：

- 和“未改动的原版 SystemC 2.3.1”模块同进程协同仿真

更合理的做法是：

- 把 `util/tlm` 也统一改成链接你那套外部原版 SystemC

否则进程里虽然都叫 “SystemC 2.3.1”，但实际仍有可能是两套略有差异的实现。

### 11.3 只有在你愿意把对方模块移植到 `gem5` 语义时，才考虑统一到 native

如果你选择统一到 native `src/systemc`，那意味着：

- 对方模块不能再链接原版 `libsystemc`
- 需要改为使用 `gem5` 的 native 头/构建路径
- 实际语义将受 `gem5` scheduler 和 `gem5` tick 驱动影响

这通常比“统一到原版 SystemC，再把 gem5 当库嵌进去”更激进。


## 12. 最终结论

`gem5 native SystemC` 的本质不是“给 SystemC 2.3.1 打几个补丁”，而是：

- 保留了大量上游 datatype/TLM 代码
- 但把 `sc_core` 的内核、调度器、时间、事件、进程、模块层大幅重写
- 并把它们接到了 `gem5` 的 SimObject 生命周期、EventQueue、Port/TLM 桥接机制上

因此：

- `ext/systemc` 是一个轻度改造过的上游分发版
- `src/systemc` 才是 `gem5 native SystemC`
- 二者不是“同一库的两个目录”，而是“vendor upstream” 和 “native runtime” 的关系

对需要与原版 SystemC 模块协同仿真的场景：

- 不要把 native `src/systemc` 和外部 `libsystemc` 混在同一进程
- 最稳妥的统一方式是选外部原版 SystemC，构建 `libgem5` 时关闭 `USE_SYSTEMC`
