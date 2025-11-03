// #ifndef __BOOTCAMP_INSPECTOR_GADGET_INSPECTOR_GADGET__HH
// #define __BOOTCAMP_INSPECTOR_GADGET_INSPECTOR_GADGET__HH

// #include "params/InspectorGadget.hh"
// #include "sim/clocked_object.hh"
// #include "mem/packet.hh"
// #include "mem/port.hh"

// namespace gem5
// {

// class InspectorGadget:public ClockedObject
// {
//     private:
//         int inspectionBufferEntries;
//         int responseBufferEntries;
//         Tick align(Tick when);

//         class CPUSidePort : public ResponsePort
//         {
//             private:
//              InspectorGadget* owner;
//              bool needToSendRetry;
//              PacketPtr blockedPacket;

//              public:
//              CPUSidePort(InspectorGadget* owner, const std::string& name):
//                 ResponsePort(name), owner(owner), needToSendRetry(false), blockedPacket(nullptr)
//                 {}

//             bool needRetry() const { return needRetry; }
//             bool blocked() const {return blockedPacket!=nullptr;}
//             void sendPacked(PacketPtr pkt);

//             virtual AddrRangeList getAddrRanges() const override;
//             virtual bool recvTimingReq(PacketPtr pkt) override;
//             virtual Tick recvAtomic(PacketPtr pkt) override;
//             virtual void recvFunctional(PacketPtr pkt) override;
//             virtual void recvRespRetry() override;
//         };

//         class MemSidePort: public RequestPort
//         {
//             private:
//             InspectorGadget* owner;
//             bool needToSendRetry;
//             PacketPtr blockedPacket;

//             public:
//             MemSidePort(InspectorGadget* owner, const std::string& name):
//                     RequestPort(name), owner(owner), needToSendRetry(false), blockedPacket(nullptr)
//                 {}
//             bool needRetry() const { return needToSendRetry; }
//             bool blocked() const { return blockedPacket != nullptr; }
//             void sendPacket(PacketPtr pkt);

//             virtual bool recvTimingResp(PacketPtr pkt) override;
//             virtual void recvReqRetry() override;
//         };

//         CPUSidePort cpuSidePort;
//         MemSidePort memSidePort;


//     public:
//         InspectorGadget(const InspectorGadget& params);
//         virtual Port& getPort(const std::string& if_name, PortID idxInvalidPortID);
// };


// }


// #endif
