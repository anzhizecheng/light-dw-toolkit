# Skill 日志机制统一规范 (Logging Convention v1.2)

> 本文档定义所有 18 个功能型 skill 的统一日志机制。
> 每个 skill 在执行时必须遵循本规范，将日志写入由 `gen-project-config` 生成的 `project_config.yaml` 中指定的位置。

---

## 1. 日志查找流程

每个 skill 启动时，按以下顺序查找日志配置：

```yaml
1. 检查工作目录或上级目录是否存在 project_config.yaml
2. 若存在 → 读取 logging 节:
   - skill_execution_log: 所有 skill 执行的统一入口日志
   - error_log: 错误日志（任何 skill 失败时追加）
   - {specific_log}: 特定 skill 的子日志（可选）
3. 若不存在 → 使用默认路径:
   - skill_execution_log: ./logs/skill_execution.log
   - error_log: ./logs/error.log
   并在控制台输出: "⚠️ 未找到 project_config.yaml，使用默认日志路径"
```

**优先级**:
1. `project_config.yaml` 中的配置（最高）
2. 环境变量 `DW_PROJECT_CONFIG` 指向的配置文件
3. 默认路径 `./logs/`（最低）

---

## 2. 日志格式规范

### 2.1 skill 执行日志 (skill_execution.log)

```text
[ISO8601 时间戳] [级别] [Skill 名] [事件] [消息]

# 字段说明
- ISO8601 时间戳: 2026-06-23T10:15:30.123Z
- 级别: INFO / WARN / ERROR / DEBUG
- Skill 名: 当前 skill 的 name（如 gen-ddl-scripts）
- 事件: START / END / PROGRESS / REPORT / ERROR
- 消息: 自由文本（建议结构化）
```

**示例**:
```text
[2026-06-23T10:15:30.123Z] [INFO] [gen-ddl-scripts] [START] - 启动 skill, project=零售数仓二期, inputs={layer_architecture: standard_4layer, table_count: 42}
[2026-06-23T10:15:35.456Z] [INFO] [gen-ddl-scripts] [PROGRESS] - 已生成 ODS DDL: 12 张表
[2026-06-23T10:15:42.789Z] [INFO] [gen-ddl-scripts] [PROGRESS] - 已生成 DWD DDL: 8 张表
[2026-06-23T10:15:50.012Z] [INFO] [gen-ddl-scripts] [PROGRESS] - 已生成 DWS DDL: 15 张表
[2026-06-23T10:15:55.345Z] [INFO] [gen-ddl-scripts] [PROGRESS] - 已生成 ADS DDL: 5 张表, DIM: 2 张表
[2026-06-23T10:16:00.567Z] [INFO] [gen-ddl-scripts] [END] - 完成, 耗时=30.444s, outputs={ddl_files: 42, ddl_dir: /data/projects/retail_dw_v2/07_ddl}
[2026-06-23T10:16:00.568Z] [INFO] [gen-ddl-scripts] [REPORT] - ✅ 成功, 42 个 DDL 文件已生成, 0 错误, 0 警告
```

### 2.2 错误日志 (error.log)

```text
[ISO8601 时间戳] [级别] [Skill 名] [ERROR] [错误码] [错误消息] [上下文]

# 示例
[2026-06-23T10:15:35.000Z] [ERROR] [gen-ddl-scripts] [E001] - 目标目录不可写: /data/projects/retail_dw_v2/07_ddl, Permission denied | context={input: layer_architecture=standard_4layer}
[2026-06-23T10:15:35.001Z] [ERROR] [gen-ddl-scripts] [E002] - 输入参数缺失: table_structures (来自 gen-source-data-dict), 需要用户提供 | context={missing: table_structures}
```

### 2.3 特定 skill 子日志 (可选)

某些 skill 有独立的子日志，便于分类查询：

