import argparse
import os
import shutil  # 引入 shutil 用于删除目录树
import subprocess

# ================= 配置区 =================
DEFAULT_GEM5_BINARY = "./build/RISCV/gem5.opt"  # gem5 可执行文件的路径
DEFAULT_CONFIG_SCRIPT = "configs/906/run.py"  # 你的仿真脚本路径
DEFAULT_OUTPUT_DIR = "./tmp"  # Log 存放的目录
# ===========================================

# Debug Flags 组合列表
DEFAULT_DEBUG_COMBINATIONS = [
    "Exec",  # 包含 Exec -> 触发拆分
    "Cache",
    "MinorMem,Cache",  # 不含 Exec -> 不拆分
]
# ===========================================


def clean_and_create_dir(path):
    """
    如果目录存在，先删除（清空），然后重新创建。
    """
    if os.path.exists(path):
        print(f"[!] Cleaning existing directory: {path}")
        try:
            shutil.rmtree(path)  # 递归删除目录及其内容
        except Exception as e:
            print(f"[x] Error cleaning directory: {e}")
            return

    os.makedirs(path)
    print(f"[Info] Created empty directory: {path}")


def split_log_by_keywords(original_log_path):
    """
    读取 Log，根据 icache/dcache 关键字拆分文件。
    """
    base_name = os.path.splitext(original_log_path)[0]
    icache_path = f"{base_name}_icache.log"
    dcache_path = f"{base_name}_dcache.log"

    print(f"    [>] Post-processing (Triggered by 'Exec')...")
    print(f"    [>] Extracting 'icache' -> {os.path.basename(icache_path)}")
    print(f"    [>] Extracting 'dcache' -> {os.path.basename(dcache_path)}")

    try:
        with open(
            original_log_path, encoding="utf-8", errors="ignore"
        ) as f_in, open(icache_path, "w", encoding="utf-8") as f_i, open(
            dcache_path, "w", encoding="utf-8"
        ) as f_d:

            for line in f_in:
                if "icache" in line:
                    f_i.write(line)
                elif "dcache" in line:
                    f_d.write(line)

        print(f"    [+] Split complete.")

    except Exception as e:
        print(f"    [!] Error during log splitting: {e}")


def run_simulation(gem5_binary, config_script, output_dir, debug_combinations):
    # 1. 运行前先清空并重建 tmp 目录
    clean_and_create_dir(output_dir)

    for flags in debug_combinations:
        # 生成文件名
        clean_name = flags.replace(", ", "_").replace(",", "_")
        log_file_path = os.path.join(output_dir, f"{clean_name}.log")

        # 运行 gem5
        cmd = [gem5_binary, f"--debug-flags={flags}", config_script]
        print(f"\n[-] Running flags: {flags}")
        print(f"    Log to: {log_file_path}")

        try:
            with open(log_file_path, "w") as f:
                subprocess.run(
                    cmd, stdout=f, stderr=subprocess.STDOUT, check=True
                )
        except subprocess.CalledProcessError:
            print(f"[!] Simulation Failed for: {flags}")
            continue

        # 后处理逻辑：当 flags 中包含 "Exec" 时触发
        if "Exec" in flags:
            split_log_by_keywords(log_file_path)
        else:
            print(f"    [.] 'Exec' flag not found, skipping post-processing.")


def build_parser():
    return argparse.ArgumentParser(
        description=(
            "Run gem5 with multiple debug flag combinations and optionally split Exec logs."
        ),
        epilog=(
            "Example:\n"
            "  python3 my_scripts/log.py --gem5-binary ./build/RISCV/gem5.opt "
            "--config-script configs/906/run.py --debug-flags Exec Cache MinorMem,Cache"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )


def main():
    parser = build_parser()
    parser.add_argument(
        "--gem5-binary",
        default=DEFAULT_GEM5_BINARY,
        help="Path to gem5 binary.",
    )
    parser.add_argument(
        "--config-script",
        default=DEFAULT_CONFIG_SCRIPT,
        help="Path to gem5 Python config script.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where log files are generated (will be recreated).",
    )
    parser.add_argument(
        "--debug-flags",
        nargs="+",
        default=DEFAULT_DEBUG_COMBINATIONS,
        metavar="FLAGS",
        help=(
            "One or more debug flag combinations. Each item can include commas, "
            'e.g. "MinorMem,Cache".'
        ),
    )
    args = parser.parse_args()

    run_simulation(
        args.gem5_binary,
        args.config_script,
        args.output_dir,
        args.debug_flags,
    )


if __name__ == "__main__":
    main()
