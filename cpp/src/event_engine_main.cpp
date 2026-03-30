#include "rocket_sim_cpp.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  rocketsim::Config cfg = rocketsim::default_config();
  std::string out_csv = "outputs/cpp_event_flight_states.csv";
  std::string summary_out = "outputs/cpp_event_summary.txt";
  std::string config_path;

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--config" && i + 1 < argc) {
      config_path = argv[++i];
    } else if (a == "--dt" && i + 1 < argc) {
      cfg.dt_s = std::stod(argv[++i]);
    } else if (a == "--duration" && i + 1 < argc) {
      cfg.duration_s = std::stod(argv[++i]);
    } else if (a == "--out" && i + 1 < argc) {
      out_csv = argv[++i];
    } else if (a == "--summary" && i + 1 < argc) {
      summary_out = argv[++i];
    }
  }

  if (!config_path.empty()) {
    std::string err;
    if (!rocketsim::load_config_yaml(config_path, cfg, err)) {
      std::cerr << "[C++] Failed to load config: " << err << "\n";
      return 1;
    }
  }

  std::filesystem::create_directories(std::filesystem::path(out_csv).parent_path());
  std::filesystem::create_directories(std::filesystem::path(summary_out).parent_path());

  const rocketsim::EventEngineResult result = rocketsim::run_simulation_event_driven(cfg);
  rocketsim::write_csv(result.sim, out_csv);

  std::ofstream sf(summary_out);
  sf << "apogee_m=" << result.sim.apogee_m << "\n";
  sf << "max_q_ascent_80km_pa=" << result.sim.max_q_ascent_80km_pa << "\n";
  sf << "events_pushed=" << result.stats.pushed << "\n";
  sf << "events_popped=" << result.stats.popped << "\n";
  sf << "events_dropped=" << result.stats.dropped << "\n";

  std::cout << "[C++ Event Engine] Apogee: " << result.sim.apogee_m / 1000.0 << " km\n";
  std::cout << "[C++ Event Engine] Max-Q(<=80km): " << result.sim.max_q_ascent_80km_pa / 1000.0 << " kPa\n";
  std::cout << "[C++ Event Engine] Queue pushed=" << result.stats.pushed << " popped=" << result.stats.popped
            << " dropped=" << result.stats.dropped << "\n";
  std::cout << "[C++ Event Engine] CSV: " << out_csv << "\n";
  return 0;
}
