#include "inst_fifo.hh"

SC_HAS_PROCESS(InstrFifo);

InstrFifo::InstrFifo(sc_module_name name) :
    sc_module(name),
    BaseAddr(0x0a082000),
    Size(FifoDataSize + 0x8),
    fifo0(4),
    fifo1(4),
    fifo2(4),
    fifo3(4),
    BusSlaveTsocket("BusSlaveTsocket")
{
    BusSlaveTsocket.register_b_transport(this, &InstrFifo::b_transport_bus);

    SC_THREAD(popFifo);
}

InstrFifo::InstOutput::InstOutput() :
    fifo0Data(0), fifo1Data(0), fifo2Data(0), fifo3Data(0)
{}

bool
InstrFifo::InAddrRange(uint64_t addr)
{
    return (addr >= BaseAddr) && (addr < BaseAddr + Size) &&
           ((addr & 0x7) == 0);
}

unsigned
InstrFifo::get_fifo_id(uint64_t addr)
{
    // base addr:0xa082000
    uint64_t offset = addr - BaseAddr;

    // offset[4:3]
    // 0x00,0x20,0x40,0x60 -> 0b00 -> fifo0
    // 0x08,0x28,0x48,0x68 -> 0b01 -> fifo1
    // 0x10,0x30,0x50,0x70 -> 0b10 -> fifo2
    // 0x18,0x38,0x58,0x78 -> 0b11 -> fifo3asd
    return (offset >> 3) & 0x3;
}

void
InstrFifo::b_transport_bus(
    tlm::tlm_generic_payload &trans, sc_core::sc_time &delay)
{
    (void)delay;
    assert(trans.get_command() == tlm::TLM_WRITE_COMMAND);

    uint64_t addr = trans.get_address();
    assert(InAddrRange(addr));
    assert(trans.get_data_length() == 8);

    unsigned char *data_ptr = trans.get_data_ptr();
    uint64_t data;
    memcpy(&data, data_ptr, 8);

    const uint64_t offset = addr - BaseAddr;

    if (offset == ExitRegOffset) {
        printf("[inst_fifo_exit] exit code 0x%016lx", data);
        if (data & (1ULL << 63)) {
            printf(" (unhandled trap cause %llu)",
                   static_cast<unsigned long long>(data & ~(1ULL << 63)));
        }
        printf("\n");

        trans.is_response_ok();
        sc_core::sc_stop();
        return;
    }

#ifdef test
    uint8_t id = get_fifo_id(addr);
    printf(
        "[inst_fifo_in] fifo%d, receive a packet from gem5,addr %lx,"
        "length 8,data %lx\n",
        id, addr, data);
#endif

    switch (get_fifo_id(addr)) {
        // fifo.write is blocking and waits for a free entry.
      case 0:
        fifo0.writeWithOffset(data, offset);
        break;
      case 1:
        fifo1.writeWithOffset(data, offset);
        break;
      case 2:
        fifo2.writeWithOffset(data, offset);
        break;
      case 3:
        fifo3.writeWithOffset(data, offset);
        break;
        default:
            assert(0);
            break;
    }

    trans.is_response_ok();
    // TODO: implement delay

    // Check whether all four FIFOs have data available.
    if (fifo0.num_available() && fifo1.num_available() &&
        fifo2.num_available() && fifo3.num_available()) {
        DataAvailEvent.notify(SC_ZERO_TIME); // todo delay
    }

    return;
}

InstrFifo::decodeInstr *
InstrFifo::decode(InstrFifo::InstOutput *data)
{
    (void)data;
    // todo
    return nullptr;
}

void
InstrFifo::dumpFifoState() const
{
#ifdef test
    fifo0.dumpEntries("fifo0", 4);
    fifo1.dumpEntries("fifo1", 4);
    fifo2.dumpEntries("fifo2", 4);
    fifo3.dumpEntries("fifo3", 4);
#endif
}

void
InstrFifo::popFifo()
{
    while (true) {
        // read will blocking, maybe no need to wait explitly
        wait(DataAvailEvent);

        // dumpFifoState();

        // todo decode

        // fifo blocking read
        InstOutput data256;
        data256.fifo0Data = fifo0.read();
        data256.fifo1Data = fifo1.read();
        data256.fifo2Data = fifo2.read();
        data256.fifo3Data = fifo3.read();

        decodeInstr *outData = decode(&data256);
        (void)outData;

#ifdef test
        printf(
            "[inst_fifo_out] pop 4 entry to next module,data3:%lx,data2:%lx,"
            "data1:%lx,data0:%lx\n",
            data256.fifo3Data, data256.fifo2Data,
            data256.fifo1Data, data256.fifo0Data);
#endif

        // mInstrFifoPPort->put(outData);
        // wake?
    }
}
