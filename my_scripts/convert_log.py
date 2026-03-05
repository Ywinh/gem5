import argparse
import re


def parse_val(val_str):
    """Normalize hex strings. Handle 0 specifically."""
    if val_str == "0":
        return "0x00000000"
    try:
        # 转换为小写 hex，不补零（除非你希望强制64位补零，这里保持原样更通用）
        return f"0x{int(val_str, 0):x}"
    except:
        return val_str


def get_reg_name(idx):
    """Convert integer index to xN format (RISC-V)"""
    return f"x{idx}"


def is_branch_inst(mnemonic):
    """Check if instruction is a branch/jump"""
    mnem = mnemonic.lower()
    return (
        mnem.startswith("b")
        or mnem.startswith("c.b")
        or mnem in ["j", "jr", "jal", "jalr"]
        or "jump" in mnem
    )


def process_instruction_block(
    time, pc, asm, op_class, res_str, reads, writes, outfile
):
    # 格式化基础列
    time_col = f"{time:>8}"
    cycle_col = " " * 8
    pc_col = f"{pc}"
    insn_col = " " * 10
    asm_col = f"{asm:<35}"

    info_parts = []

    # 1. 寄存器读 (Read Info)
    for r_idx, r_val in reads:
        info_parts.append(f"{get_reg_name(r_idx)}:{parse_val(r_val)}")

    # 2. 寄存器写 (Write Info)
    # 特殊处理：分支指令如果没有写回，强制输出 x0=0
    if is_branch_inst(asm.split()[0]) and not writes:
        info_parts.append("x0=0x00000000")
    else:
        for r_idx, r_val in writes:
            info_parts.append(f"{get_reg_name(r_idx)}={parse_val(r_val)}")

    # 3. 访存信息 (Memory Access) - 严格区分 Load/Store
    # 提取 D=... 和 A=...
    d_match = re.search(r"D=(0x[0-9a-fA-F]+|0)", res_str)
    a_match = re.search(r"A=(0x[0-9a-fA-F]+|0)", res_str)

    if d_match and a_match:
        data_val = d_match.group(1)
        addr_val = a_match.group(1)

        # 逻辑判断：是 Load 还是 Store？
        if "MemRead" in op_class or "Load" in op_class:
            # Load 指令：只输出 PA 和 load
            info_parts.append(f"PA:{parse_val(addr_val)}")
            info_parts.append(f"load:{parse_val(data_val)}")

        elif "MemWrite" in op_class or "Store" in op_class:
            # Store 指令：只输出 PA 和 store
            info_parts.append(f"PA:{parse_val(addr_val)}")
            info_parts.append(f"store:{parse_val(data_val)}")

    info_str = " ".join(info_parts)
    outfile.write(
        f"{time_col} {cycle_col} {pc_col} {insn_col} {asm_col} {info_str}\n"
    )


def build_parser():
    return argparse.ArgumentParser(
        description=(
            "Convert gem5 RISC-V execution log into a compact instruction trace table."
        ),
        epilog=(
            "Example:\n"
            "  python3 my_scripts/convert_log.py m5out/exec.log m5out/exec_compact.log"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )


def main():
    parser = build_parser()
    parser.add_argument(
        "input_log", help="Path to the input gem5 execution log file."
    )
    parser.add_argument(
        "output_log", help="Path to the converted output log file."
    )
    args = parser.parse_args()

    input_file = args.input_log
    output_file = args.output_log

    print(f"Processing {input_file} -> {output_file} ...")

    # 正则表达式 (Robust Version)
    # 能够匹配 'MemRead' 前后的空格
    re_inst = re.compile(
        r"^\s*(\d+):.*?: T0 : (0x[0-9a-fA-F]+)(?: @\S+)?\s*:(.*?):\s*(\w+)\s*:(.*)$"
    )

    re_read = re.compile(r"integer\[(\d+)\].*?as (0x[0-9a-fA-F]+|0)")
    re_write = re.compile(r"integer\[(\d+)\].*?to (0x[0-9a-fA-F]+|0)")

    curr_reads = []
    curr_writes = []
    line_count = 0
    match_count = 0

    with open(input_file, encoding="utf-8", errors="ignore") as fin, open(
        output_file, "w", encoding="utf-8"
    ) as fout:

        # 输出 Header
        fout.write(
            f"{'Time':>8} {'Cycle':>8} {'PC':>10} {'Insn':>10} {'Decoded instruction':<35} Register and memory contents\n"
        )

        for line in fin:
            line_count += 1
            if line_count % 200000 == 0:
                print(f"Processed {line_count} lines...", end="\r")

            # 1. 匹配指令行 (T0)
            if "T0" in line and "board.processor.cores.core" in line:
                m = re_inst.search(line)
                if m:
                    match_count += 1
                    process_instruction_block(
                        m.group(1),  # Time
                        m.group(2),  # PC
                        m.group(3).strip(),  # ASM
                        m.group(
                            4
                        ).strip(),  # OpClass (MemRead/MemWrite/IntAlu)
                        m.group(5).strip(),  # Result String (D=... A=...)
                        curr_reads,
                        curr_writes,
                        fout,
                    )
                    # 清空缓存
                    curr_reads = []
                    curr_writes = []
                continue

            # 2. 匹配读寄存器
            if "Reading integer" in line:
                m = re_read.search(line)
                if m:
                    curr_reads.append((m.group(1), m.group(2)))
                continue

            # 3. 匹配写寄存器
            if "Setting integer" in line:
                m = re_write.search(line)
                if m:
                    curr_writes.append((m.group(1), m.group(2)))
                continue

    print(
        f"\nFinished. Processed {line_count} lines. Matched {match_count} instructions."
    )


if __name__ == "__main__":
    main()
