---
name: gen-test-cases
description: |
  生成 SIT/UAT 测试用例集 — 包含功能测试、数据准确性测试、流程稳定性测试、性能测试 4 大类，输出 Excel 测试用例模板 + Markdown 索引。

  触发条件：用户提到「测试用例」「SIT 用例」「UAT 用例」「test cases」「测试用例集」「测试矩阵」时触发。

  适用阶段：Phase 11 测试计划及设计 + Phase 13 系统测试及培训

  绑定模板：
  - 测试用例设计@BBB-CCC 103 20060823.xls
  - 测试用例.xlsx
  - BI前期调研模版 V2.0.xls（含需求活动检查清单）

  输入不足处理：
  - 若未提供功能清单，输出测试用例框架
  - 若未提供性能基线，使用行业默认（响应 < 3s，并发 < 50）
  - 若未提供业务规则，标注「待业务方确认」
  - 严禁编造测试数据

  上游依赖（契约式输入）：
  - gen-requirements-spec → functional_requirements：功能测试的来源
  - gen-etl-mapping → mapping_doc：数据准确性测试的字段依据
  - gen-etl-unit-tests → unit_test_sql：已通过的单元测试（参考）
  - gen-sit-scripts → sit_test_plan：SIT 整体测试计划

version: 1.0.0
category: testing
template_bound:
  - "templates/11-test-cases.yaml"
related_skills:
  - gen-requirements-spec
  - gen-etl-mapping
  - gen-etl-unit-tests
  - gen-sit-scripts
---

# 生成测试用例集 (Test Cases Generator)

## 触发词

`测试用例`, `SIT 用例`, `UAT 用例`, `test cases`, `测试用例集`, `测试矩阵`, `功能测试`, `验收测试`, `test scenarios`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 11-test-cases.yaml | `templates/11-test-cases.yaml` | 参考/规范 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `feature_list` | list | 功能清单（从 gen-requirements-spec 提取）|
| `test_scope` | enum | 测试范围：SIT（系统集成）/ UAT（用户验收）/ both |

### 可选输入（来自上游 skill）

| 字段 | 来源 skill | 类型 | 说明 |
|------|-----------|------|------|
| `functional_requirements` | gen-requirements-spec | dict | 功能测试的来源 |
| `mapping_doc` | gen-etl-mapping | object | 数据准确性测试的字段依据 |
| `unit_test_results` | gen-etl-unit-tests | list | 已通过的单元测试（参考）|
| `sit_test_plan` | gen-sit-scripts | object | SIT 整体测试计划 |

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `test_type` | list | 测试类型（默认 4 类全选）：function / data_accuracy / process_stability / performance |
| `priority` | list | 优先级用例：P0 / P1 / P2 |
| `test_data` | dict | 测试数据（业务方可提供）|
| `performance_baseline` | dict | 性能基线（如 `{"response_time": 3000, "concurrency": 50}`）|
| `test_environment` | dict | 测试环境（DB / 引擎 / 网络）|

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `test_cases_xlsx_structure` | dict | Excel 结构（可由 openpyxl 渲染）|
| `test_cases_md` | Markdown | 测试用例 Markdown 索引 |
| `coverage_matrix` | Markdown | 功能-用例覆盖矩阵 |
| `test_data_template` | dict | 测试数据模板 |
| `outstanding_items` | list | 待确认项 |

---

## 4 大类测试

| # | 测试类型 | 覆盖范围 | 用例数参考 | 通过标准 |
|---|----------|----------|------------|----------|
| 1 | **功能测试 (Function)** | 业务功能、UI 操作、权限 | 30-50 用例 | 所有功能 100% 通过 |
| 2 | **数据准确性测试 (Data Accuracy)** | 字段映射、聚合计算、口径 | 15-30 用例 | 与源系统 100% 一致 |
| 3 | **流程稳定性测试 (Process Stability)** | 调度、重跑、断点续传 | 5-10 用例 | 3 次重试内成功 |
| 4 | **性能测试 (Performance)** | 响应时间、并发、资源 | 5-10 用例 | 响应 < 3s，无内存泄漏 |

