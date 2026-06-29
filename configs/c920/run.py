"""
XuanTie C920 simulation run script.

Usage:
  build/RISCV/gem5.opt configs/c920/run.py [--binary <path>]

This variant runs the workload as RISC-V FS bare-metal so fixed MMIO
addresses are treated as physical addresses.
"""

import argparse
import os

from cache_hierarchy import C920CacheHierarchy
from processor import C920Processor

import m5
from m5.objects import *
from m5.util import warn

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.memory.dram_interfaces.ddr4 import DDR4_2400_8x8
from gem5.components.memory.memory import ChanneledMemory
from gem5.components.memory.simple import SingleChannelSimpleMemory
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.resources.resource import BinaryResource
from gem5.simulate.simulator import Simulator

EXTERNAL_SYSTEMC_SIDECAR = "c920_external_systemc_simple_mem.conf"
FIFO_BASE = 0x0A082000
FIFO_SIZE = 0x80
EXIT_REG_SIZE = 0x8
FIFO_WINDOW_SIZE = FIFO_SIZE + EXIT_REG_SIZE


class DDR4_2400_8x8_NoDRAMTiming(DDR4_2400_8x8):
    """
    Preserve the DDR4_2400_8x8 geometry and controller path while collapsing
    the DRAM timing constraints to near-zero.
    """

    # Keep the DDR4 command clock so command-window accounting is unchanged.
    tCK = "0.833ns"

    # Collapse the DRAM service timing, but keep the ordering relations
    # required by DRAMInterface sanity checks.
    tBURST = "1ps"
    tBURST_MIN = "1ps"
    tBURST_MAX = "1ps"
    tRCD = "1ps"
    tRCD_WR = "1ps"
    tCL = "1ps"
    tCWL = "1ps"
    tRP = "1ps"
    tRAS = "1ps"
    tRRD = "1ps"
    tRRD_L = "1ps"
    tXAW = "4ps"
    tRFC = "1ps"
    tWR = "1ps"
    tWTR = "1ps"
    tWTR_L = "1ps"
    tRTP = "1ps"
    tRTW = "1ps"
    tCS = "1ps"
    tXP = "1ps"
    tXS = "1ps"

    # These must stay strictly larger than tBURST for DDR4 bank groups.
    tCCD_L = "2ps"
    tCCD_L_WR = "2ps"

    # Keep refresh enabled but make the refresh service time negligible.
    tREFI = "7.8us"


def SingleChannelDDR4_2400_NoDRAMTiming(size: str):
    return ChanneledMemory(DDR4_2400_8x8_NoDRAMTiming, 1, 64, size=size)


