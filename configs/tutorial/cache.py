import m5
from m5.objects import *


class L1Cache(Cache):
    """Simple L1 Cache with default values"""

    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20

    def __init__(self, options=None):
        super().__init__()
        pass

    def connectBus(self, bus):
        """Connect this cache to a memory-side bus"""
        self.mem_side = bus.cpu_side_ports

    def connectCPU(self, cpu):
        """Connect this cache's port to a CPU-side port
        This must be defined in a subclass"""
        raise NotImplementedError


class L1ICache(L1Cache):
    """Simple L1 instruction cache with default values"""

    # Set the default size
    size = "16KiB"

    def __init__(self, opts=None):
        super().__init__(opts)
        if not opts or not opts.l1i_size:
            return
        self.size = opts.l1i_size

    def connectCPU(self, cpu):
        """Connect this cache's port to a CPU icache port"""
        self.cpu_side = cpu.icache_port


class L1DCache(L1Cache):
    """Simple L1 data cache with default values"""

    # Set the default size
    size = "64KiB"

    def __init__(self, opts=None):
        super().__init__(opts)
        if not opts or not opts.l1d_size:
            return
        self.size = opts.l1d_size

    def connectCPU(self, cpu):
        """Connect this cache's port to a CPU dcache port"""
        self.cpu_side = cpu.dcache_port


class L2Cache(Cache):
    """Simple L2 Cache with default values"""

    # Default parameters
    size = "256KiB"
    assoc = 8
    tag_latency = 20
    data_latency = 20
    response_latency = 20
    mshrs = 20
    tgts_per_mshr = 12

    def __init__(self, opts=None):
        super().__init__()
        if not opts or not opts.l2_size:
            return
        self.size = opts.l2_size

    def connectCPUSideBus(self, bus):
        self.cpu_side = bus.mem_side_ports

    def connectMemSideBus(self, bus):
        self.mem_side = bus.cpu_side_ports


if __name__ == "__m5_main__":
    # create the system we are going to simulate
    system = System()

    # Set the clock frequency of the system (and all of its children)
    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = "1GHz"
    system.clk_domain.voltage_domain = VoltageDomain()

    # Set up the system
    system.mem_mode = "timing"  # Use timing accesses
    system.mem_ranges = [AddrRange("512MiB")]  # Create an address range

    # Create a simple CPU
    system.cpu = RiscvTimingSimpleCPU()

    # Create an L1 instruction and data cache
    system.cpu.icache = L1ICache()
    system.cpu.dcache = L1DCache()

    # Connect the instruction and data caches to the CPU
    system.cpu.icache.connectCPU(system.cpu)
    system.cpu.dcache.connectCPU(system.cpu)

    # Create a memory bus, a coherent crossbar, in this case
    system.l2bus = L2XBar()

    # Hook the CPU ports up to the l2bus
    system.cpu.icache.connectBus(system.l2bus)
    system.cpu.dcache.connectBus(system.l2bus)

    # Create an L2 cache and connect it to the l2bus
    system.l2cache = L2Cache()
    system.l2cache.connectCPUSideBus(system.l2bus)

    # Create a memory bus
    system.membus = SystemXBar()

    # Connect the L2 cache to the membus
    system.l2cache.connectMemSideBus(system.membus)

    # create the interrupt controller for the CPU
    system.cpu.createInterruptController()

    # Connect the system up to the membus
    system.system_port = system.membus.cpu_side_ports

    # Create a DDR3 memory controller
    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR3_1600_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports

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
