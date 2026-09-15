---
name: gen-ddl-scripts
description: |
  生成数仓各层物理 DDL 脚本（建表语句），支持 Hive / Spark / MySQL / ClickHouse / Doris / PostgreSQL / Oracle 多引擎方言，自动应用命名规范、分区策略、存储格式、索引设计。

  触发条件：用户提到「DDL 脚本」「建表语句」「表结构脚本」「CREATE TABLE」「物理模型 DDL」「DDL 生成」时触发。

  适用阶段：Phase 8 数据模型设计（物理设计阶段）+ Phase 12 系统开发（部署阶段）

  绑定模板：
  - templates/08-ddl-spec.yaml

  输入不足处理：
  - 若未提供维度模型（LDM），提示先使用 gen-dimension-model
  - 若未指定目标引擎，生成 ANSI SQL + 各方言差异说明
  - 若未提供分区策略，标注「需根据数据量决定」
  - 严禁编造字段类型、字段名

  上游依赖（契约式输入）：
  - gen-metrics-dictionary → metrics_list：决定 ADS 层度量字段
  - gen-source-data-dict → table_structures / code_tables：决定 ODS 层字段类型与代码表
  - gen-data-quality-report → data_quality_metrics：决定 ODS/DWD 层质量约束

  运行时架构决策（关键参数）：
  - layer_architecture: standard_4layer (默认) | simplified_3layer | custom
  - 若未指定 layer_architecture，按 standard_4layer 处理
version: 1.1.0
category: data-modeling
template_bound:
  - "templates/08-ddl-spec.yaml"
related_skills:
  - gen-dimension-model
  - gen-metrics-dictionary
  - gen-source-data-dict
  - gen-data-quality-report
  - gen-etl-mapping
  - gen-etl-sql
  - gen-etl-workflow
---

# 生成物理 DDL 脚本 (Physical DDL Generator)

## 触发词

`DDL 脚本`, `建表语句`, `表结构脚本`, `CREATE TABLE`, `物理模型 DDL`, `DDL 生成`, `schema`, `建库`, `建表`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 08-ddl-spec.yaml | `templates/08-ddl-spec.yaml` | 参考/规范 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `target_engine` | enum | 目标引擎：hive / spark / mysql / clickhouse / doris / postgresql / oracle |
| `database_name` | string | 目标数据库名 |
| `tables` | list | 表清单（每张表含字段定义）|

### 架构决策参数（运行时指定）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `layer_architecture` | enum | `standard_4layer` | 数仓分层架构：`standard_4layer`（ODS+DWD+DWS+ADS+DIM）/ `simplified_3layer`（ODS+DWS+ADS）/ `custom`（用户自定义层清单）|
| `layer_list` | list | null | 自定义层清单（仅当 `layer_architecture=custom` 时必填），如 `["ODS","DWD","DWS","ADS"]` |
| `skip_dwd` | bool | false | 兼容参数：true 时强制跳过 DWD 层（等同于 `simplified_3layer`）|

> 💡 **默认行为**：未指定 `layer_architecture` 时，按 `standard_4layer` 处理，输出 4 层（ODS+DWD+DWS+ADS）+ 公共维表（DIM）。

### 上游契约输入（来自其他 skill 的输出）

| 字段 | 来源 skill | 类型 | 说明 |
|------|-----------|------|------|
| `metrics_list` | gen-metrics-dictionary | list | 指标清单 → 决定 **ADS 层** 度量字段（MET_SALES_001 → `sales_amt DECIMAL(18,2)`）|
| `table_structures` | gen-source-data-dict | dict | 源表结构 → 决定 **ODS 层** 字段类型与命名 |
| `code_tables` | gen-source-data-dict | dict | 代码表 → 决定 **ODS 层** 枚举字段注释 |
| `data_quality_metrics` | gen-data-quality-report | dict | 数据质量评估结果 → 决定 **ODS/DWD 层** NOT NULL 约束、值域 CHECK |

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `partition_strategy` | dict | 分区策略（表名 -> 分区字段列表）|
| `storage_format` | enum | 存储格式：ORC / PARQUET / TEXTFILE / AVRO |
| `compression` | enum | 压缩方式：SNAPPY / GZIP / ZSTD / LZ4 |
| `indexes` | dict | 索引设计（表名 -> 索引列表）|
| `buckets` | dict | 分桶（表名 -> 桶数 + 分桶字段）|
| `lifecycle` | dict | 生命周期（表名 -> 保留天数）|
| `comments` | bool | 是否添加字段注释（默认 true）|

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `create_database_sql` | SQL | 建库语句 |
| `create_table_sql` | SQL | 各表 DDL |
| `index_ddl` | SQL | 索引 DDL |
| `partition_ddl` | SQL | 分区维护 DDL |
| `execution_script` | SQL | 完整可执行脚本（含顺序、IF NOT EXISTS）|

