---
name: gen-deploy-plan
description: |
  生成系统上线部署方案 — 部署计划、上线方案、切换流程、试运行监控、回滚预案。
  
  触发条件：用户提到「部署」「上线」「deploy」「上线方案」「切换上线」「试运行」「deployment plan」时触发。
  
  适用阶段：Phase 14 上线与试运行
  
  绑定模板：
  - 系统上线方案@BBB-CCC 107 20061205.doc
  - 系统试运行报告@BBB-CCC 107 20060822.doc
  - 生产环境网络统计列表@BBB-CCC 107 20060822.xls
  - 系统运维操作申请日志@BBB-CCC 107 20060823.xls
  - 系统运维操作记录@BBB-CCC 107 20060823.xls
  
  输入不足处理：
  - 若未提供生产环境信息，标注「待补充」
  - 若未提供切换时间窗口，使用默认值（凌晨 0-6 点）
  - 严禁编造 IP/端口/连接信息
version: 1.0.0
category: deployment
template_bound:
  - "templates/16-deploy-plan.md"
related_skills:
  - gen-etl-workflow
  - gen-sit-scripts
  - gen-user-manual
---

# 生成部署与上线方案 (Deployment Plan Generator)

## 触发词

`部署`, `上线`, `deploy`, `deployment`, `上线方案`, `切换上线`, `试运行`, `回滚`, `rollback`

---

## 模板绑定

---

| 精简模板 | 路径 | 说明 |
|----------|------|------|
| 16-deploy-plan.md | `templates/16-deploy-plan.md` | 参考/模板 |

## 输入输出映射

### 必需输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_name` | string | 项目名称 |
| `deploy_date` | date | 计划上线日期 |

### 可选输入

| 字段 | 类型 | 说明 |
|------|------|------|
| `prod_env_config` | dict | 生产环境配置（IP、端口、连接）|
| `deploy_window` | dict | 切换时间窗口 |
| `rollback_plan` | dict | 回滚方案 |
| `monitor_config` | dict | 监控告警配置 |
| `oncall_team` | list | 值班团队 |

### 输出物

| 字段 | 类型 | 说明 |
|------|------|------|
| `deploy_plan_md` | Markdown | 部署计划 |
| `deploy_checklist` | Markdown | 部署检查清单 |
| `rollback_runbook` | Markdown | 回滚操作手册 |
| `monitor_dashboard` | Markdown | 监控看板配置 |
| `cutover_timeline` | Markdown | 切换时间线 |

---

## 上线方案模板

```markdown
# 系统上线方案 — {project_name}

## 1. 上线基本信息
- 项目名称: {project_name}
- 上线日期: {deploy_date}
- 上线窗口: {deploy_window.start} ~ {deploy_window.end}
- 计划停机: {downtime_minutes} 分钟
- 责任人: 【待补充】

## 2. 上线范围

| # | 模块 | 部署类型 | 风险等级 |
|---|------|----------|----------|
| 1 | ODS 加载 | 新建 | 中 |
| 2 | DWD 转换 | 新建 | 中 |
| 3 | DWS 聚合 | 新建 | 中 |
| 4 | ADS 报表 | 新建 | 高 |
| 5 | 调度系统 | 改造 | 高 |
| ... | ... | ... | ... |

## 3. 上线前检查

### 3.1 代码检查
- [ ] 所有代码已通过代码审查
- [ ] 单元测试通过率 100%
- [ ] SIT 测试通过
- [ ] UAT 测试通过
- [ ] 性能测试达标

### 3.2 数据检查
- [ ] 源系统数据已就绪
- [ ] 历史数据已迁移（如果需要）
- [ ] 数据校验通过

### 3.3 环境检查
- [ ] 生产环境已配置
- [ ] 网络连通性测试通过
- [ ] 权限已开通
- [ ] 监控告警已配置

## 4. 切换流程

### 4.1 切换前（切换前 2 小时）
| 时间 | 任务 | 责任人 |
|------|------|--------|
| T-120 | 通知业务方暂停数据使用 | PM |
| T-60 | 停止源系统相关作业 | 源系统 DBA |
| T-30 | 备份生产数据库 | DBA |
| T-15 | 验证回滚方案可用 | 架构师 |

### 4.2 切换中（T-0 ~ T+30）
| 时间 | 任务 | 责任人 |
|------|------|--------|
| T+0 | 开始部署 DDL | DBA |
| T+5 | 执行 DDL，验证表结构 | DBA |
| T+10 | 部署 ETL 脚本 | 开发 |
| T+15 | 执行 ETL 初始加载 | 开发 |
| T+20 | 部署 OLAP / ADS 脚本 | 开发 |
| T+25 | 启动调度任务 | 运维 |
| T+30 | 验证数据产出 | QA |

### 4.3 切换后（T+30 ~ T+120）
| 时间 | 任务 | 责任人 |
|------|------|--------|
| T+30 | 对账：源系统 vs 数仓 | QA |
| T+45 | 验证核心指标 | BA + 业务方 |
| T+60 | 验证 BI 报表 | 业务方 |
| T+90 | 通知业务方恢复使用 | PM |
| T+120 | 上线完成评审 | 全员 |

## 5. 回滚方案

### 5.1 回滚触发条件
- P0 缺陷
- 数据准确性严重问题
- 性能严重不达标
- 上线超过 60 分钟仍未完成

### 5.2 回滚流程
1. 立即停止所有 ETL 任务
2. 恢复数据库备份
3. 回滚代码版本
4. 验证回滚成功
5. 通知相关方

### 5.3 回滚时间
- 目标: 30 分钟内完成
- 责任人: 架构师

## 6. 监控告警

| 监控项 | 阈值 | 告警接收人 | 告警渠道 |
|--------|------|------------|----------|
| ETL 任务失败 | 任一失败 | 值班开发 | 短信 + 钉钉 |
| 数据延迟 | > 1 小时 | 值班运维 | 钉钉 |
| 磁盘空间 | > 80% | DBA | 邮件 |
| 源系统连接 | 连接失败 | DBA | 短信 |
| 关键指标产出 | 缺失 | BA | 钉钉 |

## 7. 值班安排

| 时间段 | 值班人 | 联系方式 |
|--------|--------|----------|
| 上线当晚 0:00-8:00 | {oncall.d1} | 【待补充】 |
| 次日 8:00-18:00 | {oncall.d2} | 【待补充】 |
| 次日 18:00-24:00 | {oncall.d3} | 【待补充】 |

## 8. 试运行期（1-2 周）

- 数据准确性持续监控
- 性能基线建立
- 用户反馈收集
- 缺陷修复
```

