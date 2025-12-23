from m5.objects import (
    AddrRange,
    Cache,
    Clock,
    Root,
    SrcClockDomain,
    System,
    SystemXBar,
    VoltageDomain,
)
from m5.util import convert


def make_banked_caches(
    num_banks=4, mem_size="1GB", line_size=64, cache_size="64kB", cache_assoc=4
):
    # interleave parameters
    # intlv_bits: number of low-order address bits used to select bank (log2(num_banks))
    # intlv_low_bit: first bit of the interleave field (typically the cache-line offset width)
    # intlv_match: which bank index this cache should serve (0..num_banks-1)
    import math

    system = System()
    system.mem_ranges = [AddrRange(mem_size)]

    # simple system bus to attach caches to (example)
    system.membus = SystemXBar()

    # typical values
    line_size_bits = int(math.log2(line_size))
    intlv_bits = int(math.log2(num_banks))
    intlv_low_bit = (
        line_size_bits  # interleave at the first bit above the line offset
    )

    caches = []
    for i in range(num_banks):
        c = Cache(size=cache_size, assoc=cache_assoc, line_size=line_size)
        # assign an AddrRange that covers the whole memory but selects only
        # addresses matching this bank via the interleaving match
        c.addr_ranges = [
            AddrRange(
                0,
                size=system.mem_ranges[0].size,
                intlv_bits=intlv_bits,
                intlv_low_bit=intlv_low_bit,
                intlv_match=i,
            )
        ]
        # connect cache to system bus (example connections; adapt as needed)
        # caches typically have cpu_side and mem_side ports - here we wire mem_side
        c.mem_side = system.membus.slave
        caches.append(c)

    # minimal required system fields for running gem5 (fill in as needed)
    system.root = Root(full_system=False, system=system)

    # return the built objects for further wiring/usage by the caller
    return system, caches


if __name__ == "__main__":
    # quick smoke example: build 4 banks with 64B lines
    system, caches = make_banked_caches(
        num_banks=4, mem_size="2GB", line_size=64
    )
    # the rest of a runnable script would do simulator setup and run; this snippet
    # focuses on the cache banking pattern (addr_ranges with interleaving).
