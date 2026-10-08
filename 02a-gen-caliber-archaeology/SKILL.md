---
name: gen-caliber-archaeology
description: |
  口径考古 — 把存量 BI / 报表资产（.twb / .pbix / 帆软 / Superset / 存储过程 / ETL SQL / Excel 模板）解析成结构化口径清单，识别「同名不同口径」的冲突并附证据链，产出可直接喂给 gen-requirements-spec 的 report_list / metrics_list / 歧义清单。

  定位：gen-requirements-spec 的**解析层**。适用于「存量改造」场景（客户已有报表体系，口径散落在各处）；新建数仓的绿地场景可跳过本 skill。

  触发条件：用户提到「口径考古」「口径解析」「存量口径提取」「报表口径反推」「现有报表盘点」「口径冲突排查」「老系统口径梳理」「口径对不齐」时触发。

  适用阶段：Phase 2 现状调研（gen-requirements-spec 的上游）

  绑定模板：
  - templates/02a-caliber-archaeology.yaml

  输入不足处理：
  - 若未提供任何可解析资产 → 输出资产清点框架 + 采集清单
  - 若资产不可解析（截图 / 扫描件 / 加密文件）→ 标注「需人工转录」，不猜内容
  - 严禁编造口径：所有表达式必须逐字来自原始资产，并附资产路径 + 定位
version: 1.0.0
category: requirements
template_bound:
  - "templates/02a-caliber-archaeology.yaml"
related_skills:
  - gen-requirements-spec
  - gen-metrics-dictionary
  - gen-source-data-dict
---

# 口径考古 (Caliber Archaeology)

## 触发词

`口径考古`, `口径解析`, `存量口径提取`, `报表口径反推`, `现有报表盘点`, `口径冲突排查`, `老系统口径梳理`, `口径对不齐`, `caliber archaeology`, `legacy metric extract`

---

## 模板绑定

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 02a-caliber-archaeology.yaml | `templates/02a-caliber-archaeology.yaml` | 输出格式规范 |

---

## 定位与边界（重要）

本 skill **只做发现，不做裁决**。它是 gen-requirements-spec 的上游解析层，不是它的替代品。

| 层 | Skill | 职责 | 明确不做 |
|---|---|---|---|
| **解析层** | **02a-gen-caliber-archaeology（本 skill）** | 从存量资产**发现**口径与冲突，产出草案 + 证据链 | ❌ 不裁决最终口径 |
| 需求层 | 03-gen-requirements-spec | 把草案**成文**为 BRS | ❌ 不解析原始资产 |
| 指标层 | 04-gen-metrics-dictionary | 把已裁决口径**固化**成指标字典（编码 / 变更日志） | ❌ 不发现冲突 |
| 结构层 | 06-gen-source-data-dict | 字段级结构支撑；**反向**回喂冲突置信度 | ❌ 不解析 BI 报表 |
| — | 业务 Owner（人工） | **裁决**冲突 | — |

**数据流**：

```
原始资料（.twb / .pbix / SQL / Excel / 帆软）
        │
        ▼
  02a 解析层  ──▶  口径草案 + 歧义清单 + 证据链
        │
        ▼
  03 需求层（成文 BRS）──▶ 04 指标层（固化字典）
        ▲
        │ 字段级结构 + 一致性证据
  06 结构层
```

**与 03 的字段级对应**（本 skill 的输出直接填 03 的输入槽）：

| 本 skill 产出 | 消费方 | 对应字段 |
|---|---|---|
| 报表清单 + 报表结构 | 03-gen-requirements-spec | `report_list`（必需）|
| 指标候选 + 归一表达式 | 03 / 04 | `metrics_list`（含计算公式）|
| 歧义清单 + 证据链 | 03 | `outstanding_items` |
| 数据源归属 | 03 | `data_sources` |
| 字段级口径落点 | 06-gen-source-data-dict | 表结构 / 数据特性（交叉验证）|

**反向依赖**：06 的「数据特性 / 一致性」结果可回喂本 skill，提升冲突判定置信度。例如 06 发现 `order_amount` 存在空值 → 该口径的「不含税」判定需要复核。

