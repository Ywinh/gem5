import m5
from m5.objects import *

system = System()

system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]

system.cpu = TimingSimpleCPU()

# Create the simple memory object
system.memobj = DemoMemory()

system.cpu.icache_port = system.memobj.inst_port
system.cpu.dcache_port = system.memobj.data_port

system.membus = SystemXBar()

# Connect the memobj
system.memobj.mem_side = system.membus.cpu_side_ports

# create the interrupt controller for the CPU and connect to the membus
system.cpu.createInterruptController()
# RISCV不需要将中断控制器中的PIO和请求、访问端口与内存总线进行连接
# system.cpu.interrupts[0].pio = system.membus.mem_side_ports
# system.cpu.interrupts[0].int_master = system.membus.cpu_side_ports
# system.cpu.interrupts[0].int_slave = system.membus.mem_side_ports

# Create a DDR3 memory controller and connect it to the membus
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

# Create a process for a simple "Hello World" application
process = Process()

process.cmd = [binary]
# Set the cpu to use the process as its workload and create thread contexts
system.cpu.workload = process
system.cpu.createThreads()

# set up the root SimObject and start the simulation
root = Root(full_system=False, system=system)
# instantiate all of the objects we've created above
m5.instantiate()

print(f"Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
