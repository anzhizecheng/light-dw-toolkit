# light-dw-toolkit V2

> YAML 定义口径，DuckDB 计算，一条命令出看板。

面向个人、小团队和 AI Agent 的单机轻量数仓引擎。不依赖 Spark、调度平台或 BI 服务，
把「数据导入 → 源数据体检 → 指标语义层 → 取数校验 → 静态看板」收敛为一条可复现的链路。

## 特性

- **声明式口径**：`metrics.yaml` 是指标的唯一事实源，所有数字都由它生成 SQL 计算
- **确定性 SQL**：同一份配置、同一份数据，永远得到同一结果，可审计、可 diff
- **四种指标类型**：`simple` / `ratio` / `derived` / `sql`，覆盖聚合、比率、复合与自定义 SQL
- **零服务依赖**：DuckDB 单文件存储，看板是纯静态 HTML，可直接归档或托管
- **源数据体检**：自动扫描 Excel / CSV / Parquet，落地 Parquet 并输出字段质量报告

## 安装

```bash
git clone https://github.com/anzhizecheng/light-dw-toolkit.git
cd light-dw-toolkit
python -m venv .venv && source .venv/bin/activate
pip install -e .
dw --help
```

要求 Python 3.10+。

## 快速开始

### 1. 初始化项目

```bash
dw init --root ./my-dw --source /path/to/events.csv
```

生成：

```
my-dw/
├── config/project.yaml
├── data/raw/
├── output/
└── logs/
```

`project.yaml` 示例：

```yaml
name: 我的分析项目
source_file: "/path/to/events.csv"
timezone: Asia/Shanghai
data:
  raw: data/raw
  database: data/warehouse.duckdb
```

### 2. 导入数据

方式一：按 `schema.yaml` 精确导入 CSV（推荐，字段类型可控）。

```yaml
# config/schema.yaml
events:
  - { name: user_id, type: STRING }
  - { name: event, type: STRING }
  - { name: date1, type: STRING }
  - { name: amount, type: FLOAT }
```

```bash
dw ingest --root ./my-dw --table events
```

CSV 默认无表头、逗号分隔、双引号转义；写入 `raw.events` 并同步导出 Parquet。

方式二：自动扫描源文件，生成 `sources.yaml` 与体检报告。

```bash
dw profile --root ./my-dw
```

支持 `.xlsx` / `.xls` / `.xlsm`（全部 Sheet）与 `.csv` / `.parquet`。
CSV 默认按首行表头解析；无表头 CSV 请走 `ingest` 的 `schema.yaml` 路径。

### 3. 定义指标

```yaml
# config/metrics.yaml
version: 2
source: raw.events
time_column: CAST(date1 AS DATE)

metrics:
  - name: dau
    label: 日活用户
    type: simple
    agg: count_distinct
    expr: user_id
    where: "event = 'app_start'"
    format: count
    description: 当日启动 App 的去重用户数

  - name: pay_amount
    label: 支付金额
    type: simple
    agg: sum
    expr: amount
    where: "event = 'pay_success'"
    format: amount

  - name: arpu
    label: 人均支付金额
    type: ratio
    numerator: pay_amount
    denominator: dau
    format: amount

dimensions:
  - { name: app, column: platform_name }
  - { name: city, column: city }
```

`metrics.yaml` 既支持全局 `source` / `time_column`，也支持在单个指标上覆盖；
用户表这类没有时间字段的指标，把 `time_column` 设为 `null` 即可。

### 4. 取数校验

```bash
dw metrics --root ./my-dw
dw query --root ./my-dw -m dau -g day
dw query --root ./my-dw -m pay_amount -d app
```

### 5. 生成看板

```yaml
# config/roles.yaml
title: 经营概览
subtitle: 数据源 raw.events

roles:
  - name: overview
    label: 总览
    start: "2024-01-01"
    end: "2024-01-31"
    kpis: [dau, pay_amount, arpu]
    panels:
      - type: trend
        title: 日活趋势
        grain: day
        metrics: [dau]
      - type: pie
        title: 渠道分布
        metric: dau
        dimension: app
        top: 8
      - type: bar
        title: 城市 Top10
        metric: dau
        dimension: city
        limit: 10
```

