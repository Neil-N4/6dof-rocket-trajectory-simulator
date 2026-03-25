#include "rocket_sim_cpp.hpp"

#include <cmath>
#include <iostream>
#include <string>
#include <vector>

namespace {

bool check(bool condition, const std::string& msg, std::vector<std::string>& failures) {
  if (condition) {
    std::cout << "PASS: " << msg << "\n";
    return true;
  }
  std::cout << "FAIL: " << msg << "\n";
  failures.push_back(msg);
  return false;
}

}  // namespace

int main() {
  rocketsim::Config cfg = rocketsim::default_config();
  cfg.dt_s = 0.1;
  cfg.duration_s = 600.0;

  const rocketsim::Result res = rocketsim::run_simulation(cfg);
  std::vector<std::string> failures;

  check(!res.time_s.empty(), "Simulation produced samples", failures);
  check(res.stage_index.size() == res.time_s.size(), "Stage history length matches time history", failures);
  check(res.phase_index.size() == res.time_s.size(), "Phase history length matches time history", failures);

  int max_stage = 0;
  for (int s : res.stage_index) {
    if (s > max_stage) {
      max_stage = s;
    }
  }
  check(max_stage >= 1, "Stage transition occurred", failures);

  check(res.apogee_m > 0.0, "Apogee positive", failures);
  check(res.max_q_ascent_80km_pa > 0.0, "Ascent max-q positive", failures);
  check(res.meco_time_s >= 0.0, "MECO detected", failures);
  check(res.staging_time_s >= 0.0, "Staging detected", failures);
  if (res.meco_time_s >= 0.0 && res.staging_time_s >= 0.0) {
    check(res.meco_time_s < res.staging_time_s, "MECO precedes staging", failures);
  }

  bool has_ascent = false;
  bool has_staging = false;
  bool has_coast_or_reentry = false;
  for (int p : res.phase_index) {
    if (p == static_cast<int>(rocketsim::FlightPhase::ASCENT)) {
      has_ascent = true;
    }
    if (p == static_cast<int>(rocketsim::FlightPhase::STAGING)) {
      has_staging = true;
    }
    if (p == static_cast<int>(rocketsim::FlightPhase::COAST) || p == static_cast<int>(rocketsim::FlightPhase::REENTRY)) {
      has_coast_or_reentry = true;
    }
  }
  check(has_ascent, "ASCENT phase observed", failures);
  check(has_staging, "STAGING phase observed", failures);
  check(has_coast_or_reentry, "COAST/REENTRY phase observed", failures);

  if (!failures.empty()) {
    std::cout << "\nC++ tests failed:\n";
    for (const auto& f : failures) {
      std::cout << " - " << f << "\n";
    }
    return 1;
  }

  std::cout << "\nC++ tests passed.\n";
  return 0;
}
