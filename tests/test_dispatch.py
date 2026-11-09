from types import SimpleNamespace

import numpy as np
import pytest
import microgrid_dispatch.model as model_module
from microgrid_dispatch import Battery, Dispatch, baseline, optimize_day, validate_dispatch


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


def test_overflowing_step_capacity_is_rejected_before_solving():
    with pytest.raises(ValueError, match="step capacity.*finite"):
        optimize_day([1], [0], [1], Battery(max_power_kw=1e308))


def test_cli_large_cost_reduction_produces_valid_json(tmp_path, monkeypatch):
    import json
    from microgrid_dispatch import __main__ as cli

    csv_path = tmp_path / "large_price.csv"
    rows = _write_valid_cli_csv(csv_path)
    rows[1] = "0,10,1,0,1e307"
    rows[2:] = [row.rsplit(",", 1)[0] + ",0" for row in rows[2:]]
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    def fake_optimized(load, pv, price, battery):
        n = len(load)
        purchase = np.ones(n)
        purchase[0] = 0
        purchase[1] += 1 / 0.81
        charge = np.zeros(n)
        charge[1] = 1 / 0.81
        discharge = np.zeros(n)
        discharge[0] = 1
        soc = np.full(n + 1, battery.initial_soc_kwh)
        soc[1] -= 1 / 0.9
        return Dispatch(purchase, charge, discharge, np.zeros(n), soc,
                        np.asarray(price), 0.0, 0.0, "test solution")

    monkeypatch.setattr(cli, "optimize_day", fake_optimized)
    cli.main(["--input", str(csv_path), "--output-dir", str(tmp_path / "output")])
    summary = json.loads((tmp_path / "output" / "summary.json").read_text(encoding="utf-8"))
    assert summary["simulated_cost_reduction_percent"] == pytest.approx(100.0)


