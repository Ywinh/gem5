import argparse
import re
import sys

# 定义 RV32IMF 架构下的访存指令集
LOAD_OPS = {
    "lb",
    "lh",
    "lw",
    "lbu",
    "lhu",
    "flw",
    "c.lw",
    "c.flw",
    "c.lwsp",
    "c.flwsp",
}

STORE_OPS = {"sb", "sh", "sw", "fsw", "c.sw", "c.fsw", "c.swsp", "c.fswsp"}


def parse_objdump(file_path, output_file=None, verbose=False):
    load_count = 0
    store_count = 0

    # 用于存储 Trace 记录的列表
    # 格式: (PC, Type, Mnemonic)
    trace_records = []

    # 编译正则表达式
    # 修改点：在第一个 hex 处增加了括号 () 以捕获 PC 地址
    # Group 1: PC 地址 (hex)
    # Group 2: 指令助记符 (mnemonic)
    # Group 3: 操作数 (operands)
    line_pattern = re.compile(
        r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]+\s+([a-z\.]+)\s*(.*)$"
    )

    try:
        with open(file_path) as f:
            lines = f.readlines()

        print(f"正在分析文件: {file_path} ...")

        for line in lines:
            line = line.strip()
            match = line_pattern.match(line)

            if match:
                pc_hex = match.group(1)  # 捕获 PC
                mnemonic = match.group(2)  # 捕获助记符
                # operands = match.group(3)  # 如果需要操作数（如 offset），可以在这里处理

                is_mem_op = False
                op_type = ""

                # 判断是否为访存指令
                if mnemonic in LOAD_OPS:
                    load_count += 1
                    is_mem_op = True
                    op_type = "LOAD"
                elif mnemonic in STORE_OPS:
                    store_count += 1
                    is_mem_op = True
                    op_type = "STORE"

                # 如果是访存指令，记录下来
                if is_mem_op:
                    trace_records.append((pc_hex, op_type, mnemonic))
                    if verbose:
                        print(f"[{op_type}] PC:{pc_hex} Insn:{mnemonic}")

        # 如果指定了输出文件，则写入
        if output_file:
            print(f"正在写入 Trace 到: {output_file} ...")
            with open(output_file, "w") as f_out:
                # 写入表头 (可选，如果纯机器读可以去掉)
                f_out.write("PC,Type,Mnemonic\n")
                for pc, type_, mne in trace_records:
                    # 格式: PC, 类型, 具体指令
                    f_out.write(f"{pc},{type_},{mne}\n")
            print(f"写入完成，共 {len(trace_records)} 条记录。")

    except FileNotFoundError:
        print(f"错误: 找不到文件 {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)

    return load_count, store_count


def main():
    parser = argparse.ArgumentParser(
        description="统计 RISC-V (RV32IMF) objdump 访存指令并提取 PC"
    )
    parser.add_argument("file", help="objdump -d 生成的文本文件路径")
    parser.add_argument(
        "-o",
        "--output",
        help="输出 PC Trace 的文件路径 (例如 trace.csv)",
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="在终端输出每一条匹配到的指令详情",
    )

    args = parser.parse_args()

    loads, stores = parse_objdump(args.file, args.output, args.verbose)

    total = loads + stores

    print("-" * 40)
    print(f"统计结果 (RV32IMF):")
    print("-" * 40)
    print(f"Load 指令总数 : {loads}")
    print(f"Store 指令总数: {stores}")
    print("-" * 40)
    print(f"访存指令总计: {total}")

    if total > 0:
        print(f"Load 占比: {loads/total:.2%}")
        print(f"Store 占比: {stores/total:.2%}")


if __name__ == "__main__":
    main()
