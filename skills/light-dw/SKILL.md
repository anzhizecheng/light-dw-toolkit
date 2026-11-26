---
name: light-dw
description: 搭建并运行轻量数仓。用户提到轻量数仓、建数仓、指标口径、SQL 取数、生成数据看板、CSV 导入 DuckDB 或 dw 命令时使用。不用于重型数仓平台、实时流处理或纯前端开发。
---

# light-dw

薄封装 light-dw-toolkit 的 `dw` CLI。纯 Markdown 指令包，不依赖特定 AI 助手，也不重复实现引擎逻辑。

只负责编排命令、维护 YAML 与校验结果；实际计算由 `dw` 完成。

## 前置检查

1. 执行 `dw --help`。
2. 若命令不存在，确认 light-dw-toolkit 仓库路径，在仓库根目录执行 `pip install -e .`，再重试。
3. 确认项目根目录（含 `config/project.yaml`）；用户未提供时先询问，或使用当前目录。

## 执行顺序

### 1. 初始化

```bash
dw init --root <项目> --source <源文件>
```

已有 `config/project.yaml` 则跳过。

### 2. 导入数据

- 精确导入：先确认 `config/schema.yaml` 的表名与列类型，再执行
  `dw ingest --root <项目> --table <表>`。
- 自动体检：执行 `dw profile --root <项目>`，读取 `config/sources.yaml`
  与 `output/数据体检报告.md`。
- 不要编造列名，字段以 `schema.yaml` 或 `sources.yaml` 为准。

### 3. 定义指标

编辑 `config/metrics.yaml`：

- 顶层写 `source` 与 `time_column`；没有时间字段时写 `time_column: null`。
- 指标类型：
  - `simple`：`agg` + `expr` + 可选 `where`
  - `ratio`：`numerator` + `denominator`
  - `derived`：`expr`
  - `sql`：直接执行 DuckDB SQL
- 每个指标写 `label`、`format`（`amount` / `percent` / `number` / `count`）、`description`。
- 维度写在 `dimensions`，格式为 `{ name, column }`。

### 4. 校验

```bash
dw metrics --root <项目>
dw query --root <项目> -m <指标> [-g day] [-d <维度>]
```

未实际执行 `query` 不得汇报任何指标值。

### 5. 生成看板

编辑 `config/roles.yaml`，按 roles → kpis / panels 组织。
面板类型支持 `trend`、`bar`、`pie`、`funnel`（需要 `steps`）、`compare`（需要 `metrics`）。

```bash
dw dashboard --root <项目>
```

交付 `output/dashboard.html`。

## 约束

- raw 层只读，不要用 UPDATE / DELETE 修改原始表。
- 同一查询涉及的指标必须来自同一数据源、同一时间字段。
- SQL 指标不支持维度与时间粒度下钻。
- 百分比指标用 `ratio` 或显式声明 `format: percent`。
- 汇报时同时说明数据覆盖范围与口径陷阱。
- 更完整的 YAML 约定见仓库 `README.md`。
