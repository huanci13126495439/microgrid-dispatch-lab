# 从这里开始：Microgrid Dispatch Lab v0.1.0

这是一个已公开发布的个人教育性项目：使用 SciPy/HiGHS 混合整数线性规划（MILP）演示单日微电网电池调度。项目采用 MIT 许可证，详见 [LICENSE](LICENSE)。

## 安装与运行

需要 Python 3.11 或更高版本。在仓库根目录执行：

Windows：
```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[test]"
.venv/Scripts/python.exe examples/generate_synthetic.py
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m microgrid_dispatch --input examples/synthetic_day.csv --output-dir outputs/demo --battery-config examples/battery_config.json
```

Linux/macOS 将 `.venv/Scripts/python.exe` 替换为 `.venv/bin/python`。如有需要，虚拟环境和 pip 缓存可以放在其他磁盘。

输出目录会生成 `dispatch.csv` 和 `summary.json`。示例生成器会覆盖 `examples/synthetic_day.csv`，请勿把私有或比赛原始数据放入示例目录。

## 输入要求与结果解释

CSV 必须包含 `start_minute,end_minute,load_kwh,pv_kwh,price_per_kwh`，并包含从午夜开始、连续的 144 个十分钟时段。负荷和光伏数值是每个时段的电量（kWh），不是功率（kW）；电价按输入数据所用的货币单位计价。输入及电池参数需满足程序校验规则。

项目比较优化调度与停用电池的模拟基线，输出的是合成数据条件下的模拟结果，不是实测电费节省，也没有经过真实电网或实物电池验证。**不得将结果直接用于电网控制、保护系统或真实电池控制器。** 完整模型假设见 [数学模型](docs/mathematical_model.md) 与 [局限性](docs/limitations.md)。

## 维护与 CI

四轮维护分别改进了非有限参数校验、CSV/电池配置校验、求解失败诊断，以及计算成本溢出保护。变更记录和对应的 PR/CI 链接见 [维护历史](docs/maintenance_history.md) 与 [变更日志](CHANGELOG.md)。

第四轮代码维护合并提交 `afb1557dff86a9bde933128170c4cee62c0715d9` 的 GitHub Actions 已在 Ubuntu 和 Windows、Python 3.11 上通过依赖安装、单元测试及合成演示，详见 [CI 记录](https://github.com/huanci13126495439/microgrid-dispatch-lab/actions/runs/40689089861)。此结果不等于所有 Python 版本或所有依赖版本组合均已验证。

## 来源与许可边界

作者说明该项目由本人独立完成。Python 模型改写自作者的个人研究程序及其模型/结构；仓库不声称与原研究完全无关。开发过程中使用了 AI 辅助，但完整逐行生成记录、工具版本历史和所有适用条款并未全部留存。测试通过不等于证明每一行代码的版权归属。

本仓库仅授权其中实际包含且作者有权授权的文件。原始论文、原始研究程序与数据、竞赛支撑材料、私有验证报告及完整数模工作流均不包含在仓库内，也不因本仓库的 MIT 许可证而获得许可。学校或其他机构协议及具体竞赛披露承诺未在此独立确权；参赛者身份和独立完成情况本身不能替代对这些事项的核查。

NumPy、SciPy 及开发工具均保留各自许可证和第三方声明。更多限制请阅读 README 和项目文档。
