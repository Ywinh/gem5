import csv
import os
import re
import subprocess

# ================= 配置区域 =================
GEM5_PATH = "./build/X86/gem5.opt"
CONFIG_PY = "configs/deprecated/example/se.py"
BENCH_PATH = "/home/yinjianhui/2025-UCAS-CA-Gem5-lab/lab2-2/bench/linear"

# 严格按照要求的六组配置
configs = [
    {
        "id": "conf1",
        "freq": "1GHz",
        "l2": False,
        "l2_size": "No",
        "l2_assoc": "No",
    },
    {
        "id": "conf2",
        "freq": "4GHz",
        "l2": False,
        "l2_size": "No",
        "l2_assoc": "No",
    },
    {
        "id": "conf3",
        "freq": "1GHz",
        "l2": True,
        "l2_size": "256KiB",
        "l2_assoc": 8,
    },
    {
        "id": "conf4",
        "freq": "1GHz",
        "l2": True,
        "l2_size": "256KiB",
        "l2_assoc": 4,
    },
    {
        "id": "conf5",
        "freq": "1GHz",
        "l2": True,
        "l2_size": "2MiB",
        "l2_assoc": 8,
    },
    {
        "id": "conf6",
        "freq": "1GHz",
        "l2": True,
        "l2_size": "16MiB",
        "l2_assoc": 8,
    },
]

# ===========================================


def run_gem5(conf):
    out_dir = f"res_{conf['id']}"

    # 构建基础命令，严格遵循你给出的格式
    cmd = [
        GEM5_PATH,
        f"--outdir={out_dir}",
        CONFIG_PY,
        "-n",
        "1",
        "--sys-clock",
        conf["freq"],
        "--mem-type",
        "DDR3_1600_8x8",
        "--cpu-type",
        "O3CPU",
        "--caches",
        "--l1d_size",
        "32KiB",
        "--l1d_assoc",
        "2",
        "--l1i_size",
        "32KiB",
        "--l1i_assoc",
        "2",
    ]

    # 根据逻辑：如果没有 L2 cache 就去掉相关参数
    if conf["l2"]:
        cmd.extend(
            [
                "--l2cache",
                "--l2_size",
                conf["l2_size"],
                "--l2_assoc",
                str(conf["l2_assoc"]),
            ]
        )

    # 添加 benchmark 路径
    cmd.extend(["-c", BENCH_PATH])

    print(f"--- 正在运行 {conf['id']} ---")
    print(f"命令: {' '.join(cmd)}")

    try:
        # 运行 gem5，捕捉 stderr 以防报错
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"运行出错: {e.stderr.decode()}")

    return out_dir


def parse_stats(conf, out_dir):
    stats_file = os.path.join(out_dir, "stats.txt")
    results = {
        "ID": conf["id"],
        "Freq": conf["freq"],
        "L2_Size": conf["l2_size"],
        "L2_Assoc": conf["l2_assoc"],
        "IPC": "N/A",
        "L1D_MissRate": "N/A",
        "L2_MissRate": "N/A",
        "ROB_Full": "N/A",
        "SimSeconds": "N/A",
    }

    if not os.path.exists(stats_file):
        print(f"警告: {stats_file} 未生成")
        return results

    with open(stats_file) as f:
        content = f.read()

        def get_val(pattern):
            match = re.search(pattern, content)
            return match.group(1) if match else "0"

        results["IPC"] = get_val(r"system.cpu.ipc\s+([\d.]+)")
        results["L1D_MissRate"] = get_val(
            r"system.cpu.dcache.overallMissRate::total\s+([\d.]+)"
        )
        results["SimSeconds"] = get_val(r"simSeconds\s+([\d.]+)")
        results["ROB_Full"] = get_val(r"system.cpu.rob.rob_full\s+(\d+)")

        if conf["l2"]:
            results["L2_MissRate"] = get_val(
                r"system.l2.overallMissRate::total\s+([\d.]+)"
            )
        else:
            results["L2_MissRate"] = "None"

    return results


def main():
    final_results = []

    for conf in configs:
        out_folder = run_gem5(conf)
        data = parse_stats(conf, out_folder)
        final_results.append(data)

    # 保存到 CSV
    output_csv = "lab_results_summary.csv"
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=final_results[0].keys())
        writer.writeheader()
        writer.writerows(final_results)

    print(f"\n实验完成！结果已汇总至: {output_csv}")

    # 终端预览
    print("\n预览结果:")
    print(
        f"{'ID':<8} {'Freq':<6} {'L2':<10} {'IPC':<8} {'L2Miss':<8} {'ROB_Full':<10}"
    )
    for r in final_results:
        print(
            f"{r['ID']:<8} {r['Freq']:<6} {r['L2_Size']:<10} {r['IPC']:<8} {r['L2_MissRate']:<8} {r['ROB_Full']:<10}"
        )


if __name__ == "__main__":
    main()
