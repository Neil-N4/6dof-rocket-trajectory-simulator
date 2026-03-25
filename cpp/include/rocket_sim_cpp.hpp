#pragma once

#include <string>
#include <vector>

namespace rocketsim {

enum class FlightPhase {
  IGNITION = 0,
  ASCENT = 1,
  STAGING = 2,
  COAST = 3,
  APOGEE = 4,
  REENTRY = 5,
  LANDING = 6,
};

struct Vec3 {
  double x;
  double y;
  double z;
};

struct Stage {
  std::string name;
  double dry_mass_kg;
  double propellant_mass_kg;
  double max_thrust_n;
  double isp_s;
  double burn_time_s;
  double reference_area_m2;
  double cd;
};

struct Config {
  std::vector<Stage> stages;
  double payload_mass_kg = 15600.0;
  double earth_radius_m = 6371000.0;
  double earth_mu_m3_s2 = 3.986004418e14;
  double g0_m_s2 = 9.80665;
  double dt_s = 0.1;
  double duration_s = 2200.0;
  double staging_delay_s = 2.0;
  Vec3 wind_i_m_s{0.0, 0.0, 0.0};
};

struct State {
  Vec3 position_m;
  Vec3 velocity_m_s;
  Vec3 euler_rad;
  Vec3 body_rates_rad_s;
  double mass_kg;
};

struct Result {
  std::vector<double> time_s;
  std::vector<State> states;
  std::vector<double> altitude_m;
  std::vector<double> dynamic_pressure_pa;
  std::vector<int> stage_index;
  std::vector<int> phase_index;
  double apogee_m = 0.0;
  double apogee_time_s = 0.0;
  double max_q_pa = 0.0;
  double max_q_time_s = 0.0;
  double max_q_ascent_80km_pa = 0.0;
  double max_q_ascent_80km_time_s = 0.0;
  double meco_time_s = -1.0;
  double staging_time_s = -1.0;
  double apogee_event_time_s = -1.0;
  double reentry_time_s = -1.0;
  double landing_time_s = -1.0;
};

Config default_config();
Result run_simulation(const Config& cfg);
void write_csv(const Result& result, const std::string& out_path);

}  // namespace rocketsim
