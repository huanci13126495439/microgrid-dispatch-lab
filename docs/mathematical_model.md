# One-day MILP formulation (v0.1)

All indexed energy variables represent **kWh per time slot at the common AC bus**, not kW.

Let \(L_t\) be consumption, \(V_t\) solar generation, \(p_t\) time-of-use price. Decision variables: \(q_t\) purchased energy, \(b_t\) charged energy, \(d_t\) discharged energy, \(w_t\) curtailed solar, \(S_t\) energy in battery, binary \(z_t\) charge-mode indicator.

Minimize \(\sum_t p_t q_t\).

Subject to:

1. Power/energy balance: \(q_t+V_t+d_t = L_t+b_t+w_t\).
2. Battery recursion: \(S_{t+1}=S_t+\eta_c b_t -d_t/\eta_d\).
3. Exclusivity: \(0\le b_t\le K z_t\); \(0\le d_t\le K(1-z_t)\).
4. Solar curtailment: \(0\le w_t\le V_t\).
5. \(S_{\min}\le S_t\le S_{\max}\), initial and terminal SOC are set explicitly.
6. \(q_t\ge 0\), \(z_t\in\{0,1\}\); \(K=P_{\max}\Delta t\).

The no-dispatch baseline sets both battery actions to zero and uses \(q_t=\max(L_t-V_t,0)\). This is a *specific comparison baseline*, not the universally optimal no-storage system design.

Differences from any full study: no demand-charge, battery degradation, inverter limits, grid-export, contingency reserves, inter-day operation, uncertainty, or actual execution model. Solver `mip_gap` and constraint residuals are reported separately from physical validation.
