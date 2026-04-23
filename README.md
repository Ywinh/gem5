本开发分支基于 stable 分支 25.0.0.1 版本(commit ddd4ae35adb0a3df1f1ba11e9a973a5c2f8c2944 (tag: v25.0.0.1, tag: v25.0, origin/stable, prefetcher))
> 说明：截止 2026.4 gem5 官方最新 stable 版本是 25.1.0.1，如有需要的 feature 可以考虑 merge 到此 repo

原有的 [gem5 README](./gem5-README.md)

# Get started
## Build

## 已有修改说明
> 下面只简单说明哪些目录下的文件新增或者修改，具体修改查看 commit

新增：
1. configs/c920/ 目录下是玄铁c920的配置文件，具体使用方法见 [920-README](./configs/c920/README.md)

2. configs/906 目录下是玄铁906的配置文件

3. configs/920 目前是废弃状态，不过内部的 banked cache 有参考意义，展示了配置交织的地址来建模 cache 分块；Ruby 也是一个例子

4. src/systemc/tlm_bridge/c920* 是用于 test gem5-systemc bridge 功能正确性和性能正确性的 demo

5. ruby/proctocol 内的 MyMSI 是自定义的一组一致性协议，可参考

6. case/riscv-test 是来自官方 gem5-resource 的一些指令测试

7. my_scripts 是一些 python 脚本，具体如何执行todo

8. config/tutorial 和 src/bootcamp 是 gem5 bootcamp 的一些例子

修改：
1. src/arch/riscv/ 下寄存器相关，增加了玄铁寄存器的识别，目前仅仅能识别，没有实现对寄存器读写实现对应的功能回调，后期需要可以加上

2. util/tlm
    * fix 了官方的一个 random 报错
    * 把 tlm 接口换成更新的风格
    * scons 配置了一下 conda 环境，如果要试这个例子建议退回到 stable 分支，此处修改不一定适合所有用户环境
