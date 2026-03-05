import argparse
import csv
import re
import sys


def load_static_trace(trace_csv_path):
    pc_map = {}
    print(f"[-] Loading static trace: {trace_csv_path}")
    try:
        with open(trace_csv_path) as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) >= 2:
                    # 存储为十六进制整数以实现最通用的匹配
                    pc_val = int(row[0].strip(), 16)
                    pc_map[pc_val] = row[1].strip().upper()
        return pc_map
    except Exception as e:
        print(f"[!] Error loading CSV: {e}")
        sys.exit(1)


def parse_dynamic_log(log_path, pc_map):
    dynamic_loads = 0
    dynamic_stores = 0

    # 通用正则表达式优化：
    # 匹配 "0x" 后面跟着的一串十六进制字符
    # 且确保它前面有冒号或空格（防止误匹配数据中的0x）
    # \b0x([0-9a-fA-F]+) 匹配以 0x 开头的单词边界
    pc_pattern = re.compile(r"0x([0-9a-fA-F]+)")

    print(f"[-] Scanning Log: {log_path}")

    try:
        with open(log_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                # 在 Gem5 这种 Trace 中，一行可能有多个 0x（地址、数据、指令编码）
                # 但通常第一个出现的 0x 且紧跟在 T0/PC 之后的是 PC
                matches = pc_pattern.findall(line)
                if matches:
                    # 我们取匹配到的第一个符合长度逻辑的 hex 作为 PC
                    # 或者根据你提供的 Log，PC 总是出现在第一个位置
                    try:
                        current_pc_val = int(matches[0], 16)

                        if current_pc_val in pc_map:
                            op_type = pc_map[current_pc_val]
                            if op_type == "LOAD":
                                dynamic_loads += 1
                            elif op_type == "STORE":
                                dynamic_stores += 1
                    except ValueError:
                        continue

    except Exception as e:
        print(f"[!] Error processing log: {e}")
        sys.exit(1)

    return dynamic_loads, dynamic_stores


def main():
    parser = argparse.ArgumentParser(
        description="Universal PC Matcher for RISC-V Logs"
    )
    parser.add_argument("csv_file", help="The trace.csv from previous step")
    parser.add_argument("log_file", help="The execution log (gem5/qemu/spike)")

    args = parser.parse_args()

    static_map = load_static_trace(args.csv_file)
    d_loads, d_stores = parse_dynamic_log(args.log_file, static_map)

    print("\n" + "=" * 30)
    print(f"Final Counts:")
    print(f"LOADs : {d_loads}")
    print(f"STOREs: {d_stores}")
    print("=" * 30)


if __name__ == "__main__":
    main()
