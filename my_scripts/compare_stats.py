#!/usr/bin/env python3
"""
Compare key gem5 counters for the C920 bridge timing study.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

STAT_RE = re.compile(
    r"^(?P<name>\S+)\s+(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+|nan|inf|-inf))"
)


@dataclass(frozen=True)
class Metric:
    label: str
    kind: str


SUM_PATTERNS = {
    "simTicks": re.compile(r"^simTicks$"),
    "numCycles": re.compile(r"^board\.processor\.cores.*\.numCycles$"),
    "numInsts": re.compile(
        r"^board\.processor\.cores.*\.commitStats\d+\.numInsts$"
    ),
    "membusPktCount": re.compile(
        r"^board\.cache_hierarchy\.membus\.pktCount::total$"
    ),
    "l2OverallMisses": re.compile(
        r"^board\.cache_hierarchy\.l2cache\.overallMisses::total$"
    ),
    "hostSeconds": re.compile(r"^hostSeconds$"),
}


METRICS = [
    Metric("simTicks", "threshold"),
    Metric("numCycles", "threshold"),
    Metric("numInsts", "secondary"),
    Metric("membusPktCount", "secondary"),
    Metric("l2OverallMisses", "secondary"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare key stats for gem5 vs SystemC memory runs."
    )
    parser.add_argument("baseline", type=Path, help="Baseline stats.txt path")
    parser.add_argument(
        "candidate", type=Path, help="Candidate stats.txt path"
    )
    parser.add_argument(
        "--timing-threshold-pct",
        type=float,
        default=3.0,
        help="Allowed relative difference for simTicks and numCycles",
    )
    parser.add_argument(
        "--secondary-threshold-pct",
        type=float,
        default=0.5,
        help=(
            "Allowed relative difference for secondary counters such as "
            "numInsts and cache/bus counts"
        ),
    )
    return parser.parse_args()


def load_stats(path: Path) -> dict[str, float]:
    stats: dict[str, float] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            match = STAT_RE.match(line.strip())
            if not match:
                continue
            stats[match.group("name")] = float(match.group("value"))
    return stats


def collect_metric(stats: dict[str, float], name: str) -> float:
    pattern = SUM_PATTERNS[name]
    values = [value for key, value in stats.items() if pattern.match(key)]
    if not values:
        raise KeyError(f"Unable to find metric '{name}' in stats")
    return sum(values)


def relative_diff_pct(baseline: float, candidate: float) -> float:
    if baseline == 0:
        return 0.0 if candidate == 0 else math.inf
    return abs(candidate - baseline) / abs(baseline) * 100.0


def format_value(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.6f}"


def main() -> int:
    args = parse_args()
    baseline_stats = load_stats(args.baseline)
    candidate_stats = load_stats(args.candidate)

    results = {}
    for metric in METRICS:
        baseline_value = collect_metric(baseline_stats, metric.label)
        candidate_value = collect_metric(candidate_stats, metric.label)
        diff_pct = relative_diff_pct(baseline_value, candidate_value)

        if metric.kind == "threshold":
            passed = diff_pct <= args.timing_threshold_pct
        elif metric.kind == "secondary":
            passed = diff_pct <= args.secondary_threshold_pct
        else:
            raise ValueError(f"Unknown metric kind: {metric.kind}")

        results[metric.label] = (
            baseline_value,
            candidate_value,
            diff_pct,
            passed,
        )

    print("Metric comparison:")
    overall_pass = True
    for metric in METRICS:
        baseline_value, candidate_value, diff_pct, passed = results[
            metric.label
        ]
        overall_pass &= passed

        if metric.kind == "threshold":
            rule = f"<= {args.timing_threshold_pct:.2f}%"
        elif metric.kind == "secondary":
            rule = f"<= {args.secondary_threshold_pct:.2f}%"
        else:
            rule = "unknown"

        status = "PASS" if passed else "FAIL"
        print(
            f"  {metric.label}: baseline={format_value(baseline_value)} "
            f"candidate={format_value(candidate_value)} "
            f"diff={diff_pct:.6f}% rule={rule} => {status}"
        )

    try:
        baseline_host = collect_metric(baseline_stats, "hostSeconds")
        candidate_host = collect_metric(candidate_stats, "hostSeconds")
        print(
            "Host runtime (informational only): "
            f"baseline={format_value(baseline_host)}s "
            f"candidate={format_value(candidate_host)}s"
        )
    except KeyError:
        pass

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
