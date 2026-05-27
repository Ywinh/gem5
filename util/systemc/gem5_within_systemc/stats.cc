/*
 * Copyright (c) 2014 ARM Limited
 * All rights reserved.
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/**
 * @file
 *
 *  C++-only configuration stats handling example
 *
 *  Register with: gem5::statistics::registerHandlers(statsReset, statsDump)
 */

#include <algorithm>
#include <list>
#include <vector>

#include "base/logging.hh"
#include "base/output.hh"
#include "base/statistics.hh"
#include "base/stats/group.hh"
#include "base/stats/text.hh"
#include "sim/root.hh"
#include "sim/sim_object.hh"
#include "stats.hh"

namespace CxxConfig
{

namespace
{

using gem5::Root;
using gem5::statistics::Group;
using gem5::statistics::Info;
using gem5::statistics::Output;

Root *
rootGroup()
{
    auto *root_obj = gem5::SimObject::find("root");
    return dynamic_cast<Root *>(root_obj);
}

void
statsEnableGroup(Group &group)
{
    for (auto *info : group.getStats()) {
        info->enable();
    }

    for (const auto &[name, child] : group.getStatGroups()) {
        statsEnableGroup(*child);
    }
}

void
statsPrepareGroup(Group &group)
{
    for (auto *info : group.getStats()) {
        info->prepare();
    }

    for (const auto &[name, child] : group.getStatGroups()) {
        statsPrepareGroup(*child);
    }
}

void
statsVisitGroup(Output &output, const Group &group)
{
    for (auto *info : group.getStats()) {
        info->visit(output);
    }

    for (const auto &[name, child] : group.getStatGroups()) {
        output.beginGroup(name.c_str());
        statsVisitGroup(output, *child);
        output.endGroup();
    }
}

void
statsEnableLegacy()
{
    for (auto *info : gem5::statistics::statsList()) {
        info->enable();
    }
}

void
statsPrepareLegacy()
{
    for (auto *info : gem5::statistics::statsList()) {
        info->prepare();
    }
}

void
statsVisitLegacy(Output &output)
{
    for (auto *info : gem5::statistics::statsList()) {
        info->visit(output);
    }
}

} // anonymous namespace

void
statsPrepare()
{
    if (auto *root = rootGroup(); root != nullptr) {
        root->preDumpStats();
        statsPrepareGroup(*root);
    }

    statsPrepareLegacy();
}

void
statsDump()
{
    const bool desc = true;
    gem5::statistics::Output *output =
        gem5::statistics::initText(filename, desc, true);

    gem5::statistics::processDumpQueue();

    statsEnable();
    statsPrepare();

    output->begin();

    if (auto *root = rootGroup(); root != nullptr) {
        statsVisitGroup(*output, *root);
    }

    statsVisitLegacy(*output);
    output->end();
}

void
statsReset()
{
    gem5::statistics::processResetQueue();
}

void
statsEnable()
{
    if (auto *root = rootGroup(); root != nullptr) {
        statsEnableGroup(*root);
    }

    statsEnableLegacy();
}

} // namespace CxxConfig
