.PHONY: install run run-high-wind test validate montecarlo cpp-build cpp-run cpp-validate cpp-test parity cpp-montecarlo benchmark failure-suite

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	. .venv/bin/activate && MPLCONFIGDIR=$$PWD/.mplconfig PYTHONPATH=. python main.py --config configs/nominal.yaml --seed 42

run-high-wind:
	. .venv/bin/activate && MPLCONFIGDIR=$$PWD/.mplconfig PYTHONPATH=. python main.py --config configs/high_wind.yaml --seed 42

test:
	. .venv/bin/activate && PYTHONPATH=. pytest -q tests/test_sim.py tests/test_config.py

validate:
	. .venv/bin/activate && PYTHONPATH=. python scripts/validate.py --config configs/nominal.yaml

montecarlo:
	. .venv/bin/activate && MPLCONFIGDIR=$$PWD/.mplconfig PYTHONPATH=. python scripts/monte_carlo.py --config configs/nominal.yaml --runs 500 --seed 123

cpp-build:
	clang++ -std=c++17 -Icpp/include cpp/src/rocket_sim_cpp.cpp cpp/src/config_loader.cpp cpp/src/sim_main.cpp -o cpp_sim

cpp-run: cpp-build
	./cpp_sim --config configs/nominal.yaml --dt 0.1 --duration 2200 --out outputs/cpp_flight_states.csv --summary outputs/cpp_summary.txt

cpp-validate: cpp-build
	clang++ -std=c++17 -Icpp/include cpp/src/rocket_sim_cpp.cpp cpp/src/config_loader.cpp cpp/src/validate_main.cpp -o cpp_validate
	./cpp_validate --config configs/nominal.yaml

cpp-test: cpp-build
	clang++ -std=c++17 -Icpp/include cpp/src/rocket_sim_cpp.cpp cpp/src/config_loader.cpp cpp/src/tests_main.cpp -o cpp_tests
	./cpp_tests

parity: cpp-build
	. .venv/bin/activate && PYTHONPATH=. python scripts/parity_check.py --config configs/nominal.yaml

cpp-montecarlo: cpp-build
	clang++ -std=c++17 -Icpp/include cpp/src/rocket_sim_cpp.cpp cpp/src/config_loader.cpp cpp/src/monte_carlo_main.cpp -o cpp_monte_carlo
	./cpp_monte_carlo --config configs/nominal.yaml --runs 120 --seed 123 --outdir outputs/cpp_monte_carlo

benchmark: cpp-build
	. .venv/bin/activate && PYTHONPATH=. python scripts/benchmark.py --config configs/nominal.yaml --runs 5 --duration 1200 --dt 0.15

failure-suite: cpp-build
	. .venv/bin/activate && PYTHONPATH=. python scripts/failure_modes.py