class C920BareMetalBoard(SimpleBoard):
    def _setup_memory_ranges(self) -> None:
        memory = self.get_memory()
        self.mem_ranges = [AddrRange(start=0x80000000, size=memory.get_size())]
        memory.set_memory_range(self.mem_ranges)

    def set_baremetal_workload(self, binary: BinaryResource) -> None:
        if self.is_workload_set():
            warn("Workload has been set more than once!")
        self.set_is_workload_set(True)
        self._set_fullsystem(True)
        self.workload = RiscvBareMetal(
            bootloader=binary.get_local_path(),
            auto_reset_vect=True,
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="XuanTie C920 gem5 simulation"
    )
    mode_group = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "--binary",
        type=str,
        default=None,
        help="Path to RISC-V bare-metal ELF to run (FS bare-metal mode)",
    )
    parser.add_argument(
        "--num-cores",
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help="Number of C920 cores (1-4)",
    )
    parser.add_argument(
        "--l1i-size", type=str, default="32KiB", help="L1 I-Cache size"
    )
    parser.add_argument(
        "--l1d-size", type=str, default="32KiB", help="L1 D-Cache size"
    )
    parser.add_argument(
        "--l2-size", type=str, default="256KiB", help="L2 Cache size"
    )
    parser.add_argument(
        "--mem-size", type=str, default="1GB", help="Main memory size"
    )
    parser.add_argument(
        "--clock", type=str, default="1GHz", help="CPU clock frequency"
    )
    parser.add_argument(
        "--num-systems",
        type=int,
        default=1,
        choices=[1, 2],
        help=(
            "Instantiate this many independent C920 systems under one root. "
            "Each system keeps its own address map and FIFO ExternalSlave."
        ),
    )
    parser.add_argument(
        "--fifo-port-prefix",
        type=str,
        default="transactor",
        help=(
            "Base port_data name used for FIFO ExternalSlave endpoints. "
            "When --num-systems > 1, the system index is appended."
        ),
    )
    parser.add_argument(
        "--system-name-prefix",
        type=str,
        default="sys",
        help="Prefix used for the generated root child system names.",
    )
    mode_group.add_argument(
        "--zero-dram-latency",
        action="store_true",
        help=(
            "Preserve DDR4 burst structure/controller path but collapse "
            "DRAM timing"
        ),
    )
    mode_group.add_argument(
        "--systemc-print-mem",
        action="store_true",
        help=(
            "Route memory traffic through Gem5ToTlmBridge and a "
            "SystemC print target"
        ),
    )
    mode_group.add_argument(
        "--gem5-simple-mem",
        action="store_true",
        help=(
            "Use gem5 SimpleMemory with explicit latency/bandwidth controls"
        ),
    )
    mode_group.add_argument(
        "--systemc-simple-mem",
        action="store_true",
        help=(
            "Route memory traffic through Gem5ToTlmBridge into a "
            "SystemC simple memory"
        ),
    )
    mode_group.add_argument(
        "--external-systemc-simple-mem",
        action="store_true",
        help=(
            "Generate a util/tlm tlm_slave config so memory traffic runs "
            "against an external SystemC simple memory"
        ),
    )
    parser.add_argument(
        "--simple-mem-latency",
        type=str,
        default="30ns",
        help=(
            "Request-to-response latency for gem5/SystemC simple "
            "memory modes"
        ),
    )
    parser.add_argument(
        "--simple-mem-latency-var",
        type=str,
        default="0ns",
        help=("Latency variation for gem5/SystemC simple memory modes"),
    )
    parser.add_argument(
        "--simple-mem-bandwidth",
        type=str,
        default="12.8GiB/s",
        help=(
            "Combined read/write bandwidth for gem5/SystemC simple "
            "memory modes"
        ),
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Optional tick limit for short SystemC connectivity runs",
    )
    return parser.parse_args()


def write_external_systemc_sidecar(args) -> str:
    os.makedirs(m5.options.outdir, exist_ok=True)
    sidecar_path = os.path.join(m5.options.outdir, EXTERNAL_SYSTEMC_SIDECAR)

    with open(sidecar_path, "w", encoding="utf-8") as sidecar:
        sidecar.write("# Auto-generated by configs/c920/run.py\n")
        sidecar.write(f"latency={args.simple_mem_latency}\n")
        sidecar.write(f"latency_var={args.simple_mem_latency_var}\n")
        sidecar.write(f"bandwidth={args.simple_mem_bandwidth}\n")

    return sidecar_path


def validate_args(args) -> None:
    if not args.binary:
        raise ValueError("--binary is required for the C920 bare-metal run.")

    if args.num_systems > 1 and (
        args.systemc_print_mem
        or args.systemc_simple_mem
        or args.external_systemc_simple_mem
    ):
        raise ValueError(
            "Multi-system mode currently supports only gem5-local memory "
            "backends. The FIFO ExternalSlave remains enabled per system."
        )


def fifo_port_data(args, system_index: int) -> str:
    if args.num_systems == 1:
        return args.fifo_port_prefix

    return f"{args.fifo_port_prefix}{system_index}"


def create_memory(args):
    if args.systemc_print_mem:
        from systemc_memory import C920SystemcPrintMemory

        print(
            "SystemC print-memory mode enabled: requests are forwarded to "
            "a SystemC print target and mirrored into gem5 physmem backing "
            "store for executable SE runs."
        )
        return C920SystemcPrintMemory(args.mem_size)

    if args.systemc_simple_mem:
        from systemc_memory import C920SystemcSimpleMemory

        print(
            "SystemC simple-memory mode enabled: requests are forwarded "
            "through Gem5ToTlmBridge into a SystemC memory with "
            "SimpleMemory-like latency and bandwidth controls."
        )
        return C920SystemcSimpleMemory(
            size=args.mem_size,
            latency=args.simple_mem_latency,
            latency_var=args.simple_mem_latency_var,
            bandwidth=args.simple_mem_bandwidth,
        )

    if args.external_systemc_simple_mem:
        from systemc_memory import C920ExternalSystemcSimpleMemory

        print(
            "External SystemC simple-memory mode enabled: gem5 will emit "
            "a tlm_slave config.ini plus a simple-memory sidecar for the "
            "standalone util/tlm runner."
        )
        return C920ExternalSystemcSimpleMemory(size=args.mem_size)

    if args.gem5_simple_mem:
        print(
            "gem5 SimpleMemory mode enabled with explicit latency and "
            "bandwidth controls."
        )
        return SingleChannelSimpleMemory(
            latency=args.simple_mem_latency,
            latency_var=args.simple_mem_latency_var,
            bandwidth=args.simple_mem_bandwidth,
            size=args.mem_size,
        )

    if args.zero_dram_latency:
        return SingleChannelDDR4_2400_NoDRAMTiming(args.mem_size)

    return SingleChannelDDR4_2400(args.mem_size)


