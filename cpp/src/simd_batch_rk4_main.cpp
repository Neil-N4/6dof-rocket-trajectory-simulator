#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <iomanip>
#if defined(__x86_64__) || defined(_M_X64)
#include <immintrin.h>
#endif
#include <iostream>
#include <random>
#include <string>
#include <utility>
#include <vector>

namespace {

constexpr double kMu = 3.986004418e14;
constexpr double kRe = 6371000.0;
constexpr double kCdA = 2.5;
constexpr double kMass = 120000.0;
constexpr double kThrust = 1300000.0;

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
  return 0.0;
}

struct K1D {
  double dr;
  double dv;
};

K1D deriv(double r, double v) {
  const double g = -kMu / (r * r);
  const double rho = air_density(r - kRe);
  const double drag = -0.5 * rho * v * std::abs(v) * kCdA / kMass;
  const double a = g + drag + (kThrust / kMass);
  return K1D{v, a};
}

void rk4_scalar_step(double& r, double& v, double dt) {
  const K1D k1 = deriv(r, v);
  const K1D k2 = deriv(r + 0.5 * dt * k1.dr, v + 0.5 * dt * k1.dv);
  const K1D k3 = deriv(r + 0.5 * dt * k2.dr, v + 0.5 * dt * k2.dv);
  const K1D k4 = deriv(r + dt * k3.dr, v + dt * k3.dv);
  r += dt * (k1.dr + 2.0 * k2.dr + 2.0 * k3.dr + k4.dr) / 6.0;
  v += dt * (k1.dv + 2.0 * k2.dv + 2.0 * k3.dv + k4.dv) / 6.0;
}

#if defined(__AVX2__)
void rk4_avx2_step(double* r, double* v, double dt) {
  const __m256d dtv = _mm256_set1_pd(dt);
  const __m256d half = _mm256_set1_pd(0.5);
  const __m256d two = _mm256_set1_pd(2.0);
  const __m256d sixth = _mm256_set1_pd(1.0 / 6.0);
  const __m256d re = _mm256_set1_pd(kRe);
  const __m256d mu = _mm256_set1_pd(kMu);
  const __m256d cda = _mm256_set1_pd(kCdA);
  const __m256d mass = _mm256_set1_pd(kMass);
  const __m256d thrust_a = _mm256_set1_pd(kThrust / kMass);
  const __m256d zero = _mm256_set1_pd(0.0);
  const __m256d rho0 = _mm256_set1_pd(1.225);
  const __m256d hscale = _mm256_set1_pd(1.0 / 100000.0);

  auto deriv_avx = [&](const __m256d rv, const __m256d vv) {
    const __m256d alt = _mm256_max_pd(zero, _mm256_sub_pd(rv, re));
    const __m256d rho = _mm256_mul_pd(rho0, _mm256_max_pd(zero, _mm256_sub_pd(_mm256_set1_pd(1.0), _mm256_mul_pd(alt, hscale))));
    const __m256d r2 = _mm256_mul_pd(rv, rv);
    const __m256d g = _mm256_div_pd(_mm256_mul_pd(_mm256_set1_pd(-1.0), mu), r2);
    const __m256d vabs = _mm256_max_pd(vv, _mm256_sub_pd(zero, vv));
    const __m256d drag = _mm256_div_pd(
        _mm256_mul_pd(_mm256_set1_pd(-0.5), _mm256_mul_pd(rho, _mm256_mul_pd(vv, _mm256_mul_pd(vabs, cda)))), mass);
    const __m256d a = _mm256_add_pd(_mm256_add_pd(g, drag), thrust_a);
    return std::pair<__m256d, __m256d>(vv, a);
  };

  __m256d rv = _mm256_loadu_pd(r);
  __m256d vv = _mm256_loadu_pd(v);

  const auto [k1r, k1v] = deriv_avx(rv, vv);
  const auto [k2r, k2v] = deriv_avx(
      _mm256_add_pd(rv, _mm256_mul_pd(_mm256_mul_pd(half, dtv), k1r)),
      _mm256_add_pd(vv, _mm256_mul_pd(_mm256_mul_pd(half, dtv), k1v)));
  const auto [k3r, k3v] = deriv_avx(
      _mm256_add_pd(rv, _mm256_mul_pd(_mm256_mul_pd(half, dtv), k2r)),
      _mm256_add_pd(vv, _mm256_mul_pd(_mm256_mul_pd(half, dtv), k2v)));
  const auto [k4r, k4v] = deriv_avx(_mm256_add_pd(rv, _mm256_mul_pd(dtv, k3r)), _mm256_add_pd(vv, _mm256_mul_pd(dtv, k3v)));

  const __m256d dr = _mm256_mul_pd(
      dtv, _mm256_mul_pd(sixth, _mm256_add_pd(_mm256_add_pd(k1r, _mm256_mul_pd(two, k2r)), _mm256_add_pd(_mm256_mul_pd(two, k3r), k4r))));
  const __m256d dv = _mm256_mul_pd(
      dtv, _mm256_mul_pd(sixth, _mm256_add_pd(_mm256_add_pd(k1v, _mm256_mul_pd(two, k2v)), _mm256_add_pd(_mm256_mul_pd(two, k3v), k4v))));

  rv = _mm256_add_pd(rv, dr);
  vv = _mm256_add_pd(vv, dv);
  _mm256_storeu_pd(r, rv);
  _mm256_storeu_pd(v, vv);
}
#endif

