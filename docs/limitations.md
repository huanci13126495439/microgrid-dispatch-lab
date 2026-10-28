# Known limitations

- Educational simulation only. **Never connect these optimization results directly to an electrical grid, protection system, or physical battery controller.**
- No grid-flow, voltage, protection, network, ramping, degradation or aging constraints.
- No PV sales; surplus generation can be curtailed. Real tariffs can include additional charges.
- The day-ahead problem assumes perfect knowledge of a **user-provided** input curve and does not model actual forecast errors.
- The two efficiencies are interpreted separately; 0.9 one-way each means 0.81 round-trip, not 0.9.
- This first version does not implement year-long dispatch, rolling MPC, tariff-violation fees, emergency purchases or stochastic programming.
- Some users' input may lead to an infeasible MILP or HiGHS failing to certify the requested termination threshold; the code raises an error rather than inventing a result.
- Solver failures include SciPy MILP's reported status and message. Status 1 indicates an iteration/time limit, status 2 infeasibility, status 3 unboundedness, and status 4 another solver termination error; these diagnostics describe the solver's report and are not a substitute for independent model review.
- Battery numeric parameters and the solver time limit must be finite; NaN and infinite values are rejected before optimization.
- A simulated difference from the battery-disabled baseline is not a measured financial saving.
- Input values may be finite individually while their product or aggregate cost overflows floating-point range. The baseline, optimizer, and independent dispatch validator reject non-finite computed costs rather than reporting them as valid results.
