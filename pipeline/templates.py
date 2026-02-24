"""Template rendering infrastructure for HTML variant generation."""

import json
import re
from collections.abc import Callable
from html import escape as _esc

from pipeline.schemas import ClinicalClaim

COLORS = [
    "#0d9488", "#a855f7", "#e879a0", "#2d4a7a", "#5eead4",
    "#F39C12", "#E74C3C", "#8E44AD", "#27AE60", "#D35400",
]

COLORS_LIGHT = [
    "#ccfbf1", "#e9d5ff", "#fce7f3", "#dbeafe", "#d1fae5",
    "#FDEBD0", "#FADBD8", "#E8DAEF", "#D5F5E3", "#FAD7A0",
]

ARM_BORDER_COLORS = ["#0d9488", "#2d4a7a", "#c026d3", "#7c3aed", "#e879a0", "#F39C12"]


def _extract_drug_name(claims: list[ClinicalClaim]) -> str:
    if not claims:
        return "Clinical Data"
    arm = claims[0].treatment_arm
    name = arm.split()[0] if arm else "Clinical Data"
    return name


def _unique_values(claims: list[ClinicalClaim], field: str) -> list[str]:
    return list(dict.fromkeys(getattr(c, field) for c in claims))


def _parse_stat(stat: str) -> float | None:
    cleaned = stat.strip().rstrip("%")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _collect_qualifiers(claims: list[ClinicalClaim]) -> list[str]:
    return list(dict.fromkeys(q for c in claims for q in c.qualifiers))


def _sort_timepoint_key(tp: str) -> tuple[int, float]:
    m = re.match(r"(?:Week|Month|Day|Year)\s+([\d.]+)", tp, re.IGNORECASE)
    if not m:
        return (1, 0.0)
    val = float(m.group(1))
    word = tp.split()[0].lower()
    order = {"day": 0, "week": 1, "month": 2, "year": 3}
    return (0, order.get(word, 1) * 1000 + val)


def _group_by_keys(claims: list[ClinicalClaim], field1: str, field2: str) -> dict[tuple[str, str], list[ClinicalClaim]]:
    groups: dict[tuple[str, str], list[ClinicalClaim]] = {}
    for c in claims:
        key = (getattr(c, field1), getattr(c, field2))
        groups.setdefault(key, []).append(c)
    return groups


def _build_chart_script(canvas_id: str, chart_type: str, labels_json: str, datasets_json: str, title: str | None = None) -> str:
    title_opt = f"title: {{ display: true, text: {json.dumps(title)}, font: {{ size: 14, family: 'Inter', weight: '600' }}, color: '#1a2b4a' }}" if title else ""
    legend_opt = "legend: { labels: { font: { size: 11, family: 'Inter' }, usePointStyle: true, pointStyle: 'circle' } }"
    plugins = f"plugins: {{ {title_opt}{', ' if title_opt else ''}{legend_opt} }}"

    if chart_type == "bar":
        scales = "scales: { y: { grid: { color: 'rgba(148,163,184,0.15)' }, ticks: { font: { size: 11, family: 'Inter' } } }, x: { grid: { display: false }, ticks: { font: { size: 11, family: 'Inter' } } } }"
    else:
        scales = "scales: { y: { grid: { color: 'rgba(148,163,184,0.15)' }, ticks: { font: { size: 11, family: 'Inter' } } }, x: { grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { font: { size: 11, family: 'Inter' } } } }"

    return f"""
new Chart(document.getElementById('{canvas_id}'), {{
  type: '{chart_type}',
  data: {{ labels: {labels_json}, datasets: {datasets_json} }},
  options: {{ responsive: true, {plugins}, {scales} }}
}});"""


