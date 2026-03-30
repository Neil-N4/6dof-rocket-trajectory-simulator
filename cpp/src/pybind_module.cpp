#include "rocket_sim_cpp.hpp"

#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(rocket_sim_event_bindings, m) {
  m.doc() = "Python bindings for lock-free event-driven rocket simulation";

  py::class_<rocketsim::EventEngineStats>(m, "EventEngineStats")
      .def_readonly("pushed", &rocketsim::EventEngineStats::pushed)
      .def_readonly("popped", &rocketsim::EventEngineStats::popped)
      .def_readonly("dropped", &rocketsim::EventEngineStats::dropped);

  m.def("run_event_engine_summary", [](double dt_s, double duration_s) {
    rocketsim::Config cfg = rocketsim::default_config();
    cfg.dt_s = dt_s;
    cfg.duration_s = duration_s;
    const auto r = rocketsim::run_simulation_event_driven(cfg);
    py::dict d;
    d["apogee_m"] = r.sim.apogee_m;
    d["max_q_pa"] = r.sim.max_q_ascent_80km_pa;
    d["events_pushed"] = r.stats.pushed;
    d["events_popped"] = r.stats.popped;
    d["events_dropped"] = r.stats.dropped;
    return d;
  });
}

