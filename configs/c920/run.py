"""
XuanTie C920 simulation run script.

Usage:
  build/RISCV/gem5.opt configs/c920/run.py [--binary <path>]

Default binary: gem5-resources riscv-hello
"""

import argparse

from cache_hierarchy import C920CacheHierarchy
from processor import C920Processor

from m5.objects import *

from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.resources.resource import (
    BinaryResource,
    obtain_resource,
)
from gem5.simulate.simulator import Simulator


def parse_args():
    parser = argparse.ArgumentParser(
        description="XuanTie C920 gem5 simulation"
    )
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
    return parser.parse_args()


def main():
    args = parse_args()

    cache_hierarchy = C920CacheHierarchy(
        l1i_size=args.l1i_size,
        l1d_size=args.l1d_size,
        l2_size=args.l2_size,
    )

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
            binary=BinaryResource(local_path=args.binary)
        )
    else:
        board.set_se_binary_workload(binary=obtain_resource("riscv-hello"))

    simulator = Simulator(board=board)
    simulator.run()

    print("Simulation Done")


if __name__ == "__m5_main__":
    main()
