---
name: gen-sit-scripts
description: |
  生成 SIT（系统集成测试）脚本和方案 — 覆盖数据准确性、模块集成、流程稳定性、性能压测。

  触发条件：用户提到「SIT」「集成测试」「集成测试用例」「系统集成测试」「数据一致性」「性能压测」时触发。

  适用阶段：Phase 13 系统测试

  绑定模板：
  - templates/15-sit-tests.yaml

  输入不足处理：
  - 若未提供测试环境，标注「待配置」
  - 若未提供性能基线，使用行业默认（响应 < 3s，并发 < 50）
  - 严禁编造性能数据

  上游依赖（契约式输入）：
  - gen-etl-mapping → dependency_graph：跨层对账的关联关系
  - gen-etl-workflow → dag_file：SIT 流程稳定性测试的入口
  - gen-etl-unit-tests → unit_test_sql：模块级测试结果
  - gen-ddl-scripts → ddl_scripts：所有层表结构
  - gen-data-cleaning-rules → cleaning_rules_yaml（v1.2 新增）：验证拒绝数据是否落入 dw_reject_records
version: 1.2.0
category: integration-testing
template_bound:
  - "templates/15-sit-tests.yaml"
related_skills:
  - gen-test-cases
  - gen-etl-unit-tests
  - gen-etl-workflow
  - gen-etl-mapping
  - gen-ddl-scripts
  - gen-data-cleaning-rules
---

# 生成 SIT 系统集成测试 (SIT Test Generator)

## 触发词

`SIT`, `集成测试`, `系统集成测试`, `数据一致性`, `性能压测`, `stability test`, `integration test`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 15-sit-tests.yaml | `templates/15-sit-tests.yaml` | 参考/规范 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `test_scope` | list | 测试范围（覆盖哪些表、流程）|
| `data_cycle_days` | int | 数据周期（默认 7 天）|

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `test_env` | dict | 测试环境配置 |
| `metrics_to_verify` | list | 待验证指标（P0 指标）|
| `performance_baseline` | dict | 性能基线（响应时间、并发数）|
| `defect_severity_rules` | dict | 缺陷严重程度规则 |

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `sit_test_plan` | Markdown | SIT 测试方案 |
| `sit_test_cases` | Markdown | SIT 测试用例集 |
| `data_comparison_sql` | SQL | 数据比对脚本 |
| `performance_test_script` | Python/SQL | 性能压测脚本 |
| `test_report_template` | Markdown | 测试报告模板 |

---

## SIT 测试 4 大类

### 1. 数据准确性测试

#### 1.1 源系统 vs 数仓对账

```sql
-- 核心指标逐个核对
-- 测试方法：选取 3 个完整周期的数据，对比源端与数仓汇总值

-- 示例：销售额
SELECT 
    'sales_accuracy' AS test_name,
    'source' AS system,
    SUM(order_amount) AS total_amt,
    NULL AS dw_total
FROM source_db.orders
WHERE dt BETWEEN DATE_SUB('${bizdate}', 7) AND '${bizdate}'
UNION ALL
SELECT 
    'sales_accuracy',
    'dw',
    NULL,
    SUM(sale_amt)
FROM dws_sales_summary
WHERE dt BETWEEN DATE_SUB('${bizdate}', 7) AND '${bizdate}';
```

#### 1.2 多周期数据校验

```sql
-- 测试 7 个连续日期，确保无周期性 bug
WITH daily_summary AS (
    SELECT 
        dt,
        SUM(sale_amt) AS total_amt
    FROM dws_sales_summary
    WHERE dt BETWEEN DATE_SUB('${bizdate}', 7) AND '${bizdate}'
    GROUP BY dt
)
SELECT 
    dt,
    total_amt,
    LAG(total_amt) OVER (ORDER BY dt) AS prev_day_amt,
    total_amt - LAG(total_amt) OVER (ORDER BY dt) AS diff
FROM daily_summary
ORDER BY dt;
```

