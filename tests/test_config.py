from __future__ import annotations

from pathlib import Path

from rocket_sim.config import load_config


def test_load_nominal_config() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "configs" / "nominal.yaml", root)
    assert cfg.payload_mass_kg > 0
    assert len(cfg.stages) >= 1
    assert cfg.wind_i_m_s.shape == (3,)


def test_load_high_wind_config_changes_wind() -> None:
    root = Path(__file__).resolve().parents[1]
    nominal = load_config(root / "configs" / "nominal.yaml", root)
    high_wind = load_config(root / "configs" / "high_wind.yaml", root)
    assert high_wind.wind_i_m_s[1] != nominal.wind_i_m_s[1]