### 优先级划分

| 优先级 | 含义 | 数量占比 | 通过率要求 |
|--------|------|----------|------------|
| **P0** | 核心业务、阻塞流程 | ~20% | 100% 通过 |
| **P1** | 重要功能、主要场景 | ~50% | ≥ 95% 通过 |
| **P2** | 边缘场景、UI 细节 | ~30% | ≥ 90% 通过 |

---

## 自动执行步骤

1. **解析功能清单** — 从 `feature_list` 提取所有功能点
2. **覆盖矩阵构建** — 功能点 × 测试类型
3. **生成功能测试用例** — 每个功能点 2-5 个用例
4. **生成数据准确性用例** — 基于 `mapping_doc` 的关键字段
5. **生成流程稳定性用例** — 调度失败、重跑场景
6. **生成性能用例** — 基于 `performance_baseline`
7. **分配优先级** — P0/P1/P2
8. **生成测试数据模板** — 每个用例对应的输入/预期数据
9. **输出 Excel + Markdown 索引**

---

## 输出模板示例

### Markdown 格式

```markdown
# 测试用例集 v1.0 — {project_name}

> 测试范围：SIT + UAT
> 用例总数：80
> 通过率要求：P0=100%, P1≥95%, P2≥90%
> 责任人：{测试经理}

---

## 1. 用例统计

| 测试类型 | P0 | P1 | P2 | 小计 |
|----------|----|----|----|------|
| 功能测试 | 8 | 25 | 10 | 43 |
| 数据准确性 | 5 | 12 | 3 | 20 |
| 流程稳定性 | 2 | 5 | 0 | 7 |
| 性能测试 | 1 | 3 | 6 | 10 |
| **合计** | **16** | **45** | **19** | **80** |

## 2. 覆盖矩阵

| 功能模块 | 功能测试 | 数据准确性 | 流程稳定性 | 性能测试 |
|----------|----------|------------|------------|----------|
| 用户管理 | TC-001 ~ TC-005 | TC-051 ~ TC-053 | TC-071 | TC-076 |
| 订单管理 | TC-006 ~ TC-020 | TC-054 ~ TC-060 | TC-072 | TC-077 |
| 报表分析 | TC-021 ~ TC-030 | TC-061 ~ TC-065 | TC-073 | TC-078 |
| 数据查询 | TC-031 ~ TC-040 | TC-066 ~ TC-070 | TC-074 | TC-079 |
| 系统管理 | TC-041 ~ TC-043 | — | TC-075 | TC-080 |

## 3. 测试用例详情（示例）

### TC-001 用户登录-正常登录（P0）

| 字段 | 内容 |
|------|------|
| **用例编号** | TC-001 |
| **所属模块** | 用户管理 |
| **测试类型** | 功能测试 |
| **优先级** | P0 |
| **前置条件** | 测试用户 test_user_01 已存在 |
| **测试步骤** | 1. 打开登录页 2. 输入用户名 test_user_01 3. 输入正确密码 4. 点击登录 |
| **测试数据** | username=test_user_01, password=Test@123 |
| **预期结果** | 登录成功，跳转首页 |
| **通过标准** | 实际结果与预期完全一致 |
| **关联需求** | BRS-USER-001 |

### TC-051 订单表-字段映射准确性（P0）

| 字段 | 内容 |
|------|------|
| **用例编号** | TC-051 |
| **所属模块** | 数据准确性 |
| **测试类型** | 数据准确性 |
| **优先级** | P0 |
| **前置条件** | dwd_sales_order 已有当天数据 |
| **测试步骤** | 1. 查询 dwd_sales_order 中 100 条订单 2. 与源系统 ods_crm_order 逐条比对 3. 计算字段一致性 |
| **测试数据** | 100 条订单（按 order_id 抽取）|
| **预期结果** | 字段一致性 = 100%（user_key、order_amount、date_key 均正确）|
| **通过标准** | 一致性 ≥ 99.99% |
| **关联映射** | mapping_doc 中 dwd_sales_order 的 11 个字段 |
| **测试 SQL** | 见 gen-etl-unit-tests 输出的对账 SQL |

### TC-071 ETL 调度-断点续传（P1）

| 字段 | 内容 |
|------|------|
| **用例编号** | TC-071 |
| **所属模块** | 流程稳定性 |
| **测试类型** | 流程稳定性 |
| **优先级** | P1 |
| **前置条件** | DAG 已部署到 Airflow |
| **测试步骤** | 1. 手动触发 DAG 2. 在 dws_sales_user_d 任务执行到 50% 时 Kill 3. 重新触发 DAG 4. 观察是否续传 |
| **测试数据** | bizdate=2026-06-15 |
| **预期结果** | DAG 从 Kill 点继续执行，最终成功 |
| **通过标准** | 断点续传 3 次内成功，无重复数据 |
| **关联** | gen-etl-workflow 生成的 DAG |

### TC-076 订单查询-响应时间（P1）

| 字段 | 内容 |
|------|------|
| **用例编号** | TC-076 |
| **所属模块** | 性能测试 |
| **测试类型** | 性能测试 |
| **优先级** | P1 |
| **前置条件** | ADS 报表已部署，1 亿订单数据 |
| **测试步骤** | 1. 使用 JMeter 设置 50 并发 2. 持续压测 5 分钟 3. 采集 P95 响应时间 |
| **测试数据** | 并发 50，时长 300s |
| **预期结果** | P95 响应时间 < 3000ms，无错误 |
| **通过标准** | 响应 < 3s，错误率 < 0.1% |
| **性能基线** | response_time=3000, concurrency=50 |

## 4. 测试数据模板

```yaml
# TC-001 测试数据
TC-001:
  input:
    username: "test_user_01"
    password: "Test@123"
  expected:
    http_code: 200
    redirect_url: "/home"

