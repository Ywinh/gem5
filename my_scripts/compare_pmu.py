#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

Number = int | float | None
ValueFn = Callable[[dict[str, Number], dict[str, Number]], Number]


@dataclass(frozen=True)
class Candidate:
    label: str
    fn: ValueFn


@dataclass(frozen=True)
class Row:
    event: str
    hw_fn: ValueFn
    primary: Candidate


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_number(raw: str) -> Number:
    try:
        if any(ch in raw for ch in ".eE"):
            return float(raw)
        return int(raw)
    except ValueError:
        return None


def parse_hw(path: Path) -> dict[str, Number]:
    values: dict[str, Number] = {}
    event_re = re.compile(r"\(([^)]+)\)\s*=\s*([0-9]+)")
    time_re = re.compile(r"\[@([0-9]+)ps")
    with path.open() as fh:
        for line in fh:
            if match := event_re.search(line):
                values[match.group(1)] = int(match.group(2))
            if match := time_re.search(line):
                values["__time_seconds__"] = int(match.group(1)) / 1e12
    return values


def parse_stats(path: Path) -> dict[str, Number]:
    values: dict[str, Number] = {}
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("-"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            values[parts[0]] = parse_number(parts[1])
    return values


def hw_key(name: str) -> ValueFn:
    return lambda hw, stats: hw.get(name)


def stat_key(name: str) -> ValueFn:
    return lambda hw, stats: stats.get(name)


def sum_stats(*names: str) -> ValueFn:
    return lambda hw, stats: sum((stats.get(name) or 0) for name in names)


def fmt_number(value: Number) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.6f}"
    return str(int(value))


def calc_delta(hw_value: Number, gem5_value: Number) -> Number:
    if hw_value is None or gem5_value is None:
        return None
    return gem5_value - hw_value


def calc_ratio(hw_value: Number, gem5_value: Number) -> Number:
    if hw_value is None or gem5_value is None or hw_value == 0:
        return None
    return gem5_value / hw_value


def display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def pad(text: str, width: int, align: str = "left") -> str:
    padding = max(width - display_width(text), 0)
    if align == "right":
        return " " * padding + text
    return text + " " * padding


def format_row(
    values: list[str], widths: list[int], numeric_cols: set[int]
) -> str:
    cells = []
    for index, value in enumerate(values):
        align = "right" if index in numeric_cols else "left"
        cells.append(pad(value, widths[index], align))
    return "  ".join(cells)


