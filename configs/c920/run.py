"""
XuanTie C920 simulation run script.

Usage:
  build/RISCV/gem5.opt configs/c920/run.py [--binary <path>]

Default binary: gem5-resources riscv-hello
"""

import argparse
import os

from cache_hierarchy import C920CacheHierarchy
from processor import C920Processor

import m5
from m5.objects import *

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.memory.dram_interfaces.ddr4 import DDR4_2400_8x8
from gem5.components.memory.memory import ChanneledMemory
from gem5.components.memory.simple import SingleChannelSimpleMemory
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.resources.resource import (
    BinaryResource,
    obtain_resource,
)
from gem5.simulate.simulator import Simulator

EXTERNAL_SYSTEMC_SIDECAR = "c920_external_systemc_simple_mem.conf"


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


def parse_args():
    parser = argparse.ArgumentParser(
        description="XuanTie C920 gem5 simulation"
    )
    mode_group = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "--binary",
        type=str,
        default=None,
        help="Path to RISC-V binary to run (SE mode)",
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


def main():
    args = parse_args()

    cache_hierarchy = C920CacheHierarchy(
        l1i_size=args.l1i_size,
        l1d_size=args.l1d_size,
        l2_size=args.l2_size,
    )

    if args.systemc_print_mem:
        from systemc_memory import C920SystemcPrintMemory

        print(
            "SystemC print-memory mode enabled: requests are forwarded to "
            "a SystemC print target and mirrored into gem5 physmem backing "
            "store for executable SE runs."
        )
        memory = C920SystemcPrintMemory(args.mem_size)
    elif args.systemc_simple_mem:
        from systemc_memory import C920SystemcSimpleMemory

        print(
            "SystemC simple-memory mode enabled: requests are forwarded "
            "through Gem5ToTlmBridge into a SystemC memory with "
            "SimpleMemory-like latency and bandwidth controls."
        )
        memory = C920SystemcSimpleMemory(
            size=args.mem_size,
            latency=args.simple_mem_latency,
            latency_var=args.simple_mem_latency_var,
            bandwidth=args.simple_mem_bandwidth,
        )
    elif args.external_systemc_simple_mem:
        from systemc_memory import C920ExternalSystemcSimpleMemory

        print(
            "External SystemC simple-memory mode enabled: gem5 will emit "
            "a tlm_slave config.ini plus a simple-memory sidecar for the "
            "standalone util/tlm runner."
        )
        memory = C920ExternalSystemcSimpleMemory(size=args.mem_size)
    elif args.gem5_simple_mem:
        print(
            "gem5 SimpleMemory mode enabled with explicit latency and "
            "bandwidth controls."
        )
        memory = SingleChannelSimpleMemory(
            latency=args.simple_mem_latency,
            latency_var=args.simple_mem_latency_var,
            bandwidth=args.simple_mem_bandwidth,
            size=args.mem_size,
        )
    elif args.zero_dram_latency:
        memory = SingleChannelDDR4_2400_NoDRAMTiming(args.mem_size)
    else:
        memory = SingleChannelDDR4_2400(args.mem_size)

    processor = C920Processor(num_cores=args.num_cores)

    board = SimpleBoard(
        clk_freq=args.clock,
        processor=processor,
        memory=memory,
        cache_hierarchy=cache_hierarchy,
    )

    if args.binary:
        board.set_se_binary_workload(
            binary=BinaryResource(local_path=os.path.abspath(args.binary))
        )
    else:
        board.set_se_binary_workload(binary=obtain_resource("riscv-hello"))

    if args.external_systemc_simple_mem:
        if hasattr(board.workload, "addr_check"):
            board.workload.addr_check = False
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