# TC-051 测试数据
TC-051:
  input:
    sample_size: 100
    bizdate: "2026-06-15"
  expected:
    consistency_rate: 1.0
    field_match_count: 1100  # 100 条 × 11 字段
```

## 5. 待确认项

- ⚠️ TC-051 性能基线（1 亿订单下的查询响应时间）需运维确认
- ⚠️ TC-071 断点续传最大重试次数需与 ETL 架构师确认
- ⚠️ TC-076 并发数（50）是否覆盖业务峰值需业务方确认
```

### Excel 测试用例结构

```markdown
📊 test_cases.xlsx 结构：

Sheet 1: 用例主表
  列：用例编号 | 模块 | 类型 | 优先级 | 用例名称 | 前置条件 | 步骤 | 测试数据 | 预期结果 | 通过标准 | 关联需求 | 状态

Sheet 2: 覆盖矩阵
  行：功能模块 | 列：测试类型 | 值：用例数

Sheet 3: 用例统计
  列：测试类型 | P0 | P1 | P2 | 合计

Sheet 4: 测试数据
  列：用例编号 | 输入数据 | 预期数据

Sheet 5: 缺陷跟踪
  列：缺陷ID | 用例编号 | 严重程度 | 状态 | 责任人

Sheet 6: 测试报告
  列：模块 | 总用例 | 通过 | 失败 | 阻塞 | 通过率
```

---

## 4 类用例的详细生成策略

### 1. 功能测试用例

每个功能点生成 3-5 个用例：

| 场景 | 说明 |
|------|------|
| **正常流程** | 输入合法数据，验证预期输出 |
| **异常流程** | 输入非法数据，验证错误提示 |
| **边界值** | 输入最大/最小值 |
| **权限校验** | 不同角色的访问控制 |
| **数据依赖** | 上下游数据联动 |

### 2. 数据准确性用例

| 检查项 | 方法 |
|--------|------|
| **字段映射** | 抽样 N 条记录，与源系统比对 |
| **聚合计算** | 与源系统 SUM/COUNT 核对 |
| **空值处理** | NULL → 默认值的处理 |
| **枚举转换** | 代码 → 中文映射 |
| **跨表对账** | 不同层表的同字段一致性 |

### 3. 流程稳定性用例