---

## 自动执行步骤

1. **校验输入** — 检查表结构、字段类型、命名规范
2. **生成建库语句** — CREATE DATABASE
3. **生成建表语句** — 按层（ODS → DWD → DWS → ADS → DIM）顺序
4. **添加字段注释** — COMMENT ON COLUMN
5. **添加表注释** — COMMENT ON TABLE
6. **应用分区策略** — PARTITIONED BY
7. **应用分桶策略** — CLUSTERED BY / BUCKETS
8. **应用存储格式** — STORED AS ORC / PARQUET
9. **添加索引** — 唯一索引、二级索引
10. **生成完整脚本** — 整合 + 排序 + IF NOT EXISTS 保护

---

## 引擎方言适配

### Hive / Spark SQL

```sql
-- 库
CREATE DATABASE IF NOT EXISTS dwd
COMMENT '数据仓库明细层'
LOCATION '/user/hive/warehouse/dwd.db';

-- 表（DWD 层）
CREATE TABLE IF NOT EXISTS dwd.dwd_sales_order (
    order_id         BIGINT        COMMENT '订单号',
    user_key         BIGINT        COMMENT '用户代理键',
    product_key      BIGINT        COMMENT '商品代理键',
    date_key         INT           COMMENT '订单日期键',
    order_amount     DECIMAL(18,2) COMMENT '订单金额',
    discount_amount  DECIMAL(18,2) COMMENT '优惠金额',
    pay_amount       DECIMAL(18,2) COMMENT '实付金额',
    item_count       INT           COMMENT '商品件数',
    create_time      TIMESTAMP     COMMENT '创建时间',
    update_time      TIMESTAMP     COMMENT '更新时间',
    etl_time         TIMESTAMP     COMMENT 'ETL 处理时间'
)
COMMENT '销售订单明细表'
PARTITIONED BY (dt STRING COMMENT '数据日期分区')
CLUSTERED BY (user_key) SORTED BY (order_id) INTO 32 BUCKETS
STORED AS ORC
TBLPROPERTIES (
    'orc.compress'='SNAPPY',
    'lifecycle'='3650',
    'transactional'='false'
);
```

### MySQL

```sql
CREATE DATABASE IF NOT EXISTS dws
DEFAULT CHARACTER SET utf8mb4
DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dws.dws_sales_user_d (
    user_key      BIGINT        NOT NULL  COMMENT '用户代理键',
    date_key      INT           NOT NULL  COMMENT '日期键',
    order_cnt     INT           NOT NULL  DEFAULT 0 COMMENT '订单数',
    gmv           DECIMAL(18,2) NOT NULL  DEFAULT 0.00 COMMENT 'GMV',
    pay_amount    DECIMAL(18,2) NOT NULL  DEFAULT 0.00 COMMENT '实付金额',
    item_cnt      INT           NOT NULL  DEFAULT 0 COMMENT '商品件数',
    first_order_time  TIMESTAMP NULL   COMMENT '当日首单时间',
    last_order_time   TIMESTAMP NULL   COMMENT '当日末单时间',
    etl_time      TIMESTAMP     NOT NULL  DEFAULT CURRENT_TIMESTAMP COMMENT 'ETL 处理时间',
    PRIMARY KEY (user_key, date_key),
    KEY idx_date (date_key),
    KEY idx_user (user_key)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COMMENT='用户日销售汇总表';
```

