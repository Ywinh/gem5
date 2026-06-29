# 设置反汇编风格与输出格式（可选）
set disassembly-flavor intel
set output-radix 16
set print pretty on

# 设置断点（根据你的调试目标修改）
b Process::initState()

# 6. 运行 gem5 并加载配置脚本
run /tmp/dramsys_riscv_hello.py

layout split