def configure_fifo_pma(processor: C920Processor) -> None:
    fifo_range = AddrRange(FIFO_BASE, size=FIFO_WINDOW_SIZE)
    for core in processor.get_cores():
        pma = core.get_mmu().pma_checker
        pma.uncacheable = [fifo_range]
        # pma.strict_order = [fifo_range]


def build_board(args, system_index: int = 0):
    cache_hierarchy = C920CacheHierarchy(
        l1i_size=args.l1i_size,
        l1d_size=args.l1d_size,
        l2_size=args.l2_size,
        fifo_port_data=fifo_port_data(args, system_index),
        fifo_base=FIFO_BASE,
        fifo_size=FIFO_WINDOW_SIZE,
    )

    memory = create_memory(args)
    processor = C920Processor(num_cores=args.num_cores)
    configure_fifo_pma(processor)

    board = C920BareMetalBoard(
        clk_freq=args.clock,
        processor=processor,
        memory=memory,
        cache_hierarchy=cache_hierarchy,
    )
    board.set_baremetal_workload(
        binary=BinaryResource(local_path=os.path.abspath(args.binary))
    )

    if args.external_systemc_simple_mem and hasattr(
        board.workload, "addr_check"
    ):
        board.workload.addr_check = False

    return board


def attach_board_to_root(root: Root, system_name: str, board) -> None:
    board._connect_things()
    setattr(root, system_name, board)

    board.get_processor()._pre_instantiate(root)
    board.get_memory()._pre_instantiate(root)
    if board.get_cache_hierarchy():
        board.get_cache_hierarchy()._pre_instantiate(root)


def run_multi_system(args) -> None:
    boards = []
    for system_index in range(args.num_systems):
        system_name = f"{args.system_name_prefix}{system_index}"
        board = build_board(args, system_index)
        boards.append((system_name, board))

    print(
        f"Multi-system mode enabled: building {args.num_systems} independent "
        "C920 systems under one root."
    )
    for system_index, (system_name, _) in enumerate(boards):
        print(
            f"  {system_name}: FIFO ExternalSlave port_data="
            f"{fifo_port_data(args, system_index)}"
        )

    root = Root(full_system=all(board.is_fullsystem() for _, board in boards))
    for system_name, board in boards:
        attach_board_to_root(root, system_name, board)

    max_ticks = m5.MaxTick if args.max_ticks is None else args.max_ticks
    m5.instantiate()

    for _, board in boards:
        board._post_instantiate()

    exit_event = m5.simulate(max_ticks)
    print(f"Exiting @ tick {m5.curTick()} because " f"{exit_event.getCause()}")
    print("Simulation Done")


def main():
    args = parse_args()
    validate_args(args)

    if args.num_systems > 1:
        run_multi_system(args)
        return

    board = build_board(args)

    if args.external_systemc_simple_mem:
        sidecar_path = write_external_systemc_sidecar(args)
        config_path = os.path.join(m5.options.outdir, "config.ini")
        print(f"External SystemC sidecar written to: {sidecar_path}")
        print(
            "After gem5 emits the config, run: "
            f"util/tlm/build/examples/c920_simple_mem/gem5.sc {config_path}"
        )
        print(
            "This gem5 invocation is expected to stop once the ExternalSlave "
            "port handler is needed; the handler lives in the external "
            "SystemC executable."
        )

    simulator = Simulator(board=board)
    simulator.run(max_ticks=args.max_ticks)

    print("Simulation Done")


if __name__ == "__m5_main__":
    main()
