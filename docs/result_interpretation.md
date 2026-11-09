# Interpreting results

This guide describes the existing `dispatch.csv` and `summary.json` files. The
program models one day as 144 ten-minute intervals. Flow fields such as load,
PV, purchases, charging, discharging and curtailment are **kWh per interval**,
not kW. SOC fields are stored energy at interval boundaries in kWh, not interval
flows. `price_per_kwh` is in the input currency per kWh; reported costs use that
same currency unit.

## `dispatch.csv`

| Field | Meaning and physical interpretation | Unit | How to read it |
| --- | --- | --- | --- |
| `start_minute` | Interval start measured from midnight | minute | First interval is 0. |
| `end_minute` | Interval end measured from midnight | minute | Each interval is ten minutes. |
| `load_kwh` | Energy consumed by load during this interval | kWh/interval | Input demand for the interval. |
| `pv_kwh` | PV energy generated during this interval | kWh/interval | Input PV generation before curtailment. |
| `price_per_kwh` | Grid purchase price | input currency/kWh | The input price used to cost grid purchases. |
| `purchase_kwh` | Energy purchased from the grid in the optimized dispatch | kWh/interval | Grid energy used to balance this interval. |
| `charge_kwh` | Energy sent into battery charging in this interval | kWh/interval | Battery-side SOC gain is reduced by charging losses. |
| `discharge_kwh` | Energy supplied by battery discharge in this interval | kWh/interval | SOC draw is larger than delivered energy because of losses. |
| `curtailed_pv_kwh` | PV energy not used by the model | kWh/interval | Zero means all available PV is used by load and/or charging. |
| `soc_start_kwh` | Battery state of charge at interval start | kWh | Equals the previous row's `soc_end_kwh`. |
| `soc_end_kwh` | Battery state of charge at interval end | kWh | Reflects charging and discharging efficiencies. |
| `baseline_purchase_kwh` | Grid purchase for the same input interval with battery dispatch disabled | kWh/interval | Comparison baseline, not a second optimized schedule. |

To express an interval-average power in kW, divide a flow field's kWh by the
interval duration in hours (10/60). This conversion does not turn the
optimization output into a measured power trace.

## `summary.json`

| Field | Meaning | Interpretation |
| --- | --- | --- |
| `optimized_cost` | Total simulated cost for optimized grid purchases | Sum of interval grid purchase energy times interval price. |
| `battery_disabled_baseline_cost` | Total simulated cost for the battery-disabled baseline | Uses the same input load, PV and prices with no battery dispatch. |
| `simulated_cost_difference` | Baseline cost minus optimized cost | Positive means the modeled optimized purchases cost less under these assumptions; negative means more. |
| `simulated_cost_reduction_percent` | `100 × (baseline cost - optimized cost) / baseline cost` | `null` when baseline cost is zero; otherwise a simulated percentage, not financial savings. |
| `optimized_purchases_kwh` | Sum of optimized grid purchases | Daily simulated grid energy purchased. |
| `baseline_purchases_kwh` | Sum of baseline grid purchases | Daily simulated grid energy purchased with battery disabled. |
| `solver_mip_gap` | Solver-reported mixed-integer optimality gap | A dimensionless solver quantity; `null` can mean the solver did not provide it. |
| `solver_message` | Solver termination message | Diagnostic text from SciPy/HiGHS. |
| `constraints` | Algebraic checks on the returned dispatch | See [constraint diagnostics](#constraint-diagnostics). |
| `disclaimer` | Scope warning written by the program | The result is not grid-control software and asserts no real-world savings. |

The cost difference is calculated as:

```text
simulated cost difference = battery-disabled baseline cost - optimized cost
```

### Cost by interval

There is no separate interval-cost column in the current CSV. Calculate it from
the existing columns:

```text
interval purchase cost = purchase_kwh × price_per_kwh
daily purchase cost = sum of all interval purchase costs
```

For example, if an interval has `purchase_kwh = 12` and
`price_per_kwh = 0.40` currency units/kWh, its simulated purchase cost is
`12 × 0.40 = 4.80` currency units. Sum the 144 interval costs to reproduce the
optimized purchase cost, subject to normal floating-point rounding.

## SOC trajectory and efficiencies

`soc_start_kwh` and `soc_end_kwh` show the stored-energy state at the beginning
and end of each interval. The model's per-interval relationship is:

```text
SOC end = SOC start
          + charge_efficiency × charge_kwh
          - discharge_kwh / discharge_efficiency
```

Thus a charging efficiency below 1 stores less energy than the charging input,
and a discharge efficiency below 1 consumes more stored energy than the energy
delivered. Initial SOC and terminal SOC are model constraints. For the CLI's
battery-disabled baseline, they must be equal.

## PV use

`pv_kwh` is PV generation supplied as input; `curtailed_pv_kwh` is the part the
model leaves unused. Total PV used can be calculated per interval as:

```text
PV used = pv_kwh - curtailed_pv_kwh
```

The current outputs do not identify how much PV went directly to load versus
into battery charging. They also do not identify the source of each unit of
charging energy. Do not infer those splits from these files.

## Constraint diagnostics

The `constraints` object reports:

| Field | Meaning | Unit / reading |
| --- | --- | --- |
| `max_balance_residual_kwh` | Largest absolute per-interval energy-balance residual | kWh; should be near zero within numerical tolerance. |
| `max_soc_residual_kwh` | Largest absolute SOC recursion residual | kWh; should be near zero within numerical tolerance. |
| `max_constraint_violation` | Largest numeric value among several validation checks: negative flow values, PV-curtailment and charge/discharge bounds, SOC bounds and endpoint deviations, total-cost consistency, and the count of simultaneous charge/discharge intervals | A mixed diagnostic aggregate with no single physical unit; it is not a residual measured only in kWh. |
| `simultaneous_charge_discharge_slots` | Number of intervals with both charge and discharge above the validation threshold | intervals; expected to be zero. |
| `min_soc_kwh` | Lowest SOC in the trajectory | kWh. |
| `max_soc_kwh` | Highest SOC in the trajectory | kWh. |

`max_balance_residual_kwh` and `max_soc_residual_kwh` are reported separately;
they are not folded into `max_constraint_violation`. The latter also includes
initial- and terminal-SOC deviations, the difference between reported and
recomputed total cost, and a count of simultaneous charge/discharge intervals.
Because it combines energy-valued checks, a cost difference, and a count, it has
no single unit. Read it only as a mixed validation diagnostic, not as a physical
residual in kWh.

## Limits

These are mathematical optimization results for supplied inputs and model
assumptions. They are not real grid operating results or measured physical
battery performance. A simulated cost difference is not realized financial
savings. Do not use the software to control a real grid, protection system, or
battery controller.
