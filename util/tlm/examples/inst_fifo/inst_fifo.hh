#pragma once

#include <tlm_utils/simple_target_socket.h>

#include <cstdint>
#include <cstdio>
#include <systemc>
#include <tlm>
#include <vector>

using namespace sc_core;

#define test 1

template <typename T>
class DebugFifo : public sc_fifo<T>
{
  public:
    explicit DebugFifo(int size_ = 16) :
        sc_fifo<T>(size_), offsets(size_, 0)
    {}

    explicit DebugFifo(const char *name_, int size_ = 16) :
        sc_fifo<T>(name_, size_), offsets(size_, 0)
    {}

    void writeWithOffset(const T &val, uint64_t offset)
    {
        sc_fifo<T>::write(val);
        const int slot = (this->m_wi + this->m_size - 1) % this->m_size;
        offsets[slot] = offset;
    }

    void dumpEntries(const char *fifo_name, unsigned entry_count) const
    {
        std::printf("[inst_fifo_dump] %s num_available=%d num_free=%d\n",
                    fifo_name, this->num_available(), this->num_free());

        int idx = this->m_ri;
        const int readable = this->m_size - this->m_free;
        for (unsigned entry = 0; entry < entry_count; ++entry) {
            if (entry < static_cast<unsigned>(readable)) {
                const auto offset =
                    static_cast<unsigned long long>(offsets[idx]);
                const auto data =
                    static_cast<unsigned long long>(this->m_buf[idx]);
                std::printf(
                    "[inst_fifo_dump] %s entry%u offset 0x%02llx "
                    "data 0x%016llx\n",
                    fifo_name, entry, offset, data);
                idx = (idx + 1) % this->m_size;
            } else {
                std::printf(
                    "[inst_fifo_dump] %s entry%u offset <empty> "
                    "data <empty>\n",
                    fifo_name, entry);
            }
        }
    }

  private:
    std::vector<uint64_t> offsets;
};

class InstrFifo : public sc_module
{
  public:
    class InstOutput
    {
      public:
        InstOutput();

        uint64_t fifo0Data;
        uint64_t fifo1Data;
        uint64_t fifo2Data;
        uint64_t fifo3Data;
    };

    class decodeInstr
    {
        // todo
    };

    InstrFifo(sc_module_name name);

    tlm_utils::simple_target_socket<InstrFifo> BusSlaveTsocket;

  private:
    static constexpr uint64_t FifoDataSize = 0x80;
    static constexpr uint64_t ExitRegOffset = 0x80;

    DebugFifo<uint64_t> fifo0;
    DebugFifo<uint64_t> fifo1;
    DebugFifo<uint64_t> fifo2;
    DebugFifo<uint64_t> fifo3;

    void b_transport_bus(tlm::tlm_generic_payload &trans,
                         sc_core::sc_time &delay);

    uint64_t BaseAddr;
    uint64_t Size;

    void pushFifo(sc_fifo<uint64_t> &fifo, uint64_t &data);
    void dumpFifoState() const;
    unsigned get_fifo_id(uint64_t addr);
    bool InAddrRange(uint64_t addr);
    void popFifo();

    decodeInstr *decode(InstOutput *data);

    sc_core::sc_event DataAvailEvent;
};
