"""Command-line entry point for reproducible synthetic-data demonstrations."""
import argparse
import csv
import json
from pathlib import Path

from .model import Battery, baseline, optimize_day, validate_dispatch


def _load_csv(path: Path):
    required = ["start_minute", "end_minute", "load_kwh", "pv_kwh", "price_per_kwh"]
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or any(k not in reader.fieldnames for k in required):
            raise ValueError(f"CSV must contain columns: {', '.join(required)}")
        records = list(reader)
    if not records:
        raise ValueError("CSV is empty")
    starts = [int(r["start_minute"]) for r in records]
    ends = [int(r["end_minute"]) for r in records]
    if starts[0] != 0 or any(ends[k]-starts[k] != 10 for k in range(len(starts))) or any(starts[k] != ends[k-1] for k in range(1,len(starts))):
        raise ValueError("CSV must contain contiguous ten-minute slots starting at midnight")
    if len(records) != 144:
        raise ValueError("v0.1 CLI expects exactly 144 ten-minute slots (one day)")
    return records, [[float(r[key]) for r in records] for key in ["load_kwh", "pv_kwh", "price_per_kwh"]]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Educational, single-day microgrid battery MILP")
    parser.add_argument("--input", type=Path, required=True, help="CSV with synthetic or licensed ten-minute data")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--battery-config", type=Path, help="Optional JSON file of Battery parameters")
    args = parser.parse_args(argv)
    rows, (load, pv, price) = _load_csv(args.input)
    battery = Battery(**json.loads(args.battery_config.read_text(encoding="utf-8"))) if args.battery_config else Battery()
    if battery.interval_minutes != 10:
        raise ValueError("v0.1 CLI expects ten-minute slots; battery.interval_minutes must be 10")
    opt = optimize_day(load, pv, price, battery)
    base = baseline(load, pv, price, battery)
    summary = {"scope": "single simulated day; synthetic example unless otherwise stated",
               "unit": "kWh per ten-minute interval; cost in input price currency",
               "algorithm": "mixed-integer linear programming, SciPy milp / HiGHS",
               "optimized_cost": opt.total_cost,
               "battery_disabled_baseline_cost": base.total_cost,
               "simulated_cost_difference": base.total_cost - opt.total_cost,
               "simulated_cost_reduction_percent": 100*(base.total_cost-opt.total_cost)/base.total_cost if base.total_cost else None,
               "optimized_purchases_kwh": float(opt.purchase_kwh.sum()),
               "baseline_purchases_kwh": float(base.purchase_kwh.sum()),
               "solver_mip_gap": opt.mip_gap,
               "solver_message": opt.message,
               "constraints": validate_dispatch(opt, load, pv, battery),
               "disclaimer": "Not grid-control software; no real-world savings are asserted"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "dispatch.csv").open("w", encoding="utf-8", newline="") as f:
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
    with (args.output_dir / "summary.json").open("w",encoding="utf-8") as f:
        json.dump(summary,f,indent=2,ensure_ascii=False,allow_nan=False)
    print(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False))

if __name__ == "__main__":
    main()
