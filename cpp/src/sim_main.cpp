#include "rocket_sim_cpp.hpp"

#include <filesystem>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  rocketsim::Config cfg = rocketsim::default_config();
  std::string out_csv = "outputs/cpp_flight_states.csv";

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--dt" && i + 1 < argc) {
      cfg.dt_s = std::stod(argv[++i]);
    } else if (a == "--duration" && i + 1 < argc) {
      cfg.duration_s = std::stod(argv[++i]);
    } else if (a == "--out" && i + 1 < argc) {
      out_csv = argv[++i];
    }
  }

  std::filesystem::create_directories(std::filesystem::path(out_csv).parent_path());
  const rocketsim::Result result = rocketsim::run_simulation(cfg);
  rocketsim::write_csv(result, out_csv);

  std::cout << "[C++] Apogee: " << result.apogee_m / 1000.0 << " km at t=" << result.apogee_time_s << " s\n";
  std::cout << "[C++] Max-Q: " << result.max_q_pa / 1000.0 << " kPa at t=" << result.max_q_time_s << " s\n";
  std::cout << "[C++] CSV: " << out_csv << "\n";
  return 0;
}
