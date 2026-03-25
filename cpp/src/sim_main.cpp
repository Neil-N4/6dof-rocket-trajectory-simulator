#include "rocket_sim_cpp.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  rocketsim::Config cfg = rocketsim::default_config();
  std::string out_csv = "outputs/cpp_flight_states.csv";
  std::string summary_out = "outputs/cpp_summary.txt";

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--dt" && i + 1 < argc) {
      cfg.dt_s = std::stod(argv[++i]);
    } else if (a == "--duration" && i + 1 < argc) {
      cfg.duration_s = std::stod(argv[++i]);
    } else if (a == "--out" && i + 1 < argc) {
      out_csv = argv[++i];
    } else if (a == "--summary" && i + 1 < argc) {
      summary_out = argv[++i];
    }
  }

  std::filesystem::create_directories(std::filesystem::path(out_csv).parent_path());
  std::filesystem::create_directories(std::filesystem::path(summary_out).parent_path());
  const rocketsim::Result result = rocketsim::run_simulation(cfg);
  rocketsim::write_csv(result, out_csv);

  std::ofstream sf(summary_out);
  sf << "apogee_m=" << result.apogee_m << "\n";
  sf << "apogee_time_s=" << result.apogee_time_s << "\n";
  sf << "max_q_pa=" << result.max_q_pa << "\n";
  sf << "max_q_time_s=" << result.max_q_time_s << "\n";
  sf << "max_q_ascent_80km_pa=" << result.max_q_ascent_80km_pa << "\n";
  sf << "max_q_ascent_80km_time_s=" << result.max_q_ascent_80km_time_s << "\n";
  sf << "meco_time_s=" << result.meco_time_s << "\n";
  sf << "staging_time_s=" << result.staging_time_s << "\n";
  sf << "apogee_event_time_s=" << result.apogee_event_time_s << "\n";
  sf << "reentry_time_s=" << result.reentry_time_s << "\n";
  sf << "landing_time_s=" << result.landing_time_s << "\n";

  std::cout << "[C++] Apogee: " << result.apogee_m / 1000.0 << " km at t=" << result.apogee_time_s << " s\n";
  std::cout << "[C++] Max-Q (all): " << result.max_q_pa / 1000.0 << " kPa at t=" << result.max_q_time_s << " s\n";
  std::cout << "[C++] Max-Q (<=80 km ascent): " << result.max_q_ascent_80km_pa / 1000.0 << " kPa at t="
            << result.max_q_ascent_80km_time_s << " s\n";
  std::cout << "[C++] CSV: " << out_csv << "\n";
  std::cout << "[C++] Summary: " << summary_out << "\n";
  return 0;
}
