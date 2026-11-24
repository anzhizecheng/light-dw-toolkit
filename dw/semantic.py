"""05 semantic：加载 metrics.yaml，生成确定性 SQL 并执行。"""
from __future__ import annotations

from datetime import date

import pandas as pd

AGG = {
    "sum": "SUM({})",
    "count": "COUNT({})",
    "count_distinct": "COUNT(DISTINCT {})",
    "avg": "AVG({})",
    "min": "MIN({})",
    "max": "MAX({})",
}

GRAIN_SQL = {
    "day": "{col}",
    "week": "date_trunc('week', {col})::DATE",
    "month": "date_trunc('month', {col})::DATE",
    "quarter": "date_trunc('quarter', {col})::DATE",
    "year": "date_trunc('year', {col})::DATE",
}


class SemanticError(ValueError):
    pass


def load(project) -> dict:
    conf = project.load_config("metrics")
    if not conf:
        raise SemanticError("缺少 metrics.yaml")
    names = {m["name"] for m in conf.get("metrics", [])}
    for m in conf.get("metrics", []):
        if m["type"] == "sql":
            if not m.get("sql"):
                raise SemanticError(f"指标 {m['name']} 缺少 sql")
            continue
        if m["type"] == "ratio":
            for key in ("numerator", "denominator"):
                if m[key] not in names:
                    raise SemanticError(f"指标 {m['name']} 引用了不存在的 {m[key]}")
        if m["type"] == "derived":
            import re
            refs = re.findall(r"[a-z_][a-z0-9_]*", m.get("expr", ""))
            for r in refs:
                if r not in names and r not in {"coalesce", "nullif"}:
                    raise SemanticError(f"指标 {m['name']} 引用了不存在的 {r}")
    dims = {d["name"]: d for d in conf.get("dimensions", [])}
    return {"conf": conf, "metrics": {m["name"]: m for m in conf.get("metrics", [])}, "dims": dims}


def list_metrics(project) -> list[dict]:
    sem = load(project)
    return [
        {"name": m["name"], "label": m.get("label", m["name"]),
         "type": m["type"], "synonyms": m.get("synonyms", []),
         "description": m.get("description", "")}
        for m in sem["metrics"].values()
    ]


def describe_metric(project, name: str) -> dict:
    sem = load(project)
    if name not in sem["metrics"]:
        raise SemanticError(f"未知指标：{name}")
    return sem["metrics"][name]


def _simple_expr(m: dict) -> str:
    tmpl = AGG.get(m["agg"])
    if not tmpl:
        raise SemanticError(f"不支持的聚合：{m['agg']}")
    expr = tmpl.format(m["expr"])
    if m.get("where"):
        expr += f" FILTER (WHERE {m['where']})"
    return expr


def build_sql(project, metric: str, dimensions: list[str] | None = None,
              start: str | date | None = None, end: str | date | None = None,
              grain: str | None = None, limit: int | None = None) -> str:
    sem = load(project)
    conf, metrics, dims = sem["conf"], sem["metrics"], sem["dims"]
    if metric not in metrics:
        raise SemanticError(f"未知指标：{metric}")
    m = metrics[metric]

    # 收集所需的 simple 指标（含 ratio/derived 的依赖）
    needed: list[str] = []
    _collect(metric, metrics, needed)
    simple_needed = [n for n in needed if metrics[n]["type"] == "simple"]

    source, time_col = _resolve_source(conf, metrics, simple_needed)

    dim_exprs, group_pos = [], []
    for d in dimensions or []:
        if d not in dims:
            raise SemanticError(f"未知维度：{d}")
        dim_exprs.append(f"{dims[d]['column']} AS {d}")
        group_pos.append(len(dim_exprs))

    grain_expr = None
    if grain:
        if not time_col:
            raise SemanticError(f"指标 {metric} 未定义时间字段，无法按时间聚合")
        if grain not in GRAIN_SQL:
            raise SemanticError(f"不支持的时间粒度：{grain}")
        grain_expr = GRAIN_SQL[grain].format(col=time_col) + " AS period"
        group_pos.append(len(dim_exprs) + 1)

    select_base = [f"{e}" for e in dim_exprs]
    if grain_expr:
        select_base.append(grain_expr)
    for n in simple_needed:
        select_base.append(f"{_simple_expr(metrics[n])} AS {n}")

    where = []
    if start and time_col:
        where.append(f"{time_col} >= DATE '{start}'")
    if end and time_col:
        where.append(f"{time_col} <= DATE '{end}'")
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    group_by = ", ".join(str(i) for i in group_pos) if group_pos else ""
    group_sql = f"GROUP BY {group_by}" if group_by else ""

    base_cte = (
        f"WITH base AS (SELECT {', '.join(select_base)} "
        f"FROM {source} {where_sql} {group_sql})"
    )

    outer = []
    if dimensions:
        outer += [f"{d}" for d in dimensions]
    if grain:
        outer.append("period")
    if m["type"] == "simple":
        outer.append(metric)
        sql = f"{base_cte} SELECT {', '.join(outer)} FROM base"
    else:
        outer += [f"{_computed_expr(n, metrics)} AS {n}" for n in needed if metrics[n]["type"] != "simple"]
        sql = f"{base_cte} SELECT {', '.join(outer)} FROM base"

    order = []
    if dimensions:
        order.append(", ".join(dimensions))
    if grain:
        order.append("period")
    if order:
        sql += " ORDER BY " + ", ".join(order)
    if limit:
        sql += f" LIMIT {int(limit)}"
    return sql