@pytest.mark.parametrize("power", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_battery_power_is_rejected(power):
    with pytest.raises(ValueError, match="finite"):
        optimize_day([1], [0], [1], Battery(max_power_kw=power))


@pytest.mark.parametrize("time_limit", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_time_limit_is_rejected(time_limit):
    with pytest.raises(ValueError, match="finite"):
        optimize_day([1], [0], [1], time_limit_s=time_limit)


@pytest.mark.parametrize(
    ("status", "expected_reason"),
    [
        (1, "iteration or time limit"),
        (2, "infeasible"),
        (3, "unbounded"),
        (4, "termination error"),
        (99, "unrecognized status"),
    ],
)
def test_solver_failure_reports_status_reason(monkeypatch, status, expected_reason):
    monkeypatch.setattr(
        model_module,
        "milp",
        lambda *args, **kwargs: SimpleNamespace(
            status=status, x=None, message="simulated solver message"
        ),
    )
    with pytest.raises(RuntimeError, match=expected_reason) as exc_info:
        optimize_day([1], [0], [1])
    assert f"status {status}" in str(exc_info.value)
    assert "simulated solver message" in str(exc_info.value)


def test_solver_success_without_solution_vector_is_reported(monkeypatch):
    monkeypatch.setattr(
        model_module,
        "milp",
        lambda *args, **kwargs: SimpleNamespace(
            status=0, x=None, message="empty solution"
        ),
    )
    with pytest.raises(RuntimeError, match="reported success but returned no solution vector"):
        optimize_day([1], [0], [1])


def test_baseline_rejects_overflowing_total_cost():
    with pytest.raises(ValueError, match="input magnitudes exceed the supported numeric range"):
        baseline([2.0], [0.0], [1e308])


def test_optimizer_rejects_overflowing_total_cost(monkeypatch):
    # A solver-reported feasible vector can still produce an unrepresentable cost.
    x = np.zeros(7)
    x[0] = 2.0  # purchase for the single interval
    x[4] = 6000.0
    x[5] = 6000.0
    monkeypatch.setattr(
        model_module,
        "milp",
        lambda *args, **kwargs: SimpleNamespace(
            status=0, x=x, message="simulated successful solve", mip_gap=0.0
        ),
    )
    with pytest.raises(ValueError, match="input magnitudes exceed the supported numeric range"):
        optimize_day([2.0], [0.0], [1e308])


@pytest.mark.parametrize("bad_cost", [float("nan"), float("inf"), float("-inf")])
def test_validate_dispatch_rejects_non_finite_reported_cost(bad_cost):
    sol = Dispatch(
        purchase_kwh=np.array([2.0]),
        charge_kwh=np.array([0.0]),
        discharge_kwh=np.array([0.0]),
        curtailed_pv_kwh=np.array([0.0]),
        soc_kwh=np.array([6000.0, 6000.0]),
        price_per_kwh=np.array([1.0]),
        total_cost=bad_cost,
        mip_gap=0.0,
        message="test dispatch",
    )
    with pytest.raises(ValueError, match="total_cost must be finite"):
        validate_dispatch(sol, [2.0], [0.0])


def test_validate_dispatch_rejects_overflowing_recomputed_cost():
    sol = Dispatch(
        purchase_kwh=np.array([2.0]),
        charge_kwh=np.array([0.0]),
        discharge_kwh=np.array([0.0]),
        curtailed_pv_kwh=np.array([0.0]),
        soc_kwh=np.array([6000.0, 6000.0]),
        price_per_kwh=np.array([1e308]),
        total_cost=1e308,
        mip_gap=0.0,
        message="test dispatch",
    )
    with pytest.raises(ValueError, match="input magnitudes exceed the supported numeric range"):
        validate_dispatch(sol, [2.0], [0.0])


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
    rows[0] = "start_minute,end_minute,load_kwh,pv_kwh,price_per_kwh,load_kwh"
    rows[1] = rows[1] + ",1"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="column names must be unique"):
        main(["--input", str(p), "--output-dir", str(tmp_path / "output")])


@pytest.mark.parametrize(
    ("config_text", "message"),
    [
        ("[]", "must be a JSON object"),
        ('{"unknown_parameter": 1}', "Unknown battery config parameter"),
        ('{"max_power_kw": "high"}', "must be numeric"),
        ('{"max_power_kw": NaN}', "must be finite"),
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


@pytest.mark.parametrize("second", [1, 2])
def test_cli_rejects_duplicate_battery_keys(tmp_path, second):
    from microgrid_dispatch.__main__ import main
    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    config = tmp_path / "battery.json"
    config.write_text('{"max_power_kw": 1, "max_power_kw": ' + str(second) + '}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate.*max_power_kw"):
        main(["--input", str(csv_path), "--battery-config", str(config)])


@pytest.mark.parametrize("value", [10**309, True, float("inf"), float("nan"), "3"])
def test_battery_invalid_number_names_parameter(value):
    with pytest.raises(ValueError, match="max_power_kw"):
        Battery(max_power_kw=value).validate()


@pytest.mark.parametrize("value", [3, 3.0, np.int64(3), np.float64(3)])
def test_battery_accepts_python_and_numpy_numbers(value):
    Battery(max_power_kw=value).validate()


def test_cli_rejects_huge_integer_with_parameter_name(tmp_path):
    from microgrid_dispatch.__main__ import main
    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    config = tmp_path / "battery.json"
    config.write_text('{"max_power_kw": ' + '9'*309 + '}', encoding="utf-8")
    with pytest.raises(ValueError, match="max_power_kw"):
        main(["--input", str(csv_path), "--battery-config", str(config)])


@pytest.mark.parametrize(("index", "row", "expected"), [
    (1, "1,11,1,0,1", r"row 2.*expected 0.*actual 1"),
    (3, "20,31,1,0,1", r"row 4.*expected 30.*actual 31"),
    (3, "21,31,1,0,1", r"row 4.*expected 20.*actual 21"),
    (3, "19,29,1,0,1", r"row 4.*expected 20.*actual 19"),
    (3, "0,10,1,0,1", r"row 4.*expected 20.*actual 0"),
])
def test_cli_reports_time_row_and_expected_actual(tmp_path, index, row, expected):
    from microgrid_dispatch.__main__ import _load_csv
    csv_path = tmp_path / "input.csv"
    rows = _write_valid_cli_csv(csv_path)
    rows[index] = row
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=expected):
        _load_csv(csv_path)


def test_data_guides_cover_all_fields_and_battery_parameters():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    fields = ("start_minute", "end_minute", "load_kwh", "pv_kwh", "price_per_kwh")
    battery_fields = ("capacity_kwh", "min_soc_kwh", "max_soc_kwh",
                      "initial_soc_kwh", "terminal_soc_kwh", "max_power_kw",
                      "charge_efficiency", "discharge_efficiency", "interval_minutes")
    for name in ("data_preparation.md", "data_preparation_zh.md"):
        guide = (root / "docs" / name).read_text(encoding="utf-8")
        assert all(f"`{key}`" in guide for key in fields + battery_fields)
        assert "144" in guide and "1440" in guide


def test_documentation_links_to_existing_guides():
    from pathlib import Path
    import re
    root = Path(__file__).resolve().parents[1]
    files = ("README.md", "START_HERE_中文.md", "docs/data_preparation.md",
             "docs/data_preparation_zh.md", "docs/wheel_installation.md")
    for name in files:
        path = root / name
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not target.startswith(("https://", "http://", "#")):
                assert (path.parent / target.split("#", 1)[0]).is_file(), (name, target)


def test_cli_rejects_soc_mismatch_before_optimization(tmp_path, monkeypatch):
    from microgrid_dispatch import __main__ as cli

    csv_path = tmp_path / "input.csv"
    config_path = tmp_path / "battery.json"
    _write_valid_cli_csv(csv_path)
    config_path.write_text(
        '{"initial_soc_kwh": 6000, "terminal_soc_kwh": 5000}', encoding="utf-8"
    )
    called = False

    def unexpected_optimize(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("optimizer must not run for a baseline SOC conflict")

    monkeypatch.setattr(cli, "optimize_day", unexpected_optimize)
    with pytest.raises(ValueError, match=r"initial_soc_kwh.*6000.*terminal_soc_kwh.*5000"):
        cli.main(["--input", str(csv_path), "--battery-config", str(config_path)])
    assert not called


def test_cli_keeps_battery_soc_boundary_validation_before_optimization(tmp_path, monkeypatch):
    from microgrid_dispatch import __main__ as cli

    csv_path = tmp_path / "input.csv"
    config_path = tmp_path / "battery.json"
    _write_valid_cli_csv(csv_path)
    config_path.write_text(
        '{"initial_soc_kwh": 11000, "terminal_soc_kwh": 11000}', encoding="utf-8"
    )
    monkeypatch.setattr(
        cli, "optimize_day", lambda *args, **kwargs: pytest.fail("optimizer was called")
    )
    with pytest.raises(ValueError, match="Initial SOC is outside storage bounds"):
        cli.main(["--input", str(csv_path), "--battery-config", str(config_path)])


def test_cli_entrypoint_formats_missing_csv_error(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    missing = tmp_path / "missing.csv"
    with pytest.raises(SystemExit) as exc_info:
        cli(["--input", str(missing)])
    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert str(missing) in err and "CSV" in err and "check" in err.lower()
    assert "Traceback" not in err


def test_cli_entrypoint_formats_csv_read_errors_with_path(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "csv-directory"
    csv_path.mkdir()
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path)])
    err = capsys.readouterr().err
    assert str(csv_path) in err and "read" in err.lower()
    assert "Traceback" not in err


def test_cli_entrypoint_formats_csv_encoding_errors(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "invalid.csv"
    csv_path.write_bytes(b"\xff")
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path)])
    err = capsys.readouterr().err
    assert str(csv_path) in err and "UTF-8" in err
    assert "Traceback" not in err


def test_cli_entrypoint_formats_missing_battery_json_with_path(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    missing = tmp_path / "missing.json"
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path), "--battery-config", str(missing)])
    err = capsys.readouterr().err
    assert str(missing) in err and "JSON" in err and "check" in err.lower()
    assert "Traceback" not in err


