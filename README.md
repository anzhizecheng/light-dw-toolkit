# light dw toolkit — 轻量级数据仓库工具箱

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE) [![Skills](https://img.shields.io/badge/skills-17-green.svg)](#skill-清单) [![Templates](https://img.shields.io/badge/templates-15-orange.svg)](#精简模板库)

> 面向 LLM Agent 的功能型 Skill 集合，覆盖数据仓库建设全流程。 轻量、可独立、可组合。

---

## 它是什么？

light dw toolkit 是一套用于数据仓库项目开发交付的工具集。它把传统数仓实施中繁琐的流程，**精简为 15 个 markdown / yaml / sql 模板**，配套 **17 个可独立调用的 Skill**，大幅提升数仓建设的效率。

### 设计哲学

|原则|说明|
|---|---|
|**轻量模板**|使用 AI 友好的 markdown / yaml / sql 文件格式|
|**功能解耦**|每个 Skill 独立，按需调用，不绑定阶段|
|**禁止编造**|每个 Skill 显式声明「禁止编造」，待确认的部分通过人工交互补充|

---

## 快速上手

### 1. 完整数仓项目（推荐顺序）

按 SOP Phase 0→15 顺序，一个一个调用：

```
# Phase 0 — 初始化
01-gen-project-config          # 生成 project_config.yaml

# Phase 1-2 — 项目启动
02-gen-project-plan             # AI 辅助 WBS + 排期

# Phase 3 — 系统需求
03-gen-requirements-spec        # BRS 业务需求规格说明书
04-gen-metrics-dictionary       # 指标体系字典

# Phase 7 — 数据源分析
05-gen-data-quality-report      # 数据质量 5 维度评估
06-gen-source-data-dict         # 源端数据字典

# Phase 8 — 数据模型设计
07-gen-dimension-model          # CDM / LDM 维度模型
08-gen-ddl-scripts              # 物理 DDL（4/3 层可配，多引擎方言）

# Phase 9 — ETL 设计
09-gen-etl-mapping              # 字段级映射 + 维表优先加载序
10-gen-data-cleaning-rules      # 清洗规则 + 拒绝数据落库 + CORRECT 3 阶段警示

# Phase 12 — 系统开发
11-gen-test-cases               # SIT/UAT 4 大类测试用例
12-gen-etl-sql                  # ETL SQL（集成清洗规则 + 审计日志）
13-gen-etl-workflow             # ETL 调度 DAG（含 clean_task 节点）
14-gen-etl-unit-tests           # ETL 单元测试脚本

# Phase 13 — 系统测试
15-gen-sit-scripts              # 跨层对账 + 清洗审计验证

# Phase 14-15 — 部署与交付
16-gen-deploy-plan              # 部署方案 + 回滚预案
17-gen-user-manual              # 用户操作手册
```

### 2. 独立调用

只做单点任务：

```
用户: "帮我生成指标字典"
助手: 触发 04-gen-metrics-dictionary
输入: 业务目标、报表清单
输出: metrics.yaml
```

### 3. 组合调用

复用已有产出：

```
用户: "我已经有 data_dict 和 quality_report，想生成清洗规则"
助手: 触发 10-gen-data-cleaning-rules
输入: data_dict + quality_report + data_standard_doc (可选)
输出: cleaning_rules.yaml + reject_records_schema.sql
```

---

## Skill 清单

|#|Skill|SOP Phase|类型|精简模板|
|---|---|---|---|---|
|01|gen-project-config|**0** 基础设施|基础设施|—|
|02|gen-project-plan|1-2 项目启动|项目管理|—|
|03|gen-requirements-spec|3 系统需求|需求分析|`03-requirements-spec.md`|
|04|gen-metrics-dictionary|3 系统需求|指标体系|`04-metrics-dictionary.yaml`|
|05|gen-data-quality-report|7 数据源分析|数据治理|`05-data-quality-report.yaml`|
|06|gen-source-data-dict|7 数据源分析|数据治理|`06-source-data-dict.yaml`|
|07|gen-dimension-model|8 数据模型|建模|`07-dimension-model.md`|
|08|gen-ddl-scripts|8 数据模型|建模|`08-ddl-spec.yaml`|
|09|gen-etl-mapping|9 ETL 设计|ETL|`09-etl-mapping.yaml`|
|10|gen-data-cleaning-rules|9 ETL 设计|数据治理|`10-cleaning-rules.yaml`|
|11|gen-test-cases|11/13 测试|测试|`11-test-cases.yaml`|
|12|gen-etl-sql|12 系统开发|ETL|`12-etl-sql.md`|
|13|gen-etl-workflow|12 系统开发|ETL|`13-etl-workflow.yaml`|
|14|gen-etl-unit-tests|12 系统开发|测试|`14-etl-unit-tests.sql`|
|15|gen-sit-scripts|13 系统测试|测试|`15-sit-tests.yaml`|
|16|gen-deploy-plan|14 上线试运行|运维|`16-deploy-plan.md`|
|17|gen-user-manual|13/15 交付|文档|`17-user-manual.md`|

---

## 精简模板库

所有模板位于 `[templates/](templates/)`，共 **15 个**：

```
templates/
├── 03-requirements-spec.md    # BRS 需求规格说明书
├── 04-metrics-dictionary.yaml # 指标体系字典
├── 05-data-quality-report.yaml# 数据质量 5 维度
├── 06-source-data-dict.yaml   # 源端数据字典
├── 07-dimension-model.md      # CDM / LDM + 命名规范
├── 08-ddl-spec.yaml           # 物理 DDL 规范
├── 09-etl-mapping.yaml        # ETL 字段级映射
├── 10-cleaning-rules.yaml     # 清洗规则 (v1.5: CORRECT 3 阶段警示)
├── 11-test-cases.yaml         # 4 大类 SIT/UAT 用例
├── 12-etl-sql.md              # ETL SQL 脚本规范
├── 13-etl-workflow.yaml       # DAG 调度定义
├── 14-etl-unit-tests.sql      # 单元测试 SQL
├── 15-sit-tests.yaml          # SIT 集成测试
├── 16-deploy-plan.md          # 部署上线方案
└── 17-user-manual.md          # 用户操作手册
```

格式说明：

|格式|用途|示例|
|---|---|---|
|**yaml**|结构化配置（指标字典、清洗规则、DAG、测试用例）|`.yaml`|
|**markdown**|叙述性文档（需求、模型、手册、SQL 规范）|`.md`|
|**sql**|可执行 SQL 脚本（单元测试）|`.sql`|

> 为什么不用 Excel？— 因为 AI 解析 `.xlsx` 需要依赖 `openpyxl` / `pandas`， 而 `.yaml` 可以直接读、直接写、直接 diff。对 AI 来说 YAML 比 Excel 更友好。

---

## Skill 间的契约依赖

```
                     01-gen-project-config  ◀── 必须首先调用
                            │
                            ▼
               ┌────────────┼────────────┐
               ▼            ▼            ▼
         03-requirements  04-metrics  02-project
            -spec          -dictionary   -plan
                            │
                            ▼
               ┌────────────┼────────────┐
               ▼            ▼            ▼
         06-source-data   05-data-quality
            -dict          -report
               │            │
               ▼            ▼
            └────┬─────────┘
                 ▼
          07-gen-dimension-model
                 │
                 ▼
           08-gen-ddl-scripts
                 │
                 ▼
          09-gen-etl-mapping
                 │
                 ▼
          10-gen-data-cleaning-rules
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
   12-gen-etl  13-gen-etl  14-gen-etl
    -sql       -workflow    -unit-tests
        │        │        │
        └────────┼────────┘
                 ▼
          15-gen-sit-scripts
                 │
                 ▼
          16-gen-deploy-plan
                 │
                 ▼
          17-gen-user-manual
```

---

## 关键约束（每个 Skill 强制执行）

|#|约束|执行 Skill|说明|
|---|---|---|---|
|1|DDL 默认 4 层；可切换 3 层|08-gen-ddl-scripts|`layer_architecture` 参数控制|
|2|ETL 加载顺序：DIM → ODS → DWD → DWS → ADS|09-gen-etl-mapping|维表优先加载|
|3|ETL SQL 必须基于 mapping_doc|12-gen-etl-sql|禁止编造字段映射|
|4|DAG 任务依赖必须与 load_order 一致|13-gen-etl-workflow|防止任务乱序|
|5|每个 transform 前必须有 clean_task|13-gen-etl-workflow|v1.2 强制|
|6|cleaning_rules.yaml CORRECT 动作为危险不可逆操作|10-gen-data-cleaning-rules|v1.5：3 阶段警示 + 用户确认|
|7|拒绝数据必须落 dw_reject_records|12-gen-etl-sql|同时写 cleaning_audit.log|
|8|所有 Skill 写 skill_execution.log|全部|统一日志机制|

---

## 目录结构

```
dw-functional-skills/
├── LICENSE                         # Apache 2.0
├── CITATION.cff                    # 引用文件
├── README.md                       # 本文档
├── LOGGING-CONVENTION.md           # 统一日志机制
├── SKILLS-STRUCTURE.md             # 内部设计文档（归档）
│
├── templates/                      # 15 个精简模板
│   ├── 03-requirements-spec.md
│   ├── 04-metrics-dictionary.yaml
│   ├── ...
│   └── 17-user-manual.md
│
└── 01-gen-project-config/          # 17 个 Skill 目录
    ├── SKILL.md
    └── ...
```

---

## 引用方式

### BibTeX

```
@software{lightdwtoolkit,
  author  = {anzhizecheng},
  title   = {light dw toolkit: 轻量级数据仓库建设 AI 工具箱},
  year    = {2026},
  month   = sep,
  version = {2.0.0},
  license = {Apache-2.0},
  url     = {https://github.com/anzhizecheng/dw-functional-skills},
}
```

### 纯文本

> anzhizecheng. (2026). _light dw toolkit: 轻量级数据仓库建设 AI 工具箱_ (v2.0.0). [Computer software]. [https://github.com/anzhizecheng/dw-functional-skills](https://github.com/anzhizecheng/dw-functional-skills)

### 直接复制 CITATION.cff

```
cp CITATION.cff ~/my-paper/
```

---

## 许可

本项目基于 **Apache License 2.0** 开源。详见 [LICENSE](LICENSE)。

**SPDX-License-Identifier:** `Apache-2.0`

---

## 贡献

欢迎 Issue、PR、讨论。