def _build_data_table(claims: list[ClinicalClaim]) -> str:
    rows = ""
    for c in claims:
        rows += (
            f"<tr><td>{_esc(c.treatment_arm)}</td><td>{_esc(c.statistic)}</td>"
            f"<td>{_esc(c.context)}</td><td>{_esc(c.sample_size)}</td></tr>\n"
        )
    return (
        '<table><thead><tr><th>Treatment Arm</th><th>Statistic</th>'
        '<th>Context</th><th>Sample Size</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


def _build_citations_section(claims: list[ClinicalClaim]) -> str:
    citations = _unique_values(claims, "citation")
    items = "".join(f'<p class="citation">{_esc(c)}</p>' for c in citations)
    return f'<h2>Citations</h2>{items}'


def _build_qualifiers_section(claims: list[ClinicalClaim]) -> str:
    qualifiers = _collect_qualifiers(claims)
    if not qualifiers:
        return ""
    items = "".join(f'<span class="qualifier">{_esc(q)}</span>' for q in qualifiers)
    return f'<h2>Qualifiers</h2><div>{items}</div>'


def _build_footer(claims: list[ClinicalClaim]) -> str:
    return f'<div class="footer-section">{_build_citations_section(claims)}{_build_qualifiers_section(claims)}</div>'


def render_grouped_bar(claims: list[ClinicalClaim]) -> str:
    drug_name = _extract_drug_name(claims)
    groups = _group_by_keys(claims, "timepoint", "endpoint")

    body_parts = []
    script_parts = []
    chart_idx = 0

    for (timepoint, endpoint), group in groups.items():
        arms = _unique_values(group, "treatment_arm")
        values = [_parse_stat(c.statistic) for c in group]
        colors = [COLORS[i % len(COLORS)] for i, _ in enumerate(arms)]

        canvas_id = f"chart-{chart_idx}"
        body_parts.append(
            f'<div class="card"><h2>{_esc(endpoint)} — {_esc(timepoint)}</h2>'
            f'<canvas id="{canvas_id}"></canvas>'
            f'{_build_data_table(group)}</div>'
        )

        datasets_json = json.dumps([{
            "label": arm,
            "data": [val if val is not None else 0],
            "backgroundColor": color,
            "borderRadius": 6,
            "borderSkipped": False,
        } for arm, val, color in zip(arms, values, colors)])

        title_text = f"{endpoint} — {timepoint}"
        script_parts.append(_build_chart_script(
            canvas_id, "bar", json.dumps([endpoint]), datasets_json, title_text
        ))
        chart_idx += 1

    body_parts.append(_build_footer(claims))

    body = "\n".join(body_parts)
    script = "<script>" + "\n".join(script_parts) + "</script>"
    title = f"{drug_name} Efficacy by Subgroup"
    return _html_skeleton(title, body, script, drug_name=drug_name, variant_label="Efficacy by Subgroup")


def render_timeline(claims: list[ClinicalClaim]) -> str:
    drug_name = _extract_drug_name(claims)
    timepoints = _unique_values(claims, "timepoint")
    single_tp = len(timepoints) <= 1

    if single_tp:
        return _render_timeline_as_bar(claims)

    groups = _group_by_keys(claims, "treatment_arm", "endpoint")

    sorted_tps = sorted(timepoints, key=_sort_timepoint_key)

    body_parts = []
    script_parts = []

    endpoints = _unique_values(claims, "endpoint")
    chart_idx = 0
    for ep in endpoints:
        ep_groups = {k: v for k, v in groups.items() if k[1] == ep}
        canvas_id = f"chart-{chart_idx}"

        datasets = []
        for i, ((arm, _), group) in enumerate(ep_groups.items()):
            tp_map = {c.timepoint: _parse_stat(c.statistic) for c in group}
            data = [tp_map.get(tp, 0) if tp_map.get(tp) is not None else 0 for tp in sorted_tps]
            datasets.append({
                "label": arm,
                "data": data,
                "borderColor": COLORS[i % len(COLORS)],
                "backgroundColor": COLORS[i % len(COLORS)],
                "fill": False,
                "tension": 0.3,
                "pointRadius": 5,
                "pointHoverRadius": 7,
            })

        ep_claims = [c for c in claims if c.endpoint == ep]
        body_parts.append(
            f'<div class="card"><h2>{_esc(ep)}</h2>'
            f'<canvas id="{canvas_id}"></canvas>'
            f'{_build_data_table(ep_claims)}</div>'
        )

        labels_json = json.dumps(sorted_tps)
        datasets_json = json.dumps(datasets)
        script_parts.append(_build_chart_script(
            canvas_id, "line", labels_json, datasets_json, ep
        ))
        chart_idx += 1

    body_parts.append(_build_footer(claims))

    body = "\n".join(body_parts)
    script = "<script>" + "\n".join(script_parts) + "</script>"
    title = f"{drug_name} Response Over Time"
    return _html_skeleton(title, body, script, drug_name=drug_name, variant_label="Response Over Time")


def _render_timeline_as_bar(claims: list[ClinicalClaim]) -> str:
    drug_name = _extract_drug_name(claims)
    arms = _unique_values(claims, "treatment_arm")
    values = [_parse_stat(c.statistic) for c in claims]
    colors = [COLORS[i % len(COLORS)] for i, _ in enumerate(arms)]
    endpoint = claims[0].endpoint if claims else "Data"

    datasets_json = json.dumps([{
        "label": arm,
        "data": [val if val is not None else 0],
        "backgroundColor": color,
        "borderRadius": 6,
        "borderSkipped": False,
    } for arm, val, color in zip(arms, values, colors)])

    body = (
        f'<div class="card"><h2>{_esc(endpoint)}</h2>'
        f'<canvas id="chart-0"></canvas>'
        f'{_build_data_table(claims)}</div>'
        f'{_build_footer(claims)}'
    )
    script = "<script>" + _build_chart_script(
        "chart-0", "bar", json.dumps([endpoint]), datasets_json
    ) + "\n</script>"
    title = f"{drug_name} Response Over Time"
    return _html_skeleton(title, body, script, drug_name=drug_name, variant_label="Response Over Time")


def render_spotlight_cards(claims: list[ClinicalClaim]) -> str:
    drug_name = _extract_drug_name(claims)
    contexts = _unique_values(claims, "context")
    cards = []
    for idx, ctx in enumerate(contexts):
        ctx_claims = [c for c in claims if c.context == ctx]
        hero_claim = ctx_claims[0]
        border_color = ARM_BORDER_COLORS[idx % len(ARM_BORDER_COLORS)]
        stat_items = "".join(
            f'<div class="stat-row">'
            f'<span class="stat-label">{_esc(c.treatment_arm)}</span>'
            f'<span class="stat-value">{_esc(c.statistic)}</span>'
            f'<span class="stat-endpoint">{_esc(c.endpoint)} — {_esc(c.timepoint)}</span>'
            f'</div>'
            for c in ctx_claims
        )
        cards.append(
            f'<div class="spotlight-card" style="border-left: 4px solid {border_color};">'
            f'<div class="spotlight-hero-stat">{_esc(hero_claim.statistic)}</div>'
            f'<div class="spotlight-subtitle">{_esc(hero_claim.treatment_arm)}</div>'
            f'<h3>{_esc(ctx)}</h3>'
            f'{stat_items}'
            f'</div>'
        )

    grid = f'<div class="spotlight-grid">{"".join(cards)}</div>'

    extra_css = """
        .spotlight-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }
        .spotlight-card {
            background: var(--color-surface);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            padding: 28px 32px;
            box-shadow: var(--shadow-card);
            transition: box-shadow 0.3s ease, transform 0.3s ease;
        }
        .spotlight-card:hover {
            box-shadow: var(--shadow-card-hover);
            transform: translateY(-2px);
        }
        .spotlight-hero-stat {
            font-size: 3rem;
            font-weight: 800;
            background: var(--gradient-accent);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.1;
            margin-bottom: 8px;
        }
        .spotlight-subtitle {
            font-size: 0.875rem;
            color: var(--color-text-secondary);
            margin-bottom: 16px;
        }
        .stat-row {
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            gap: 8px;
            padding: 8px 0;
            border-top: 1px solid var(--color-border);
        }
        .stat-label {
            font-size: 0.8rem;
            color: var(--color-text-secondary);
            flex: 1;
        }
        .stat-value {
            font-size: 1rem;
            font-weight: 600;
            color: var(--color-navy);
        }
        .stat-endpoint {
            font-size: 0.75rem;
            color: var(--color-text-muted);
            width: 100%;
        }
    """

    body = (
        f'{grid}'
        f'{_build_footer(claims)}'
    )
    title = f"{drug_name} Clinical Spotlight"
    return _html_skeleton(title, body, "", include_chart_js=False, extra_css=extra_css, drug_name=drug_name, variant_label="Clinical Spotlight")


def render_heatmap(claims: list[ClinicalClaim]) -> str:
    drug_name = _extract_drug_name(claims)
    groups = _group_by_keys(claims, "timepoint", "endpoint")

    all_vals = [_parse_stat(c.statistic) for c in claims if _parse_stat(c.statistic) is not None]
    min_val = min(all_vals) if all_vals else 0
    max_val = max(all_vals) if all_vals else 1
    val_range = max_val - min_val if max_val != min_val else 1

    def _cell_color(stat_str: str) -> str:
        v = _parse_stat(stat_str)
        if v is None:
            return "#FFFFFF"
        t = (v - min_val) / val_range
        r = int(224 + (26 - 224) * t)
        g = int(242 + (43 - 242) * t)
        b = int(254 + (74 - 254) * t)
        return f"rgb({r},{g},{b})"

    def _cell_text_color(stat_str: str) -> str:
        v = _parse_stat(stat_str)
        if v is None:
            return "#1e293b"
        t = (v - min_val) / val_range
        return "#ffffff" if t > 0.6 else "#1a2b4a"

    color_legend = (
        '<div class="color-legend">'
        '<span class="legend-label">Low</span>'
        '<div class="legend-bar"></div>'
        '<span class="legend-label">High</span>'
        '</div>'
    )

    tables = []
    for (timepoint, endpoint), group in groups.items():
        rows = ""
        for c in group:
            bg = _cell_color(c.statistic)
            fg = _cell_text_color(c.statistic)
            rows += (
                f'<tr>'
                f'<td>{_esc(c.treatment_arm)}</td>'
                f'<td style="background-color: {bg}; color: {fg}; font-weight: 600; text-align: center; border-radius: 6px;">{_esc(c.statistic)}</td>'
                f'<td>{_esc(c.context)}</td>'
                f'<td>{_esc(c.sample_size)}</td>'
                f'</tr>\n'
            )
        tables.append(
            f'<div class="card"><h2>{_esc(endpoint)} — {_esc(timepoint)}</h2>'
            f'<table><thead><tr>'
            f'<th>Treatment Arm</th><th>Statistic</th><th>Context</th><th>Sample Size</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
        )

    extra_css = """
        .color-legend {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 24px;
            padding: 12px 16px;
            background: var(--color-surface);
            border-radius: var(--radius-sm);
            border: 1px solid var(--color-border);
            width: fit-content;
        }
        .legend-bar {
            width: 200px;
            height: 12px;
            border-radius: 6px;
            background: linear-gradient(90deg, #e0f2fe 0%, #0d9488 50%, #1a2b4a 100%);
        }
        .legend-label {
            font-size: 0.6875rem;
            font-weight: 600;
            color: var(--color-text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }
    """

    body = (
        f'{color_legend}'
        f'{"".join(tables)}'
        f'{_build_footer(claims)}'
    )
    title = f"{drug_name} Efficacy Matrix"
    return _html_skeleton(title, body, "", include_chart_js=False, extra_css=extra_css, drug_name=drug_name, variant_label="Efficacy Matrix")


def render_infographic(claims: list[ClinicalClaim]) -> str:
    drug_name = _extract_drug_name(claims)
    hero_claim = claims[0] if claims else None

    hero_html = ""
    if hero_claim:
        hero_html = (
            f'<div class="hero">'
            f'<div class="hero-stat">{_esc(hero_claim.statistic)}</div>'
            f'<div class="hero-label">{_esc(hero_claim.treatment_arm)}</div>'
            f'<div class="hero-context">{_esc(hero_claim.endpoint)} — {_esc(hero_claim.context)} — {_esc(hero_claim.timepoint)}</div>'
            f'</div>'
        )

    detail_items = "".join(
        f'<div class="detail-item" style="border-left: 4px solid {COLORS[i % len(COLORS)]};">'
        f'<div class="detail-stat">{_esc(c.statistic)}</div>'
        f'<div class="detail-arm">{_esc(c.treatment_arm)}</div>'
        f'<div class="detail-meta">{_esc(c.endpoint)} — {_esc(c.context)} — {_esc(c.timepoint)}</div>'
        f'</div>'
        for i, c in enumerate(claims)
    )

    values = [_parse_stat(c.statistic) for c in claims]
    colors = [COLORS[i % len(COLORS)] for i, _ in enumerate(claims)]
    labels = [c.treatment_arm for c in claims]

    datasets_json = json.dumps([{
        "label": "Value",
        "data": [v if v is not None else 0 for v in values],
        "backgroundColor": colors,
        "borderRadius": 6,
        "borderSkipped": False,
    }])
    labels_json = json.dumps(labels)

    extra_css = """
        .hero {
            background: var(--gradient-header);
            color: white;
            border-radius: var(--radius);
            padding: 48px 32px;
            text-align: center;
            margin-bottom: 24px;
        }
        .hero-stat {
            font-size: 4rem;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 12px;
        }
        .hero-label {
            font-size: 1.1rem;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        .hero-context {
            font-size: 0.875rem;
            opacity: 0.7;
        }
        .detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .detail-item {
            background: var(--color-surface);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-sm);
            padding: 20px 24px;
            transition: box-shadow 0.3s ease;
        }
        .detail-item:hover {
            box-shadow: var(--shadow-card-hover);
        }
        .detail-stat {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--color-navy);
        }
        .detail-arm {
            font-size: 0.875rem;
            color: var(--color-text);
            margin-top: 4px;
        }
        .detail-meta {
            font-size: 0.75rem;
            color: var(--color-text-muted);
            margin-top: 8px;
        }
    """

    body = (
        f'{hero_html}'
        f'<div class="detail-grid">{detail_items}</div>'
        f'<div class="card"><h2>Summary</h2><canvas id="chart-0"></canvas></div>'
        f'{_build_data_table(claims)}'
        f'{_build_footer(claims)}'
    )

    script = "<script>" + _build_chart_script(
        "chart-0", "bar", labels_json, datasets_json, "Summary"
    ) + "\n</script>"

    title = f"{drug_name} Clinical Overview"
    return _html_skeleton(title, body, script, extra_css=extra_css, drug_name=drug_name, variant_label="Clinical Overview")


def _html_skeleton(title: str, body: str, script: str, *, include_chart_js: bool = True, extra_css: str = "", drug_name: str = "Clinical Data", variant_label: str = "") -> str:
    chart_js_tag = '\n    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>' if include_chart_js else ""
    subtitle_html = f'<div class="subtitle">{_esc(variant_label)}</div>' if variant_label else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>{chart_js_tag}
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {{
            --color-navy: #1a2b4a;
            --color-navy-light: #2d4a7a;
            --color-teal: #0d9488;
            --color-teal-light: #5eead4;
            --color-magenta: #a855f7;
            --color-magenta-light: #e9d5ff;
            --color-rose: #e879a0;
            --color-text: #1e293b;
            --color-text-secondary: #64748b;
            --color-text-muted: #94a3b8;
            --color-surface: rgba(255, 255, 255, 0.72);
            --color-surface-hover: rgba(255, 255, 255, 0.88);
            --color-border: rgba(148, 163, 184, 0.2);
            --gradient-bg: linear-gradient(135deg, #f0e6ff 0%, #e8f0fe 30%, #fce7f3 60%, #e0f2fe 100%);
            --gradient-header: linear-gradient(135deg, #1a2b4a 0%, #2d4a7a 50%, #4a3a6a 100%);
            --gradient-accent: linear-gradient(135deg, #0d9488 0%, #a855f7 100%);
            --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
            --shadow-card-hover: 0 12px 40px rgba(0, 0, 0, 0.1), 0 4px 8px rgba(0, 0, 0, 0.06);
            --radius: 16px;
            --radius-sm: 8px;
            --radius-xs: 4px;
        }}

        *, *::before, *::after {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: var(--color-text);
            background: var(--gradient-bg);
            min-height: 100vh;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}

        .page-header {{
            background: var(--gradient-header);
            padding: 40px 48px 32px;
            margin-bottom: 32px;
        }}

        .page-header h1 {{
            color: white;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            text-transform: uppercase;
            margin: 0;
        }}

        .page-header .subtitle {{
            color: rgba(255,255,255,0.7);
            font-size: 0.875rem;
            font-weight: 400;
            margin-top: 4px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 32px 48px;
        }}

        .card {{
            background: var(--color-surface);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            padding: 28px 32px;
            margin-bottom: 24px;
            box-shadow: var(--shadow-card);
            transition: box-shadow 0.3s ease, transform 0.3s ease;
        }}

        .card:hover {{
            box-shadow: var(--shadow-card-hover);
            transform: translateY(-1px);
        }}

        h2 {{
            font-size: 1.125rem;
            font-weight: 700;
            color: var(--color-navy);
            margin-bottom: 20px;
            letter-spacing: -0.01em;
        }}

        h3 {{
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--color-text-secondary);
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8125rem;
        }}

        th {{
            font-weight: 600;
            text-align: left;
            padding: 10px 16px;
            border-bottom: 2px solid var(--color-navy);
            color: var(--color-navy);
            text-transform: uppercase;
            font-size: 0.6875rem;
            letter-spacing: 0.08em;
        }}

        td {{
            padding: 10px 16px;
            border-bottom: 1px solid var(--color-border);
            color: var(--color-text);
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        .citation {{
            font-size: 0.7rem;
            color: var(--color-text-muted);
            line-height: 1.5;
            margin-top: 8px;
        }}

        .qualifier {{
            display: inline-block;
            background: var(--color-magenta-light);
            color: #7c3aed;
            font-size: 0.6875rem;
            font-weight: 500;
            padding: 4px 12px;
            border-radius: 20px;
            margin-right: 6px;
            margin-bottom: 6px;
        }}

        .footer-section {{
            margin-top: 40px;
            padding-top: 24px;
            border-top: 1px solid var(--color-border);
        }}

        .footer-section h2 {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--color-text-muted);
            margin-bottom: 12px;
        }}

        {extra_css}

        @media print {{
            body {{
                background: white;
            }}
            .page-header {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
            .container {{
                max-width: none;
                padding: 0;
            }}
            .card {{
                box-shadow: none;
                border: 1px solid #ddd;
                break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="page-header">
        <h1>{_esc(drug_name)}</h1>
        {subtitle_html}
    </div>
    <div class="container">
        {body}
    </div>
    {script}
</body>
</html>"""


VARIANT_RENDERERS: dict[str, Callable[[list[ClinicalClaim]], str]] = {
    "grouped_bar": render_grouped_bar,
    "timeline": render_timeline,
    "spotlight_cards": render_spotlight_cards,
    "heatmap": render_heatmap,
    "infographic": render_infographic,
}
