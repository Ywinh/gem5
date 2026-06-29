#include <systemc>
#include <tlm>

#include "cli_parser.hh"
#include "inst_fifo.hh"
#include "report_handler.hh"
#include "sim_control.hh"
#include "slave_transactor.hh"
#include "stats.hh"

int
sc_main(int argc, char **argv)
{
    CliParser parser;
    parser.parse(argc, argv);

    sc_core::sc_report_handler::set_handler(reportHandler);

    Gem5SystemC::Gem5SimControl sim_control("gem5",
                                            parser.getConfigFile(),
                                            parser.getSimulationEnd(),
                                            parser.getDebugFlags());

    Gem5SystemC::Gem5SlaveTransactor transactor("transactor", "transactor");

    InstrFifo fifo("fifo");
    fifo.BusSlaveTsocket.bind(transactor.socket);
    transactor.sim_control.bind(sim_control);

    sc_core::sc_start();

    SC_REPORT_INFO("sc_main", "End of Simulation");

    CxxConfig::statsDump();

    return EXIT_SUCCESS;
}