@pytest.mark.parametrize(
    ("config_text", "expected"),
    [
        ('{"max_power_kw": 1, "max_power_kw": 2}', "duplicate.*max_power_kw"),
        ('{"unknown_parameter": 1}', "Unknown battery config parameter"),
        ('{"max_power_kw": -1}', "Power limit and interval duration must be positive"),
    ],
)
def test_cli_entrypoint_formats_battery_config_errors(tmp_path, capsys, config_text, expected):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    config = tmp_path / "battery.json"
    config.write_text(config_text, encoding="utf-8")
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path), "--battery-config", str(config)])
    err = capsys.readouterr().err
    assert str(config) in err
    assert __import__("re").search(expected, err)
    assert "Traceback" not in err


def test_cli_entrypoint_formats_csv_structure_error_with_path(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "bad-structure.csv"
    csv_path.write_text("time,load\n0,1\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path)])
    err = capsys.readouterr().err
    assert str(csv_path) in err and "columns" in err
    assert "Traceback" not in err


def test_cli_entrypoint_json_syntax_error_includes_path_line_and_column(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    config = tmp_path / "battery.json"
    config.write_text('{\n  "max_power_kw": }\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path), "--battery-config", str(config)])
    err = capsys.readouterr().err
    assert str(config) in err and "line 2" in err and "column" in err
    assert "Traceback" not in err


def test_cli_entrypoint_formats_output_directory_creation_error(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    output_path = tmp_path / "not-a-directory"
    output_path.write_text("file", encoding="utf-8")
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path), "--output-dir", str(output_path)])
    err = capsys.readouterr().err
    assert str(output_path) in err and "output" in err.lower()
    assert "Traceback" not in err


def test_cli_entrypoint_formats_dispatch_write_error_with_file_path(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    dispatch_path = output_dir / "dispatch.csv"
    dispatch_path.mkdir()
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path), "--output-dir", str(output_dir)])
    err = capsys.readouterr().err
    assert str(dispatch_path) in err and "write" in err.lower()
    assert "Traceback" not in err


