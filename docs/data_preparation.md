# Preparing input data

The CLI models one day using 144 contiguous ten-minute intervals, beginning at
midnight. Provide a UTF-8 CSV with a header and exactly 144 data rows. The
repository's [synthetic example](../examples/synthetic_day.csv) illustrates the
format; it is not real grid data.

| Column | Meaning | Unit |
| --- | --- | --- |
| `start_minute` | Interval start since midnight, integer | minute |
| `end_minute` | Interval end since midnight, integer | minute |
| `load_kwh` | Energy consumed during the interval | kWh |
| `pv_kwh` | PV energy generated during the interval | kWh |
| `price_per_kwh` | Purchase price of energy | chosen currency/kWh |

The first interval is 0–10; each next start equals the previous end, ending at
1440. Energy and price values must be numeric, finite and non-negative. Load
and PV are energy per interval, not power. Do not duplicate column names.

## Battery configuration

The optional `--battery-config path/to/battery.json` must contain a JSON
object with unique keys. Missing keys use defaults. Values must be finite
numbers, not booleans; unknown keys are rejected.

| Keys | Meaning and constraints |
| --- | --- |
| `capacity_kwh`, `min_soc_kwh`, `max_soc_kwh` | kWh; 0 ≤ minimum SOC < maximum SOC ≤ capacity |
| `initial_soc_kwh`, `terminal_soc_kwh` | kWh; each within SOC bounds; equal for the CLI's static-battery baseline |
| `max_power_kw` | positive charge/discharge limit in kW |
| `charge_efficiency`, `discharge_efficiency` | dimensionless, each in (0, 1] |
| `interval_minutes` | duration in minutes; the CLI requires 10 |

The derived per-interval power limit must also be finite. See
[battery_config.json](../examples/battery_config.json) for synthetic defaults.

## Common errors

- Missing or duplicate header: use each required column name once.
- Empty, nonnumeric, negative, NaN or infinite value: correct the indicated
  row and column with a finite non-negative number.
- Time error: use the reported row, expected and actual minute to fix gaps,
  overlaps, backwards time or incorrect duration. Supply exactly 144 rows.
- Invalid battery JSON: fix its syntax, duplicate or unknown key, numeric type,
  or reported parameter boundary.

Results are simulations, not measured savings or instructions for controlling
an electrical grid or physical battery.
