/*
 * Copyright (c) 2026
 * All rights reserved.
 */

#include "arch/riscv/insts/ext.hh"

#include <sstream>
#include <string>

#include "arch/riscv/utility.hh"

namespace gem5
{

namespace RiscvISA
{

std::string
ExtOp::generateDisassembly(Addr pc, const loader::SymbolTable *symtab) const
{
    std::stringstream ss;
    ss << mnemonic << ' ' << registerName(destRegIdx(0)) << ", "
       << registerName(srcRegIdx(0)) << ", "
       << static_cast<uint32_t>(imm1) << ", "
       << static_cast<uint32_t>(imm2);
    return ss.str();
}

} // namespace RiscvISA
} // namespace gem5