def test_cli_entrypoint_formats_summary_write_error_with_file_path(tmp_path, capsys):
    from microgrid_dispatch.__main__ import cli

    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    summary_path = output_dir / "summary.json"
    summary_path.mkdir()
    with pytest.raises(SystemExit):
        cli(["--input", str(csv_path), "--output-dir", str(output_dir)])
    err = capsys.readouterr().err
    assert str(summary_path) in err and "write" in err.lower()
    assert "Traceback" not in err


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("MILP solve failed: the model is infeasible under supplied inputs (status 2): infeasible", "status 2"),
        ("MILP solve failed: the solver reached an iteration or time limit (status 1): time limit", "status 1"),
    ],
)
def test_cli_entrypoint_formats_known_solver_failures(tmp_path, monkeypatch, capsys, message, expected):
    from microgrid_dispatch import __main__ as cli

    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)

    def fail(*args, **kwargs):
        raise RuntimeError(message)

    monkeypatch.setattr(cli, "optimize_day", fail)
    with pytest.raises(SystemExit):
        cli.cli(["--input", str(csv_path)])
    err = capsys.readouterr().err
    assert expected in err and "MILP solve failed" in err
    assert "Traceback" not in err


def test_cli_entrypoint_does_not_hide_unexpected_runtime_error(tmp_path, monkeypatch, capsys):
    from microgrid_dispatch import __main__ as cli

    csv_path = tmp_path / "input.csv"
    _write_valid_cli_csv(csv_path)
    unexpected = RuntimeError("unexpected programming failure")

    def fail(*args, **kwargs):
        raise unexpected

    monkeypatch.setattr(cli, "optimize_day", fail)
    with pytest.raises(RuntimeError, match="unexpected programming failure"):
        cli.cli(["--input", str(csv_path)])
    assert capsys.readouterr().err == ""


