"""Educational MILP implementation of single-day dispatch.

Power is represented as interval energy (kWh at the microgrid bus), not kW.
Adapted from the author's individual modeling research, with AI assistance.
See LICENSE and the source/release review limits in the authorization checklist.
"""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


@dataclass(frozen=True)
class Battery:
    capacity_kwh: float = 12000.0
    min_soc_kwh: float = 1200.0
    max_soc_kwh: float = 10800.0
    initial_soc_kwh: float = 6000.0
    terminal_soc_kwh: float = 6000.0
    max_power_kw: float = 5000.0
    charge_efficiency: float = 0.90
    discharge_efficiency: float = 0.90
    interval_minutes: int = 10

    def validate(self) -> None:
        numeric_parameters = (
            self.capacity_kwh, self.min_soc_kwh, self.max_soc_kwh,
            self.initial_soc_kwh, self.terminal_soc_kwh, self.max_power_kw,
            self.charge_efficiency, self.discharge_efficiency, self.interval_minutes,
        )
        if not all(np.isfinite(value) for value in numeric_parameters):
            raise ValueError("Battery parameters must be finite")
        if not (0 <= self.min_soc_kwh < self.max_soc_kwh <= self.capacity_kwh):
            raise ValueError("Require 0 <= min SOC < max SOC <= capacity")
        if not (self.min_soc_kwh <= self.initial_soc_kwh <= self.max_soc_kwh):
            raise ValueError("Initial SOC is outside storage bounds")
        if not (self.min_soc_kwh <= self.terminal_soc_kwh <= self.max_soc_kwh):
            raise ValueError("Terminal SOC is outside storage bounds")
        if self.max_power_kw <= 0 or self.interval_minutes <= 0:
            raise ValueError("Power limit and interval duration must be positive")
        if not (0 < self.charge_efficiency <= 1 and 0 < self.discharge_efficiency <= 1):
            raise ValueError("Charge and discharge efficiencies must be in (0, 1]")


@dataclass
class Dispatch:
    purchase_kwh: np.ndarray
    charge_kwh: np.ndarray
    discharge_kwh: np.ndarray
    curtailed_pv_kwh: np.ndarray
    soc_kwh: np.ndarray
    price_per_kwh: np.ndarray
    total_cost: float
    mip_gap: float | None
    message: str
    is_baseline: bool = False


def _input_arrays(load_kwh, pv_kwh, price_per_kwh):
    arrays = [np.asarray(x, dtype=float) for x in (load_kwh, pv_kwh, price_per_kwh)]
    if any(x.ndim != 1 for x in arrays) or not len(arrays[0]):
        raise ValueError("Inputs must be non-empty one-dimensional arrays")
    if not (len(arrays[0]) == len(arrays[1]) == len(arrays[2])):
        raise ValueError("Load, PV, and price arrays must have equal lengths")
    if any(np.any(~np.isfinite(x)) or np.any(x < 0) for x in arrays):
        raise ValueError("Load, PV, and price must be finite non-negative values")
    return arrays


def baseline(load_kwh, pv_kwh, price_per_kwh, battery: Battery = Battery()) -> Dispatch:
    """Battery disabled, so external power fills positive net-load demand."""
    battery.validate()
    if abs(battery.initial_soc_kwh - battery.terminal_soc_kwh) > 1e-8:
        raise ValueError("Static-battery baseline needs equal initial and terminal SOC")
    load, pv, price = _input_arrays(load_kwh, pv_kwh, price_per_kwh)
    purchase = np.maximum(load - pv, 0)
    curtailed = np.maximum(pv - load, 0)
    return Dispatch(purchase, np.zeros_like(load), np.zeros_like(load), curtailed,
                    np.full(len(load) + 1, battery.initial_soc_kwh), price,
                    float(price @ purchase), None, "No battery dispatch", True)