double mean(const std::vector<double>& x) {
  double s = 0.0;
  for (double v : x) s += v;
  return x.empty() ? 0.0 : s / static_cast<double>(x.size());
}

}  // namespace

int main(int argc, char** argv) {
  int trajectories = 16384;
  int steps = 500;
  double dt = 0.05;

  for (int i = 1; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--trajectories" && i + 1 < argc) trajectories = std::stoi(argv[++i]);
    else if (a == "--steps" && i + 1 < argc) steps = std::stoi(argv[++i]);
    else if (a == "--dt" && i + 1 < argc) dt = std::stod(argv[++i]);
  }

  std::mt19937 rng(42);
  std::normal_distribution<double> dv0(0.0, 2.0);

  std::vector<double> r0(static_cast<std::size_t>(trajectories), kRe + 1.0);
  std::vector<double> v0(static_cast<std::size_t>(trajectories), 0.0);
  for (int i = 0; i < trajectories; ++i) {
    v0[static_cast<std::size_t>(i)] = dv0(rng);
  }

  auto rs = r0;
  auto vs = v0;
  const auto t0 = std::chrono::high_resolution_clock::now();
  for (int s = 0; s < steps; ++s) {
    for (int i = 0; i < trajectories; ++i) {
      rk4_scalar_step(rs[static_cast<std::size_t>(i)], vs[static_cast<std::size_t>(i)], dt);
    }
  }
  const auto t1 = std::chrono::high_resolution_clock::now();
  const double scalar_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

  auto rb = r0;
  auto vb = v0;
  const auto t2 = std::chrono::high_resolution_clock::now();
  for (int s = 0; s < steps; ++s) {
    int i = 0;
#if defined(__AVX2__)
    for (; i + 3 < trajectories; i += 4) {
      rk4_avx2_step(&rb[static_cast<std::size_t>(i)], &vb[static_cast<std::size_t>(i)], dt);
    }
#endif
    for (; i < trajectories; ++i) {
      rk4_scalar_step(rb[static_cast<std::size_t>(i)], vb[static_cast<std::size_t>(i)], dt);
    }
  }
  const auto t3 = std::chrono::high_resolution_clock::now();
  const double batch_ms = std::chrono::duration<double, std::milli>(t3 - t2).count();

  double l1 = 0.0;
  for (int i = 0; i < trajectories; ++i) {
    l1 += std::abs(rs[static_cast<std::size_t>(i)] - rb[static_cast<std::size_t>(i)]);
  }
  l1 /= static_cast<double>(trajectories);

  std::cout << std::fixed << std::setprecision(6);
  std::cout << "trajectories=" << trajectories << "\n";
  std::cout << "steps=" << steps << "\n";
  std::cout << "scalar_ms=" << scalar_ms << "\n";
  std::cout << "batch_ms=" << batch_ms << "\n";
  std::cout << "speedup=" << (scalar_ms / std::max(batch_ms, 1e-9)) << "x\n";
#if defined(__AVX2__)
  std::cout << "simd_mode=avx2\n";
#else
  std::cout << "simd_mode=scalar_fallback\n";
#endif
  std::cout << "mean_final_altitude_m_scalar=" << (mean(rs) - kRe) << "\n";
  std::cout << "mean_final_altitude_m_batch=" << (mean(rb) - kRe) << "\n";
  std::cout << "mean_abs_altitude_diff_m=" << l1 << "\n";
  return 0;
}
