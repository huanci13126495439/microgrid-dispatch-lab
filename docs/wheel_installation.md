# Build and install a wheel / 构建并安装 wheel

## English

From a checkout of this repository, build a wheel with Python 3.11 or later:

```text
python -m pip wheel --no-deps --wheel-dir dist .
```

Create a separate environment and install the resulting filename (replace it
with the actual file shown in `dist`):

```powershell
python -m venv .venv-wheel
.venv-wheel/Scripts/python.exe -m pip install dist/microgrid_dispatch_lab-0.1.1-py3-none-any.whl
.venv-wheel/Scripts/microgrid-dispatch.exe --help
.venv-wheel/Scripts/microgrid-dispatch.exe --input path/to/input.csv --battery-config path/to/battery.json --output-dir path/to/output
```

On Linux/macOS use `.venv-wheel/bin/python` and
`.venv-wheel/bin/microgrid-dispatch`. The battery configuration is optional.
The wheel contains the Python package and license, not the repository's
`examples` directory or synthetic generator. Supply your own appropriately
licensed CSV/config, or clone the repository separately to use its synthetic
examples. Running the source checkout's examples and installing only the wheel
are separate workflows. See [data preparation](data_preparation.md).

## 中文

在仓库源码目录使用 Python 3.11 或更高版本构建：

```text
python -m pip wheel --no-deps --wheel-dir dist .
```

创建独立环境，安装 `dist` 中实际生成的文件名：

```powershell
python -m venv .venv-wheel
.venv-wheel/Scripts/python.exe -m pip install dist/microgrid_dispatch_lab-0.1.1-py3-none-any.whl
.venv-wheel/Scripts/microgrid-dispatch.exe --help
.venv-wheel/Scripts/microgrid-dispatch.exe --input path/to/input.csv --battery-config path/to/battery.json --output-dir path/to/output
```

Linux/macOS 使用 `.venv-wheel/bin/python` 和
`.venv-wheel/bin/microgrid-dispatch`。电池配置可省略。
wheel 包含 Python 包和许可证，不包含仓库的 `examples` 目录或合成数据生成器。
请自行提供有权使用的 CSV/配置，或单独克隆仓库使用合成示例。
源码演示与仅安装 wheel 是两种不同场景。详见[数据准备](data_preparation_zh.md)。
