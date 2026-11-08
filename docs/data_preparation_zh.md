# 准备输入数据

命令行程序模拟一天，要求从午夜开始、连续的 144 个十分钟时段。CSV 使用
UTF-8，包含表头和恰好 144 行数据。仓库中的[合成示例](../examples/synthetic_day.csv)
可供参考，它不是实际电网数据。

| 字段 | 含义 | 单位 |
| --- | --- | --- |
| `start_minute` | 自午夜起的时段开始时间，整数 | 分钟 |
| `end_minute` | 自午夜起的时段结束时间，整数 | 分钟 |
| `load_kwh` | 时段内负荷电量 | kWh |
| `pv_kwh` | 时段内光伏发电量 | kWh |
| `price_per_kwh` | 购电价格 | 所选货币/kWh |

第一段为 0–10，后段起点等于前段终点，最后结束于 1440。电量和电价必须是
有限、非负数值；负荷与光伏是时段电量，不是功率。列名不得重复。

## 电池配置

可使用 `--battery-config path/to/battery.json`。文件必须是键名唯一的 JSON
对象，未提供的键使用默认值；参数必须是有限数字，不能是布尔值，不允许未知键。

| 参数 | 含义及约束 |
| --- | --- |
| `capacity_kwh`、`min_soc_kwh`、`max_soc_kwh` | 单位 kWh；0 ≤ 最小 SOC < 最大 SOC ≤ 容量 |
| `initial_soc_kwh`、`terminal_soc_kwh` | 单位 kWh；均在 SOC 范围内；CLI 静态电池基线要求两者相等 |
| `max_power_kw` | 充放电功率上限，kW，必须为正 |
| `charge_efficiency`、`discharge_efficiency` | 无量纲，均在 (0, 1] |
| `interval_minutes` | 分钟；CLI 要求为 10 |

计算出的单时段功率上限也必须有限。合成默认配置见
[battery_config.json](../examples/battery_config.json)。

## 常见错误

- 缺少或重复列名：每个必需字段只出现一次。
- 空值、非数字、负数、NaN 或无穷大：按提示行和列改为有限非负数字。
- 时间错误：依据提示的行号、期望值和实际值修正间隔、重叠、倒退或时长；数据必须为 144 行。
- 电池 JSON 错误：修正语法、重复或未知键、数值类型或提示的参数边界。

结果属于模拟，不是实测收益，也不能直接用于控制真实电网或实体电池。
