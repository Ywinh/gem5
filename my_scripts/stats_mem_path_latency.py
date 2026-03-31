import argparse
import math
import sys


def parse_stats_file(stats_path):
    """
    Parse the last stats block in a gem5 stats.txt file.
    """
    blocks = []
    current = None

    try:
        with open(stats_path, encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.rstrip("\n")
                if "Begin Simulation Statistics" in line:
                    current = {}
                    continue
                if "End Simulation Statistics" in line:
                    if current is not None:
                        blocks.append(current)
                    current = None
                    continue
                if current is None:
                    continue

                # Remove comments and parse "<name> <value>" pairs.
                body = line.split("#", 1)[0].strip()
                if not body:
                    continue
                parts = body.split()
                if len(parts) < 2:
                    continue

                key = parts[0]
                value_str = parts[1]

                try:
                    value = float(value_str)
                except ValueError:
                    continue

                current[key] = value
    except FileNotFoundError:
        print(f"[!] Stats file not found: {stats_path}")
        sys.exit(1)

    if not blocks:
        print(f"[!] No stats block found in {stats_path}")
        sys.exit(1)

    return blocks[-1]


def get_required(stats, key):
    if key not in stats:
        print(f"[!] Required stat not found: {key}")
        sys.exit(1)
    return stats[key]


def get_optional(stats, key):
    return stats.get(key)


def to_cycles(ticks, ticks_per_cycle):
    return ticks / ticks_per_cycle


def fmt_value(value, ticks_per_cycle, unit_hint="ticks"):
    if value is None or math.isnan(value):
        return "N/A"
    if unit_hint == "ticks":
        return f"{value:.2f} ticks ({to_cycles(value, ticks_per_cycle):.2f} cycles)"
    return f"{value:.2f}"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Estimate LLC->DRAM path latency components from gem5 stats.txt. "
            "This is intended for comparing gem5 against hardware when you "
            "want to subtract DRAM-side and off-core bus-side latency."
        )
    )
    parser.add_argument("stats_file", help="Path to gem5 stats.txt")
    parser.add_argument(
        "--cpu-cycles-stat",
        default="board.processor.cores.core.numCycles",
        help="Stat name for CPU cycles. Default matches this repo's board config.",
    )
    parser.add_argument(
        "--llc-miss-lat-stat",
        default="board.cache_hierarchy.l2cache.demandAvgMissLatency::processor.cores.core.data",
        help="LLC demand miss average latency stat in ticks.",
    )
    parser.add_argument(
        "--dram-avg-lat-stat",
        default="board.memory.mem_ctrl.dram.avgMemAccLat",
        help="DRAM average access latency stat in ticks.",
    )
    parser.add_argument(
        "--dram-q-lat-stat",
        default="board.memory.mem_ctrl.dram.avgQLat",
        help="DRAM average queue latency stat in ticks.",
    )
    parser.add_argument(
        "--dram-bus-lat-stat",
        default="board.memory.mem_ctrl.dram.avgBusLat",
        help="DRAM average data-bus latency stat in ticks.",
    )
    parser.add_argument(
        "--llc-miss-total-stat",
        default="board.cache_hierarchy.l2cache.demandMissLatency::processor.cores.core.data",
        help="LLC demand miss total latency stat in ticks.",
    )
    parser.add_argument(
        "--llc-miss-count-stat",
        default="board.cache_hierarchy.l2cache.demandMisses::processor.cores.core.data",
        help="LLC demand miss count stat.",
    )
    parser.add_argument(
        "--requestor-read-accesses-stat",
        default="board.memory.mem_ctrl.requestorReadAccesses::processor.cores.core.data",
        help="CPU data read accesses serviced by mem_ctrl.",
    )
    parser.add_argument(
        "--requestor-read-total-lat-stat",
        default="board.memory.mem_ctrl.requestorReadTotalLat::processor.cores.core.data",
        help="CPU data read total latency as seen at mem_ctrl.",
    )
    parser.add_argument(
        "--dram-total-lat-stat",
        default="board.memory.mem_ctrl.dram.totMemAccLat",
        help="DRAM total access latency for all read bursts.",
    )
    parser.add_argument(
        "--dram-total-q-lat-stat",
        default="board.memory.mem_ctrl.dram.totQLat",
        help="DRAM total queue latency for all read bursts.",
    )
    parser.add_argument(
        "--dram-total-bus-lat-stat",
        default="board.memory.mem_ctrl.dram.totBusLat",
        help="DRAM total data-bus latency for all read bursts.",
    )
    parser.add_argument(
        "--membus-req-occ-stat",
        default="board.cache_hierarchy.membus.reqLayer0.occupancy",
        help="Memory-bus request layer occupancy stat in ticks.",
    )
    parser.add_argument(
        "--membus-resp-occ-stat",
        default="board.cache_hierarchy.membus.respLayer1.occupancy",
        help="Memory-bus response layer occupancy stat in ticks.",
    )
    parser.add_argument(
        "--membus-pkt-count-stat",
        default="board.cache_hierarchy.membus.pktCount::total",
        help="Memory-bus total packet count stat.",
    )
    args = parser.parse_args()

    stats = parse_stats_file(args.stats_file)

    sim_ticks = get_required(stats, "simTicks")
    cpu_cycles = get_required(stats, args.cpu_cycles_stat)
    ticks_per_cycle = sim_ticks / cpu_cycles

    llc_miss_lat = get_required(stats, args.llc_miss_lat_stat)
    dram_avg_lat = get_required(stats, args.dram_avg_lat_stat)
    dram_q_lat = get_required(stats, args.dram_q_lat_stat)
    dram_bus_lat = get_required(stats, args.dram_bus_lat_stat)
    llc_miss_total = get_required(stats, args.llc_miss_total_stat)
    llc_miss_count = get_required(stats, args.llc_miss_count_stat)
    requestor_read_accesses = get_optional(
        stats, args.requestor_read_accesses_stat
    )
    requestor_read_total_lat = get_optional(
        stats, args.requestor_read_total_lat_stat
    )
    dram_total_lat = get_optional(stats, args.dram_total_lat_stat)
    dram_total_q_lat = get_optional(stats, args.dram_total_q_lat_stat)
    dram_total_bus_lat = get_optional(stats, args.dram_total_bus_lat_stat)

    membus_req_occ = get_optional(stats, args.membus_req_occ_stat)
    membus_resp_occ = get_optional(stats, args.membus_resp_occ_stat)
    membus_pkt_count = get_optional(stats, args.membus_pkt_count_stat)

    coarse_non_dram = llc_miss_lat - dram_avg_lat

    membus_avg_pkt_occ = None
    if (
        membus_req_occ is not None
        and membus_resp_occ is not None
        and membus_pkt_count is not None
        and membus_pkt_count > 0
    ):
        membus_avg_pkt_occ = (
            membus_req_occ + membus_resp_occ
        ) / membus_pkt_count

    est_cpu_data_dram_total = None
    est_cpu_data_dram_q_total = None
    est_cpu_data_dram_bus_total = None
    est_cpu_data_membus_total = None
    est_cpu_data_offcore_total = None
    adj_sim_seconds_no_dram = None
    adj_sim_seconds_no_dram_bus = None
    adj_cycles_no_dram = None
    adj_cycles_no_dram_bus = None
    if requestor_read_accesses is not None:
        est_cpu_data_dram_total = requestor_read_accesses * dram_avg_lat
        est_cpu_data_dram_q_total = requestor_read_accesses * dram_q_lat
        est_cpu_data_dram_bus_total = requestor_read_accesses * dram_bus_lat
        if membus_avg_pkt_occ is not None:
            est_cpu_data_membus_total = (
                requestor_read_accesses * membus_avg_pkt_occ
            )
            est_cpu_data_offcore_total = (
                est_cpu_data_dram_total + est_cpu_data_membus_total
            )
        adj_sim_seconds_no_dram = (
            sim_ticks - est_cpu_data_dram_total
        ) / get_required(stats, "simFreq")
        adj_cycles_no_dram = (
            sim_ticks - est_cpu_data_dram_total
        ) / ticks_per_cycle
        if est_cpu_data_offcore_total is not None:
            adj_sim_seconds_no_dram_bus = (
                sim_ticks - est_cpu_data_offcore_total
            ) / get_required(stats, "simFreq")
            adj_cycles_no_dram_bus = (
                sim_ticks - est_cpu_data_offcore_total
            ) / ticks_per_cycle

    print(f"Stats file: {args.stats_file}")
    print(f"ticks_per_cycle: {ticks_per_cycle:.6f}")
    print()

    print("[Observable LLC miss latency]")
    print(
        f"  LLC miss avg latency: {fmt_value(llc_miss_lat, ticks_per_cycle)}"
    )
    print(
        f"  LLC miss total latency: {fmt_value(llc_miss_total, ticks_per_cycle)}"
    )
    print(f"  LLC miss count: {int(llc_miss_count)}")
    print()

    print("[DRAM-side latency]")
    print(f"  DRAM avg access:     {fmt_value(dram_avg_lat, ticks_per_cycle)}")
    print(f"  DRAM avg queue:      {fmt_value(dram_q_lat, ticks_per_cycle)}")
    print(f"  DRAM avg data bus:   {fmt_value(dram_bus_lat, ticks_per_cycle)}")
    if dram_total_lat is not None:
        print(
            f"  DRAM total access:   {fmt_value(dram_total_lat, ticks_per_cycle)}"
        )
    if dram_total_q_lat is not None:
        print(
            f"  DRAM total queue:    {fmt_value(dram_total_q_lat, ticks_per_cycle)}"
        )
    if dram_total_bus_lat is not None:
        print(
            f"  DRAM total data bus: {fmt_value(dram_total_bus_lat, ticks_per_cycle)}"
        )
    print()

    print("[LLC<->DRAM bus rough estimate]")
    if membus_avg_pkt_occ is not None:
        print(
            f"  membus avg occupancy per packet: "
            f"{fmt_value(membus_avg_pkt_occ, ticks_per_cycle)}"
        )
        print(
            "  note: this comes from (reqLayer0.occupancy + respLayer1.occupancy) "
            "/ pktCount::total, so it is a rough per-packet bus residency, "
            "not a strict per-read latency."
        )
        print(
            f"  membus total occupancy (all packets): "
            f"{fmt_value(membus_req_occ + membus_resp_occ, ticks_per_cycle)}"
        )
    else:
        print("  membus occupancy stats not found; skip bus estimate.")
    print()

    print("[Coarse subtractable estimate]")
    print(
        f"  LLC miss - DRAM avg access: {fmt_value(coarse_non_dram, ticks_per_cycle)}"
    )
    print("  formula: LLC_miss_avg_latency - DRAM_avgMemAccLat")
    print(
        "  meaning: everything outside the DRAM service window as seen from "
        "the LLC miss path, including interconnect/controller/bookkeeping."
    )
    print()

    print("[CPU data read total estimate]")
    if requestor_read_accesses is not None:
        print(
            f"  mem_ctrl cpu-data read accesses: {int(requestor_read_accesses)}"
        )
    if requestor_read_total_lat is not None:
        print(
            f"  mem_ctrl cpu-data total latency: "
            f"{fmt_value(requestor_read_total_lat, ticks_per_cycle)}"
        )
    if est_cpu_data_dram_total is not None:
        print(
            f"  est cpu-data DRAM total:         "
            f"{fmt_value(est_cpu_data_dram_total, ticks_per_cycle)}"
        )
    if est_cpu_data_dram_q_total is not None:
        print(
            f"  est cpu-data DRAM queue total:   "
            f"{fmt_value(est_cpu_data_dram_q_total, ticks_per_cycle)}"
        )
    if est_cpu_data_dram_bus_total is not None:
        print(
            f"  est cpu-data DRAM bus total:     "
            f"{fmt_value(est_cpu_data_dram_bus_total, ticks_per_cycle)}"
        )
    if est_cpu_data_membus_total is not None:
        print(
            f"  est cpu-data LLC<->DRAM bus total: "
            f"{fmt_value(est_cpu_data_membus_total, ticks_per_cycle)}"
        )
    if est_cpu_data_offcore_total is not None:
        print(
            f"  est cpu-data off-core total:     "
            f"{fmt_value(est_cpu_data_offcore_total, ticks_per_cycle)}"
        )
    print()

    print("[Adjusted total runtime]")
    print(f"  original simSeconds: {get_required(stats, 'simSeconds'):.12f}")
    if adj_sim_seconds_no_dram is not None:
        print(
            f"  adjusted simSeconds (no DRAM): {adj_sim_seconds_no_dram:.12f}"
        )
        print(f"  adjusted cycles (no DRAM):     {adj_cycles_no_dram:.2f}")
    if adj_sim_seconds_no_dram_bus is not None:
        print(
            f"  adjusted simSeconds (no DRAM+bus): "
            f"{adj_sim_seconds_no_dram_bus:.12f}"
        )
        print(
            f"  adjusted cycles (no DRAM+bus):     "
            f"{adj_cycles_no_dram_bus:.2f}"
        )
    print()

    print("[How to use]")
    print(
        "  If your hardware measurement should ignore off-core memory time, "
        "subtract at least the DRAM avg access term."
    )
    print(
        "  If you also want to ignore the LLC->DRAM on-chip bus contribution, "
        "use the membus estimate only as a rough reference, not as an exact value."
    )


if __name__ == "__main__":
    main()
