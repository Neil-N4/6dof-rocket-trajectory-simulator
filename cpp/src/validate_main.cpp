#include "rocket_sim_cpp.hpp"

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
  const rocketsim::Result result = rocketsim::run_simulation(cfg);

  std::vector<std::string> failures;

  const double apogee_km = result.apogee_m / 1000.0;
  const double max_q_ascent_kpa = result.max_q_ascent_80km_pa / 1000.0;

  check(apogee_km >= 500.0, "Apogee >= 500 km", failures);
  check(max_q_ascent_kpa >= 10.0, "Max-Q ascent >= 10 kPa", failures);
  check(max_q_ascent_kpa <= 120.0, "Max-Q ascent <= 120 kPa", failures);

  check(result.meco_time_s >= 0.0, "MECO event present", failures);
  check(result.staging_time_s >= 0.0, "Staging event present", failures);
  if (result.meco_time_s >= 0.0 && result.staging_time_s >= 0.0) {
    check(result.meco_time_s < result.staging_time_s, "Event ordering meco < staging", failures);
  }

  if (result.apogee_event_time_s >= 0.0 && result.reentry_time_s >= 0.0) {
    check(result.apogee_event_time_s <= result.reentry_time_s, "Event ordering apogee <= reentry", failures);
  }

  bool saw_ascent = false;
  bool saw_staging = false;
  bool saw_coast_or_reentry = false;
  for (int p : result.phase_index) {
    if (p == static_cast<int>(rocketsim::FlightPhase::ASCENT)) saw_ascent = true;
    if (p == static_cast<int>(rocketsim::FlightPhase::STAGING)) saw_staging = true;
    if (p == static_cast<int>(rocketsim::FlightPhase::COAST) || p == static_cast<int>(rocketsim::FlightPhase::REENTRY)) {
      saw_coast_or_reentry = true;
    }
  }
  check(saw_ascent, "Phase ASCENT present", failures);
  check(saw_staging, "Phase STAGING present", failures);
  check(saw_coast_or_reentry, "Phase COAST/REENTRY present", failures);

  if (!failures.empty()) {
    std::cout << "\nC++ validation failed:\n";
    for (const auto& f : failures) {
      std::cout << " - " << f << "\n";
    }
    return 1;
  }

  std::cout << "\nC++ validation passed.\n";
  std::cout << "Apogee: " << apogee_km << " km\n";
  std::cout << "Max-Q ascent (<=80 km): " << max_q_ascent_kpa << " kPa\n";
  return 0;
}