### ClickHouse

```sql
CREATE DATABASE IF NOT EXISTS dws;

CREATE TABLE IF NOT EXISTS dws.dws_sales_user_d (
    user_key         Int64,
    date_key         Int32,
    order_cnt        Int32 DEFAULT 0,
    gmv              Decimal(18, 2) DEFAULT 0,
    pay_amount       Decimal(18, 2) DEFAULT 0,
    item_cnt         Int32 DEFAULT 0,
    first_order_time DateTime,
    last_order_time  DateTime,
    etl_time         DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(toDate(date_key * 10000 + 101))  -- 错误：ClickHouse 不支持 date_key 转 date
ORDER BY (user_key, date_key)
TTL etl_time + INTERVAL 3 YEAR
SETTINGS index_granularity = 8192;
```

> ⚠️ 上面 ClickHouse 例子是错误示范。正确做法是使用 `date_value DATE` 而非 date_key INT。AI 应识别此类问题并标注。

### Doris

```sql
CREATE DATABASE IF NOT EXISTS ads;

CREATE TABLE IF NOT EXISTS ads.ads_sales_dashboard (
    date_key       INT           NOT NULL  COMMENT '日期键',
    region_key     INT           NOT NULL  COMMENT '地区键',
    order_cnt      BIGINT        NOT NULL  DEFAULT 0 COMMENT '订单数',
    gmv            DECIMAL(18,2) NOT NULL  DEFAULT 0.00 COMMENT 'GMV',
    pay_amount     DECIMAL(18,2) NOT NULL  DEFAULT 0.00 COMMENT '实付金额',
    user_cnt       BIGINT        NOT NULL  DEFAULT 0 COMMENT '下单用户数'
)
DUPLICATE KEY(date_key, region_key)
PARTITION BY RANGE(date_key) (
    PARTITION p202401 VALUES [20240101, 20240201),
    PARTITION p202402 VALUES [20240201, 20240301)
)
DISTRIBUTED BY HASH(region_key) BUCKETS 16
PROPERTIES (
    "replication_num" = "3",
    "storage_medium" = "SSD"
);
```

### PostgreSQL

```sql
CREATE SCHEMA IF NOT EXISTS dwd;

CREATE TABLE IF NOT EXISTS dwd.dwd_sales_order (
    order_id         BIGINT,
    user_key         BIGINT,
    product_key      BIGINT,
    date_key         INTEGER,
    order_amount     NUMERIC(18,2),
    discount_amount  NUMERIC(18,2),
    pay_amount       NUMERIC(18,2),
    item_count       INTEGER,
    create_time      TIMESTAMP,
    update_time      TIMESTAMP,
    etl_time         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, date_key)
)
PARTITION BY RANGE (date_key);

-- 创建分区
CREATE TABLE dwd.dwd_sales_order_202401 PARTITION OF dwd.dwd_sales_order
FOR VALUES FROM (20240101) TO (20240201);
```

---

## 命名规范校验规则

| 规则 | 校验逻辑 |
|------|----------|
| 表名小写 + 下划线 | 正则 `^[a-z][a-z0-9_]*$` |
| 表名前缀 | 必须是 `ods` / `dwd` / `dws` / `ads` / `dim` / `tmp` |
| 字段名小写 + 下划线 | 正则 `^[a-z][a-z0-9_]*$` |
| 字段不能与关键字冲突 | 检查保留字列表（`order`、`group`、`user` 等）|
| 主键字段 | 必须是 `*_id` 或 `*_key` 结尾 |

---

## 分区策略选择

| 场景 | 推荐分区 | 理由 |
|------|----------|------|
| 交易/订单类（按日期）| `dt` 字符串 | T+1 增量 |
| 日志类（按小时）| `dt + hr` | 实时性高 |
| 维表（小、变化少）| 不分区 | 全量一次更新 |
| 大维表（用户/商品）| 按 `dt` 拉链分区 | 保留历史 |
| ADS 报表类 | 按 `dt` | 与业务时间一致 |

> **分区字段推荐使用 STRING 类型**（`dt='2024-01-15'`），避免 INT 转换问题。

