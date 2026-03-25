#include <cmath>
#include <iostream>

struct State {
  double h_m;
  double v_m_s;
};

static State deriv(double t_s, const State& x, double m0_kg, double mdot_kg_s, double thrust_n, double g_m_s2) {
  (void)x.h_m;
  const double m = std::max(m0_kg - mdot_kg_s * t_s, 1.0);
  return State{ x.v_m_s, thrust_n / m - g_m_s2 };
}

static State add(const State& a, const State& b, double scale) {
  return State{a.h_m + scale * b.h_m, a.v_m_s + scale * b.v_m_s};
}

static State rk4_step(double t_s, const State& x, double dt_s, double m0_kg, double mdot_kg_s, double thrust_n, double g_m_s2) {
  const State k1 = deriv(t_s, x, m0_kg, mdot_kg_s, thrust_n, g_m_s2);
  const State k2 = deriv(t_s + 0.5 * dt_s, add(x, k1, 0.5 * dt_s), m0_kg, mdot_kg_s, thrust_n, g_m_s2);
  const State k3 = deriv(t_s + 0.5 * dt_s, add(x, k2, 0.5 * dt_s), m0_kg, mdot_kg_s, thrust_n, g_m_s2);
  const State k4 = deriv(t_s + dt_s, add(x, k3, dt_s), m0_kg, mdot_kg_s, thrust_n, g_m_s2);

  return State{
      x.h_m + dt_s * (k1.h_m + 2.0 * k2.h_m + 2.0 * k3.h_m + k4.h_m) / 6.0,
      x.v_m_s + dt_s * (k1.v_m_s + 2.0 * k2.v_m_s + 2.0 * k3.v_m_s + k4.v_m_s) / 6.0,
  };
}

int main() {
  const double m0_kg = 150000.0;
  const double thrust_n = 2000000.0;
  const double isp_s = 300.0;
  const double g_m_s2 = 9.80665;
  const double burn_time_s = 35.0;
  const double dt_s = 0.02;
  const double mdot_kg_s = thrust_n / (isp_s * g_m_s2);

  State x{0.0, 0.0};
  double t_s = 0.0;
  for (int i = 0; i < static_cast<int>(burn_time_s / dt_s); ++i) {
    x = rk4_step(t_s, x, dt_s, m0_kg, mdot_kg_s, thrust_n, g_m_s2);
    t_s += dt_s;
  }

  std::cout << "Vertical burn altitude (RK4, C++): " << x.h_m << " m\n";
  std::cout << "Vertical burn velocity (RK4, C++): " << x.v_m_s << " m/s\n";
  return 0;
}
