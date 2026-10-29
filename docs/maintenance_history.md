# Maintenance history and verification evidence

This log records the four focused code-maintenance pull requests and subsequent release-documentation maintenance merged after the initial public commit. It records repository changes and CI evidence, not claims of field deployment, measured savings, or independent legal verification.

## Verified baselines

### PR #8 — Post-release cleanup

- PR: [#8](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/8), merged into `main`.
- Merge commit: [`0fc3b0f5f829c6813fd609561adb2ef64ed2d019`](https://github.com/huanci13126495439/microgrid-dispatch-lab/commit/0fc3b0f5f829c6813fd609561adb2ef64ed2d019).
- Post-merge CI: [run 40912349520](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40912349520).
- Result: dependency installation, unit tests, and the synthetic demonstration passed on both Ubuntu and Windows with Python 3.11.
- Scope: removed the one-time v0.1.1 publishing workflow and updated README, the Chinese getting-started guide, CHANGELOG, and this maintenance history. Model logic, tests, license, version, and the published v0.1.1 tag and Release were unchanged.

### Published v0.1.1 and post-release main

- Release: [v0.1.1 — Maintenance Release](https://github.com/huanci13126495439/microgrid-dispatch-lab/releases/tag/v0.1.1), published 2026-10-29; neither a draft nor a prerelease.
- Tag target: [`77981a5be2dd89d072de36135a24af8ebdc7ac81`](https://github.com/huanci13126495439/microgrid-dispatch-lab/commit/77981a5be2dd89d072de36135a24af8ebdc7ac81).
- Tag-target CI: [run 40693971051](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40693971051).
- Publication: [run 40861636168](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40861636168) succeeded.
- Post-release automation merge: [`59d1a8320915ed7854b3935f790caf2dca8cdcb0`](https://github.com/huanci13126495439/microgrid-dispatch-lab/commit/59d1a8320915ed7854b3935f790caf2dca8cdcb0); [CI run 40861636393](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40861636393).
- Both CI runs passed dependency installation, unit tests, and the synthetic demonstration on Ubuntu and Windows with Python 3.11.
- The published tag retains its original candidate-era documentation. The post-release documentation correction does not move the tag or alter the Release.
- The one-time publishing workflow is retired after successful publication. The independent `tests.yml` workflow continues on pushes and pull requests.

### Fourth code-maintenance merge (before documentation updates)

- Commit: [`afb1557dff86a9bde933128170c4cee62c0715d9`](https://github.com/huanci13126495439/microgrid-dispatch-lab/commit/afb1557dff86a9bde933128170c4cee62c0715d9)
- CI: [run 40689089861](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40689089861)
- Result: Ubuntu and Windows jobs completed successfully; dependency installation, unit tests, and synthetic demonstration all passed on both platforms.

### Documentation merge (before v0.1.1 preparation)

- Commit: [`5a040e443556ef707d192da5ff27d949bdeebcb4`](https://github.com/huanci13126495439/microgrid-dispatch-lab/commit/5a040e443556ef707d192da5ff27d949bdeebcb4)
- CI: [run 40691937787](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40691937787)
- Result: Ubuntu and Windows jobs completed successfully; dependency installation, unit tests, and synthetic demonstration all passed on both platforms.

The CI matrix uses Python 3.11. Other Python versions and all possible dependency versions have not been exhaustively tested.

## Maintenance rounds

### 1. Reject non-finite battery and solver parameters

- PR: [#1](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/1)
- CI: [run 40496614503](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40496614503)
- Purpose: reject NaN and infinite parameter values before they reach the optimization process.
- Scope: parameter validation and regression coverage; no change to the MILP objective or core constraints.

### 2. Validate CSV and battery configuration input

- PR: [#2](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/2)
- CI: [run 40667702835](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40667702835)
- Purpose: improve errors for malformed CSV cells, duplicate column names, invalid numeric values, non-contiguous time intervals, and malformed battery configuration.
- Scope: input validation, regression tests, and documentation; no change to the MILP objective or core constraints.

### 3. Improve solver failure diagnostics

- PR: [#3](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/3)
- CI: [run 40684793370](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40684793370)
- Purpose: map SciPy MILP status codes to clearer error messages and test handling of missing solution vectors and unknown statuses.
- Evidence boundary: tests with mocked solver results validate message handling; they do not establish that every real-world optimization failure has been numerically reproduced.

### 4. Reject non-finite computed dispatch costs

- PR: [#4](https://github.com/huanci13126495439/microgrid-dispatch-lab/pull/4)
- CI: [run 40689089861](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40689089861)
- Purpose: catch floating-point overflow when individually finite prices and energy values produce a non-finite total cost, and reject non-finite reported costs during validation.
- Scope: cost calculation and output validation, regression tests, and limitations documentation; no change to the MILP objective or core constraints.

## What the evidence does and does not establish

The linked GitHub Actions runs show that the repository's configured CI completed successfully on Ubuntu and Windows with Python 3.11. They do not establish physical performance, real-world savings, suitability for grid control, or correctness under every possible input and dependency combination.

The project uses synthetic demonstration data. Reported cost differences are simulated outcomes under stated assumptions, not measured savings. The repository excludes the original research paper, original research programs and data, competition support materials, private verification reports, and the complete private modeling workflow.

This maintenance record is not a legal opinion or proof of copyright ownership. Authorship, source history, AI-assisted development records, and any applicable institutional or competition disclosure requirements remain separate matters.
