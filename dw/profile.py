"""02 profile：扫描源文件，落地 raw Parquet，生成 sources.yaml 与数据体检报告。"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd

TIME_HINT = re.compile(r"(date|day|time|dt|日期|时间|月份|年月)", re.I)


def _slug(name: str, idx: int) -> str:
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", str(name)).strip("_").lower()
    return s or f"table_{idx}"


def _read_tables(src: Path, sheets: list[str] | None) -> list[tuple[str, str, pd.DataFrame]]:
    """返回 [(表名, 源 Sheet/文件名, DataFrame)]。"""
    suffix = src.suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        xl = pd.ExcelFile(src)
        selected = sheets or xl.sheet_names
        missing = [s for s in selected if s not in xl.sheet_names]
        if missing:
            raise ValueError(f"Sheet 不存在：{', '.join(missing)}")
        return [(_slug(s, i + 1), s, pd.read_excel(src, sheet_name=s))
                for i, s in enumerate(selected)]
    if suffix == ".csv":
        return [(_slug(src.stem, 1), src.name, pd.read_csv(src))]
    if suffix == ".parquet":
        return [(_slug(src.stem, 1), src.name, pd.read_parquet(src))]
    raise ValueError(f"暂不支持的源文件类型：{suffix}（支持 xlsx/xls/xlsm/csv/parquet）")


def _describe(df: pd.DataFrame) -> list[dict]:
    cols = []
    for c in df.columns:
        s = df[c]
        item = {
            "name": str(c),
            "dtype": str(s.dtype),
            "null_rate": round(float(s.isna().mean()), 4),
            "unique": int(s.nunique(dropna=True)),
            "sample": [str(v)[:40] for v in s.dropna().unique()[:3]],
        }
        if pd.api.types.is_numeric_dtype(s):
            item["min"] = None if s.dropna().empty else float(s.min())
            item["max"] = None if s.dropna().empty else float(s.max())
        cols.append(item)
    return cols


def _time_column(df: pd.DataFrame) -> str | None:
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            return str(c)
    for c in df.columns:
        if TIME_HINT.search(str(c)):
            return str(c)
    return None


def run(project, sheets: list[str] | None = None) -> dict:
    src = Path(project.cfg.get("source_file", "")).expanduser()
    if not src or not src.exists():
        raise FileNotFoundError(f"源文件不存在：{src}")

    project.log(f"profile 开始：{src.name}（{src.stat().st_size // 1024} KB）")
    raw_dir = project.data_path("raw")
    tables = []
    for name, origin, df in _read_tables(src, sheets):
        df.to_parquet(raw_dir / f"{name}.parquet", index=False)
        t = {
            "name": name,
            "origin": origin,
            "rows": int(len(df)),
            "file": f"data/raw/{name}.parquet",
        }
        tcol = _time_column(df)
        if tcol:
            t["time_column"] = tcol
        t["columns"] = _describe(df)
        tables.append(t)
        project.log(f"  {origin} → {name}.parquet  {len(df):,} 行 × {len(df.columns)} 列")

    sources = {
        "version": 2,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": str(src),
        "tables": tables,
    }
    project.save_config("sources", sources)

    report = _report(project, tables)
    out = project.root / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "数据体检报告.md").write_text(report, encoding="utf-8")
    project.log(f"profile 完成：{len(tables)} 张表，体检报告已生成")
    return sources


def _report(project, tables: list[dict]) -> str:
    lines = [
        f"# 数据体检报告 — {project.name}",
        "",
        f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## 总览",
        "",
        "| 表 | 来源 | 行数 | 列数 | 时间字段 |",
        "|---|---|---|---|---|",
    ]
    for t in tables:
        lines.append(
            f"| {t['name']} | {t['origin']} | {t['rows']:,} | "
            f"{len(t['columns'])} | {t.get('time_column', '—')} |"
        )

    lines += ["", "## 字段质量", ""]
    for t in tables:
        lines += [f"### {t['name']}（{t['rows']:,} 行）", "",
                  "| 字段 | 类型 | 空值率 | 基数 | 样例 |", "|---|---|---|---|---|"]
        for c in t["columns"]:
            sample = " / ".join(c["sample"]) if c["sample"] else ""
            lines.append(
                f"| {c['name']} | {c['dtype']} | {c['null_rate']:.1%} | "
                f"{c['unique']:,} | {sample} |"
            )
        lines.append("")

    lines += ["## 关注项", ""]
    issues = []
    for t in tables:
        for c in t["columns"]:
            if c["null_rate"] == 1.0:
                issues.append(f"- `{t['name']}.{c['name']}` 全空，建议在清洗阶段删除")
            elif c["null_rate"] >= 0.5:
                issues.append(f"- `{t['name']}.{c['name']}` 空值率 {c['null_rate']:.1%}，需确认业务含义")
            elif c["unique"] == 1:
                issues.append(f"- `{t['name']}.{c['name']}` 仅 1 个取值，确认是否常量字段")
    lines += issues or ["- 未发现明显字段级问题"]

    lines += ["", "## 建议", "",
              "1. 全空列可在清洗阶段声明删除",
              "2. 日期字段统一转为 date 类型，时间口径以事实表日期为准",
              "3. 对高基数文本字段（产品、门店等）建立维表，避免明细表膨胀",
              "4. 在 metrics.yaml 中为每个指标显式声明 source、聚合方式与过滤条件"]
    return "\n".join(lines)