---

## 存储格式对比

| 格式 | 压缩比 | 查询性能 | 列式 | 适用 |
|------|--------|----------|------|------|
| **ORC** | 高 | 优 | ✓ | Hive 首选 |
| **Parquet** | 高 | 优 | ✓ | Spark 首选 |
| **TextFile** | 低 | 差 | ✗ | 临时表 |
| **AVRO** | 中 | 中 | ✗ | Schema Evolution |
| **SequenceFile** | 中 | 差 | ✗ | 已过时 |

> **推荐**：Hive 用 ORC，Spark 用 Parquet。

---

## 压缩算法对比

| 算法 | 压缩比 | CPU 消耗 | 适用 |
|------|--------|----------|------|
| **Snappy** | 中 | 低 | 默认推荐（性能均衡）|
| **GZIP** | 高 | 高 | 冷数据 |
| **ZSTD** | 高 | 中 | 新一代推荐 |
| **LZ4** | 低 | 极低 | 实时数据 |
| **None** | 无 | 无 | 调试用 |

> **推荐**：热数据 Snappy，冷数据 ZSTD/GZIP。

---

## 完整执行脚本结构

```sql
-- ============================================
-- 数仓 DDL 完整脚本
-- 数据库：{database_name}
-- 引擎：{target_engine}
-- 生成时间：{timestamp}
-- 责任人：{owner}
-- ============================================

-- 1. 建库
CREATE DATABASE IF NOT EXISTS {database_name}
COMMENT '{comment}';

-- 2. 使用库
USE {database_name};

-- 3. 建表（按层顺序）
-- 3.1 ODS 层
CREATE TABLE IF NOT EXISTS ods_crm_order (...);
CREATE TABLE IF NOT EXISTS ods_crm_customer (...);

-- 3.2 DWD 层
CREATE TABLE IF NOT EXISTS dwd_sales_order (...);
CREATE TABLE IF NOT EXISTS dwd_user_profile (...);

-- 3.3 DWS 层
CREATE TABLE IF NOT EXISTS dws_sales_user_d (...);
CREATE TABLE IF NOT EXISTS dws_sales_product_d (...);

-- 3.4 ADS 层
CREATE TABLE IF NOT EXISTS ads_sales_dashboard (...);

-- 3.5 DIM 层
CREATE TABLE IF NOT EXISTS dim_user (...);
CREATE TABLE IF NOT EXISTS dim_date (...);

-- 4. 索引（OLAP 引擎一般不需要）
-- 4.1 MySQL 索引
ALTER TABLE dws_sales_user_d ADD INDEX idx_date (date_key);
```

---

## Input Validation — 输入不足处理

### 情况 1: 未提供目标引擎
**处理**: 生成 ANSI SQL 伪 DDL + 各方言差异说明

```sql
-- ⚠️ 未指定目标引擎
-- ANSI SQL 标准 DDL：

CREATE TABLE dwd_sales_order (
    order_id BIGINT NOT NULL,
    order_amount DECIMAL(18, 2),
    -- ...
    PRIMARY KEY (order_id)
);

-- 引擎适配提示:
-- Hive: 改为 STORED AS ORC + PARTITIONED BY (dt STRING)
-- MySQL: 添加 ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
-- ClickHouse: 改用 ENGINE = MergeTree() + ORDER BY
```

### 情况 2: 未提供维度模型
**处理**: 提示先使用 gen-dimension-model

```markdown
⚠️ 缺少维度模型（LDM）输入。

请先使用 `gen-dimension-model` skill 完成：
1. 主题域划分
2. 事实表/维度表定义
3. 字段清单

然后将 LDM 作为本 skill 的输入。
```

### 情况 3: 未提供字段类型
**处理**: 标注「待补充」+ 推荐类型

```sql
CREATE TABLE dwd_xxx (
    field_1 【待补充类型】 COMMENT '业务主键',
    -- 推荐类型: BIGINT / STRING / DECIMAL
);
```

### 情况 4: 未提供分区策略
**处理**: 标注「需根据数据量决定」

