"""
Simple SE-mode example: TimingSimpleCPU + private L1s connected to N interleaved
L2 banks, backed by a SimpleMemory. Use with an ISA-matching binary (e.g.
`riscv-hello` built for RISC-V).

Example:
  ./build/RISCV/gem5.opt configs/example/cache_banked_riscv_se.py \
    --num-banks=4 --binary=/path/to/riscv-hello

This script focuses on showing how to set `AddrRange(..., intlv_*)` on each
bank so that addresses interleave across banks.
"""

import argparse
import math

from Caches import (
    L1_DCache,
    L1_ICache,
    L2Cache,
)

import m5
from m5.objects import *


def build_system(
    binary,
    num_banks=4,
    mem_size="1GB",
    line_size=64,
    l1_size="32KiB",
    l1_assoc=2,
    l2_size="256KiB",
    l2_assoc=8,
):
    assert (num_banks & (num_banks - 1)) == 0, "num_banks must be power of two"

    system = System()
    system.clk_domain = SrcClockDomain(
        clock="1GHz", voltage_domain=VoltageDomain()
    )
    system.cpu_clk_domain = system.clk_domain

    # Simple single CPU
    system.cpu = TimingSimpleCPU()
    system.cpu.createInterruptController()

    # Memory ranges
    system.mem_ranges = [AddrRange(mem_size)]

    # Main memory crossbar
    system.membus = SystemXBar()

    # L1-to-L2 bus
    system.tol2bus = L2XBar()

    # Create private L1 caches and attach to CPU
    l1i = L1_ICache(size=l1_size, assoc=l1_assoc)
    l1d = L1_DCache(size=l1_size, assoc=l1_assoc)

    system.cpu.addPrivateSplitL1Caches(l1i, l1d, None, None)

    # Create N interleaved L2 banks
    line_size_bits = int(math.log2(line_size))
    intlv_bits = int(math.log2(num_banks)) if num_banks > 1 else 0
    intlv_low_bit = line_size_bits

    l2_banks = []
    for i in range(num_banks):
        bank = L2Cache(size=l2_size, assoc=l2_assoc)
        # AddrRange: cover whole memory but match only interleaved subset
        if num_banks > 1:
            bank.addr_ranges = [
                AddrRange(
                    0,
                    size=system.mem_ranges[0].size,
                    intlv_bits=intlv_bits,
                    intlv_low_bit=intlv_low_bit,
                    intlv_match=i,
                )
            ]
        else:
            bank.addr_ranges = [AddrRange(system.mem_ranges[0])]

        # wire bank between tol2bus and membus
        # bank.cpu_side connects to tol2bus.mem_side_ports (L1s -> tol2bus -> banks)
        bank.cpu_side = system.tol2bus.mem_side_ports
        # bank.mem_side connects to main membus cpu side
        bank.mem_side = system.membus.cpu_side_ports

        l2_banks.append(bank)

    # Attach L1s and CPU ports to the buses (connectAllPorts uses this order)
    system.cpu.connectAllPorts(
        system.tol2bus.cpu_side_ports,
        system.membus.cpu_side_ports,
        system.membus.mem_side_ports,
    )

    # Simple memory controller backing store
    system.mem_ctrl = SimpleMemory(bandwidth="1GiB/s", latency="50ns")
    system.mem_ctrl.range = AddrRange(mem_size)
    system.mem_ctrl.port = system.membus.mem_side_ports

    # Workload/process
    process = Process()
    process.cmd = [binary]
    system.cpu.workload = process
    system.cpu.createThreads()

    root = Root(full_system=False, system=system)
    root.system.mem_mode = "timing"

    # attach l2_banks to the returned system object only as a Python attribute
    # (not a SimObject parameter) so callers can inspect them if desired.
    # Avoid assigning to `system` directly to prevent SimObject parameter errors.
    return root, system, l2_banks


parser = argparse.ArgumentParser()
parser.add_argument(
    "--num-banks",
    type=int,
    default=4,
    help="Number of interleaved L2 banks (power of two)",
)
parser.add_argument(
    "--binary",
    type=str,
    required=True,
    help="Path to SE-mode binary to run (ISA must match build)",
)
parser.add_argument(
    "--mem-size", default="1GB", help="System memory size (AddrRange)"
)
parser.add_argument(
    "--line-size", type=int, default=64, help="Cache line size in bytes"
)
parser.add_argument("--l1-size", default="32KiB")
parser.add_argument("--l2-size", default="256KiB")
args = parser.parse_args()

m5.ticks.setGlobalFrequency("1GHz")

root, system, l2_banks = build_system(
    args.binary,
    num_banks=args.num_banks,
    mem_size=args.mem_size,
    line_size=args.line_size,
    l1_size=args.l1_size,
    l2_size=args.l2_size,
)

print(f"Running binary: {args.binary}")
print(
    f"num_banks={args.num_banks}, line_size={args.line_size}, intlv_low_bit={int(math.log2(args.line_size)) if args.line_size>0 else 0}"
)

m5.instantiate()
print("Starting simulation...")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
