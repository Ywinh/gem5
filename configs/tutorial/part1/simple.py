# 导入m5库
import m5

# 导入所有SimObjects
from m5.objects import *

system = System()

system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]

system.cpu = RiscvTimingSimpleCPU()

system.membus = SystemXBar()
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports
system.cpu.createInterruptController()

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports
# Connect the system up to the membus
system.system_port = system.membus.cpu_side_ports

# 二进制可执行文件
binary = "tests/test-progs/hello/bin/riscv/linux/hello"
# 设置负载
system.workload = SEWorkload.init_compatible(binary)
# 实例化进程
process = Process()
# 然后将 processes 命令设置为要运行的命令。这是一个类似于 argv 的列表，可执行文件位于第一个位置，可执行文件的参数位于列表的其余部分。
process.cmd = [binary]
# 将 CPU 设置为使用进程作为其工作负载
system.cpu.workload = process
# 创建线程

system.cpu.createThreads()
# 设置root作为模拟对象（SE模式）
root = Root(full_system=False, system=system)
# 实例化以上所有我们创建的 SimObject
m5.instantiate()

print(f"Beginning simulation!")
# 一旦模拟完成，就可以检查系统的状态。
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