def build_rows() -> list[Row]:
    return [
        Row(
            "总时间",
            hw_key("__time_seconds__"),
            Candidate("simSeconds", stat_key("simSeconds")),
        ),
        Row(
            "L1 ICache Miss",
            hw_key("L1 ICache Miss"),
            Candidate(
                "board.cache_hierarchy.l1icaches.overallMisses::total",
                stat_key(
                    "board.cache_hierarchy.l1icaches.overallMisses::total"
                ),
            ),
        ),
        Row(
            "I-UTLB Miss",
            hw_key("I-UTLB Miss"),
            Candidate(
                "board.processor.cores.core.mmu.itb.misses",
                stat_key("board.processor.cores.core.mmu.itb.misses"),
            ),
        ),
        Row(
            "D-UTLB Miss",
            hw_key("D-UTLB Miss"),
            Candidate(
                "board.processor.cores.core.mmu.dtb.misses",
                stat_key("board.processor.cores.core.mmu.dtb.misses"),
            ),
        ),
        Row(
            "Conditional Branch",
            hw_key("Conditional Branch"),
            Candidate(
                "board.processor.cores.core.commitStats0.committedControl::IsCondControl",
                stat_key(
                    "board.processor.cores.core.commitStats0.committedControl::IsCondControl"
                ),
            ),
        ),
        Row(
            "Store Instruction",
            hw_key("Store Instruction"),
            Candidate(
                "board.processor.cores.core.commit.committedInstType_0::MemWrite",
                stat_key(
                    "board.processor.cores.core.commit.committedInstType_0::MemWrite"
                ),
            ),
        ),
        Row(
            "LDST Instruction",
            hw_key("LDST Instruction"),
            Candidate(
                "MemRead + MemWrite",
                sum_stats(
                    "board.processor.cores.core.commit.committedInstType_0::MemRead",
                    "board.processor.cores.core.commit.committedInstType_0::MemWrite",
                ),
            ),
        ),
        Row(
            "L1 DCache store access",
            hw_key("L1 DCache store access"),
            Candidate(
                "board.processor.cores.core.commit.committedInstType_0::MemWrite",
                stat_key(
                    "board.processor.cores.core.commit.committedInstType_0::MemWrite"
                ),
            ),
        ),
        Row(
            "ALU Instruction",
            hw_key("ALU Instruction"),
            Candidate(
                "board.processor.cores.core.commit.committedInstType_0::IntAlu",
                stat_key(
                    "board.processor.cores.core.commit.committedInstType_0::IntAlu"
                ),
            ),
        ),
        Row(
            "L1 ICache Access",
            hw_key("L1 ICache Access"),
            Candidate(
                "board.cache_hierarchy.l1icaches.overallAccesses::total",
                stat_key(
                    "board.cache_hierarchy.l1icaches.overallAccesses::total"
                ),
            ),
        ),
        Row(
            "JTLB Miss",
            hw_key("JTLB Miss"),
            Candidate("无直接对应", lambda hw, stats: None),
        ),
        Row(
            "Conditional Branch Mispredict",
            hw_key("Conditional Branch Mispredict"),
            Candidate(
                "board.processor.cores.core.branchPred.mispredictDueToPredictor_0::DirectCond",
                stat_key(
                    "board.processor.cores.core.branchPred.mispredictDueToPredictor_0::DirectCond"
                ),
            ),
        ),
        Row(
            "Indirect Branch",
            hw_key("Indirect Branch"),
            Candidate(
                "board.processor.cores.core.branchPred.indirectLookups",
                stat_key(
                    "board.processor.cores.core.branchPred.indirectLookups"
                ),
            ),
        ),
        Row(
            "Indirect Branch Mispredict",
            hw_key("Indirect Branch Mispredict"),
            Candidate(
                "board.processor.cores.core.branchPred.mispredicted_0::CallIndirect",
                stat_key(
                    "board.processor.cores.core.branchPred.mispredicted_0::CallIndirect"
                ),
            ),
        ),
        Row(
            "IFU Branch Target Instruction",
            hw_key("IFU Branch Target Instruction"),
            Candidate(
                "lookups_0::CallDirect + DirectCond + DirectUncond",
                sum_stats(
                    "board.processor.cores.core.branchPred.lookups_0::CallDirect",
                    "board.processor.cores.core.branchPred.lookups_0::DirectCond",
                    "board.processor.cores.core.branchPred.lookups_0::DirectUncond",
                ),
            ),
        ),
        Row(
            "IFU Branch Target Mispred",
            hw_key("IFU Branch Target Mispred"),
            Candidate(
                "board.processor.cores.core.branchPred.BTBMispredicted",
                stat_key(
                    "board.processor.cores.core.branchPred.BTBMispredicted"
                ),
            ),
        ),
        Row(
            "Frontend Stall Cycles",
            hw_key("Stalled Cycles Frontend"),
            Candidate(
                "board.processor.cores.core.decode.blockedCycles",
                stat_key("board.processor.cores.core.decode.blockedCycles"),
            ),
        ),
        Row(
            "LSU Spec Fail",
            hw_key("LSU Spec Fail"),
            Candidate(
                "board.processor.cores.core.lsq0.squashedLoads",
                stat_key("board.processor.cores.core.lsq0.squashedLoads"),
            ),
        ),
        Row(
            "L1 DCache load access",
            hw_key("L1 DCache load access"),
            Candidate(
                "board.processor.cores.core.commitStats0.numLoadInsts",
                stat_key(
                    "board.processor.cores.core.commitStats0.numLoadInsts"
                ),
            ),
        ),
        Row(
            "L1 DCache load miss",
            hw_key("L1 DCache load miss"),
            Candidate(
                "board.cache_hierarchy.l1dcaches.ReadReq.misses::total",
                stat_key(
                    "board.cache_hierarchy.l1dcaches.ReadReq.misses::total"
                ),
            ),
        ),
        Row(
            "L1 DCache store miss",
            hw_key("L1 DCache store miss"),
            Candidate(
                "board.cache_hierarchy.l1dcaches.WriteReq.mshrMisses::total",
                stat_key(
                    "board.cache_hierarchy.l1dcaches.WriteReq.mshrMisses::total"
                ),
            ),
        ),
        Row(
            "L2 load access",
            hw_key("L2 load access"),
            Candidate(
                "board.cache_hierarchy.l2cache.demandAccesses::processor.cores.core.data",
                stat_key(
                    "board.cache_hierarchy.l2cache.demandAccesses::processor.cores.core.data"
                ),
            ),
        ),
        Row(
            "L2 load miss",
            hw_key("L2 load miss"),
            Candidate(
                "board.cache_hierarchy.l2cache.demandMisses::processor.cores.core.data",
                stat_key(
                    "board.cache_hierarchy.l2cache.demandMisses::processor.cores.core.data"
                ),
            ),
        ),
        Row(
            "L2 store access",
            hw_key("L2 store access"),
            Candidate(
                "board.cache_hierarchy.l2cache.ReadExReq.accesses::total",
                stat_key(
                    "board.cache_hierarchy.l2cache.ReadExReq.accesses::total"
                ),
            ),
        ),
        Row(
            "L2 store miss",
            hw_key("L2 store miss"),
            Candidate(
                "board.cache_hierarchy.l2cache.ReadExReq.misses::total",
                stat_key(
                    "board.cache_hierarchy.l2cache.ReadExReq.misses::total"
                ),
            ),
        ),
        Row(
            "LSU Other Stall",
            hw_key("LSU Other Stall"),
            Candidate(
                "board.processor.cores.core.lsq0.blockedByCache",
                stat_key("board.processor.cores.core.lsq0.blockedByCache"),
            ),
        ),
        Row(
            "Backend Stall Cycles",
            hw_key("Stalled Cycles Backend"),
            Candidate(
                "board.processor.cores.core.iew.blockCycles",
                stat_key("board.processor.cores.core.iew.blockCycles"),
            ),
        ),
    ]


