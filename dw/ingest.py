"""01 ingest：按建表结构把 CSV 导入 raw 层（DuckDB 表 + Parquet）。"""
from __future__ import annotations

from pathlib import Path

TYPE_MAP = {
    "STRING": "VARCHAR", "FLOAT": "DOUBLE", "BOOLEAN": "BOOLEAN",
    "INT": "INTEGER", "BIGINT": "BIGINT", "DOUBLE": "DOUBLE",
}


def _columns_literal(schema: list[dict]) -> str:
    parts = [
        f"'{c['name']}': '{TYPE_MAP.get(str(c['type']).upper(), 'VARCHAR')}'"
        for c in schema
    ]
    return "{" + ", ".join(parts) + "}"


def run(project, table: str) -> dict:
    schema_conf = project.load_config("schema")
    if table not in schema_conf:
        raise RuntimeError(f"schema.yaml 缺少表结构：{table}")
    schema = schema_conf[table]

    csv_conf = project.cfg.get("csv") or {}
    src_value = csv_conf.get(table) or project.cfg.get("source_file")
    if not src_value:
        raise RuntimeError(f"未配置 {table} 的 CSV 路径：请在 project.yaml 设置 csv.{table} 或 source_file")
    src = Path(src_value).expanduser()
    if not src.exists():
        raise FileNotFoundError(f"CSV 不存在：{src}")

    project.log(f"ingest 开始：{table} ← {src.name}（{src.stat().st_size // 1024 // 1024} MB）")
    con = project.db()
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        f"CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM read_csv("
        f"'{src}', header=false, columns={_columns_literal(schema)}, "
        f"delim=',', quote='\"', escape='\"', nullstr='')"
    )
    rows = con.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]

    parquet = project.data_path("raw") / f"{table}.parquet"
    parquet.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY raw.{table} TO '{parquet}' (FORMAT PARQUET)")
    con.close()

    project.log(f"  raw.{table} 写入 {rows:,} 行 × {len(schema)} 列 → {parquet.name}")
    return {"table": table, "rows": int(rows), "columns": len(schema)}