def _resolve_source(conf: dict, metrics: dict, simple_needed: list[str]) -> tuple[str, str | None]:
    """指标可覆盖全局 source / time_column；同一次查询内必须一致。"""
    def src(m):
        return m.get("source") or conf.get("source", "clean.fct_funnel")

    def tcol(m):
        return m["time_column"] if "time_column" in m else conf.get("time_column", "event_date")

    sources = {src(metrics[n]) for n in simple_needed}
    if len(sources) > 1:
        raise SemanticError("同一查询内的指标必须来自同一数据源：" + "、".join(sorted(sources)))
    source = sources.pop() if sources else conf.get("source", "clean.fct_funnel")

    tcols = {tcol(metrics[n]) for n in simple_needed}
    if len(tcols) > 1:
        raise SemanticError("同一查询内的指标必须使用同一时间字段")
    time_col = tcols.pop() if tcols else conf.get("time_column", "event_date")
    return source, time_col


def _collect(name: str, metrics: dict, out: list[str]) -> None:
    if name in out:
        return
    m = metrics[name]
    if m["type"] == "sql":
        raise SemanticError(f"SQL 指标 {name} 不能参与 ratio/derived 计算")
    if m["type"] == "simple":
        out.append(name)
        return
    if m["type"] == "ratio":
        _collect(m["numerator"], metrics, out)
        _collect(m["denominator"], metrics, out)
        out.append(name)
        return
    if m["type"] == "derived":
        import re
        for r in re.findall(r"[a-z_][a-z0-9_]*", m.get("expr", "")):
            if r in metrics:
                _collect(r, metrics, out)
        out.append(name)


def _computed_expr(name: str, metrics: dict) -> str:
    m = metrics[name]
    if m["type"] == "ratio":
        return f"base.{m['numerator']} * 1.0 / NULLIF(base.{m['denominator']}, 0)"
    if m["type"] == "derived":
        expr = m["expr"]
        import re
        for r in re.findall(r"[a-z_][a-z0-9_]*", expr):
            if r in metrics:
                expr = re.sub(rf"\b{r}\b", f"base.{r}", expr, count=1)
        return expr
    return f"base.{name}"


def _fill_dates(sql: str, start, end) -> str:
    if start:
        sql = sql.replace("{start}", f"DATE '{start}'")
    if end:
        sql = sql.replace("{end}", f"DATE '{end}'")
    return sql


def query(project, metric: str, dimensions: list[str] | None = None,
          start=None, end=None, grain=None, limit=None) -> pd.DataFrame:
    m = load(project)["metrics"].get(metric)
    if not m:
        raise SemanticError(f"未知指标：{metric}")
    if m["type"] == "sql":
        if dimensions or grain:
            raise SemanticError(f"SQL 指标 {metric} 不支持维度或时间粒度下钻")
        sql = _fill_dates(m["sql"], start, end)
    else:
        sql = build_sql(project, metric, dimensions, start, end, grain, limit)
    con = project.db()
    try:
        return con.execute(sql).fetch_df()
    finally:
        con.close()


def scalar(project, metric: str, start=None, end=None) -> float | None:
    df = query(project, metric, start=start, end=end)
    if df.empty:
        return None
    v = df.iloc[0, 0]
    return None if pd.isna(v) else float(v)