### 2. 模块集成测试

#### 2.1 跨层数据流转

```sql
-- 验证 ODS → DWD → DWS → ADS 的数据流转
-- 1. ODS 行数
SELECT 'ods_row_count' AS layer, COUNT(*) AS cnt FROM ods_orders WHERE dt = '${bizdate}'
UNION ALL
-- 2. DWD 行数
SELECT 'dwd_row_count', COUNT(*) FROM dwd_fact_sales WHERE dt = '${bizdate}'
UNION ALL
-- 3. DWS 行数
SELECT 'dws_row_count', COUNT(*) FROM dws_user_order_1d WHERE dt = '${bizdate}'
UNION ALL
-- 4. ADS 行数
SELECT 'ads_row_count', COUNT(*) FROM ads_sales_report_daily WHERE dt = '${bizdate}';
```

#### 2.2 维度覆盖测试

```sql
-- 验证维度表的覆盖率
SELECT 
    dwd.dim_field,
    COUNT(*) AS total_facts,
    COUNT(DISTINCT dwd.dim_field) AS distinct_dims,
    COUNT(dim.dim_key) AS matched_dims,
    COUNT(DISTINCT dim.dim_key) AS total_dims,
    COUNT(*) - COUNT(dim.dim_key) AS orphan_facts
FROM dwd_fact_sales dwd
LEFT JOIN dwd_dim_product dim ON dwd.dim_field = dim.dim_key
WHERE dwd.dt = '${bizdate}'
GROUP BY dwd.dim_field;
```

### 3. 流程稳定性测试

#### 3.1 长时间运行测试

```bash
#!/bin/bash
# stability_test.sh
# 持续运行 ETL 流程 24 小时，观察稳定性

END_TIME=$(date -d '+24 hours' +%s)
COUNT=0
FAIL_COUNT=0

while [ $(date +%s) -lt $END_TIME ]; do
    COUNT=$((COUNT+1))
    echo "[$(date)] Run #$COUNT"
    
    # 执行 ETL 流程
    hive -f scripts/dwd_transform.sql -hivevar bizdate=$(date -d 'yesterday' +%Y-%m-%d) 2>&1
    if [ $? -ne 0 ]; then
        FAIL_COUNT=$((FAIL_COUNT+1))
        echo "FAIL: Run #$COUNT" >> /var/log/etl_stability.log
    fi
    
    # 间隔 1 小时
    sleep 3600
done

echo "Total runs: $COUNT, Failures: $FAIL_COUNT"
echo "Success rate: $(echo "scale=2; ($COUNT-$FAIL_COUNT)*100/$COUNT" | bc)%"
```

#### 3.2 异常恢复测试

```sql
-- 模拟 ETL 失败场景，验证重试和恢复机制
-- 测试 1: 模拟源系统不可用
-- 测试 2: 模拟中间表被删除
-- 测试 3: 模拟网络中断
```

### 4. 性能压测

#### 4.1 压测脚本（JMeter/Python）