```sql
-- ⚠️ 未指定分区策略
-- 推荐方案：
-- 1. 交易类表：按 dt 字符串分区
-- 2. 维表：不分区或按 dt 拉链
-- 3. 实时表：按 dt + hr
```

---

## 禁止编造

- ❌ 表名（必须来自 LDM）
- ❌ 字段名（必须来自 LDM）
- ❌ 字段类型（必须用户提供或基于 LDM）
- ❌ 分区字段（必须用户确认）
- ❌ 索引（需基于查询场景）
- ❌ 注释内容（"用户ID"等业务描述）

---

## 关键规范

### 字段类型映射

| 业务类型 | Hive | MySQL | ClickHouse | Doris |
|----------|------|-------|------------|-------|
| 业务主键 | BIGINT | BIGINT | Int64 | BIGINT |
| 名称 | STRING | VARCHAR(255) | String | VARCHAR |
| 金额 | DECIMAL(18,2) | DECIMAL(18,2) | Decimal(18,2) | DECIMAL(18,2) |
| 数量 | INT | INT | Int32 | INT |
| 时间戳 | TIMESTAMP | DATETIME | DateTime | DATETIME |
| 日期 | DATE | DATE | Date | DATE |
| 标志 | STRING (Y/N) | TINYINT | UInt8 | TINYINT |
| 文本(长) | STRING | TEXT | String | STRING |

### 主键设计规范

| 表类型 | 主键策略 |
|--------|----------|
| ODS 表 | 无主键（保留原始数据）|
| DWD 事实表 | 业务主键 + 分区键 |
| DWD 维表 | 业务主键 + 分区键 |
| DWS 汇总表 | 维度键 + 时间键 |
| ADS 应用表 | 自增 ID 或业务主键 |
| DIM 维表 | 代理键（自增/Hash）|

### 必须添加的审计字段

```sql
etl_time       TIMESTAMP COMMENT 'ETL 处理时间',
etl_batch_id   STRING    COMMENT 'ETL 批次号',
source_system  STRING    COMMENT '来源系统',
```

---

## 示例对话

```
用户: "生成 dwd_sales_order 的 DDL，Hive 引擎"
助手: "我需要以下信息：

必需：
1. 字段清单（字段名 + 类型 + 注释）
2. 数据库名
3. 分区字段（推荐 dt）

可选（推荐提供）：
4. 存储格式（推荐 ORC）
5. 压缩方式（推荐 SNAPPY）
6. 生命周期
"
```

```
用户: "字段：order_id BIGINT, user_key BIGINT, order_amount DECIMAL(18,2)，分区 dt，ORC+SNAPPY"
助手: "正在生成 DDL 脚本..."
```

---

## 关联 Skill

- **gen-dimension-model** — 前置：提供 LDM
- **gen-etl-sql** — 后置：基于本 DDL 生成 ETL SQL
- **gen-etl-workflow** — 后置：基于本 DDL 生成调度依赖

---


## 日志机制

> 📋 详细规范见 [`LOGGING-CONVENTION.md`](data-pipeline/projects/light-dw-toolkit/LOGGING-CONVENTION.md)

本 skill 执行时遵循统一日志机制 v1.2：

### 日志路径查找

```yaml
1. 读取 project_config.yaml 中的 logging 节:
   - skill_execution_log: 所有 skill 执行的统一入口
   - error_log: 错误日志
2. 若 project_config.yaml 不存在 → 使用默认 ./logs/ 目录
3. 优先级: project_config > 环境变量 DW_PROJECT_CONFIG > 默认
```

### 必须记录的事件

| # | 事件 | 何时 | 字段 |
|---|------|------|------|
| 1 | **START** | skill 启动时 | 时间戳、skill 名、项目名、关键输入参数 |
| 2 | **PROGRESS** | 每完成 10% 进度 | 阶段描述、累计进度 |
| 3 | **END** | skill 主体逻辑完成 | 完成时间、耗时、输出物清单 |
| 4 | **REPORT** | END 之后立即 | 成功/部分/失败、警告数、错误数 |
| 5 | **ERROR** | 任何失败（写入 error.log） | 错误码（E0xx-E9xx）、错误消息、上下文 |

