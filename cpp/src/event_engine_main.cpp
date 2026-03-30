#include "rocket_sim_cpp.hpp"

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  rocketsim::Config cfg = rocketsim::default_config();
  std::string out_csv = "outputs/cpp_event_flight_states.csv";
  std::string summary_out = "outputs/cpp_event_summary.txt";
  std::string config_path;
  double opt_dt = -1.0;
  double opt_duration = -1.0;

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--config" && i + 1 < argc) {
      config_path = argv[++i];
    } else if (a == "--dt" && i + 1 < argc) {
      opt_dt = std::stod(argv[++i]);
    } else if (a == "--duration" && i + 1 < argc) {
      opt_duration = std::stod(argv[++i]);
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
  if (opt_dt > 0.0) {
    cfg.dt_s = opt_dt;
  }
  if (opt_duration > 0.0) {
    cfg.duration_s = opt_duration;
  }

  std::filesystem::create_directories(std::filesystem::path(out_csv).parent_path());
  std::filesystem::create_directories(std::filesystem::path(summary_out).parent_path());

  const auto t0 = std::chrono::high_resolution_clock::now();
  const rocketsim::EventEngineResult result = rocketsim::run_simulation_event_driven(cfg);
  const auto t1 = std::chrono::high_resolution_clock::now();
  const double runtime_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
  const double throughput_eps = (runtime_ms > 0.0) ? (1000.0 * static_cast<double>(result.stats.popped) / runtime_ms) : 0.0;
  rocketsim::write_csv(result.sim, out_csv);

  std::ofstream sf(summary_out);
  sf << "apogee_m=" << result.sim.apogee_m << "\n";
  sf << "max_q_ascent_80km_pa=" << result.sim.max_q_ascent_80km_pa << "\n";
  sf << "events_pushed=" << result.stats.pushed << "\n";
  sf << "events_popped=" << result.stats.popped << "\n";
  sf << "events_dropped=" << result.stats.dropped << "\n";
  sf << "event_mean_latency_s=" << result.stats.mean_latency_s << "\n";
  sf << "event_max_latency_s=" << result.stats.max_latency_s << "\n";
  sf << "runtime_ms=" << runtime_ms << "\n";
  sf << "throughput_events_per_s=" << throughput_eps << "\n";

  std::cout << "[C++ Event Engine] Apogee: " << result.sim.apogee_m / 1000.0 << " km\n";
  std::cout << "[C++ Event Engine] Max-Q(<=80km): " << result.sim.max_q_ascent_80km_pa / 1000.0 << " kPa\n";
  std::cout << "[C++ Event Engine] Queue pushed=" << result.stats.pushed << " popped=" << result.stats.popped
            << " dropped=" << result.stats.dropped << "\n";
  std::cout << "[C++ Event Engine] Mean latency=" << result.stats.mean_latency_s * 1000.0 << " ms max="
            << result.stats.max_latency_s * 1000.0 << " ms\n";
  std::cout << "[C++ Event Engine] Runtime=" << runtime_ms << " ms throughput=" << throughput_eps << " events/s\n";
  std::cout << "[C++ Event Engine] CSV: " << out_csv << "\n";
  return 0;
}
