import numpy as np
import pytest
from microgrid_dispatch import Battery, baseline, optimize_day, validate_dispatch


def test_optimizer_respects_physics():
    load = np.array([100., 120., 115., 100.])
    pv = np.array([0., 0., 50., 0.])
    price = np.array([.30, .40, 1.50, 1.60])
    cfg = Battery()
    sol = optimize_day(load, pv, price, cfg)
    checks = validate_dispatch(sol, load, pv, cfg)
    assert checks["max_balance_residual_kwh"] < 1e-6
    assert checks["max_soc_residual_kwh"] < 1e-6
    assert checks["max_constraint_violation"] < 1e-6
    assert checks["simultaneous_charge_discharge_slots"] == 0
    assert np.isclose(sol.soc_kwh[0], 6000)
    assert np.isclose(sol.soc_kwh[-1], 6000)
    assert sol.total_cost <= baseline(load,pv,price,cfg).total_cost + 1e-6


def test_known_two_interval_arbitrage():
    # At eta=1, shift <=100 kWh from cheap to expensive: 100*1+100*3 -> 200*1.
    cfg = Battery(charge_efficiency=1.0, discharge_efficiency=1.0)
    sol = optimize_day([100,100],[0,0],[1,3],cfg)
    assert np.isclose(sol.total_cost, 200, atol=1e-6)
    assert np.isclose(baseline([100,100],[0,0],[1,3],cfg).total_cost,400)


def test_pv_curtailment_and_zero_load():
    cfg = Battery()
    sol = optimize_day([0,0],[500,0],[.1,.1],cfg)
    assert validate_dispatch(sol,[0,0],[500,0],cfg)["max_constraint_violation"] < 1e-6


@pytest.mark.parametrize('l,v,p', [([-1],[0],[1]),([1],[float('nan')],[1]),([1,2],[1],[1,2])])
def test_bad_input_is_rejected(l,v,p):
    with pytest.raises(ValueError):
        optimize_day(l,v,p)


def test_bad_battery_parameters():
    with pytest.raises(ValueError):
        optimize_day([1],[0],[1], Battery(charge_efficiency=0))


@pytest.mark.parametrize("power", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_battery_power_is_rejected(power):
    with pytest.raises(ValueError, match="finite"):
        optimize_day([1], [0], [1], Battery(max_power_kw=power))


@pytest.mark.parametrize("time_limit", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_time_limit_is_rejected(time_limit):
    with pytest.raises(ValueError, match="finite"):
        optimize_day([1], [0], [1], time_limit_s=time_limit)


def test_baseline_does_not_schedule_battery():
    sol=baseline([50,70],[100,10],[1,2])
    assert np.allclose(sol.purchase_kwh,[0,60])
    assert np.allclose(sol.curtailed_pv_kwh,[50,0])
    assert np.allclose(sol.soc_kwh,6000)


def test_cli_creates_outputs(tmp_path):
    from microgrid_dispatch.__main__ import main
    from pathlib import Path
    import json
    demo = Path(__file__).resolve().parents[1] / "examples" / "synthetic_day.csv"
    cfg = Path(__file__).resolve().parents[1] / "examples" / "battery_config.json"
    main(["--input", str(demo), "--battery-config", str(cfg), "--output-dir", str(tmp_path)])
    assert (tmp_path / "dispatch.csv").exists()
    summary=json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["constraints"]["simultaneous_charge_discharge_slots"] == 0
    assert summary["optimized_cost"] <= summary["battery_disabled_baseline_cost"]


def _write_valid_cli_csv(path):
    header = "start_minute,end_minute,load_kwh,pv_kwh,price_per_kwh"
    rows = [header]
    rows.extend(f"{10*k},{10*(k+1)},1,0,1" for k in range(144))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return rows


def test_cli_requires_contiguous_ten_minute_slots(tmp_path):
    from microgrid_dispatch.__main__ import main
    p = tmp_path / "invalid.csv"
    rows = _write_valid_cli_csv(p)
    rows[2] = "25,30,1,0,1"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="contiguous ten-minute slots"):
        main(["--input", str(p), "--output-dir", str(tmp_path / "output")])


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("load_kwh", "NaN", "must be finite"),
        ("pv_kwh", "Infinity", "must be finite"),
        ("price_per_kwh", "-1", "must be non-negative"),
        ("load_kwh", "not-a-number", "must be a number"),
    ],
)
def test_cli_rejects_invalid_csv_numeric_values(tmp_path, column, value, message):
    from microgrid_dispatch.__main__ import main
    p = tmp_path / "invalid.csv"
    rows = _write_valid_cli_csv(p)
    keys = rows[0].split(",")
    values = rows[1].split(",")
    values[keys.index(column)] = value
    rows[1] = ",".join(values)
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        main(["--input", str(p), "--output-dir", str(tmp_path / "output")])


def test_cli_rejects_missing_csv_cell_with_row_context(tmp_path):
    from microgrid_dispatch.__main__ import main
    p = tmp_path / "invalid.csv"
    rows = _write_valid_cli_csv(p)
    rows[1] = "0,10,,0,1"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"row 2.*load_kwh.*missing"):
        main(["--input", str(p), "--output-dir", str(tmp_path / "output")])


def test_cli_rejects_duplicate_csv_headers(tmp_path):
    from microgrid_dispatch.__main__ import main
    p = tmp_path / "invalid.csv"
    rows = _write_valid_cli_csv(p)
    rows[0] = "start_minute,end_minute,load_kwh,pv_kwh,pv_kwh"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="column names must be unique"):
        main(["--input", str(p), "--output-dir", str(tmp_path / "output")])


@pytest.mark.parametrize(
    ("config_text", "message"),
    [
        ("[]", "must be a JSON object"),
        ('{"unknown_parameter": 1}', "Unknown battery config parameter"),
        ('{"max_power_kw": "high"}', "must be numeric"),
        ("{not-json}", "must be valid JSON"),
    ],
)
def test_cli_rejects_invalid_battery_config(tmp_path, config_text, message):
    from microgrid_dispatch.__main__ import main
    csv_path = tmp_path / "valid.csv"
    config_path = tmp_path / "battery.json"
    _write_valid_cli_csv(csv_path)
    config_path.write_text(config_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        main([
            "--input", str(csv_path),
            "--battery-config", str(config_path),
            "--output-dir", str(tmp_path / "output"),
        ])