---

## 部署检查清单

```markdown
# 部署检查清单 — {project_name}

## 1. 上线前 7 天
- [ ] 上线方案评审通过
- [ ] 回滚方案就绪
- [ ] 监控告警配置完成
- [ ] 值班表发布
- [ ] 业务方培训完成

## 2. 上线前 3 天
- [ ] 生产环境部署脚本验证（STAGE 环境）
- [ ] 性能压测报告通过
- [ ] 数据迁移完成（如需）
- [ ] 应急预案发布

## 3. 上线前 1 天
- [ ] 源系统确认无变更
- [ ] 网络连通性测试
- [ ] 权限再次确认
- [ ] 通知所有相关方

## 4. 上线当天
- [ ] 业务方确认可暂停数据使用
- [ ] 数据库备份完成
- [ ] DDL 部署成功
- [ ] ETL 部署成功
- [ ] 数据验证通过
- [ ] 业务方验收
- [ ] 通知恢复使用

## 5. 上线后 1 周
- [ ] 试运行报告
- [ ] 缺陷全部修复
- [ ] 性能达标
- [ ] 文档归档
```

---

## 回滚 Runbook

```markdown
# 回滚操作手册 — {project_name}

## 触发条件
- P0 缺陷
- 数据准确性失败
- 性能严重不达标

## 回滚步骤

### Step 1: 停止所有 ETL 任务（5 分钟）
\`\`\`bash
# 停调度系统
airflow dags pause {workflow_name}

# 停止正在运行的任务
airflow tasks clear {workflow_name} --start-date $(date +%Y-%m-%d)
\`\`\`

### Step 2: 恢复数据库（10 分钟）
\`\`\`bash
# 恢复 DDL
mysql -u root -p < backup/ddl_backup_{timestamp}.sql

# 恢复 ODS 数据（仅当日）
hive -e "INSERT OVERWRITE TABLE ods_xxx PARTITION (dt='${bizdate}') SELECT * FROM backup.ods_xxx_${timestamp} WHERE dt='${bizdate}'"
\`\`\`

### Step 3: 回滚代码（5 分钟）
\`\`\`bash
git checkout {previous_version_tag}
./deploy.sh
\`\`\`

### Step 4: 验证（5 分钟）
- [ ] 调度系统恢复
- [ ] ETL 任务可执行
- [ ] 数据产出正常

### Step 5: 通知
- PM → 业务方
- DBA → 源系统对接方
```

---

## Input Validation — 输入不足处理

### 情况 1: 未提供切换时间窗口
**处理**: 使用默认值（凌晨 0-6 点）

```markdown
- 上线窗口: 00:00 - 06:00（默认）
```

### 情况 2: 未提供生产环境信息
**处理**: 标注「待补充」

```markdown
- 生产 DB: 【待补充】
- 生产集群: 【待补充】
- 监控告警平台: 【待补充】
```

---

## 禁止编造

- ❌ IP 地址 / 端口号
- ❌ 数据库连接串
- ❌ 监控告警配置（具体阈值）
- ❌ 业务方联系人

---

## 关联 Skill

- **gen-etl-workflow** - 调度 DAG 部署
- **gen-sit-scripts** - 上线前的 SIT
- **gen-user-manual** - 上线后用户手册

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

- [ ] 上线范围明确
- [ ] 切换流程时间线清晰
- [ ] 回滚方案可行（目标 < 30 分钟）
- [ ] 监控告警覆盖关键节点
- [ ] 值班表已发布
- [ ] 试运行期计划明确
