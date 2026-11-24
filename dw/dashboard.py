"""06 dashboard：按 roles.yaml 生成静态 HTML 看板。"""
from __future__ import annotations

import json
from datetime import date, datetime

import pandas as pd

from . import semantic

PALETTE = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
           "#59A14F", "#EDC948", "#B07AA1", "#9C755F", "#BAB0AC"]

def _clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (pd.Timestamp, date)):
        return str(v)
    if isinstance(v, (int, float)):
        return round(float(v), 4)
    return str(v)


def _metric_fmt(m: dict) -> str:
    if m.get("format"):
        return m["format"]
    return "percent" if m.get("type") == "ratio" else "count"


def _fmt(v, fmt: str = "count") -> str:
    if v is None or pd.isna(v):
        return "—"
    v = float(v)
    if fmt == "amount":
        if abs(v) >= 1e8:
            return f"{v / 1e8:.2f} 亿"
        if abs(v) >= 1e4:
            return f"{v / 1e4:.1f} 万"
        return f"{v:,.0f}"
    if fmt == "percent":
        return f"{v:.1%}"
    if fmt == "number":
        return f"{v:,.1f}"
    return f"{v:,.0f}"


def _kpi_cards(project, role) -> tuple[str, str]:
    metrics = semantic.load(project)["metrics"]
    start, end = role.get("start"), role.get("end")
    cards = []
    for item in role.get("kpis", []):
        if isinstance(item, str):
            name, label, extra = item, None, []
        else:
            name, label, extra = item["metric"], item.get("label"), item.get("extra", [])
        m = metrics.get(name, {})
        v = semantic.scalar(project, name, start, end)
        label = label or m.get("label", name)
        sub = ""
        for ex in extra:
            em = metrics.get(ex["metric"], {})
            ev = semantic.scalar(project, ex["metric"], start, end)
            sub += (f'<span class="kpi-sub">{ex.get("label", ex["metric"])} '
                    f'<b>{_fmt(ev, _metric_fmt(em))}</b></span>')
        cards.append(
            f'<div class="kpi"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{_fmt(v, _metric_fmt(m))}</div>'
            f'{f"<div class=kpi-extras>{sub}</div>" if sub else ""}</div>'
        )
    return "".join(cards), ""


def _panel_funnel(project, role, panel) -> dict:
    steps = panel.get("steps") or []
    if not steps:
        return {"series": []}
    items = []
    for step in steps:
        metric, label = step["metric"], step.get("label", step["metric"])
        v = semantic.scalar(project, metric, role.get("start"), role.get("end")) or 0
        items.append({"name": label, "value": int(v)})
    base = items[0]["value"] or 1
    for it in items:
        it["rate"] = f"{it['value'] / base:.1%}"
    return {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({@rate})"},
        "series": [{
            "type": "funnel", "left": "8%", "right": "8%", "top": 20, "bottom": 20,
            "minSize": "18%", "sort": "descending", "gap": 4,
            "label": {"position": "inside", "formatter": "{b}\n{c}", "color": "#fff", "fontSize": 12},
            "itemStyle": {"borderColor": "#fff", "borderWidth": 2},
            "data": items,
        }],
    }


def _panel_trend(project, role, panel) -> dict:
    metrics = semantic.load(project)["metrics"]
    grain = panel.get("grain", "month")
    frames = {}
    periods = []
    for name in panel["metrics"]:
        df = semantic.query(project, name, grain=grain,
                            start=role.get("start"), end=role.get("end"))
        if df.empty:
            continue
        periods = [str(p)[:10] for p in df["period"]]
        frames[name] = df[name].tolist()
    series = []
    for i, (name, vals) in enumerate(frames.items()):
        series.append({
            "name": metrics[name].get("label", name),
            "type": "line", "smooth": True, "symbolSize": 5,
            "data": [_clean(v) for v in vals],
            "itemStyle": {"color": PALETTE[i % len(PALETTE)]},
        })
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 0},
        "grid": {"left": 60, "right": 24, "top": 40, "bottom": 40},
        "xAxis": {"type": "category", "data": periods, "axisLabel": {"fontSize": 10}},
        "yAxis": {"type": "value", "axisLabel": {"formatter": "{value}"}},
        "series": series,
    }


