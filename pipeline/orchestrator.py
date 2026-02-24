"""Orchestrator — wires extract -> generate -> validate and persists outputs."""

import json
import logging
from pathlib import Path

from pipeline.extract import extract_claims
from pipeline.generate import generate_all_variants, VARIANT_TYPES
from pipeline.schemas import VariantResult
from pipeline.validate import validate_variant

logger = logging.getLogger(__name__)


_VARIANT_LABELS: dict[str, tuple[str, str]] = {
    "grouped_bar": ("Efficacy by Subgroup", "Grouped bar charts comparing treatment arms across endpoints and timepoints"),
    "timeline": ("Response Over Time", "Line charts tracking efficacy progression across study timepoints"),
    "spotlight_cards": ("Clinical Spotlight", "Card-based layout highlighting key statistics by patient subgroup"),
    "heatmap": ("Efficacy Matrix", "Color-coded matrix visualizing response rates across arms and subgroups"),
    "infographic": ("Clinical Overview", "Hero statistic with detail grid summarizing all endpoints"),
}

_VARIANT_ICONS: dict[str, str] = {
    "grouped_bar": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="12" width="4" height="9" rx="1"/><rect x="10" y="7" width="4" height="14" rx="1"/><rect x="17" y="3" width="4" height="18" rx="1"/></svg>',
    "timeline": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    "spotlight_cards": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>',
    "heatmap": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>',
    "infographic": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
}

_ACCENT_COLORS = ["#0d9488", "#a855f7", "#e879a0", "#2d4a7a", "#c026d3"]


