"""命令行入口：init / profile / run / metrics / query / dashboard。"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import dashboard, ingest, pipeline, profile, semantic
from .config import Project

DEFAULT_PROJECT = """\
name: 未命名分析项目
industry: crm-sales
source_file: ""
timezone: Asia/Shanghai
data:
  raw: data/raw
  clean: data/clean
  mart: data/mart
  database: data/demo.duckdb
"""


def _cmd_init(args) -> None:
    root = Path(args.root).expanduser().resolve()
    for sub in ("config", "data/raw", "data/clean", "data/mart", "output", "logs"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    cfg = root / "config" / "project.yaml"
    if not cfg.exists():
        text = DEFAULT_PROJECT
        if args.source:
            text = text.replace('source_file: ""', f'source_file: "{args.source}"')
        cfg.write_text(text, encoding="utf-8")
        print(f"已创建项目配置：{cfg}")
    else:
        print(f"项目配置已存在：{cfg}")
    print(f"项目根目录：{root}")


def _cmd_ingest(args) -> None:
    project = Project.load(args.root)
    ingest.run(project, args.table)


def _cmd_profile(args) -> None:
    project = Project.load(args.root)
    sheets = args.sheets.split(",") if args.sheets else None
    profile.run(project, sheets)


def _cmd_run(args) -> None:
    project = Project.load(args.root)
    pipeline.run(project)


def _cmd_metrics(args) -> None:
    project = Project.load(args.root)
    rows = semantic.list_metrics(project)
    print(f"{'指标字段':<24}{'名称':<18}{'类型':<10}同义词")
    print("-" * 90)
    for m in rows:
        syn = "、".join(m["synonyms"])
        print(f"{m['name']:<24}{m['label']:<18}{m['type']:<10}{syn}")


def _cmd_query(args) -> None:
    project = Project.load(args.root)
    dims = args.dimension or None
    df = semantic.query(
        project, args.metric, dimensions=dims,
        start=args.start, end=args.end, grain=args.grain, limit=args.limit,
    )
    if df.empty:
        print("（无数据）")
        return
    print(df.to_string(index=False))


def _cmd_dashboard(args) -> None:
    project = Project.load(args.root)
    out = dashboard.run(project)
    print(f"看板：{out}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dw", description="light-dw-toolkit V2 执行引擎")
    p.add_argument("--root", default=".", help="项目根目录（含 config/project.yaml）")
    sub = p.add_subparsers(dest="command", required=True)

    # 允许 --root 也写在子命令之后
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS, help="项目根目录")

    sp = sub.add_parser("init", parents=[common], help="初始化项目目录与配置")
    sp.add_argument("--source", help="源数据文件路径（写入 project.yaml）")
    sp.set_defaults(func=_cmd_init)

    sp = sub.add_parser("ingest", parents=[common], help="按 schema.yaml 把 CSV 导入 raw 层")
    sp.add_argument("--table", required=True)
    sp.set_defaults(func=_cmd_ingest)

    sp = sub.add_parser("profile", parents=[common], help="扫描源文件，落地 raw Parquet 并生成 sources/体检报告")
    sp.add_argument("--sheets", help="仅处理指定 sheet，逗号分隔")
    sp.set_defaults(func=_cmd_profile)

    sp = sub.add_parser("run", parents=[common], help="清洗并构建 clean/mart 事实表")
    sp.set_defaults(func=_cmd_run)

    sp = sub.add_parser("metrics", parents=[common], help="列出指标口径")
    sp.set_defaults(func=_cmd_metrics)

    sp = sub.add_parser("query", parents=[common], help="按指标取数")
    sp.add_argument("-m", "--metric", required=True)
    sp.add_argument("-d", "--dimension", action="append", help="维度，可重复")
    sp.add_argument("-s", "--start", help="起始日期 YYYY-MM-DD")
    sp.add_argument("-e", "--end", help="结束日期 YYYY-MM-DD")
    sp.add_argument("-g", "--grain", choices=["day", "week", "month", "quarter", "year"])
    sp.add_argument("--limit", type=int)
    sp.set_defaults(func=_cmd_query)

    sp = sub.add_parser("dashboard", parents=[common], help="按 roles.yaml 生成 HTML 看板")
    sp.set_defaults(func=_cmd_dashboard)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
