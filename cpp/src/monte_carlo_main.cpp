#include "rocket_sim_cpp.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

namespace {

double percentile(std::vector<double> v, double p) {
  if (v.empty()) return 0.0;
  std::sort(v.begin(), v.end());
  const double idx = (p / 100.0) * (static_cast<double>(v.size() - 1));
  const auto lo = static_cast<std::size_t>(std::floor(idx));
  const auto hi = static_cast<std::size_t>(std::ceil(idx));
  if (lo == hi) return v[lo];
  const double t = idx - static_cast<double>(lo);
  return (1.0 - t) * v[lo] + t * v[hi];
}

}  // namespace

int main(int argc, char** argv) {
  rocketsim::Config base = rocketsim::default_config();
  std::string config_path;
  std::string out_dir = "outputs/cpp_monte_carlo";
  int runs = 200;
  int seed = 123;
  double thrust_sigma = 0.03;
  double mass_sigma = 0.02;
  double cd_sigma = 0.05;
  double wind_sigma = 20.0;

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--config" && i + 1 < argc) config_path = argv[++i];
    else if (a == "--runs" && i + 1 < argc) runs = std::stoi(argv[++i]);
    else if (a == "--seed" && i + 1 < argc) seed = std::stoi(argv[++i]);
    else if (a == "--outdir" && i + 1 < argc) out_dir = argv[++i];
  }

  if (!config_path.empty()) {
    std::string err;
    if (!rocketsim::load_config_yaml(config_path, base, err)) {
      std::cerr << "Failed to load config: " << err << "\n";
      return 1;
    }
  }

  std::filesystem::create_directories(out_dir);
  std::ofstream csv(out_dir + "/monte_carlo_runs.csv");
  csv << "run,apogee_km,max_q_kpa\n";

  std::mt19937_64 rng(static_cast<std::mt19937_64::result_type>(seed));
  std::normal_distribution<double> d_thrust(0.0, thrust_sigma);
  std::normal_distribution<double> d_mass(0.0, mass_sigma);
  std::normal_distribution<double> d_cd(0.0, cd_sigma);
  std::normal_distribution<double> d_wind(0.0, wind_sigma);

  std::vector<double> apogees;
  std::vector<double> maxqs;

  for (int r = 0; r < runs; ++r) {
    rocketsim::Config cfg = base;
    for (auto& s : cfg.stages) {
      const double thrust_scale = std::max(0.75, 1.0 + d_thrust(rng));
      const double mass_scale = std::max(0.75, 1.0 + d_mass(rng));
      const double prop_scale = std::max(0.75, 1.0 + d_mass(rng));
      const double cd_scale = std::max(0.6, 1.0 + d_cd(rng));
      s.max_thrust_n *= thrust_scale;
      s.dry_mass_kg *= mass_scale;
      s.propellant_mass_kg *= prop_scale;
      s.cd *= cd_scale;
    }
    cfg.wind_i_m_s.y += d_wind(rng);

    const auto res = rocketsim::run_simulation(cfg);
    const double apogee_km = res.apogee_m / 1000.0;
    const double maxq_kpa = res.max_q_ascent_80km_pa / 1000.0;
    apogees.push_back(apogee_km);
    maxqs.push_back(maxq_kpa);
    csv << r << ',' << std::fixed << std::setprecision(6) << apogee_km << ',' << maxq_kpa << '\n';

    const int stride = std::max(1, runs / 10);
    if ((r + 1) % stride == 0) {
      std::cout << "Completed " << (r + 1) << "/" << runs << " runs...\n";
    }
  }

  const double ap_p50 = percentile(apogees, 50.0);
  const double ap_p95 = percentile(apogees, 95.0);
  const double q_p50 = percentile(maxqs, 50.0);
  const double q_p95 = percentile(maxqs, 95.0);

  std::ofstream summary(out_dir + "/summary.txt");
  summary << "runs=" << runs << "\n";
  summary << "seed=" << seed << "\n";
  summary << "apogee_km_p50=" << ap_p50 << "\n";
  summary << "apogee_km_p95=" << ap_p95 << "\n";
  summary << "max_q_kpa_p50=" << q_p50 << "\n";
  summary << "max_q_kpa_p95=" << q_p95 << "\n";

  std::cout << "Wrote " << out_dir << "/monte_carlo_runs.csv\n";
  std::cout << "Wrote " << out_dir << "/summary.txt\n";
  std::cout << "P50/P95 Apogee (km): " << ap_p50 << " / " << ap_p95 << "\n";
  std::cout << "P50/P95 Max-Q (kPa): " << q_p50 << " / " << q_p95 << "\n";
  return 0;
}
