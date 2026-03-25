#include "rocket_sim_cpp.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace rocketsim {
namespace {

std::string trim(const std::string& s) {
  std::size_t a = 0;
  while (a < s.size() && std::isspace(static_cast<unsigned char>(s[a]))) ++a;
  std::size_t b = s.size();
  while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) --b;
  return s.substr(a, b - a);
}

bool starts_with(const std::string& s, const std::string& p) {
  return s.rfind(p, 0) == 0;
}

bool parse_double(const std::string& s, double& out) {
  try {
    out = std::stod(trim(s));
    return true;
  } catch (...) {
    return false;
  }
}

bool parse_vec3(const std::string& raw, Vec3& v) {
  auto s = trim(raw);
  if (s.empty() || s.front() != '[' || s.back() != ']') return false;
  s = s.substr(1, s.size() - 2);
  std::replace(s.begin(), s.end(), ',', ' ');
  std::istringstream iss(s);
  return (iss >> v.x >> v.y >> v.z) ? true : false;
}

}  // namespace

bool load_config_yaml(const std::string& path, Config& cfg, std::string& err) {
  std::ifstream in(path);
  if (!in) {
    err = "failed to open config: " + path;
    return false;
  }

  Config out = cfg;
  std::vector<Stage> stages;
  bool in_stages = false;
  Stage cur{};
  bool have_stage = false;

  std::string line;
  int line_no = 0;
  while (std::getline(in, line)) {
    ++line_no;
    const std::string t = trim(line);
    if (t.empty() || starts_with(t, "#")) continue;

    if (t == "stages:") {
      in_stages = true;
      continue;
    }

    if (in_stages) {
      if (starts_with(t, "- ")) {
        if (have_stage) stages.push_back(cur);
        cur = Stage{};
        have_stage = true;
        const std::string rest = trim(t.substr(2));
        if (!rest.empty() && starts_with(rest, "name:")) {
          cur.name = trim(rest.substr(5));
        }
        continue;
      }

      const auto colon = t.find(':');
      if (colon == std::string::npos) {
        continue;
      }
      const std::string key = trim(t.substr(0, colon));
      const std::string val = trim(t.substr(colon + 1));
      double d = 0.0;
      if (key == "name") cur.name = val;
      else if (key == "dry_mass_kg" && parse_double(val, d)) cur.dry_mass_kg = d;
      else if (key == "propellant_mass_kg" && parse_double(val, d)) cur.propellant_mass_kg = d;
      else if (key == "max_thrust_n" && parse_double(val, d)) cur.max_thrust_n = d;
      else if (key == "isp_s" && parse_double(val, d)) cur.isp_s = d;
      else if (key == "burn_time_s" && parse_double(val, d)) cur.burn_time_s = d;
      else if (key == "reference_area_m2" && parse_double(val, d)) cur.reference_area_m2 = d;
      else if (key == "cd" && parse_double(val, d)) cur.cd = d;
      continue;
    }

    const auto colon = t.find(':');
    if (colon == std::string::npos) {
      err = "invalid line " + std::to_string(line_no);
      return false;
    }
    const std::string key = trim(t.substr(0, colon));
    const std::string val = trim(t.substr(colon + 1));
    double d = 0.0;

    if (key == "payload_mass_kg" && parse_double(val, d)) out.payload_mass_kg = d;
    else if ((key == "dt_s" || key == "dt") && parse_double(val, d)) out.dt_s = d;
    else if ((key == "sim_duration_s" || key == "duration_s") && parse_double(val, d)) out.duration_s = d;
    else if (key == "staging_delay_s" && parse_double(val, d)) out.staging_delay_s = d;
    else if (key == "wind_i_m_s") {
      Vec3 w{};
      if (!parse_vec3(val, w)) {
        err = "failed to parse wind_i_m_s at line " + std::to_string(line_no);
        return false;
      }
      out.wind_i_m_s = w;
    }
  }

  if (have_stage) stages.push_back(cur);
  if (!stages.empty()) out.stages = stages;
  if (out.stages.empty()) {
    err = "config produced zero stages";
    return false;
  }

  cfg = out;
  return true;
}

}  // namespace rocketsim
