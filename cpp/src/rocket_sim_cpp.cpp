#include "rocket_sim_cpp.hpp"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <stdexcept>

namespace rocketsim {
namespace {

double norm(const Vec3& v) {
  return std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
}

Vec3 add(const Vec3& a, const Vec3& b) { return Vec3{a.x + b.x, a.y + b.y, a.z + b.z}; }
Vec3 sub(const Vec3& a, const Vec3& b) { return Vec3{a.x - b.x, a.y - b.y, a.z - b.z}; }
Vec3 scale(const Vec3& v, double s) { return Vec3{v.x * s, v.y * s, v.z * s}; }

Vec3 gravity_accel(const Vec3& pos, double mu) {
  const double r = norm(pos);
  if (r < 1.0) {
    return Vec3{0.0, 0.0, -9.80665};
  }
  const double k = -mu / (r * r * r);
  return scale(pos, k);
}

double air_density(double altitude_m) {
  const double h = std::max(0.0, altitude_m);
  if (h <= 11000.0) {
    const double t = 288.15 - 0.0065 * h;
    const double p = 101325.0 * std::pow(t / 288.15, 5.2558797);
    return p / (287.05 * t);
  }
  if (h <= 20000.0) {
    const double t = 216.65;
    const double p = 22632.06 * std::exp(-9.80665 * (h - 11000.0) / (287.05 * t));
    return p / (287.05 * t);
  }
  if (h <= 32000.0) {
    const double t = 216.65 + 0.001 * (h - 20000.0);
    const double p = 5474.889 * std::pow(216.65 / t, 9.80665 / (287.05 * 0.001));
    return p / (287.05 * t);
  }
  return 0.0;
}

struct Derivative {
  Vec3 dpos;
  Vec3 dvel;
  double dmass;
};

Derivative deriv(const State& s, const Config& cfg, const Stage* stage, double stage_time_s, bool burning) {
  const double r = norm(s.position_m);
  const double altitude_m = std::max(0.0, r - cfg.earth_radius_m);

  double thrust_n = 0.0;
  double mdot = 0.0;
  double cd = 0.25;
  double area = 5.0;

  if (burning && stage != nullptr && stage_time_s <= stage->burn_time_s) {
    thrust_n = stage->max_thrust_n;
    mdot = thrust_n / (stage->isp_s * cfg.g0_m_s2);
    cd = stage->cd;
    area = stage->reference_area_m2;
  }

  const Vec3 grav = gravity_accel(s.position_m, cfg.earth_mu_m3_s2);
  const Vec3 radial_hat = scale(s.position_m, 1.0 / std::max(r, 1.0));

  // Gravity-turn style command in inertial frame.
  const double pitch_cmd_rad = (stage_time_s < 8.0) ? 0.0 : std::min((stage_time_s - 8.0) * M_PI / 180.0 * 0.28, 28.0 * M_PI / 180.0);
  const Vec3 ref{0.0, 0.0, 1.0};
  Vec3 east = Vec3{ref.y * radial_hat.z - ref.z * radial_hat.y, ref.z * radial_hat.x - ref.x * radial_hat.z,
                   ref.x * radial_hat.y - ref.y * radial_hat.x};
  const double en = norm(east);
  if (en > 1e-8) {
    east = scale(east, 1.0 / en);
  } else {
    east = Vec3{0.0, 1.0, 0.0};
  }

  const Vec3 thrust_dir = add(scale(radial_hat, std::cos(pitch_cmd_rad)), scale(east, std::sin(pitch_cmd_rad)));
  const Vec3 thrust = scale(thrust_dir, thrust_n);

  const Vec3 rel_v = sub(s.velocity_m_s, cfg.wind_i_m_s);
  const double speed = norm(rel_v);
  Vec3 drag{0.0, 0.0, 0.0};
  if (speed > 1e-6) {
    const double rho = air_density(altitude_m);
    const double drag_mag = 0.5 * rho * speed * speed * cd * area;
    drag = scale(rel_v, -drag_mag / speed);
  }

  const Vec3 accel = add(grav, scale(add(thrust, drag), 1.0 / std::max(s.mass_kg, 1.0)));
  return Derivative{s.velocity_m_s, accel, -mdot};
}

State add_state(const State& s, const Derivative& k, double dt) {
  return State{
      add(s.position_m, scale(k.dpos, dt)),
      add(s.velocity_m_s, scale(k.dvel, dt)),
      s.euler_rad,
      s.body_rates_rad_s,
      s.mass_kg + dt * k.dmass,
  };
}

State rk4_step(const State& s, const Config& cfg, const Stage* stage, double stage_time_s, double dt, bool burning) {
  const Derivative k1 = deriv(s, cfg, stage, stage_time_s, burning);
  const Derivative k2 = deriv(add_state(s, k1, 0.5 * dt), cfg, stage, stage_time_s + 0.5 * dt, burning);
  const Derivative k3 = deriv(add_state(s, k2, 0.5 * dt), cfg, stage, stage_time_s + 0.5 * dt, burning);
  const Derivative k4 = deriv(add_state(s, k3, dt), cfg, stage, stage_time_s + dt, burning);

  const Vec3 dpos = scale(add(add(k1.dpos, scale(k2.dpos, 2.0)), add(scale(k3.dpos, 2.0), k4.dpos)), 1.0 / 6.0);
  const Vec3 dvel = scale(add(add(k1.dvel, scale(k2.dvel, 2.0)), add(scale(k3.dvel, 2.0), k4.dvel)), 1.0 / 6.0);
  const double dmass = (k1.dmass + 2.0 * k2.dmass + 2.0 * k3.dmass + k4.dmass) / 6.0;

  return State{
      add(s.position_m, scale(dpos, dt)),
      add(s.velocity_m_s, scale(dvel, dt)),
      s.euler_rad,
      s.body_rates_rad_s,
      s.mass_kg + dt * dmass,
  };
}

}  // namespace

Config default_config() {
  Config cfg;
  cfg.stages = {
      Stage{"Stage 1", 22000.0, 395000.0, 7600000.0, 282.0, 162.0, 10.8, 0.34},
      Stage{"Stage 2", 4000.0, 92000.0, 981000.0, 348.0, 340.0, 3.5, 0.22},
  };
  return cfg;
}

Result run_simulation(const Config& cfg) {
  if (cfg.stages.empty()) {
    throw std::runtime_error("At least one stage is required.");
  }

  const int n = static_cast<int>(cfg.duration_s / cfg.dt_s) + 1;
  Result out;
  out.time_s.reserve(n);
  out.states.reserve(n);
  out.altitude_m.reserve(n);
  out.dynamic_pressure_pa.reserve(n);
  out.stage_index.reserve(n);
  out.phase_index.reserve(n);

  double mass0 = cfg.payload_mass_kg;
  for (const auto& s : cfg.stages) {
    mass0 += s.dry_mass_kg + s.propellant_mass_kg;
  }

  State state{{cfg.earth_radius_m, 0.0, 0.0}, {0.0, 0.0, 0.0}, {0.0, 0.0, 0.0}, {0.0, 0.0, 0.0}, mass0};
  int stage_idx = 0;
  double stage_prop = cfg.stages[0].propellant_mass_kg;
  double stage_t = 0.0;
  bool staging = false;
  double staging_t = 0.0;
  double drop_mass = 0.0;
  FlightPhase phase = FlightPhase::IGNITION;
  double prev_vertical_speed = 0.0;
  bool have_prev_vertical_speed = false;

  for (int i = 0; i < n; ++i) {
    const double t = i * cfg.dt_s;
    const double r = norm(state.position_m);
    const double alt = std::max(0.0, r - cfg.earth_radius_m);
    const Vec3 rel_v = sub(state.velocity_m_s, cfg.wind_i_m_s);
    const double speed = norm(rel_v);
    const double q = 0.5 * air_density(alt) * speed * speed;
    const Vec3 radial_hat = scale(state.position_m, 1.0 / std::max(r, 1.0));
    const double vertical_speed = state.velocity_m_s.x * radial_hat.x + state.velocity_m_s.y * radial_hat.y +
                                  state.velocity_m_s.z * radial_hat.z;

    out.time_s.push_back(t);
    out.states.push_back(state);
    out.altitude_m.push_back(alt);
    out.dynamic_pressure_pa.push_back(q);
    out.stage_index.push_back(stage_idx);
    out.phase_index.push_back(static_cast<int>(phase));

    if (i == n - 1) {
      break;
    }

    bool burning = false;
    const Stage* stage = nullptr;
    if (!staging && stage_idx < static_cast<int>(cfg.stages.size()) && stage_prop > 0.0) {
      burning = true;
      stage = &cfg.stages[stage_idx];
    }

    State next = rk4_step(state, cfg, stage, stage_t, cfg.dt_s, burning);

    if (burning && stage != nullptr) {
      const double mdot = stage->max_thrust_n / (stage->isp_s * cfg.g0_m_s2);
      stage_prop = std::max(0.0, stage_prop - mdot * cfg.dt_s);
      stage_t += cfg.dt_s;
      if (stage_prop <= 0.0 || stage_t >= stage->burn_time_s) {
        if (out.meco_time_s < 0.0) {
          out.meco_time_s = t;
        }
        phase = FlightPhase::STAGING;
        staging = true;
        staging_t = 0.0;
        drop_mass = stage->dry_mass_kg;
      }
    } else if (staging) {
      staging_t += cfg.dt_s;
      if (staging_t >= cfg.staging_delay_s) {
        next.mass_kg -= drop_mass;
        stage_idx += 1;
        staging = false;
        if (out.staging_time_s < 0.0) {
          out.staging_time_s = t;
        }
        if (stage_idx < static_cast<int>(cfg.stages.size())) {
          stage_prop = cfg.stages[stage_idx].propellant_mass_kg;
          stage_t = 0.0;
          phase = FlightPhase::ASCENT;
        } else {
          phase = FlightPhase::COAST;
        }
      }
    }

    if (phase == FlightPhase::IGNITION && t >= 2.0) {
      phase = FlightPhase::ASCENT;
    }
    if (have_prev_vertical_speed && (phase == FlightPhase::ASCENT || phase == FlightPhase::COAST) &&
        prev_vertical_speed > 0.0 && vertical_speed <= 0.0) {
      phase = FlightPhase::APOGEE;
      if (out.apogee_event_time_s < 0.0) {
        out.apogee_event_time_s = t;
      }
    } else if (phase == FlightPhase::APOGEE) {
      phase = FlightPhase::REENTRY;
      if (out.reentry_time_s < 0.0) {
        out.reentry_time_s = t;
      }
    } else if (phase == FlightPhase::REENTRY && alt <= 50.0) {
      phase = FlightPhase::LANDING;
      if (out.landing_time_s < 0.0) {
        out.landing_time_s = t;
      }
    }

    next.mass_kg = std::max(next.mass_kg, cfg.payload_mass_kg);
    state = next;
    prev_vertical_speed = vertical_speed;
    have_prev_vertical_speed = true;
  }

  const auto apogee_it = std::max_element(out.altitude_m.begin(), out.altitude_m.end());
  const auto maxq_it = std::max_element(out.dynamic_pressure_pa.begin(), out.dynamic_pressure_pa.end());
  const std::size_t apogee_idx = static_cast<std::size_t>(std::distance(out.altitude_m.begin(), apogee_it));
  const std::size_t maxq_idx = static_cast<std::size_t>(std::distance(out.dynamic_pressure_pa.begin(), maxq_it));
  out.apogee_m = *apogee_it;
  out.apogee_time_s = out.time_s[apogee_idx];
  out.max_q_pa = *maxq_it;
  out.max_q_time_s = out.time_s[maxq_idx];

  double maxq_ascent_80 = -1.0;
  double maxq_ascent_80_t = 0.0;
  for (std::size_t i = 0; i < out.time_s.size(); ++i) {
    if (out.altitude_m[i] <= 80000.0 && out.time_s[i] <= out.apogee_time_s) {
      if (out.dynamic_pressure_pa[i] > maxq_ascent_80) {
        maxq_ascent_80 = out.dynamic_pressure_pa[i];
        maxq_ascent_80_t = out.time_s[i];
      }
    }
  }
  if (maxq_ascent_80 < 0.0) {
    maxq_ascent_80 = out.max_q_pa;
    maxq_ascent_80_t = out.max_q_time_s;
  }
  out.max_q_ascent_80km_pa = maxq_ascent_80;
  out.max_q_ascent_80km_time_s = maxq_ascent_80_t;

  return out;
}

void write_csv(const Result& result, const std::string& out_path) {
  std::ofstream f(out_path);
  if (!f) {
    throw std::runtime_error("Failed to open output CSV: " + out_path);
  }

  f << "time_s,stage_idx,altitude_m,dynamic_pressure_pa,x_m,y_m,z_m,vx_m_s,vy_m_s,vz_m_s,mass_kg\n";
  f << std::fixed << std::setprecision(6);
  for (std::size_t i = 0; i < result.time_s.size(); ++i) {
    const State& s = result.states[i];
    f << result.time_s[i] << ',' << result.stage_index[i] << ',' << result.altitude_m[i] << ',' << result.dynamic_pressure_pa[i] << ','
      << s.position_m.x << ',' << s.position_m.y << ',' << s.position_m.z << ',' << s.velocity_m_s.x << ',' << s.velocity_m_s.y << ','
      << s.velocity_m_s.z << ',' << s.mass_kg << '\n';
  }
}

}  // namespace rocketsim
