"""Command-line entry point for reproducible synthetic-data demonstrations."""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

from .model import Battery, baseline, optimize_day, validate_dispatch


class CLIError(ValueError):
    """An actionable input, solver, or output error suitable for CLI display."""


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Battery config has duplicate parameter '{key}'")
        result[key] = value
    return result


def _load_csv(path: Path):
    required = ["start_minute", "end_minute", "load_kwh", "pv_kwh", "price_per_kwh"]
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or any(k not in reader.fieldnames for k in required):
                raise ValueError(f"CSV must contain columns: {', '.join(required)}")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError("CSV column names must be unique")
            records = list(reader)
    except UnicodeDecodeError as exc:
        raise CLIError(
            f"CSV '{path}' is not valid UTF-8. Save it as UTF-8 and check the file contents."
        ) from exc
    except csv.Error as exc:
        raise CLIError(
            f"Could not parse CSV '{path}': {exc}. Check its header and row structure."
        ) from exc
    except OSError as exc:
        raise CLIError(
            f"Could not read CSV '{path}': {exc}. Check that the path names a readable CSV file."
        ) from exc
    if not records:
        raise ValueError("CSV is empty")

    starts, ends = [], []
    numeric_columns = {key: [] for key in ("load_kwh", "pv_kwh", "price_per_kwh")}
    for row_number, record in enumerate(records, start=2):
        if None in record:
            raise ValueError(f"CSV row {row_number} has more fields than the header")
        for key in required:
            value = record.get(key)
            if value is None or not value.strip():
                raise ValueError(f"CSV row {row_number}: column '{key}' is missing a value")

        try:
            start_minute = int(record["start_minute"])
            end_minute = int(record["end_minute"])
        except ValueError as exc:
            raise ValueError(
                f"CSV row {row_number}: start_minute and end_minute must be integers"
            ) from exc
        starts.append(start_minute)
        ends.append(end_minute)

        for key, values in numeric_columns.items():
            try:
                value = float(record[key])
            except ValueError as exc:
                raise ValueError(
                    f"CSV row {row_number}: column '{key}' must be a number"
                ) from exc
            if not math.isfinite(value):
                raise ValueError(
                    f"CSV row {row_number}: column '{key}' must be finite"
                )
            if value < 0:
                raise ValueError(
                    f"CSV row {row_number}: column '{key}' must be non-negative"
                )
            values.append(value)

    for k, (start, end) in enumerate(zip(starts, ends)):
        expected_start = 0 if k == 0 else ends[k - 1]
        if start != expected_start:
            raise ValueError(
                f"CSV must contain contiguous ten-minute slots starting at midnight: "
                f"row {k+2} expected {expected_start} start_minute, actual {start}"
            )
        expected_end = start + 10
        if end != expected_end:
            raise ValueError(
                f"CSV must contain contiguous ten-minute slots: row {k+2} "
                f"expected {expected_end} end_minute, actual {end}"
            )
    if len(records) != 144:
        raise ValueError("v0.1 CLI expects exactly 144 ten-minute slots (one day)")
    return records, [numeric_columns[key] for key in ("load_kwh", "pv_kwh", "price_per_kwh")]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Educational, single-day microgrid battery MILP")
    parser.add_argument("--input", type=Path, required=True, help="CSV with synthetic or licensed ten-minute data")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--battery-config", type=Path, help="Optional JSON file of Battery parameters")
    args = parser.parse_args(argv)
    try:
        rows, (load, pv, price) = _load_csv(args.input)
    except CLIError:
        raise
    except ValueError as exc:
        raise CLIError(f"Invalid CSV '{args.input}': {exc}") from exc
    if args.battery_config:
        try:
            config_text = args.battery_config.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise CLIError(
                f"Battery JSON '{args.battery_config}' is not valid UTF-8. Save it as UTF-8."
            ) from exc
        except OSError as exc:
            raise CLIError(
                f"Could not read battery JSON '{args.battery_config}': {exc}. "
                "Check that the path names a readable file."
            ) from exc
        try:
            config = json.loads(config_text, object_pairs_hook=_unique_json_object)
        except json.JSONDecodeError as exc:
            raise CLIError(
                f"Battery JSON '{args.battery_config}' must be valid JSON; error at line {exc.lineno}, "
                f"column {exc.colno}: {exc.msg}. Check the JSON syntax."
            ) from exc
        except ValueError as exc:
            raise CLIError(f"Invalid battery JSON '{args.battery_config}': {exc}") from exc
        if not isinstance(config, dict):
            raise CLIError(
                f"Battery JSON '{args.battery_config}' must be a JSON object of parameter names and values."
            )
        allowed = {
            "capacity_kwh", "min_soc_kwh", "max_soc_kwh", "initial_soc_kwh",
            "terminal_soc_kwh", "max_power_kw", "charge_efficiency",
            "discharge_efficiency", "interval_minutes",
        }
        unknown = sorted(set(config) - allowed)
        if unknown:
            raise CLIError(
                f"Invalid battery JSON '{args.battery_config}': "
                f"Unknown battery config parameter(s): {', '.join(unknown)}"
            )
        for key, value in config.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise CLIError(
                    f"Invalid battery JSON '{args.battery_config}': "
                    f"parameter '{key}' must be numeric"
                )
        battery = Battery(**config)
        try:
            battery.validate()
        except ValueError as exc:
            raise CLIError(f"Invalid battery JSON '{args.battery_config}': {exc}") from exc
    else:
        battery = Battery()
        battery.validate()
    if battery.interval_minutes != 10:
        source = f" in '{args.battery_config}'" if args.battery_config else ""
        raise CLIError(
            f"v0.1 CLI expects ten-minute slots; battery.interval_minutes must be 10{source}."
        )
    if abs(battery.initial_soc_kwh - battery.terminal_soc_kwh) > 1e-8:
        raise CLIError(
            "The CLI's battery-disabled baseline requires equal initial_soc_kwh "
            f"({battery.initial_soc_kwh}) and terminal_soc_kwh ({battery.terminal_soc_kwh})."
        )
    try:
        opt = optimize_day(load, pv, price, battery)
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith(("MILP solve failed:", "Numerically invalid dispatch:")):
            raise CLIError(message) from exc
        raise
    base = baseline(load, pv, price, battery)
    summary = {"scope": "single simulated day; synthetic example unless otherwise stated",
               "unit": "kWh per ten-minute interval; cost in input price currency",
               "algorithm": "mixed-integer linear programming, SciPy milp / HiGHS",
               "optimized_cost": opt.total_cost,
               "battery_disabled_baseline_cost": base.total_cost,
               "simulated_cost_difference": base.total_cost - opt.total_cost,
               "simulated_cost_reduction_percent": 100*((base.total_cost-opt.total_cost)/base.total_cost) if base.total_cost else None,
               "optimized_purchases_kwh": float(opt.purchase_kwh.sum()),
               "baseline_purchases_kwh": float(base.purchase_kwh.sum()),
               "solver_mip_gap": opt.mip_gap,
               "solver_message": opt.message,
               "constraints": validate_dispatch(opt, load, pv, battery),
               "disclaimer": "Not grid-control software; no real-world savings are asserted"}
    summary_json = json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False)
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CLIError(
            f"Cannot create output directory '{args.output_dir}': {exc}. "
            "Choose a writable directory path."
        ) from exc
    dispatch_path = args.output_dir / "dispatch.csv"
    try:
        with dispatch_path.open("w", encoding="utf-8", newline="") as f:
            fieldnames = ["start_minute", "end_minute", "load_kwh", "pv_kwh", "price_per_kwh",
                          "purchase_kwh", "charge_kwh", "discharge_kwh", "curtailed_pv_kwh",
                          "soc_start_kwh", "soc_end_kwh", "baseline_purchase_kwh"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for k,r in enumerate(rows):
                writer.writerow({"start_minute":r["start_minute"], "end_minute":r["end_minute"],
                                 "load_kwh":load[k], "pv_kwh":pv[k], "price_per_kwh":price[k],
                                 "purchase_kwh":opt.purchase_kwh[k], "charge_kwh":opt.charge_kwh[k],
                                 "discharge_kwh":opt.discharge_kwh[k],
                                 "curtailed_pv_kwh":opt.curtailed_pv_kwh[k],
                                 "soc_start_kwh":opt.soc_kwh[k], "soc_end_kwh":opt.soc_kwh[k+1],
                                 "baseline_purchase_kwh":base.purchase_kwh[k]})
    except (OSError, csv.Error) as exc:
        raise CLIError(
            f"Could not write output file '{dispatch_path}': {exc}. "
            "Choose a writable output directory and check for conflicting files."
        ) from exc
    summary_path = args.output_dir / "summary.json"
    try:
        with summary_path.open("w",encoding="utf-8") as f:
            f.write(summary_json)
    except OSError as exc:
        raise CLIError(
            f"Could not write output file '{summary_path}': {exc}. "
            "Choose a writable output directory and check for conflicting files."
        ) from exc
    print(summary_json)


def cli(argv=None):
    """Command-line wrapper: concise known errors, tracebacks for unknown bugs."""
    try:
        main(argv)
    except CLIError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None

if __name__ == "__main__":
    cli()