def print_rows(
    rows: list[Row], hw: dict[str, Number], stats: dict[str, Number]
) -> None:
    headers = [
        "硬件事件",
        "硬件值",
        "gem5 对照项",
        "gem5 值",
        "差值(gem5-hw)",
        "倍率(gem5/hw)",
    ]
    numeric_cols = {1, 3, 4, 5}
    rendered_rows: list[list[str]] = []

    for row in rows:
        hw_value = row.hw_fn(hw, stats)
        gem5_value = row.primary.fn(hw, stats)
        rendered_rows.append(
            [
                row.event,
                fmt_number(hw_value),
                row.primary.label,
                fmt_number(gem5_value),
                fmt_number(calc_delta(hw_value, gem5_value)),
                fmt_number(calc_ratio(hw_value, gem5_value)),
            ]
        )

    widths = [display_width(header) for header in headers]
    for rendered in rendered_rows:
        for index, value in enumerate(rendered):
            widths[index] = max(widths[index], display_width(value))

    print(format_row(headers, widths, set()))
    print(format_row(["-" * width for width in widths], widths, set()))
    for rendered in rendered_rows:
        print(format_row(rendered, widths, numeric_cols))


def main() -> None:
    root = repo_root()
    parser = argparse.ArgumentParser(
        description="Compare hardware PMU counters with gem5 stats using the C920 mapping."
    )
    parser.add_argument(
        "--hw",
        type=Path,
        default=root / "920_results",
        help="Hardware PMU dump path",
    )
    parser.add_argument(
        "--stats",
        type=Path,
        default=root / "m5out" / "stats.txt",
        help="gem5 stats.txt path",
    )
    args = parser.parse_args()

    hw = parse_hw(args.hw)
    stats = parse_stats(args.stats)
    print_rows(build_rows(), hw, stats)


if __name__ == "__main__":
    main()