def optimize_day(load_kwh, pv_kwh, price_per_kwh, battery: Battery = Battery(),
                 time_limit_s: float = 60.0) -> Dispatch:
    """Cost-minimizing MILP with binary charge/discharge mutual exclusion.

    Requires scipy >=1.11. Solve success means the solver satisfied its
    termination criteria; it does not establish real-world dispatch suitability.
    """
    battery.validate()
    load, pv, price = _input_arrays(load_kwh, pv_kwh, price_per_kwh)
    if not np.isfinite(time_limit_s) or time_limit_s <= 0:
        raise ValueError("time_limit_s must be finite and > 0")
    n = len(load)
    step_capacity = battery.max_power_kw * battery.interval_minutes / 60.0
    # Variable blocks: purchases, charge, discharge, curtailment, SOC, binary mode.
    q = np.arange(0, n)
    b = np.arange(n, 2*n)
    d = np.arange(2*n, 3*n)
    w = np.arange(3*n, 4*n)
    s = np.arange(4*n, 5*n+1)
    z = np.arange(5*n+1, 6*n+1)
    nv = 6*n+1

    objective = np.zeros(nv)
    objective[q] = price
    lb = np.zeros(nv)
    ub = np.full(nv, np.inf)
    ub[b] = step_capacity
    ub[d] = step_capacity
    ub[w] = pv
    lb[s] = battery.min_soc_kwh
    ub[s] = battery.max_soc_kwh
    ub[z] = 1

    eq = lil_matrix((2*n+2, nv), dtype=float)
    eq_rhs = np.zeros(2*n+2)
    ineq = lil_matrix((2*n, nv), dtype=float)
    ineq_rhs = np.zeros(2*n)

    for k in range(n):
        # purchase + PV + discharge = load + charge + curtailed PV
        eq[k, q[k]] = 1
        eq[k, b[k]] = -1
        eq[k, d[k]] = 1
        eq[k, w[k]] = -1
        eq_rhs[k] = load[k] - pv[k]
        # SOC[k+1] = SOC[k] + eta_c * charge - discharge / eta_d
        eq[n+k, s[k+1]] = 1
        eq[n+k, s[k]] = -1
        eq[n+k, b[k]] = -battery.charge_efficiency
        eq[n+k, d[k]] = 1 / battery.discharge_efficiency
        # charge <= Pmax*dt*z; discharge <= Pmax*dt*(1-z)
        ineq[2*k, b[k]] = 1
        ineq[2*k, z[k]] = -step_capacity
        ineq[2*k+1, d[k]] = 1
        ineq[2*k+1, z[k]] = step_capacity
        ineq_rhs[2*k+1] = step_capacity

    eq[2*n, s[0]] = 1
    eq_rhs[2*n] = battery.initial_soc_kwh
    eq[2*n+1, s[-1]] = 1
    eq_rhs[2*n+1] = battery.terminal_soc_kwh
    integrality = np.zeros(nv, dtype=np.int32)
    integrality[z] = 1
    result = milp(objective, integrality=integrality,
                  bounds=Bounds(lb, ub),
                  constraints=[LinearConstraint(eq.tocsr(), eq_rhs, eq_rhs),
                               LinearConstraint(ineq.tocsr(), -np.inf, ineq_rhs)],
                  options={"time_limit": float(time_limit_s), "mip_rel_gap": 1e-9})
    if result.status != 0 or result.x is None:
        status = int(result.status)
        reasons = {
            1: "the solver reached an iteration or time limit before satisfying its termination criteria",
            2: "the model is infeasible under the supplied inputs and constraints",
            3: "the model is unbounded; inspect the objective and variable bounds",
            4: "the solver encountered another termination error",
        }
        if status == 0 and result.x is None:
            reason = "the solver reported success but returned no solution vector"
        else:
            reason = reasons.get(status, "the solver returned an unrecognized status")
        raise RuntimeError(
            f"MILP solve failed: {reason} (status {status}): {result.message}"
        )
    sol = Dispatch(result.x[q], result.x[b], result.x[d], result.x[w],
                   result.x[s], price, float(price @ result.x[q]),
                   float(result.mip_gap) if getattr(result, "mip_gap", None) is not None else None,
                   str(result.message))
    checks = validate_dispatch(sol, load, pv, battery)
    if checks["max_balance_residual_kwh"] > 1e-5 or checks["max_soc_residual_kwh"] > 1e-5 or checks["max_constraint_violation"] > 1e-5:
        raise RuntimeError(f"Numerically invalid dispatch: {checks}")
    return sol


def validate_dispatch(sol: Dispatch, load_kwh, pv_kwh, battery: Battery = Battery()) -> dict:
    """Independent algebraic checks of the optimized or baseline dispatch."""
    battery.validate()
    load, pv, price = _input_arrays(load_kwh, pv_kwh, sol.price_per_kwh)
    n = len(load)
    for field in [sol.purchase_kwh, sol.charge_kwh, sol.discharge_kwh, sol.curtailed_pv_kwh]:
        if np.shape(field) != (n,) or not np.isfinite(field).all():
            raise ValueError("Output interval arrays have invalid shape or values")
    if sol.soc_kwh.shape != (n+1,) or not np.isfinite(sol.soc_kwh).all():
        raise ValueError("Output SOC trajectory has invalid shape or values")
    cap = battery.max_power_kw*battery.interval_minutes/60
    balance = sol.purchase_kwh + pv + sol.discharge_kwh - load - sol.charge_kwh - sol.curtailed_pv_kwh
    recursion = np.diff(sol.soc_kwh) - battery.charge_efficiency*sol.charge_kwh + sol.discharge_kwh/battery.discharge_efficiency
    issues = [np.max(np.maximum(0, -x)) for x in
              (sol.purchase_kwh, sol.charge_kwh, sol.discharge_kwh, sol.curtailed_pv_kwh)]
    issues.extend([np.max(np.maximum(0, sol.curtailed_pv_kwh-pv)),
                   np.max(np.maximum(0, sol.charge_kwh-cap)),
                   np.max(np.maximum(0, sol.discharge_kwh-cap)),
                   np.max(np.maximum(0, battery.min_soc_kwh-sol.soc_kwh)),
                   np.max(np.maximum(0, sol.soc_kwh-battery.max_soc_kwh)),
                   abs(sol.soc_kwh[0]-battery.initial_soc_kwh),
                   abs(sol.soc_kwh[-1]-battery.terminal_soc_kwh),
                   abs(sol.total_cost-float(price@sol.purchase_kwh))])
    simultaneous = int(np.count_nonzero((sol.charge_kwh > 1e-6)&(sol.discharge_kwh > 1e-6)))
    issues.append(float(simultaneous))
    return {"max_balance_residual_kwh": float(np.max(np.abs(balance))),
            "max_soc_residual_kwh": float(np.max(np.abs(recursion))),
            "max_constraint_violation": float(max(issues)),
            "simultaneous_charge_discharge_slots": simultaneous,
            "min_soc_kwh": float(np.min(sol.soc_kwh)),
            "max_soc_kwh": float(np.max(sol.soc_kwh))}
