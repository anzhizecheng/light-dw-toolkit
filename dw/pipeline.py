"""04 pipeline：清洗 raw 并构建统一漏斗事实表 fct_funnel。"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from .profile import product_line

FUNNEL_COLUMNS = [
    "stage", "event_id", "event_date", "amount", "amount_net",
    "lead_id", "opp_id", "order_id", "invoice_id",
    "lead_source", "business_unit", "product_line", "product_name",
    "employee_id", "employee_name", "customer_id", "customer_type", "status",
]

STAGE_ORDER = ["lead", "opportunity", "order", "invoice", "payment"]


def _load_raw(project) -> dict[str, pd.DataFrame]:
    raw_dir = project.data_path("raw")
    data = {}
    for p in sorted(raw_dir.glob("*.parquet")):
        data[p.stem] = pd.read_parquet(p)
    if not data:
        raise RuntimeError("raw 层为空，请先执行 profile")
    return data


def _apply_cleaning(project, raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    rules = project.load_config("cleaning")
    drop = rules.get("drop_columns", {})
    for table, cols in drop.items():
        if table in raw:
            existing = [c for c in cols if c in raw[table].columns]
            if existing:
                raw[table] = raw[table].drop(columns=existing)
                project.log(f"  删除全空列 {table}: {existing}")
    if rules.get("dedup", True):
        for name, df in raw.items():
            before = len(df)
            raw[name] = df.drop_duplicates()
            if len(raw[name]) < before:
                project.log(f"  去重 {name}: {before - len(raw[name])} 行")
    return raw


def _dimension_base(raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    emps = raw["employees"]
    cust = raw["customers"]
    lead = raw["leads"]

    emp_name = dict(zip(emps["员工ID"], emps["员工姓名"]))
    emp_bu = dict(zip(emps["员工ID"], emps["事业部NAME"]))
    cust_type = dict(zip(cust["客户ID"], cust["客户类型NAME"]))

    base = pd.DataFrame({
        "lead_id": lead["线索编号"],
        "employee_id": lead["跟进人ID"],
        "customer_id": lead["客户编号"],
        "lead_source": lead["线索来源NAME"],
    })
    base["employee_name"] = base["employee_id"].map(emp_name)
    base["business_unit"] = base["employee_id"].map(emp_bu)
    base["customer_type"] = base["customer_id"].map(cust_type)
    return base


def _col(df: pd.DataFrame, name: str, dtype: str | None = None) -> pd.Series:
    """取列，缺失时回填空值 Series，避免标量 NaN 混入 DataFrame。"""
    if name in df.columns:
        return df[name]
    return pd.Series([pd.NA] * len(df), index=df.index, dtype=dtype or "object")


def _frame(df, stage, id_col, date_col, amount_col, ids,
           amount_net_col=None, status_col=None) -> pd.DataFrame:
    product = _col(df, "产品类型NAME")
    out = pd.DataFrame({
        "stage": stage,
        "event_id": _col(df, id_col),
        "event_date": pd.to_datetime(_col(df, date_col), errors="coerce"),
        "amount": pd.to_numeric(_col(df, amount_col), errors="coerce"),
        "amount_net": pd.to_numeric(_col(df, amount_net_col), errors="coerce")
        if amount_net_col else pd.Series([float("nan")] * len(df), index=df.index),
        "product_name": product,
        "product_line": product.map(product_line),
        "lead_source": _col(df, "lead_source"),
        "business_unit": _col(df, "business_unit"),
        "employee_id": _col(df, "employee_id"),
        "employee_name": _col(df, "employee_name"),
        "customer_id": _col(df, "customer_id"),
        "customer_type": _col(df, "customer_type"),
        "status": _col(df, status_col) if status_col else pd.Series([pd.NA] * len(df), index=df.index),
    })
    for col, src in ids.items():
        out[col] = _col(df, src)
    for col in FUNNEL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.Series([pd.NA] * len(df), index=df.index)
    return out[FUNNEL_COLUMNS]


def build_funnel(project, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    base = _dimension_base(raw)
    lead = raw["leads"].merge(base, left_on="线索编号", right_on="lead_id", how="left")

    opp = raw["opps"].merge(
        lead[["线索编号", "lead_id", "lead_source", "business_unit",
              "employee_id", "employee_name", "customer_id", "customer_type"]],
        left_on="线索编号", right_on="线索编号", how="left",
    )

    order = raw["orders"].merge(
        opp[["商机编号", "lead_id", "lead_source", "business_unit",
             "employee_id", "employee_name", "customer_id", "customer_type"]],
        on="商机编号", how="left",
    )

    invoice = raw["invoices"].merge(
        order[["订单编号", "商机编号", "lead_id", "lead_source", "business_unit",
               "employee_id", "employee_name", "customer_id", "customer_type",
               "产品类型NAME"]],
        on="订单编号", how="left",
    )

    payment = raw["payments"].merge(
        invoice[["开票ID", "订单编号", "商机编号", "lead_id", "lead_source", "business_unit",
                 "employee_id", "employee_name", "customer_id", "customer_type",
                 "产品类型NAME"]],
        left_on="开票ID", right_on="开票ID", how="left",
    )

    frames = [
        _frame(lead, "lead", "线索编号", "咨询日期", "线索金额",
               {"lead_id": "线索编号"}, status_col="线索状态NAME"),
        _frame(opp, "opportunity", "商机编号", "商机日期", "商机金额",
               {"lead_id": "lead_id", "opp_id": "商机编号"}, status_col="商机状态NAME"),
        _frame(order, "order", "订单编号", "订单日期", "订单金额",
               {"lead_id": "lead_id", "opp_id": "商机编号", "order_id": "订单编号"}),
        _frame(invoice, "invoice", "开票ID", "开票日期", "开票金额(含税)",
               {"lead_id": "lead_id", "opp_id": "商机编号", "order_id": "订单编号",
                "invoice_id": "开票ID"},
               amount_net_col="开票金额(不含税)"),
        _frame(payment, "payment", "回款ID", "回款日期", "回款金额",
               {"lead_id": "lead_id", "opp_id": "商机编号", "order_id": "订单编号",
                "invoice_id": "开票ID"}),
    ]
    funnel = pd.concat(frames, ignore_index=True)
    funnel["stage"] = funnel["stage"].astype(str)
    funnel["event_date"] = pd.to_datetime(funnel["event_date"], errors="coerce").dt.date
    return funnel


def run(project) -> dict:
    project.log("pipeline 开始")
    project.data_path("raw").mkdir(parents=True, exist_ok=True)
    raw = _load_raw(project)
    raw = _apply_cleaning(project, raw)

    funnel = build_funnel(project, raw)
    clean_dir = project.data_path("clean")
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_path = clean_dir / "fct_funnel.parquet"
    funnel.to_parquet(clean_path, index=False)
    project.log(f"fct_funnel 写入 {clean_path.name}：{len(funnel):,} 行")

    con = project.db()
    con.execute("CREATE SCHEMA IF NOT EXISTS clean")
    con.execute(
        f"CREATE OR REPLACE TABLE clean.fct_funnel AS "
        f"SELECT * FROM read_parquet('{clean_path}')"
    )
    stats = con.execute(
        "SELECT stage, COUNT(*) AS n, ROUND(SUM(amount), 0) AS amount "
        "FROM clean.fct_funnel GROUP BY ROLLUP(stage) ORDER BY stage NULLS LAST"
    ).fetchall()
    con.close()

    for stage, n, amount in stats:
        project.log(f"  {stage or '合计':<12} {n:>8,} 行  金额 {amount or 0:>18,.0f}")

    summary = {
        "rows": int(len(funnel)),
        "stages": {str(s): int(n) for s, n, _ in stats if s},
        "built_at": datetime.now().isoformat(timespec="seconds"),
    }
    project.save_config("build_summary", summary)
    project.log("pipeline 完成")
    return summary