### 任务完成报告

完成后输出：

```markdown
## 任务完成报告 — {skill_name}

| 项目 | 值 |
|------|-----|
| 项目名 | {project.name} |
| Skill | {skill_name} v{version} |
| 启动时间 | {start_time ISO8601} |
| 完成时间 | {end_time ISO8601} |
| 耗时 | {duration_seconds} 秒 |
| 结果 | ✅ 成功 / ⚠️ 部分成功 / ❌ 失败 |
| 警告 | {warning_count} |
| 错误 | {error_count} |
```

### 与其他 skill 的日志协同

- 读取 `project_config.yaml` 的 `logging.skill_execution_log` 作为本 skill 的主日志
- 失败时同时写 `error.log`（与所有 skill 共享）
- ETL 类 skill 还会写 `etl_runtime.log`；质量类写 `quality_check.log`；清洗类写 `cleaning_audit.log`
- 如适用，将执行状态写回 `project_config.yaml` 的 `etl_status.tables`

---


## 验证清单

- [ ] 所有表名前缀符合规范
- [ ] 所有字段名符合命名规范
- [ ] 字段类型与目标引擎兼容
- [ ] 分区策略已应用
- [ ] 存储格式与压缩已配置
- [ ] 主键/唯一键已声明
- [ ] 注释已添加（表 + 字段）
- [ ] 审计字段已包含
- [ ] 引擎方言语法正确
- [ ] 脚本可一次性执行
- [ ] 含 IF NOT EXISTS 保护
- [ ] **layer_architecture 参数已应用（4 层 / 3 层 / custom）**
- [ ] **若为 3 层架构，DWD 层未生成**
- [ ] **上游契约字段已应用（metrics_list / table_structures / data_quality_metrics）**

---

## 附录 A：分层架构详解

### A.1 标准 4 层架构（默认）

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│   ODS   │ →  │   DWD   │ →  │   DWS   │ →  │   ADS   │
│ 源数据层│    │ 明细层  │    │ 汇总层  │    │ 应用层  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                  ↑
              ┌─────────┐
              │   DIM   │
              │ 公共维表│
              └─────────┘
```

**层级职责**：

| 层级 | 命名 | 职责 | 范式 | 分区 |
|------|------|------|------|------|
| **ODS** | `ods_{系统}_{表}` | 源数据原始镜像 | 与源一致 | dt |
| **DWD** | `dwd_{主题域}_{业务过程}` | 清洗、转换、标准化 | 3NF / 范式化 | dt |
| **DWS** | `dws_{主题域}_{维度}_{粒度}` | 轻度/高度汇总 | 维度建模 | dt |
| **ADS** | `ads_{应用名}` | 应用层报表、宽表 | 维度建模 / 宽表 | dt |
| **DIM** | `dim_{维度名}` | 公共维表 | SCD 策略 | dt（拉链）|

### A.2 精简 3 层架构

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│   ODS   │ →  │   DWS   │ →  │   ADS   │
│ 源数据层│    │ 整合层  │    │ 应用层  │
└─────────┘    └─────────┘    └─────────┘
                  ↑
              ┌─────────┐
              │   DIM   │
              │ 公共维表│
              └─────────┘
```

**层级职责**：

| 层级 | 命名 | 职责 | 说明 |
|------|------|------|------|
| **ODS** | `ods_{系统}_{表}` | 源数据原始镜像 | 同 4 层 |
| **DWS** | `dws_{主题域}_{业务过程}_{粒度}` | 清洗+汇总一体化 | 承担 4 层中 DWD + DWS 的职责 |
| **ADS** | `ads_{应用名}` | 应用层报表 | 同 4 层 |
| **DIM** | `dim_{维度名}` | 公共维表 | 同 4 层 |

> ⚠️ **3 层架构风险**：DWS 层承担清洗+汇总，违反"单一职责"，数据追溯困难。建议**仅在 MVP 或数据量 < 1TB 的小型数仓**使用。

### A.3 自定义架构（custom）

当 `layer_architecture=custom` 时，必须提供 `layer_list`：

