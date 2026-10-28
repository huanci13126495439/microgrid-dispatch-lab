# Changelog

All notable project changes are documented here. This file links to reviewed pull requests and actual CI runs.

## 0.1.1 — Maintenance release candidate (tag pending)

This candidate includes the following maintenance changes after the initial v0.1.0 public version. The `v0.1.1` Git tag and GitHub release have **not** been created yet.

### Validation and reliability

- Reject non-finite battery parameters and solver time limits. [PR #1](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/1) · [CI](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40496614503)
- Improve CSV and battery configuration validation, including malformed values and time-interval checks. [PR #2](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/2) · [CI](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40667702835)
- Provide more actionable diagnostics for MILP solver termination statuses. [PR #3](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/3) · [CI](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40684793370)
- Reject non-finite computed dispatch costs, including overflow from finite input values. [PR #4](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/4) · [CI](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40689089861)
- Refresh README and Chinese getting-started documentation, and add a maintenance history and changelog. [PR #5](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/5) · [CI](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40691937787)

These changes add validation, diagnostics, regression coverage, and documentation. They do not change the MILP objective or core constraint formulation. The linked CI runs cover the configured Python 3.11 environments on Ubuntu and Windows, including the unit-test step and synthetic demonstration.

## 0.1.0 — Initial public version

- Educational single-day microgrid battery dispatch using SciPy/HiGHS MILP.
- Deterministic synthetic input generator and example configuration.
- Dispatch output and algebraic constraint validation.
- Unit tests, documentation, MIT license, and GitHub Actions for Ubuntu and Windows.

The synthetic demonstration is not evidence of measured financial savings, real-grid suitability, or physical system validation.