```python
"""
performance_test.py
ADS 表查询性能压测
"""
import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor

ADS_QUERY_API = "http://bi.example.com/api/query"

QUERIES = [
    {"sql": "SELECT * FROM ads_sales_report_daily WHERE dt = '2026-06-22' LIMIT 100", "weight": 30},
    {"sql": "SELECT region_id, SUM(sale_amt) FROM ads_sales_report_daily WHERE dt BETWEEN '2026-06-15' AND '2026-06-22' GROUP BY region_id", "weight": 40},
    {"sql": "SELECT product_id, COUNT(DISTINCT user_id) FROM ads_user_product_matrix WHERE dt = '2026-06-22' GROUP BY product_id LIMIT 50", "weight": 20},
    {"sql": "SELECT * FROM ads_sales_report_daily WHERE region_id IN (1, 2, 3) AND dt >= '2026-06-01' ORDER BY sale_amt DESC LIMIT 1000", "weight": 10},
]

def run_query(query):
    start = time.time()
    try:
        r = requests.post(ADS_QUERY_API, json={"sql": query["sql"]}, timeout=10)
        elapsed = time.time() - start
        return {
            "status": "success" if r.status_code == 200 else "fail",
            "elapsed": elapsed,
            "rows": len(r.json().get("data", [])) if r.status_code == 200 else 0
        }
    except Exception as e:
        return {"status": "error", "elapsed": time.time() - start, "error": str(e)}

def main():
    CONCURRENT_USERS = 50
    DURATION_SEC = 300  # 5 分钟
    start_time = time.time()
    
    results = []
    with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        while time.time() - start_time < DURATION_SEC:
            query = random.choices(QUERIES, weights=[q["weight"] for q in QUERIES])[0]
            future = executor.submit(run_query, query["sql"])
            results.append(future)
            time.sleep(0.1)
    
    # 统计
    completed = [f.result() for f in results]
    success_count = sum(1 for r in completed if r["status"] == "success")
    elapsed_list = [r["elapsed"] for r in completed if r["status"] == "success"]
    
    print(f"Total requests: {len(completed)}")
    print(f"Success: {success_count} ({success_count*100/len(completed):.1f}%)")
    print(f"Avg response: {sum(elapsed_list)/len(elapsed_list)*1000:.0f}ms")
    print(f"P95 response: {sorted(elapsed_list)[int(len(elapsed_list)*0.95)]*1000:.0f}ms")
    print(f"P99 response: {sorted(elapsed_list)[int(len(elapsed_list)*0.99)]*1000:.0f}ms")
```

---

## SIT 测试方案

```markdown
# SIT 测试方案 — {project_name}

## 1. 测试目标
- 验证各层数据流转正确性
- 验证端到端业务流程稳定性
- 验证系统性能满足要求
- 验证数据与源系统一致

## 2. 测试范围
- 表清单: {test_scope}
- 测试周期: {data_cycle_days} 天
- 业务场景: ...

## 3. 测试环境
- 测试数据库: {test_env.db}
- 测试集群: {test_env.cluster}
- 源系统对接: {test_env.source}

## 4. 测试策略

| 测试类型 | 方法 | 工具 | 责任人 | 周期 |
|----------|------|------|--------|------|
| 数据准确性 | 源 vs 数仓对账 | SQL | QA | 3 天 |
| 模块集成 | 跨层流转测试 | SQL | QA | 2 天 |
| 流程稳定性 | 长时间运行 | Shell | QA | 1 天 |
| 性能压测 | 50 并发 5 分钟 | Python | QA | 1 天 |

## 5. 准入条件
- [ ] 单元测试全部通过
- [ ] 测试环境已部署
- [ ] 测试数据已准备

## 6. 准出条件
- [ ] 所有 P0 测试通过
- [ ] 性能指标达标
- [ ] 缺陷修复率 100%
```

---

## Input Validation — 输入不足处理

### 情况 1: 未提供性能基线
**处理**: 使用行业默认

```markdown
> ⚠️ 未提供性能基线，使用默认值：
> - 响应时间: < 3 秒
> - 并发数: 50
> - 数据量级: 1-10 TB
```

### 情况 2: 未提供测试环境
**处理**: 标注「待配置」

```markdown
- 测试数据库: 【待配置】
- 测试集群: 【待配置】
```

---

## 禁止编造

- ❌ 性能数据（响应时间、QPS）
- ❌ 缺陷严重程度规则
- ❌ 业务指标对账结果

---

## 关联 Skill

- **gen-test-cases** - 单元测试用例
- **gen-etl-unit-tests** - ETL 单元测试
- **gen-etl-workflow** - 调度 DAG

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

- [ ] 测试覆盖所有 P0 指标
- [ ] 数据周期 ≥ 3 天
- [ ] 性能压测有明确基线
- [ ] 缺陷跟踪机制已建立
- [ ] 准入/准出条件清晰
