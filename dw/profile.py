"""02 profile：扫描源文件，落地 raw Parquet，生成 sources.yaml 与体检报告。"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

# Excel sheet → 表名
SHEET_TABLE = {
    "线索": "leads",
    "商机": "opps",
    "订单": "orders",
    "开票": "invoices",
    "回款": "payments",
    "客户": "customers",
    "员工": "employees",
}

GRAIN = {
    "leads": "lead",
    "opps": "opportunity",
    "orders": "order",
    "invoices": "invoice",
    "payments": "payment",
    "customers": "customer",
    "employees": "employee",
}

TIME_COL = {
    "leads": "咨询日期",
    "opps": "商机日期",
    "orders": "订单日期",
    "invoices": "开票日期",
    "payments": "回款日期",
}


def _describe(df: pd.DataFrame) -> list[dict]:
    cols = []
    for c in df.columns:
        s = df[c]
        cols.append({
            "name": str(c),
            "dtype": str(s.dtype),
            "null_rate": round(float(s.isna().mean()), 4),
            "unique": int(s.nunique(dropna=True)),
            "sample": [str(v)[:40] for v in s.dropna().unique()[:3]],
        })
    return cols


def run(project, sheets: list[str] | None = None) -> dict:
    src = Path(project.cfg["source_file"])
    if not src.exists():
        raise FileNotFoundError(f"源文件不存在：{src}")

    project.log(f"profile 开始：{src.name} ({src.stat().st_size // 1024} KB)")
    xl = pd.ExcelFile(src)
    selected = sheets or [s for s in xl.sheet_names if s in SHEET_TABLE]
    skipped = [s for s in xl.sheet_names if s not in selected]

    raw_dir = project.data_path("raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    tables = []
    for sheet in selected:
        name = SHEET_TABLE[sheet]
        df = pd.read_excel(src, sheet_name=sheet)
        df.to_parquet(raw_dir / f"{name}.parquet", index=False)
        t = {
            "name": name,
            "sheet": sheet,
            "rows": int(len(df)),
            "grain": GRAIN[name],
            "file": f"data/raw/{name}.parquet",
        }
        if name in TIME_COL:
            t["time_column"] = TIME_COL[name]
        t["columns"] = _describe(df)
        tables.append(t)
        project.log(f"  {sheet} → {name}.parquet  {len(df)} 行 × {len(df.columns)} 列")

    sources = {
        "version": 2,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": str(src),
        "tables": tables,
    }
    project.save_config("sources", sources)

    report = _report(project, tables, skipped)
    (project.root / "output").mkdir(parents=True, exist_ok=True)
    (project.root / "output" / "数据体检报告.md").write_text(report, encoding="utf-8")
    project.log(f"profile 完成：{len(tables)} 张表，体检报告已生成")
    return sources


def _report(project, tables: list[dict], skipped: list[str]) -> str:
    lines = [
        f"# 数据体检报告 — {project.name}",
        "",
        f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## 总览",
        "",
        "| 表 | 源 Sheet | 行数 | 列数 | 粒度 |",
        "|---|---|---|---|---|",
    ]
    for t in tables:
        lines.append(f"| {t['name']} | {t['sheet']} | {t['rows']:,} | {len(t['columns'])} | {t['grain']} |")

    if skipped:
        lines += ["", f"未纳入的表：{', '.join(skipped)}（说明类/辅助映射）"]

    lines += ["", "## 字段质量", ""]
    for t in tables:
        lines += [f"### {t['name']}（{t['rows']:,} 行）", "",
                  "| 字段 | 类型 | 空值率 | 基数 | 样例 |", "|---|---|---|---|---|"]
        for c in t["columns"]:
            sample = " / ".join(c["sample"]) if c["sample"] else ""
            lines.append(
                f"| {c['name']} | {c['dtype']} | {c['null_rate']:.1%} | {c['unique']:,} | {sample} |"
            )
        lines.append("")

    lines += ["## 关注项", ""]
    issues = []
    for t in tables:
        for c in t["columns"]:
            if c["null_rate"] == 1.0:
                issues.append(f"- `{t['name']}.{c['name']}` 全空，建议在清洗阶段删除")
            elif 0 < c["null_rate"] < 0.05:
                issues.append(f"- `{t['name']}.{c['name']}` 空值率 {c['null_rate']:.1%}，需确认业务含义")
    lines += issues or ["- 未发现明显字段级问题"]

    lines += ["", "## 建议", "",
              "1. 全空列在 `cleaning.yaml` 的 `drop_columns` 中声明删除",
              "2. 日期字段统一转为 date 类型，时间口径以事实表日期为准",
              "3. 产品名按 `-编号` 后缀归并出产品线，避免 394 个 SKU 分散分析",
              "4. 维度缺失（如商机无事业部）通过外键回溯线索补齐"]
    return "\n".join(lines)


def product_line(name: str) -> str:
    """从产品名提取产品线：'彧策 us UM-50' → '彧策 us UM'。"""
    return re.sub(r"-\d+$", "", str(name)).strip()