```bash
dw dashboard --root ./my-dw
```

输出 `output/dashboard.html`，可直接用浏览器打开。

## CLI

| 命令 | 作用 |
|---|---|
| `dw init` | 初始化项目目录与 `project.yaml` |
| `dw ingest --table T` | 按 `schema.yaml` 把 CSV 导入 `raw.T` |
| `dw profile` | 扫描源文件、落地 Parquet、生成 `sources.yaml` 与体检报告 |
| `dw metrics` | 列出全部指标及口径 |
| `dw query -m M [-d DIM] [-g GRAIN] [-s START] [-e END]` | 按指标取数 |
| `dw dashboard` | 按 `roles.yaml` 生成静态 HTML 看板 |

`--root` 可写在子命令前或后，默认当前目录。

## YAML 约定

### 指标类型

| 类型 | 字段 | 说明 |
|---|---|---|
| `simple` | `agg` + `expr` + `where` | 单次聚合，`agg` 支持 sum/count/count_distinct/avg/min/max |
| `ratio` | `numerator` + `denominator` | 两个 simple 指标相除，分母为 0 返回空 |
| `derived` | `expr` | 引用其他指标的表达式，如 `pay_amount / dau` |
| `sql` | `sql` | 直接执行 DuckDB SQL，支持 `{start}` / `{end}` 占位符 |

### 展示格式

`format` 支持 `amount`（自动万/亿）、`percent`、`number`、`count`。
未声明时，`ratio` 默认按百分比展示，其余按整数展示。

### 看板面板

| 类型 | 必填字段 | 说明 |
|---|---|---|
| `trend` | `metrics`、`grain` | 多指标时间趋势 |
| `bar` | `metric`、`dimension` | 维度排行 |
| `pie` | `metric`、`dimension` | 环形图，`top` 控制 TopN |
| `funnel` | `steps: [{metric, label}]` | 漏斗 |
| `compare` | `metrics: [{metric, label}]` | 多指标对比柱状图 |

KPI 支持字符串或对象写法，对象可加 `label` 与 `extra`（合计/日均等副值）。
页面底部会自动生成「口径说明」表，内容全部来自 `metrics.yaml`。

## 设计原则

1. **口径即代码**：指标定义与展示配置都在 YAML 中，可评审、可版本化
2. **只读 raw**：导入后原始层不被修改，所有计算在查询时完成
3. **确定性**：语义层只生成 SQL，不在 Python 侧做隐式计算
4. **轻量**：一个 DuckDB 文件 + 一个 HTML 文件即可交付

## 目录结构

```
dw/
├── cli.py        # 命令行入口
├── config.py     # 项目上下文与配置加载
├── ingest.py     # 按 schema 导入 CSV
├── profile.py    # 源文件扫描与体检
├── semantic.py   # 指标语义层与 SQL 生成
└── dashboard.py  # 声明式看板生成
```

## 与 AI Agent 配合

- 输入全部是 YAML，Agent 可以直接生成或修改，无需理解内部 Python
- 输出是确定性的 CLI 文本与静态 HTML，便于自动对账与回归
- 推荐流程：Agent 生成 `project/schema/metrics/roles` → 人工评审口径 → `dw query` 对账 → `dw dashboard`

## 适用边界

适合：单机、百万到千万行、批量分析、指标口径需要审计的场景。

不适合：TB 级数据、实时/流式、多租户权限、复杂调度。这些场景请使用数仓平台
（如 Doris / ClickHouse / Snowflake）或调度系统。

已知限制：

- SQL 指标不支持维度与时间粒度下钻（由 SQL 自行聚合）
- 同一次查询涉及的指标必须来自同一数据源、同一时间字段
- 看板为静态 HTML，不含鉴权

## License

Apache-2.0。引用方式见 [CITATION.cff](CITATION.cff)。