def _panel_bar(project, role, panel) -> dict:
    metrics = semantic.load(project)["metrics"]
    name = panel["metric"]
    dim = panel["dimension"]
    df = semantic.query(project, name, dimensions=[dim],
                        start=role.get("start"), end=role.get("end"))
    if df.empty:
        return {"series": []}
    df = df.sort_values(name, ascending=False).head(panel.get("limit", 12))
    cats = [str(x) for x in df[dim]]
    vals = [_clean(v) for v in df[name]]
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 70, "right": 24, "top": 20, "bottom": 60},
        "xAxis": {"type": "category", "data": cats,
                  "axisLabel": {"rotate": 30, "fontSize": 10}},
        "yAxis": {"type": "value"},
        "series": [{
            "type": "bar", "data": vals, "barMaxWidth": 36,
            "itemStyle": {"color": PALETTE[0], "borderRadius": [4, 4, 0, 0]},
            "label": {"show": True, "position": "top", "fontSize": 10,
                      "formatter": "{c}"},
        }],
    }


def _panel_pie(project, role, panel) -> dict:
    metrics = semantic.load(project)["metrics"]
    name = panel["metric"]
    dim = panel["dimension"]
    df = semantic.query(project, name, dimensions=[dim],
                        start=role.get("start"), end=role.get("end"))
    if df.empty:
        data = []
    else:
        df = df.sort_values(name, ascending=False)
        top = panel.get("top")
        if top and len(df) > top:
            head = df.head(top)
            rest = df.iloc[top:][name].sum()
            df = head.copy()
            df.loc[len(df)] = {dim: "其它", name: rest}
        data = [{"name": str(k), "value": _clean(v)} for k, v in zip(df[dim], df[name]) if v]
    return {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"bottom": 0, "fontSize": 10},
        "series": [{
            "type": "pie", "radius": ["42%", "68%"], "center": ["50%", "45%"],
            "data": data,
            "itemStyle": {"borderColor": "#fff", "borderWidth": 2},
            "label": {"fontSize": 10, "formatter": "{b}\n{d}%"},
        }],
        "color": PALETTE,
    }


def _panel_compare(project, role, panel) -> dict:
    metrics = semantic.load(project)["metrics"]
    items = panel.get("metrics", [])
    cats, data = [], []
    for it in items:
        name = it["metric"]
        m = metrics.get(name, {})
        v = semantic.scalar(project, name, role.get("start"), role.get("end"))
        fmt = it.get("format") or _metric_fmt(m)
        cats.append(it.get("label", name))
        data.append({
            "value": _clean(v),
            "label": {"show": True, "position": "top", "fontSize": 11,
                      "formatter": _fmt(v, fmt)},
        })
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 60, "right": 24, "top": 30, "bottom": 40},
        "xAxis": {"type": "category", "data": cats},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": data, "barMaxWidth": 60,
                    "itemStyle": {"color": PALETTE[0], "borderRadius": [4, 4, 0, 0]}}],
    }


BUILDERS = {"funnel": _panel_funnel, "trend": _panel_trend,
            "bar": _panel_bar, "pie": _panel_pie, "compare": _panel_compare}


def _render_role(project, role, idx) -> tuple[str, list[str]]:
    body, scripts = [], []
    kpis, _ = _kpi_cards(project, role)
    body.append(f'<section class="role" id="role{idx}">')
    body.append(f'<h2>{role.get("label", role["name"])}'
                f'<span class="range">{role.get("start", "")} ~ {role.get("end", "")}</span></h2>')
    body.append(f'<div class="kpis">{kpis}</div>')
    body.append('<div class="grid">')

    for j, panel in enumerate(role.get("panels", [])):
        builder = BUILDERS.get(panel["type"])
        if not builder:
            continue
        option = builder(project, role, panel)
        cid = f"c{idx}_{j}"
        cls = "card wide" if panel["type"] in {"trend", "funnel"} else "card"
        body.append(f'<div class="{cls}"><h3>{panel.get("title", "")}</h3>'
                    f'<div id="{cid}" class="chart"></div></div>')
        scripts.append(f'init("{cid}", {json.dumps(option, ensure_ascii=False)});')

    body.append("</div></section>")
    return "\n".join(body), scripts


