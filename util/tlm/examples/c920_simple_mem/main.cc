/*
 * Copyright 2026
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <systemc>
#include <tlm>
#include <vector>

#include "c920_memory.hh"
#include "report_handler.hh"
#include "sim_control.hh"
#include "slave_transactor.hh"
#include "stats.hh"

namespace
{

constexpr const char *SidecarName = "c920_external_systemc_simple_mem.conf";
constexpr const char *DefaultLatency = "30ns";
constexpr const char *DefaultLatencyVar = "0ns";
constexpr const char *DefaultBandwidth = "12.8GiB/s";

struct Options
{
    std::string configFile;
    uint64_t simulationEnd = 0;
    bool verbose = false;
    std::vector<std::string> debugFlags;
    std::string latency;
    std::string latencyVar;
    std::string bandwidth;
    bool latencySet = false;
    bool latencyVarSet = false;
    bool bandwidthSet = false;
};

struct MemoryModelConfig
{
    std::string latency = DefaultLatency;
    std::string latencyVar = DefaultLatencyVar;
    std::string bandwidth = DefaultBandwidth;
};

[[noreturn]] void
usage(const char *prog)
{
    std::cerr
        << "Usage: " << prog << " <config.ini> [options]\n\n"
        << "Options:\n"
        << "    -d <flag>                Set a gem5 debug flag\n"
        << "    -e <ticks>               End simulation after the given "
        << "ticks\n"
        << "    -v                       Print each memory transaction\n"
        << "    --latency <time>         Override response latency "
        << "(e.g. 30ns)\n"
        << "    --latency-var <time>     Override latency variation\n"
        << "    --bandwidth <bw>         Override bandwidth (e.g. 12.8GiB/s)\n"
        << "\n"
        << "If the overrides are omitted, the runner reads " << SidecarName
        << " next to config.ini.\n";
    std::exit(EXIT_FAILURE);
}

std::string
trim(std::string value)
{
    const auto notSpace = [](unsigned char c) { return !std::isspace(c); };
    value.erase(
        value.begin(),
        std::find_if(value.begin(), value.end(), notSpace));
    value.erase(
        std::find_if(value.rbegin(), value.rend(), notSpace).base(),
        value.end());
    return value;
}

std::string
lower(std::string value)
{
    std::transform(value.begin(), value.end(), value.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return value;
}

std::string
siblingPath(const std::string &path, const char *name)
{
    const auto slash = path.find_last_of("/\\");
    if (slash == std::string::npos) {
        return std::string(name);
    }

    return path.substr(0, slash + 1) + name;
}

Options
parseArgs(int argc, char **argv)
{
    if (argc < 2) {
        usage(argv[0]);
    }

    Options options;
    options.configFile = argv[1];

    for (int i = 2; i < argc; ++i) {
        const std::string arg(argv[i]);

        if (arg == "-d") {
            if (i + 1 >= argc) {
                usage(argv[0]);
            }
            options.debugFlags.emplace_back(argv[++i]);
        } else if (arg == "-e") {
            if (i + 1 >= argc) {
                usage(argv[0]);
            }
            options.simulationEnd = std::stoull(argv[++i], nullptr, 0);
        } else if (arg == "-v") {
            options.verbose = true;
        } else if (arg == "--latency") {
            if (i + 1 >= argc) {
                usage(argv[0]);
            }
            options.latency = argv[++i];
            options.latencySet = true;
        } else if (arg == "--latency-var") {
            if (i + 1 >= argc) {
                usage(argv[0]);
            }
            options.latencyVar = argv[++i];
            options.latencyVarSet = true;
        } else if (arg == "--bandwidth") {
            if (i + 1 >= argc) {
                usage(argv[0]);
            }
            options.bandwidth = argv[++i];
            options.bandwidthSet = true;
        } else if (arg == "-h" || arg == "--help") {
            usage(argv[0]);
        } else {
            usage(argv[0]);
        }
    }

    return options;
}

std::string
getDebugFlags(const Options &options)
{
    std::ostringstream flags;
    for (const auto &flag : options.debugFlags) {
        flags << flag << ' ';
    }
    return flags.str();
}

gem5::AddrRange
parseMemoryRange(const std::string &configPath)
{
    std::ifstream config(configPath);
    if (!config) {
        std::cerr << "Unable to open config file: " << configPath << '\n';
        std::exit(EXIT_FAILURE);
    }

    std::string line;
    while (std::getline(config, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#' || line.front() == '[') {
            continue;
        }

        constexpr const char *prefix = "mem_ranges=";
        if (line.rfind(prefix, 0) != 0) {
            continue;
        }

        const std::string ranges = trim(line.substr(std::strlen(prefix)));
        if (ranges.empty() || ranges.find(' ') != std::string::npos) {
            std::cerr << "Expected a single top-level memory range, got: "
                      << ranges << '\n';
            std::exit(EXIT_FAILURE);
        }

        const auto colon = ranges.find(':');
        if (colon == std::string::npos) {
            std::cerr << "Unsupported mem_ranges format: " << ranges << '\n';
            std::exit(EXIT_FAILURE);
        }

        const auto start = std::stoull(ranges.substr(0, colon), nullptr, 0);
        const auto size = std::stoull(ranges.substr(colon + 1), nullptr, 0);
        return gem5::RangeSize(start, size);
    }

    std::cerr << "Did not find mem_ranges in " << configPath << '\n';
    std::exit(EXIT_FAILURE);
}

MemoryModelConfig
loadSidecar(const std::string &configPath)
{
    MemoryModelConfig config;
    const auto sidecarPath = siblingPath(configPath, SidecarName);
    std::ifstream sidecar(sidecarPath);
    if (!sidecar) {
        return config;
    }

    std::string line;
    while (std::getline(sidecar, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') {
            continue;
        }

        const auto equals = line.find('=');
        if (equals == std::string::npos) {
            continue;
        }

        const auto key = trim(line.substr(0, equals));
        const auto value = trim(line.substr(equals + 1));
        if (key == "latency") {
            config.latency = value;
        } else if (key == "latency_var") {
            config.latencyVar = value;
        } else if (key == "bandwidth") {
            config.bandwidth = value;
        }
    }

    return config;
}

gem5::Tick
parseTimeToTicks(const std::string &value)
{
    const auto compact = lower(trim(value));
    size_t consumed = 0;
    const double magnitude = std::stod(compact, &consumed);
    const std::string unit = compact.substr(consumed);

    double scale = 0.0;
    if (unit == "fs") {
        scale = 1.0e-3;
    } else if (unit == "ps") {
        scale = 1.0;
    } else if (unit == "ns") {
        scale = 1.0e3;
    } else if (unit == "us") {
        scale = 1.0e6;
    } else if (unit == "ms") {
        scale = 1.0e9;
    } else if (unit == "s") {
        scale = 1.0e12;
    } else {
        std::cerr << "Unsupported time unit: " << value << '\n';
        std::exit(EXIT_FAILURE);
    }

    return static_cast<gem5::Tick>(std::llround(magnitude * scale));
}

double
parseBandwidthToTicksPerByte(const std::string &value)
{
    const auto compact = lower(trim(value));
    size_t consumed = 0;
    const double magnitude = std::stod(compact, &consumed);
    const std::string unit = compact.substr(consumed);

    double bytesPerSecond = 0.0;
    if (unit == "b/s") {
        bytesPerSecond = magnitude;
    } else if (unit == "kib/s") {
        bytesPerSecond = magnitude * 1024.0;
    } else if (unit == "mib/s") {
        bytesPerSecond = magnitude * 1024.0 * 1024.0;
    } else if (unit == "gib/s") {
        bytesPerSecond = magnitude * 1024.0 * 1024.0 * 1024.0;
    } else if (unit == "tib/s") {
        bytesPerSecond = magnitude * 1024.0 * 1024.0 * 1024.0 * 1024.0;
    } else if (unit == "kb/s") {
        bytesPerSecond = magnitude * 1.0e3;
    } else if (unit == "mb/s") {
        bytesPerSecond = magnitude * 1.0e6;
    } else if (unit == "gb/s") {
        bytesPerSecond = magnitude * 1.0e9;
    } else if (unit == "tb/s") {
        bytesPerSecond = magnitude * 1.0e12;
    } else {
        std::cerr << "Unsupported bandwidth unit: " << value << '\n';
        std::exit(EXIT_FAILURE);
    }

    if (bytesPerSecond <= 0.0) {
        std::cerr << "Bandwidth must be positive: " << value << '\n';
        std::exit(EXIT_FAILURE);
    }

    return sc_core::sc_time(1, sc_core::SC_SEC).value() / bytesPerSecond;
}

} // anonymous namespace

int
sc_main(int argc, char **argv)
{
    const Options options = parseArgs(argc, argv);
    MemoryModelConfig model = loadSidecar(options.configFile);

    if (options.latencySet) {
        model.latency = options.latency;
    }
    if (options.latencyVarSet) {
        model.latencyVar = options.latencyVar;
    }
    if (options.bandwidthSet) {
        model.bandwidth = options.bandwidth;
    }

    sc_core::sc_report_handler::set_handler(reportHandler);

    Gem5SystemC::Gem5SimControl sim_control(
        "gem5", options.configFile, options.simulationEnd,
        getDebugFlags(options));

    const auto range = parseMemoryRange(options.configFile);
    C920SimpleMemoryTarget memory(
        "memory", range, parseTimeToTicks(model.latency),
        parseTimeToTicks(model.latencyVar),
        parseBandwidthToTicksPerByte(model.bandwidth), options.verbose);
    Gem5SystemC::Gem5SlaveTransactor transactor("transactor", "transactor");

    memory.socket.bind(transactor.socket);
    transactor.sim_control.bind(sim_control);

    std::cout << "[c920_simple_mem] range=" << range.to_string()
              << " latency=" << model.latency
              << " latency_var=" << model.latencyVar
              << " bandwidth=" << model.bandwidth << '\n';

    SC_REPORT_INFO("sc_main", "Start of Simulation");
    sc_core::sc_start();
    SC_REPORT_INFO("sc_main", "End of Simulation");

    CxxConfig::statsDump();
    return EXIT_SUCCESS;
}
