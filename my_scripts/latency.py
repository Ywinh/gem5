import argparse
import re
import sys
from collections import defaultdict


def analyze_exec_latency(log_file_path, sort_key):
    # 初始化哈希表
    # 结构: pc_stats[pc] = {'count': 0, 'total_time': 0, 'instruction': ''}
    pc_stats = defaultdict(
        lambda: {"count": 0, "total_time": 0, "instruction": ""}
    )

    prev_time = None

    # 改进的正则表达式：
    # 1. ^\s* 允许行首有空格（你的 log 中时间戳前有空格）
    # 2. 自动过滤掉所有不符合此特征的 gem5 启动 header 信息
    log_pattern = re.compile(
        r"^\s*(\d+):\s+.*?(0x[0-9a-fA-F]+)\s+@.*?:\s+([^:]+?)\s*:"
    )

    try:
        # 加上 errors='ignore' 防止解析庞大 log 时遇到非法字符报错中断
        with open(log_file_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = log_pattern.search(line)
                if match:
                    current_time = int(match.group(1))
                    current_pc = match.group(2)
                    instruction = match.group(3).strip()

                    # 记录汇编指令（如果是同一条PC，覆盖无妨）
                    pc_stats[current_pc]["instruction"] = instruction

                    if prev_time is not None:
                        # 计算当前指令与上一条指令的 Retire 时间差
                        time_diff = current_time - prev_time

                        # 更新哈希表
                        pc_stats[current_pc]["count"] += 1
                        pc_stats[current_pc]["total_time"] += time_diff

                    # 更新 prev_time 为下一条指令做准备
                    prev_time = current_time

    except FileNotFoundError:
        print(f"[!] Error: 找不到文件 {log_file_path}")
        sys.exit(1)

    # 提取并计算数据
    results = []
    for pc, stats in pc_stats.items():
        count = stats["count"]
        if count > 0:
            total_latency = stats["total_time"]
            avg_latency = total_latency / count
            results.append(
                (pc, stats["instruction"], count, total_latency, avg_latency)
            )

    # 执行排序逻辑
    if sort_key == "pc":
        # 按 PC 物理地址升序 (将 16 进制字符串转为 int 比较)
        results.sort(key=lambda x: int(x[0], 16))
    elif sort_key == "count":
        # 按执行次数降序
        results.sort(key=lambda x: x[2], reverse=True)
    elif sort_key == "total":
        # 按总延时降序
        results.sort(key=lambda x: x[3], reverse=True)
    elif sort_key == "avg":
        # 按平均延时降序
        results.sort(key=lambda x: x[4], reverse=True)

    # 格式化输出
    print(
        f"{'PC':<18} | {'Instruction':<30} | {'Count':<10} | {'Total Latency':<15} | {'Avg Latency':<15}"
    )
    print("-" * 95)

    for pc, inst, count, total_latency, avg_latency in results:
        print(
            f"{pc:<18} | {inst:<30} | {count:<10} | {total_latency:<15} | {avg_latency:.2f}"
        )


if __name__ == "__main__":
    # 配置 argparse
    parser = argparse.ArgumentParser(
        description="gem5 Exec log Pipeline Latency Analyzer"
    )

    # 必填位置参数：log文件路径
    parser.add_argument("log_file", help="Path to the gem5 Exec log file.")

    # 可选参数：排序维度
    parser.add_argument(
        "--sort",
        choices=["pc", "count", "total", "avg"],
        default="pc",
        help="Sort output by: 'pc', 'count', 'total', or 'avg'. Default is 'pc'.",
    )

    args = parser.parse_args()

    # 执行核心逻辑
    analyze_exec_latency(args.log_file, args.sort)
