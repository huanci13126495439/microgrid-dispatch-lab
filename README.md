# Microgrid Dispatch Lab v0.1 — public release candidate

An educational, single-day microgrid battery scheduling demonstrator using
SciPy/HiGHS mixed-integer linear programming. This is an unpublished review
candidate maintained by Xie Sentao. The author confirms this is an individually
completed project with no teammates or coauthors. The candidate is licensed under
MIT; it has not been uploaded or publicly released.

## Quick start

Python 3.11 or later, from this directory:

```text
python -m venv .venv
```

On Windows PowerShell, use the environment's interpreter directly:

```powershell
.venv/Scripts/python.exe -m pip install -e ".[test]"
.venv/Scripts/python.exe examples/generate_synthetic.py
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m microgrid_dispatch --input examples/synthetic_day.csv --output-dir outputs/demo
```

On Linux/macOS, replace `.venv/Scripts/python.exe` with `.venv/bin/python`.
The environment and pip cache may be placed on another drive using a path of
your choice. Do not place private inputs in the examples directory: the generator
overwrites `examples/synthetic_day.csv` with deterministic synthetic values.

To exercise the explicit configuration, append
`--battery-config examples/battery_config.json` to the demonstration command.
Outputs are `dispatch.csv` and `summary.json` in the requested output directory;
generated results are not part of the reviewed public file list.

## Inputs and assumptions

The CSV columns are `start_minute,end_minute,load_kwh,pv_kwh,price_per_kwh`.
The CLI requires 144 contiguous ten-minute slots starting at midnight.
Load and PV are energy per interval in kWh, not power in kW. Prices use the
input currency per kWh; load, PV and prices must be finite and non-negative.

Illustrative defaults are 12,000 kWh capacity, SOC bounds 1,200–10,800 kWh,
initial and terminal SOC 6,000 kWh, 5,000 kW charge/discharge power, and 0.90
efficiency in each direction (0.81 round-trip). These are configurable model
assumptions, not equipment specifications or suitability recommendations.

## Scope and limitations

The optimizer minimizes simulated purchases with energy balance, SOC bounds,
efficiencies and binary charge/discharge exclusion. The comparison baseline
disables battery dispatch. It exports simulated costs and algebraic constraint
residuals. These are not measured financial savings or physical validation.
See [model](docs/mathematical_model.md) and [limitations](docs/limitations.md).
No private-study reproduction claim is made.

## Personal project background and AI assistance

Xie Sentao states that the underlying mathematical modeling work was completed
individually, with no teammates or coauthors, as a competition result. Earlier
descriptions of collaborative research and teammate consent were inaccurate.
The Python model adapts the author's private research formulation and program
structure into a small configurable teaching tool; it is not presented as an
implementation developed independently of that research.

AI-assisted development and documentation review were used. Complete line-level
generation records, tool/version history and applicable terms are not available
for every file; those gaps remain explicit. Testing does not determine copyright
ownership or establish the originality of every generated expression.

The review traced the original 15 candidate files to the local application,
examined the relevant private solver without including it, and checked source
imports, notices and synthetic-data generation. No embedded third-party source
or explicit conflicting license was identified in that scope. This is a bounded
source review, not proof against every possible external match or rights claim.

This candidate contains reviewed Python, deterministic synthetic examples, tests,
dependency configuration, documentation, a CI workflow and the MIT license.
Original papers, research programs/data, competition supporting materials,
private verification reports and the complete private workflow remain excluded.
The original research files and historical results are not licensed or disclosed
by this candidate's LICENSE.

## License and release status

See [LICENSE](LICENSE) for the standard MIT license.
Copyright (c) 2026 Xie Sentao. This notice follows the author's stated authorship
and explicit licensing instruction; it is not an independent legal determination
of title and cannot grant rights in someone else's work.

The school, applicable school agreements and current competition review status
were not established. General institutional-rights and competition rules were
reviewed, but that does not clear institution-specific terms or any signed
commitment. These remain release checks, not evidence of another rights holder.
See the [authorization checklist](docs/open_source_checklist.md). Creating this
local candidate and license does not authorize an upload or public release.
The release checklist is a maintainer workflow and adds no conditions to MIT.

NumPy and SciPy are runtime dependencies; pytest and setuptools are test/build
tools. They retain their respective licenses and bundled binary notices. No
third-party source, packages or environments are bundled here. The project MIT
license does not replace their terms or claim their copyright.

The workflow describes proposed Windows/Linux checks on Python 3.11; the presence
of the YAML file does not mean remote jobs have run. Only the versions and local
platform in the separate review evidence have been exercised. The declared open
dependency ranges and other Python versions have not all been validated.