---

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_name` | string | 项目名称 |
| `asset_root` | path / list | 存量资产根目录或文件清单 |
| `subject_scope` | list | 本次考古的主题域范围（试点模式建议只给一个）|

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `existing_metric_doc` | path | 已有指标文档 / 口径表（作为交叉验证，不作为真值）|
| `source_data_dict` | path | 已有数据字典（来自 06，提供字段级佐证）|
| `owner_mapping` | dict | 报表 / 资产 → 业务责任人 |
| `desensitize_rules` | list | 证据链脱敏规则（客户名、金额、手机号等）|

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `asset_inventory` | yaml | 资产清点结果（含可解析性判定）|
| `metric_candidates` | yaml | 口径候选（未去重，保留全部出现位置）|
| `normalized_metrics` | yaml | 归一化后的指标口径 |
| `conflicts` | yaml | 口径冲突清单（L1/L2/L3 分级 + 证据链）|
| `report_list` | list | 直接喂 03 的报表清单 |
| `data_sources` | list | 直接喂 03 的数据源清单 |
| `outstanding_items` | list | 直接喂 03 的待确认项（= 冲突汇总视图）|
| `handover` | dict | 移交记录（试点模式：客户团队独立完成的第二主题草案）|

输出落位：`${project_root}/03_requirements/archaeology/`（复用 `directories.requirements`，不新增目录）

---

## 自动执行步骤

### Step 1 — 资产清点 (Inventory)

1. 扫描 `asset_root`，按扩展名 + 内容特征登记每个资产
2. 判定可解析性：不可解析的（截图 / 扫描件 / 加密文件）标 `parseable: false` 并写明 `skip_reason`
3. 标注每个资产的来源系统与责任人（若 `owner_mapping` 提供）
4. **产出**：`asset_inventory`

### Step 2 — 口径抽取 (Extract)

按资产类型分派解析器，统一抽取四元组 `{metric_name, expression, dimensions, time_granularity}`，并记录定位。

| 资产类型 | 扩展名 | 解析方式 | 可提取内容 |
|---|---|---|---|
| Tableau 工作簿 | `.twb` / `.twbx` | XML（`.twbx` 先解压取 `.twb`）| 计算字段、数据源、工作表引用 |
| Power BI | `.pbix` | 解压取 `DataModelSchema`(JSON) / 报表 JSON | 度量值 DAX、列、关系 |
| 帆软报表 | `.cpt` / `.frm` | XML | 数据集 SQL、单元格公式 |
| Superset | dashboard / chart 导出 JSON | JSON | SQL 表达式、指标定义 |
| SQL 资产 | `.sql` / 存储过程导出 | SQL AST 解析 | `SELECT` 列别名 → 表达式 |
| 视图 / 物化视图 | `.sql` / `information_schema` 导出 | SQL AST 解析 | 视图定义 |
| Excel | `.xlsx` / `.xlsm` | 公式解析 | 单元格公式、表头、透视定义 |
| 已有文档 | `.md` / `.docx` / `.xlsx` | 文本 / 表格解析 | 指标名 + 定义文本（**仅作交叉验证**）|

- 定位格式：SQL 用「文件路径 + 行号」，报表定义用「文件路径 + 节点路径」，Excel 用「文件路径 + Sheet!单元格」
- **产出**：`metric_candidates`（未去重，同一指标在多张报表出现就保留多条）

### Step 3 — 归一化 (Normalize)

1. **表达式归一**：统一大小写与空白 → 统一表别名 → 等价函数映射（`IFNULL` / `NVL` → `COALESCE`，`ISNULL` → `IS NULL`）→ 去除无意义的 `CAST` 与冗余括号
2. **指标名归一**：中文名 / 英文名 / 缩写 / 别名归并到 `canonical_name`。**归并是候选，不是断言** —— 存疑的标 `merge_confidence: low` 交人工确认
3. **产出**：`normalized_metrics`

### Step 4 — 冲突判定 (Conflict Detection)

1. 按 `canonical_name` 分组 → 组内按归一表达式去重 → 得到「口径簇」
2. 簇内变体数 ≥ 2 → 判定为冲突，分级：

| 级别 | 含义 | 处理 |
|---|---|---|
| **L1 语义等价** | 仅写法差异，计算结果必然相同 | 合并，**不计入冲突** |
| **L2 口径差异** | 计算结果会不同：含税/不含税、含退单/不含退单、时间口径、统计范围 | **真冲突**，标 ⚠️ 待裁决 |
| **L3 同名异义** | 名字相同但业务对象不同（如两个部门各自的"收入"）| 建议**拆分指标编码**，标 ⚠️ 待裁决 |

3. 为每个冲突生成**证据链**：列出每套变体的表达式、来源资产、定位、疑似成因
4. **产出**：`conflicts`

> ⚠️ **本步骤只判定「存在差异」，不判定「哪个对」。** 最终口径由业务 Owner 裁决，本 skill 不越界。

### Step 5 — 落位 (Emit)

1. 按 03 的输入契约输出 `report_list` / `data_sources` / `metrics_list` / `outstanding_items`
2. 写入 `${project_root}/03_requirements/archaeology/`
3. 试点模式下追加 `handover` 段：记录客户团队是否已独立完成第二个主题的口径草案（移交验收证据）

---

## 输出模板示例

```yaml
conflicts:
  - conflict_id: CF-001
    metric_name: 销售额
    canonical_name: sales_amount
    level: L2
    suspected_cause: 含税口径不一致（CRM 含税 / ERP 不含税）
    decision_owner: 【待业务方指定】
    status: ⚠️ 待裁决
    variants:
      - expression: "SUM(o.order_amount)"
        source_asset_id: A-003
        location: "sales_daily.sql:L42"
        evidence: "SUM(o.order_amount) AS 销售额"
      - expression: "SUM(f.amount_excl_tax)"
        source_asset_id: A-007
        location: "erp_revenue_view.sql:L18"
        evidence: "SUM(f.amount_excl_tax) AS 销售额"
```

---

## Input Validation — 输入不足处理

### 情况 1: 未提供任何可解析资产
**处理**: 输出资产清点框架 + 采集清单，不猜测内容

```markdown
## 资产清点

