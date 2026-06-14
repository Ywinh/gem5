/*
 * Copyright (c) 2026
 * All rights reserved.
 */

#ifndef __ARCH_RISCV_EXT_INST_HH__
#define __ARCH_RISCV_EXT_INST_HH__

#include <string>

#include "arch/riscv/insts/static_inst.hh"

namespace gem5
{

namespace RiscvISA
{

class ExtOp : public RiscvStaticInst
{
  protected:
    uint8_t imm1;
    uint8_t imm2;

    ExtOp(const char *mnem, ExtMachInst _machInst, OpClass __opClass)
        : RiscvStaticInst(mnem, _machInst, __opClass), imm1(0), imm2(0)
    {}

    std::string generateDisassembly(
        Addr pc, const loader::SymbolTable *symtab) const override;
};

} // namespace RiscvISA
} // namespace gem5

#endif // __ARCH_RISCV_EXT_INST_HH__