| 场景 | 方法 |
|------|------|
| **重跑** | 失败任务自动重试 3 次 |
| **断点续传** | Kill 后能从断点继续 |
| **并发控制** | 同表并发写入不冲突 |
| **资源隔离** | 异常任务不影响其他任务 |
| **告警触发** | 失败时通知到责任人 |

### 4. 性能测试用例

| 场景 | 基线（默认）|
|------|-------------|
| **单查询响应** | < 3s |
| **并发查询** | 50 并发，P95 < 3s |
| **批量加载** | 1 亿行 < 1h |
| **内存使用** | < 8GB |
| **CPU 使用** | < 70% |

---

## Input Validation — 输入不足处理

### 情况 1: 未提供功能清单
**处理**: 输出测试用例框架

```markdown
# 测试用例框架

请提供：
1. 系统功能清单（来自 BRS）
2. 主要业务场景
3. 性能要求

否则只能生成通用模板，无法覆盖业务特定场景。
```

### 情况 2: 未提供性能基线
**处理**: 使用行业默认基线

```yaml
performance_baseline:
  response_time: 3000      # P95 < 3s
  concurrency: 50          # 默认 50 并发
  batch_load_time: 3600    # 1 亿行 < 1h
  memory: 8GB
  cpu: 70%
```

### 情况 3: 未提供测试数据
**处理**: 生成测试数据模板

```yaml
# 通用测试数据模板
test_data_template:
  user: {prefix: "test_user_", range: 100}
  date: {start: "2026-01-01", end: "2026-12-31"}
  amount: {min: 0.01, max: 99999.99}
```

### 情况 4: 未提供关联需求
**处理**: 标注「无关联」

```markdown
| 用例编号 | 关联需求 |
|----------|----------|
| TC-001 | 【无关联】 |
```

---

## 禁止编造

- ❌ 测试数据（业务方可提供）
- ❌ 业务规则
- ❌ 性能基线（必须运维提供）
- ❌ 缺陷严重程度
- ❌ 用例通过率

---

## 关键规范

### 用例编号规范

```
TC-{测试类型编号}{顺序号}

测试类型编号：
- F: 功能测试
- D: 数据准确性
- P: 流程稳定性
- L: 性能测试（Load）

示例：
- TC-F001: 第 1 个功能测试用例
- TC-D051: 第 51 个数据准确性用例
- TC-P071: 第 71 个流程稳定性用例
- TC-L076: 第 76 个性能测试用例
```

### 优先级评估准则

| 因素 | P0 | P1 | P2 |
|------|----|----|-----|
| 业务影响 | 阻塞主流程 | 影响部分功能 | 边缘场景 |
| 使用频率 | 每日 | 每周 | 偶尔 |
| 数据准确性 | 关键财务 | 重要指标 | 辅助信息 |
| 客户要求 | 必须 | 应该 | 可以 |

---

## 示例对话

```
用户: "生成 SIT + UAT 测试用例集"
助手: "我需要以下信息：

必需：
1. 功能清单（来自 BRS）
2. 测试范围（SIT / UAT / both）

可选（推荐提供）：
3. 性能基线
4. 测试环境
5. 关联的 BRS / Mapping 文档
"
```

```
用户: "功能清单在 brs/feature-list.md，性能基线：P95 < 3s，并发 50"
助手: "正在生成测试用例集..."
```

---

## 关联 Skill

### 上游（依赖）
- **gen-requirements-spec** — 前置：提供功能清单
- **gen-etl-mapping** — 前置：提供字段映射
- **gen-etl-unit-tests** — 前置：参考已通过的单元测试

### 下游（被依赖）
- **gen-sit-scripts** — 后置：SIT 测试使用本用例集
- **gen-user-manual** — 并行：用户培训使用本用例集

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

- [ ] 所有功能点已覆盖
- [ ] 4 类测试均已生成
- [ ] P0 用例 100% 通过要求
- [ ] 覆盖矩阵已生成
- [ ] 测试数据模板已生成
- [ ] 关联到 BRS / Mapping
- [ ] 待确认项已列出
- [ ] 用例编号无重复
