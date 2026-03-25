.PHONY: install run run-high-wind test validate montecarlo cpp-build cpp-run

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	. .venv/bin/activate && MPLCONFIGDIR=$$PWD/.mplconfig PYTHONPATH=. python main.py --config configs/nominal.yaml --seed 42

run-high-wind:
	. .venv/bin/activate && MPLCONFIGDIR=$$PWD/.mplconfig PYTHONPATH=. python main.py --config configs/high_wind.yaml --seed 42

test:
	. .venv/bin/activate && PYTHONPATH=. pytest -q tests/test_sim.py

validate:
	. .venv/bin/activate && PYTHONPATH=. python scripts/validate.py --config configs/nominal.yaml

montecarlo:
	. .venv/bin/activate && MPLCONFIGDIR=$$PWD/.mplconfig PYTHONPATH=. python scripts/monte_carlo.py --config configs/nominal.yaml --runs 500 --seed 123

cpp-build:
	clang++ -std=c++17 -Icpp/include cpp/src/rocket_sim_cpp.cpp cpp/src/sim_main.cpp -o cpp_sim

cpp-run: cpp-build
	./cpp_sim --dt 0.1 --duration 400 --out outputs/cpp_flight_states.csv