def _glossary(project) -> str:
    sem = semantic.load(project)
    rows = []
    for m in sem["metrics"].values():
        caveat = "；".join(m.get("caveats", [])) or "—"
        rows.append(
            f'<tr><td>{m.get("label", m["name"])}</td><td><code>{m["name"]}</code></td>'
            f'<td>{m["type"]}</td><td>{m.get("description", "")}</td><td>{caveat}</td></tr>'
        )
    return (
        '<section class="glossary"><h2>口径说明</h2>'
        '<p class="hint">以下定义来自 metrics.yaml，是看板数字的唯一来源。</p>'
        '<table><thead><tr><th>指标</th><th>字段</th><th>类型</th><th>定义</th><th>口径陷阱</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></section>'
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
  :root {{ --bg:#f5f6f8; --card:#fff; --text:#1f2329; --muted:#8a9099; --line:#e6e8eb; --accent:#4E79A7; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
         font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; }}
  header {{ background:linear-gradient(135deg,#2c3e50,#4E79A7); color:#fff; padding:28px 36px; }}
  header h1 {{ margin:0 0 6px; font-size:22px; font-weight:600; }}
  header p {{ margin:0; opacity:.85; font-size:13px; }}
  main {{ max-width:1360px; margin:0 auto; padding:24px 20px 60px; }}
  .role h2 {{ font-size:18px; margin:28px 0 14px; display:flex; align-items:baseline; gap:12px; }}
  .range {{ font-size:12px; color:var(--muted); font-weight:400; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }}
  .kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px 18px; }}
  .kpi-label {{ font-size:12px; color:var(--muted); margin-bottom:8px; }}
  .kpi-value {{ font-size:24px; font-weight:600; letter-spacing:-.5px; }}
  .kpi-extras {{ margin-top:10px; padding-top:8px; border-top:1px dashed var(--line);
                 display:flex; gap:16px; font-size:12px; color:var(--muted); }}
  .kpi-sub b {{ color:var(--text); font-weight:600; }}
  .grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:14px; margin-top:14px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }}
  .card.wide {{ grid-column:1 / -1; }}
  .card h3 {{ margin:0 0 8px; font-size:14px; font-weight:600; color:#3a3f45; }}
  .chart {{ width:100%; height:300px; }}
  .card.wide .chart {{ height:340px; }}
  .glossary {{ margin-top:36px; background:var(--card); border:1px solid var(--line);
               border-radius:10px; padding:20px; overflow-x:auto; }}
  .glossary h2 {{ font-size:16px; margin:0 0 4px; }}
  .hint {{ font-size:12px; color:var(--muted); margin:0 0 14px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th,td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ color:var(--muted); font-weight:500; background:#fafbfc; }}
  code {{ background:#f0f2f5; padding:1px 5px; border-radius:4px; font-size:11px; }}
  footer {{ text-align:center; color:var(--muted); font-size:12px; padding:28px 0; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p>{subtitle}</p>
</header>
<main>
{body}
{glossary}
</main>
<footer>由 light-dw-toolkit V2 生成 · {ts}</footer>
<script>
const charts = [];
function init(id, option) {{
  const el = document.getElementById(id);
  if (!el) return;
  const c = echarts.init(el);
  c.setOption(option);
  charts.push(c);
}}
{scripts}
window.addEventListener("resize", () => charts.forEach(c => c.resize()));
</script>
</body>
</html>
"""


def run(project) -> str:
    conf = project.load_config("roles")
    roles = conf.get("roles", [])
    if not roles:
        raise RuntimeError("缺少 roles.yaml")

    bodies, scripts = [], []
    for i, role in enumerate(roles):
        b, s = _render_role(project, role, i)
        bodies.append(b)
        scripts.extend(s)

    total = sum(len(r.get("panels", [])) for r in roles)
    title = project.cfg.get("name", "数据看板")
    subtitle = conf.get("subtitle") or (
        f"{len(roles)} 个角色 · {total} 个分析视图 · "
        f"数据源：{project.cfg.get('source_file', '').split('/')[-1]}"
    )
    html = TEMPLATE.format(
        title=title,
        subtitle=subtitle,
        body="\n".join(bodies),
        glossary=_glossary(project),
        scripts="\n".join(scripts),
        ts=f"{datetime.now():%Y-%m-%d %H:%M}",
    )
    out = project.root / "output" / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    project.log(f"看板已生成：{out}（{len(html) // 1024} KB，{total} 个视图）")
    return str(out)