def _generate_index_html(
    results: list[tuple[int, VariantResult]],
    failed_indices: list[int],
) -> str:
    results_by_index = dict(results)
    all_indices = sorted({i for i, _ in results} | set(failed_indices))

    cards = []
    for i in all_indices:
        vt = VARIANT_TYPES[i]
        label, description = _VARIANT_LABELS.get(vt, (vt.replace("_", " ").title(), ""))
        icon_svg = _VARIANT_ICONS.get(vt, "")
        accent = _ACCENT_COLORS[i % len(_ACCENT_COLORS)]

        if i in failed_indices:
            status_badge = '<span class="badge badge-failed">Failed</span>'
            link_attr = ""
            card_class = "variant-card variant-card--disabled"
        else:
            result = results_by_index[i]
            if result.overall_passed:
                status_badge = '<span class="badge badge-passed">Passed</span>'
            else:
                status_badge = '<span class="badge badge-failed">Failed</span>'
            link_attr = f' onclick="window.location.href=\'variant_{i}.html\'" style="cursor:pointer"'
            card_class = "variant-card"

        cards.append(
            f'<div class="{card_class}"{link_attr}>'
            f'<div class="card-accent" style="background:{accent}"></div>'
            f'<div class="card-body">'
            f'<div class="card-header">'
            f'<div class="card-icon" style="color:{accent}">{icon_svg}</div>'
            f'<div class="card-meta"><span class="card-number">Variant {i}</span>{status_badge}</div>'
            f'</div>'
            f'<h2 class="card-title">{label}</h2>'
            f'<p class="card-description">{description}</p>'
            f'<div class="card-footer">'
            f'<span class="card-type">{vt}</span>'
            f'{"<span class=&quot;card-link&quot;>View &rarr;</span>" if i not in failed_indices else ""}'
            f'</div>'
            f'</div>'
            f'</div>'
        )

    total = len(all_indices)
    passed = sum(1 for i in all_indices if i not in failed_indices and results_by_index.get(i, None) and results_by_index[i].overall_passed)
    failed = len(failed_indices)

    cards_html = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Content Variance Engine</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: #1e293b;
      background: linear-gradient(135deg, #f0e6ff 0%, #e8f0fe 30%, #fce7f3 60%, #e0f2fe 100%);
      min-height: 100vh;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }}

    .page-header {{
      background: linear-gradient(135deg, #1a2b4a 0%, #2d4a7a 50%, #4a3a6a 100%);
      padding: 48px 48px 40px;
    }}

    .page-header h1 {{
      color: white;
      font-size: 2rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      text-transform: uppercase;
      margin-bottom: 4px;
    }}

    .page-header .subtitle {{
      color: rgba(255,255,255,0.6);
      font-size: 0.8125rem;
      font-weight: 400;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .stats-bar {{
      display: flex;
      gap: 32px;
      margin-top: 24px;
    }}

    .stat-chip {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: rgba(255,255,255,0.85);
      font-size: 0.8125rem;
      font-weight: 500;
    }}

    .stat-chip .stat-num {{
      font-size: 1.5rem;
      font-weight: 700;
      color: white;
    }}

    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px;
    }}

    .variant-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 24px;
    }}

    .variant-card {{
      position: relative;
      background: rgba(255, 255, 255, 0.72);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
      transition: box-shadow 0.3s ease, transform 0.3s ease;
    }}

    .variant-card:hover {{
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1), 0 4px 8px rgba(0, 0, 0, 0.06);
      transform: translateY(-2px);
    }}

    .variant-card--disabled {{
      opacity: 0.55;
      pointer-events: none;
    }}

    .card-accent {{
      height: 4px;
      width: 100%;
    }}

    .card-body {{
      padding: 24px 28px 20px;
    }}

    .card-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }}

    .card-icon {{
      width: 36px;
      height: 36px;
      padding: 6px;
      border-radius: 10px;
      background: rgba(148, 163, 184, 0.08);
    }}

    .card-icon svg {{
      width: 100%;
      height: 100%;
    }}

    .card-meta {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .card-number {{
      font-size: 0.6875rem;
      font-weight: 600;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .badge {{
      display: inline-block;
      font-size: 0.6875rem;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 20px;
      letter-spacing: 0.02em;
    }}

    .badge-passed {{
      background: #d1fae5;
      color: #065f46;
    }}

    .badge-failed {{
      background: #fee2e2;
      color: #991b1b;
    }}

    .card-title {{
      font-size: 1.125rem;
      font-weight: 700;
      color: #1a2b4a;
      margin-bottom: 6px;
      letter-spacing: -0.01em;
    }}

    .card-description {{
      font-size: 0.8125rem;
      color: #64748b;
      line-height: 1.5;
      margin-bottom: 20px;
    }}

    .card-footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 16px;
      border-top: 1px solid rgba(148, 163, 184, 0.15);
    }}

    .card-type {{
      font-size: 0.6875rem;
      font-weight: 500;
      color: #94a3b8;
      background: rgba(148, 163, 184, 0.1);
      padding: 3px 10px;
      border-radius: 6px;
      font-family: 'SF Mono', SFMono-Regular, ui-monospace, monospace;
      letter-spacing: 0.02em;
    }}

    .card-link {{
      font-size: 0.8125rem;
      font-weight: 600;
      color: #0d9488;
      letter-spacing: 0.01em;
    }}

    @media (prefers-reduced-motion: reduce) {{
      .variant-card {{ transition: none; }}
    }}

    @media (max-width: 768px) {{
      .page-header {{ padding: 32px 24px 28px; }}
      .page-header h1 {{ font-size: 1.5rem; }}
      .container {{ padding: 20px; }}
      .variant-grid {{ grid-template-columns: 1fr; }}
      .stats-bar {{ gap: 20px; }}
    }}

    @media print {{
      body {{ background: white; }}
      .variant-card {{ box-shadow: none; border: 1px solid #ddd; break-inside: avoid; }}
      .page-header {{ background: #1a2b4a; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    }}
  </style>
</head>
<body>
  <div class="page-header">
    <h1>Content Variance Engine</h1>
    <div class="subtitle">Pipeline Results</div>
    <div class="stats-bar">
      <div class="stat-chip"><span class="stat-num">{total}</span> Variants</div>
      <div class="stat-chip"><span class="stat-num">{passed}</span> Passed</div>
      <div class="stat-chip"><span class="stat-num">{failed}</span> Failed</div>
    </div>
  </div>
  <div class="container">
    <div class="variant-grid">
{cards_html}
    </div>
  </div>
</body>
</html>"""


def run_pipeline(page_content: str, output_dir: Path) -> list[VariantResult]:
    extraction = extract_claims(page_content)

    if len(extraction.claims) < 20:
        raise ValueError(f"Expected >= 20 claims, got {len(extraction.claims)}")

    raw_variants = generate_all_variants(extraction.claims, return_exceptions=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    successful: list[tuple[int, VariantResult]] = []
    failed_indices: list[int] = []

    for i, (vt, item) in enumerate(zip(VARIANT_TYPES, raw_variants)):
        if isinstance(item, Exception):
            logger.warning("Variant %d (%s) failed generation: %s", i, vt, item)
            failed_indices.append(i)
            continue
        try:
            result = validate_variant(vt, item, extraction)
            successful.append((i, result))
            (output_dir / f"variant_{i}.html").write_text(item, encoding="utf-8")
        except Exception as exc:
            logger.warning("Variant %d (%s) failed validation: %s", i, vt, exc)
            failed_indices.append(i)

    (output_dir / "claims.json").write_text(
        json.dumps(extraction.model_dump(), indent=2), encoding="utf-8"
    )

    compliance_report = {
        "compliance_methodology": {
            "programmatic_checks": (
                "Numbers, citations, qualifiers, and endpoints verified "
                "against source claims via automated text matching."
            ),
            "semantic_risk_mitigation": (
                "Semantic risks (claim expansion, tone shift, superiority implications) "
                "are structurally mitigated by template rendering — no generative prose "
                "means no drift surface."
            ),
        },
        "results": [r.model_dump(exclude={"html"}) for _, r in successful],
    }
    (output_dir / "compliance_report.json").write_text(
        json.dumps(compliance_report, indent=2), encoding="utf-8"
    )

    (output_dir / "index.html").write_text(
        _generate_index_html(successful, failed_indices), encoding="utf-8"
    )

    return [r for _, r in successful]