def test_console_script_points_to_user_facing_error_wrapper():
    from pathlib import Path

    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    assert 'microgrid_dispatch.__main__:cli' in pyproject


def test_result_interpretation_guides_cover_output_fields_and_links():
    from pathlib import Path
    import re

    root = Path(__file__).resolve().parents[1]
    fields = (
        "start_minute", "end_minute", "load_kwh", "pv_kwh", "price_per_kwh",
        "purchase_kwh", "charge_kwh", "discharge_kwh", "curtailed_pv_kwh",
        "soc_start_kwh", "soc_end_kwh", "baseline_purchase_kwh",
        "optimized_cost", "battery_disabled_baseline_cost", "simulated_cost_difference",
        "simulated_cost_reduction_percent", "optimized_purchases_kwh", "baseline_purchases_kwh",
        "solver_mip_gap", "solver_message", "constraints", "disclaimer",
        "max_balance_residual_kwh", "max_soc_residual_kwh", "max_constraint_violation",
        "simultaneous_charge_discharge_slots", "min_soc_kwh", "max_soc_kwh",
    )
    for name in ("docs/result_interpretation.md", "docs/result_interpretation_zh.md"):
        path = root / name
        guide = path.read_text(encoding="utf-8")
        assert all(f"`{field}`" in guide for field in fields)
        for target in re.findall(r"\]\(([^)]+)\)", guide):
            if not target.startswith(("https://", "http://", "#")):
                assert (path.parent / target.split("#", 1)[0]).is_file(), (name, target)


def test_entry_documents_link_result_interpretation():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert "docs/result_interpretation.md" in (root / "README.md").read_text(encoding="utf-8")
    assert "docs/result_interpretation_zh.md" in (root / "START_HERE_中文.md").read_text(encoding="utf-8")


def test_result_interpretation_explains_cost_and_constraint_limits():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    en = (root / "docs/result_interpretation.md").read_text(encoding="utf-8").lower()
    zh = (root / "docs/result_interpretation_zh.md").read_text(encoding="utf-8")
    assert "interval purchase cost" in en and "price_per_kwh" in en
    assert "null" in en
    assert "kwh per interval" in en and "not kw" in en
    assert "\u76f4\u63a5\u4f9b\u8d1f\u8377" in zh and "\u7535\u6c60\u5145\u7535" in zh
    assert "simultaneous_charge_discharge_slots" in en
    assert "\u5355\u4e00\u5355\u4f4d" in zh and "kwh" in zh


def test_cli_keeps_existing_output_schemas(tmp_path):
    from pathlib import Path
    import csv
    import json
    from microgrid_dispatch.__main__ import main

    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "output"
    main(["--input", str(root / "examples" / "synthetic_day.csv"), "--output-dir", str(output)])
    with (output / "dispatch.csv").open(newline="", encoding="utf-8") as file:
        header = next(csv.reader(file))
    assert header == [
        "start_minute", "end_minute", "load_kwh", "pv_kwh", "price_per_kwh",
        "purchase_kwh", "charge_kwh", "discharge_kwh", "curtailed_pv_kwh",
        "soc_start_kwh", "soc_end_kwh", "baseline_purchase_kwh",
    ]
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert set(summary) == {
        "scope", "unit", "algorithm", "optimized_cost", "battery_disabled_baseline_cost",
        "simulated_cost_difference", "simulated_cost_reduction_percent",
        "optimized_purchases_kwh", "baseline_purchases_kwh", "solver_mip_gap",
        "solver_message", "constraints", "disclaimer",
    }
