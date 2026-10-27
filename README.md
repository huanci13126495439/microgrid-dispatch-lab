# Microgrid Dispatch Lab v0.1.0 — public release

An educational, single-day microgrid battery scheduling demonstrator using
SciPy/HiGHS mixed-integer linear programming. This project was completed
individually by Xie Sentao, without teammates or coauthors, and is publicly
released under the MIT License.

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

The author completed this project individually as a competition entry, without
teammates or coauthors. The Python model adapts the author's private research
formulation and program structure into a small configurable teaching tool; it is
not presented as an implementation developed independently of that research.

AI-assisted development and documentation review were used. Complete line-level
generation records, tool/version history and applicable terms are not available
for every file; those gaps remain explicit. Testing does not determine copyright
ownership or establish the originality of every generated expression.

The pre-release review covered the 15 files present before the MIT license was
added, tracing them to the local application and examining the relevant private
solver without including it. It checked source imports, notices and synthetic-data
generation. No embedded third-party source or explicit conflicting license was
identified within that review scope. This is a bounded source review, not proof
against every possible external match or rights claim.

This public release contains reviewed Python code, deterministic synthetic
examples, tests, dependency configuration, documentation, a CI workflow and the
MIT license. Original papers, research programs/data, competition supporting
materials, private verification reports and the complete private workflow remain
excluded. The original research files and historical results are not licensed
or disclosed by this repository's LICENSE.

## License and release status

See [LICENSE](LICENSE) for the standard MIT license.
Copyright (c) 2026 Xie Sentao. This notice follows the author's stated authorship
and explicit licensing instruction; it is not an independent legal determination
of title and cannot grant rights in someone else's work.

This repository has been publicly released. School-specific agreements, any
applicable institutional rights, and the exact terms of any signed competition
disclosure commitment have not been independently established. Completing the
project individually and having no teammates does not, by itself, settle those
separate questions. See the [authorization checklist](docs/open_source_checklist.md).
That checklist is a maintainer workflow and adds no conditions to the MIT license.

NumPy and SciPy are runtime dependencies; pytest and setuptools are test/build
tools. They retain their respective licenses and bundled binary notices. No
third-party source, packages or environments are bundled here. The project MIT
license does not replace their terms or claim their copyright.

## Continuous integration

The GitHub Actions run for the initial public commit completed successfully on
both Ubuntu and Windows: the unit-test step and synthetic demonstration passed
on each platform. See the [workflow run](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40490349596).
These results cover the configured Python 3.11 environments only; the declared
open dependency ranges and other Python versions have not all been validated.