> ⚠️ 未发现可解析资产。请按以下清单采集：

| 资产类型 | 建议采集方式 | 优先级 |
|---|---|---|
| BI 报表定义 | Tableau 导出 .twb / Power BI 另存 .pbix | P0 |
| 存储过程 / 视图 | `SHOW CREATE VIEW` / 存储过程导出 | P0 |
| ETL SQL | 调度平台任务脚本导出 | P1 |
| Excel 模板 | 业务方在用的报表模板（含公式）| P1 |
```

### 情况 2: 资产不可解析
**处理**: 标 `parseable: false` + `skip_reason`，列入人工转录清单

```yaml
- asset_id: A-011
  path: "报表截图/销售日报.png"
  parseable: false
  skip_reason: "截图无法解析，需人工转录为表达式"
```

### 情况 3: 存在疑似同一指标但无法确认
**处理**: 标 `merge_confidence: low`，列入待确认项，**不擅自合并**

---

## 禁止编造清单

- ❌ 指标计算公式（必须逐字来自原始资产，附定位）
- ❌ 业务口径定义（含税/不含税、退单处理）
- ❌ 数据源归属（"来自 CRM 系统"）
- ❌ 别名归并结论（存疑的必须标 `merge_confidence: low` 交人工）
- ❌ 冲突的最终裁决（本 skill 只发现差异，不判定对错）

---

## 示例对话

```
用户: "客户有 40 多张 Tableau 报表和一堆存储过程，销售口径总对不上，帮我梳理一下"
助手: "正在启动口径考古...

需要确认：
1. 资产根目录（报表定义 + SQL 脚本所在位置）
2. 本次主题域范围（建议先只做一个主题做试点，比如「销售」）
3. 是否提供责任人映射（用于后续裁决）

我将执行：资产清点 → 口径抽取 → 归一化 → 冲突判定 → 落位
产出：口径草案 + 歧义清单（附证据链），可直接喂给 gen-requirements-spec

⚠️ 注意：我只负责找出「哪几套口径在打架」，最终用哪套由业务方裁决。"
```

---

## 关联 Skill

- **gen-requirements-spec** - 下游：本 skill 的输出直接作为其输入
- **gen-metrics-dictionary** - 下游：裁决后的口径由它固化
- **gen-source-data-dict** - 双向：字段级结构佐证，反向回喂冲突置信度
- **gen-data-quality-report** - 交叉：数据质量异常可作为口径差异的佐证

---

## 日志机制

> 📋 详细规范见 [`LOGGING-CONVENTION.md`](../LOGGING-CONVENTION.md)

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
| 1 | **START** | skill 启动时 | 时间戳、skill 名、项目名、asset_root、subject_scope |
| 2 | **PROGRESS** | 每完成 10% 进度 | 阶段描述、累计进度（清点资产数 / 抽取候选数 / 冲突数）|
| 3 | **END** | skill 主体逻辑完成 | 完成时间、耗时、输出物清单 |
| 4 | **REPORT** | END 之后立即 | 成功/部分/失败、警告数、错误数、冲突分级统计 |
| 5 | **ERROR** | 任何失败（写入 error.log） | 错误码（E0xx-E9xx）、错误消息、上下文 |

### 任务完成报告

完成后输出：

```markdown
## 任务完成报告 — gen-caliber-archaeology

| 项目 | 值 |
|------|-----|
| 项目名 | {project.name} |
| Skill | gen-caliber-archaeology v1.0.0 |
| 启动时间 | {start_time ISO8601} |
| 完成时间 | {end_time ISO8601} |
| 耗时 | {duration_seconds} 秒 |
| 结果 | ✅ 成功 / ⚠️ 部分成功 / ❌ 失败 |
| 清点资产 | {asset_count}（不可解析 {unparseable_count}）|
| 口径候选 | {candidate_count} |
| 冲突 | L2 {l2_count} / L3 {l3_count} |
| 警告 | {warning_count} |
| 错误 | {error_count} |
```

### 与其他 skill 的日志协同

- 读取 `project_config.yaml` 的 `logging.skill_execution_log` 作为本 skill 的主日志
- 失败时同时写 `error.log`（与所有 skill 共享）
- 读取 `directories.requirements` 作为输出目录

---

## 验证清单

- [ ] 资产清点覆盖 `asset_root` 全部文件，不可解析项已注明原因
- [ ] 每条口径候选都有资产路径 + 定位（可溯源）
- [ ] 别名归并存疑项已标 `merge_confidence: low`
- [ ] 冲突已分级（L1 不计入，L2/L3 已标 ⚠️ 待裁决）
- [ ] 每个冲突都有证据链（变体 + 来源 + 定位）
- [ ] 未对任何冲突给出「哪个对」的结论
- [ ] 输出已落位 `${project_root}/03_requirements/archaeology/`
- [ ] `outstanding_items` 可直接被 03-gen-requirements-spec 消费
- [ ] 证据链已按 `desensitize_rules` 脱敏
- [ ] 日志已写入 skill_execution.log 并输出任务完成报告