| Skill | 子日志 | 路径模板 |
|-------|--------|----------|
| gen-data-cleaning-rules | `cleaning_audit.log` | `${project_root}/logs/cleaning_audit.log` |
| gen-data-quality-report | `quality_check.log` | `${project_root}/logs/quality_check.log` |
| gen-etl-workflow | `etl_runtime.log` | `${project_root}/logs/etl_runtime.log` |
| 其他 | 无（只用 skill_execution.log + error.log）| - |

---

## 3. 标准日志事件

每个 skill 至少要记录以下 5 类事件：

### 3.1 START (必须)
```text
[time] [INFO] [skill_name] [START] - 启动 skill, project={name}, inputs={...}
```
记录：项目名、关键输入参数、启动时间。

### 3.2 PROGRESS (推荐)
```text
[time] [INFO] [skill_name] [PROGRESS] - {阶段描述}
```
记录：阶段性进展（如「已生成 50% DDL」）。**每完成 10% 进度记录一次**，避免日志爆炸。

### 3.3 END (必须)
```text
[time] [INFO] [skill_name] [END] - 完成, 耗时={duration_s}s, outputs={...}
```
记录：完成时间、耗时、输出物清单。

### 3.4 REPORT (必须)
```text
[time] [INFO] [skill_name] [REPORT] - ✅/⚠️/❌ {结果摘要}
```
记录：执行结果（成功/部分成功/失败）、统计数字、关键指标。

### 3.5 ERROR (失败时必须)
```text
[time] [ERROR] [skill_name] [ERROR] [{error_code}] - {错误消息} | context={...}
```
记录：错误码、错误消息、上下文（输入、堆栈等）。

---

## 4. 报告示例

每个 skill 在 END 后应输出「任务完成报告」段落，包括：

```markdown
## 任务完成报告 — {skill_name}

| 项目 | 值 |
|------|-----|
| 项目名 | 零售数仓二期 |
| Skill | gen-ddl-scripts v1.1.0 |
| 启动时间 | 2026-06-23T10:15:30.123Z |
| 完成时间 | 2026-06-23T10:16:00.567Z |
| 耗时 | 30.444 秒 |
| 结果 | ✅ 成功 |
| 输入 | layer_architecture=standard_4layer, table_count=42 |
| 输出 | 42 个 DDL 文件, 输出目录: /data/projects/retail_dw_v2/07_ddl |
| 警告 | 0 |
| 错误 | 0 |
```

---

## 5. Python 伪代码模板

