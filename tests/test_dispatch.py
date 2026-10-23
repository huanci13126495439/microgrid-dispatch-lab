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


def test_cli_requires_contiguous_ten_minute_slots(tmp_path):
    from microgrid_dispatch.__main__ import main
    p=tmp_path / "invalid.csv"
    p.write_text("start_minute,end_minute,load_kwh,pv_kwh,price_per_kwh\n5,15,1,0,1\n")
    with pytest.raises(ValueError):
        main(["--input", str(p), "--output-dir", str(tmp_path / "output")])