```yaml
layer_architecture: custom
layer_list: ["ODS", "DWD", "DWS", "ADS", "DMS"]  # DMS = Data Mart Service
```

> 注意：`DIM` 公共维表始终生成，不在 `layer_list` 控制范围内。

### A.4 架构选型决策树

```
是否需要明细层的 3NF 范式化？
├── 是 → standard_4layer
│         适用：金融/电信/医疗等强审计场景
│
└── 否 → 数据量是否 > 1TB？
        ├── 是 → standard_4layer
        │        适用：大型企业数仓
        │
        └── 否 → 交付周期 < 3 个月？
                ├── 是 → simplified_3layer
                │        适用：MVP/快速验证
                │
                └── 否 → simplified_3layer
                         适用：中型企业 BI 项目
```

---

## 附录 B：上游契约应用示例

### B.1 接收 gen-metrics-dictionary 输出（→ ADS 层）

```yaml
# 来自 gen-metrics-dictionary
metrics_list:
  - code: MET_SALES_001
    name: 销售额
    sql_formula: "SUM(order_amount) WHERE status='paid'"
    data_type: DECIMAL(18,2)
    unit: 元
```

↓ 生成的 ADS 层 DDL：

```sql
CREATE TABLE ads_sales_dashboard (
    date_key       INT           NOT NULL  COMMENT '日期键',
    region_key     INT           NOT NULL  COMMENT '地区键',
    -- 来自 MET_SALES_001 指标
    sales_amt      DECIMAL(18,2) NOT NULL  DEFAULT 0.00 
                   COMMENT '销售额(元) | MET_SALES_001 | SUM(order_amount) WHERE status=''paid''',
    pay_amount     DECIMAL(18,2) NOT NULL  DEFAULT 0.00 
                   COMMENT '实付金额(元) | MET_SALES_002',
    -- 审计字段
    etl_time       TIMESTAMP     NOT NULL  DEFAULT CURRENT_TIMESTAMP 
                   COMMENT 'ETL 处理时间'
);
```

### B.2 接收 gen-source-data-dict 输出（→ ODS 层）

```yaml
# 来自 gen-source-data-dict
table_structures:
  ods_crm_order:
    fields:
      - {name: order_id,    type: VARCHAR, length: 32,  pk: true,  nullable: false}
      - {name: order_amt,   type: DECIMAL, precision: 18, scale: 2, nullable: true}

code_tables:
  ods_crm_order.order_status:
    PAID: 已支付
    PENDING: 待支付
```

↓ 生成的 ODS 层 DDL：

```sql
CREATE TABLE ods_crm_order (
    order_id      VARCHAR(32)   NOT NULL  COMMENT '订单号（业务主键）',
    order_amt     DECIMAL(18,2) NULL      COMMENT '订单金额（含税）',
    order_status  VARCHAR(16)   NOT NULL  COMMENT '订单状态（PAID:已支付/PENDING:待支付/...）',
    -- 审计字段
    etl_time      TIMESTAMP     NOT NULL  DEFAULT CURRENT_TIMESTAMP
)
COMMENT 'CRM 订单源表镜像'
PARTITIONED BY (dt STRING COMMENT '数据日期分区')
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');
```

### B.3 接收 gen-data-quality-report 输出（→ ODS/DWD 约束）

```yaml
# 来自 gen-data-quality-report
data_quality_metrics:
  ods_crm_order.order_amt:
    null_rate: 0.01  # 1% NULL 率
    effective_rule: ">= 0 AND <= 999999"
    completeness_status: good
  ods_crm_order.order_id:
    null_rate: 0.0
    uniqueness_rate: 1.0
```

↓ 生成的 DDL 增加约束：

```sql
CREATE TABLE ods_crm_order (
    order_id  VARCHAR(32) NOT NULL,
    order_amt DECIMAL(18,2) NULL
        CHECK (order_amt IS NULL OR (order_amt >= 0 AND order_amt <= 999999)),
    -- 唯一键
    UNIQUE KEY uk_order (order_id)
);
```

> 注：Hive 不支持 CHECK 约束，会转换为字段注释说明。