```python
import yaml
import logging
import time
from pathlib import Path

class SkillLogger:
    """统一日志封装，所有 skill 都应使用此类"""
    
    def __init__(self, skill_name: str, config_path: str = "project_config.yaml"):
        self.skill_name = skill_name
        self.start_time = time.time()
        
        # 1. 加载配置
        config = self._load_config(config_path)
        logging_config = config.get('logging', {})
        
        # 2. 设置日志路径（优先级：config > 默认）
        self.skill_log = logging_config.get(
            'skill_execution_log',
            './logs/skill_execution.log'
        )
        self.error_log = logging_config.get(
            'error_log',
            './logs/error.log'
        )
        
        # 3. 确保日志目录存在
        Path(self.skill_log).parent.mkdir(parents=True, exist_ok=True)
        Path(self.error_log).parent.mkdir(parents=True, exist_ok=True)
        
        # 4. 记录 START
        self._write_skill_log('INFO', 'START', f"启动 skill, project={config['project']['name']}")
    
    def _load_config(self, config_path: str) -> dict:
        if not Path(config_path).exists():
            print(f"⚠️ 未找到 {config_path}, 使用默认配置")
            return {
                'project': {'name': '未命名项目'},
                'logging': {
                    'skill_execution_log': './logs/skill_execution.log',
                    'error_log': './logs/error.log'
                }
            }
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def _write_skill_log(self, level: str, event: str, message: str):
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()) + f'.{int((time.time()%1)*1000):03d}Z'
        line = f"[{timestamp}] [{level}] [{self.skill_name}] [{event}] - {message}\n"
        with open(self.skill_log, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def _write_error_log(self, error_code: str, message: str, context: dict = None):
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()) + 'Z'
        ctx = f" | context={context}" if context else ""
        line = f"[{timestamp}] [ERROR] [{self.skill_name}] [{error_code}] - {message}{ctx}\n"
        with open(self.error_log, 'a', encoding='utf-8') as f:
            f.write(line)
    
    # === 公共 API ===
    def progress(self, message: str):
        self._write_skill_log('INFO', 'PROGRESS', message)
    
    def warn(self, message: str):
        self._write_skill_log('WARN', 'PROGRESS', message)
    
    def error(self, error_code: str, message: str, context: dict = None):
        self._write_skill_log('ERROR', 'ERROR', f"[{error_code}] {message}")
        self._write_error_log(error_code, message, context)
    
    def finish(self, outputs: dict, status: str = 'success', warnings: int = 0, errors: int = 0):
        duration = time.time() - self.start_time
        self._write_skill_log(
            'INFO', 'END',
            f"完成, 耗时={duration:.3f}s, outputs={outputs}"
        )
        emoji = '✅' if status == 'success' else ('⚠️' if status == 'partial' else '❌')
        self._write_skill_log(
            'INFO', 'REPORT',
            f"{emoji} {status}, warnings={warnings}, errors={errors}"
        )

# === 使用示例 ===
def main():
    logger = SkillLogger('gen-ddl-scripts')
    try:
        logger.progress("已生成 ODS DDL: 12 张表")
        # ... 业务逻辑 ...
        logger.finish(outputs={'ddl_files': 42}, status='success')
    except Exception as e:
        logger.error('E001', str(e), context={'input': 'layer_architecture=standard_4layer'})
        raise
```

---

## 6. 错误码规范

| 错误码前缀 | 含义 | 范围 |
|-----------|------|------|
| `E0xx` | 输入参数错误 | E001=缺失, E002=类型错误, E003=值越界 |
| `E1xx` | 文件 I/O 错误 | E101=路径不存在, E102=权限拒绝, E103=磁盘满 |
| `E2xx` | 配置错误 | E201=project_config.yaml 格式错误 |
| `E3xx` | 上游依赖错误 | E301=缺失上游输出, E302=上游格式不兼容 |
| `E4xx` | 业务逻辑错误 | E401=规则冲突, E402=数据校验失败 |
| `E5xx` | 资源耗尽 | E501=内存不足, E502=超时 |
| `E9xx` | 未知错误 | E999=兜底 |

---

## 7. 与 gen-project-config 的关系

| 读取 | 用途 |
|------|------|
| `logging.skill_execution_log` | 主日志路径 |
| `logging.error_log` | 错误日志路径 |
| `logging.cleaning_audit_log` | 清洗审计日志（仅 gen-data-cleaning-rules / gen-etl-sql 使用）|
| `logging.quality_check_log` | 质量检查日志（仅 gen-data-quality-report 使用）|
| `logging.etl_runtime_log` | ETL 运行时日志（仅 gen-etl-workflow / gen-etl-sql 使用）|

| 写回 | 用途 |
|------|------|
| `skill_execution.records` | 追加本次执行记录（含 skill_name、start_time、end_time、status）|
| `etl_status.tables` | gen-etl-sql / gen-etl-workflow 完成后追加执行状态 |

---

## 8. 验证清单（每个 skill 都需检查）

- [ ] skill 启动时已读取 `project_config.yaml` 并找到日志路径
- [ ] 已写入 `START` 事件
- [ ] 关键进度有 `PROGRESS` 事件
- [ ] 完成后已写入 `END` 和 `REPORT` 事件
- [ ] 失败时已写入 `error.log` 并携带 error_code
- [ ] 任务完成报告段落已输出
- [ ] 如适用，已将执行状态写回 `project_config.yaml`
- [ ] 日志格式符合 ISO8601 + 5 字段规范

---

*版本: 1.2.0*
*更新日期: 2026-06-23*
