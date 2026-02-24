"""Orchestrator — wires extract -> generate -> validate and persists outputs."""

import json
from pathlib import Path

from pipeline.extract import extract_claims
from pipeline.generate import generate_all_variants, VARIANT_TYPES
from pipeline.schemas import VariantResult
from pipeline.validate import validate_variant


def _generate_index_html(
    results: list[tuple[int, VariantResult]],
    failed_indices: list[int],
) -> str:
    results_by_index = {i: r for i, r in results}

    all_indices = sorted({i for i, _ in results} | set(failed_indices))
    rows = []
    for i in all_indices:
        vt = VARIANT_TYPES[i]
        if i in failed_indices:
            rows.append(
                f'<tr><td>{i}</td><td>{vt}</td>'
                f'<td style="color:#6b7280">GENERATION FAILED</td><td>—</td></tr>'
            )
        else:
            result = results_by_index[i]
            status_color = "#22c55e" if result.overall_passed else "#ef4444"
            status_text = "PASSED" if result.overall_passed else "FAILED"
            rows.append(
                f'<tr><td>{i}</td><td>{vt}</td>'
                f'<td style="color:{status_color}">{status_text}</td>'
                f'<td><a href="variant_{i}.html">variant_{i}.html</a></td></tr>'
            )

    rows_html = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Content Variance Engine — Pipeline Results</title>
  <style>
    body {{ font-family: sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 1.5rem; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 0.5rem 1rem; border-bottom: 1px solid #e5e7eb; }}
    th {{ background: #f9fafb; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>Content Variance Engine — Pipeline Results</h1>
  <table>
    <thead><tr><th>#</th><th>Variant Type</th><th>Compliance</th><th>File</th></tr></thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
</body>
</html>"""


def run_pipeline(page_content: str, output_dir: Path) -> list[VariantResult]:
    extraction = extract_claims(page_content)

    if len(extraction.claims) < 20:
        raise ValueError(f"Expected >= 20 claims, got {len(extraction.claims)}")

    raw_variants = generate_all_variants(extraction.claims, return_exceptions=True)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    successful: list[tuple[int, VariantResult]] = []
    failed_indices: list[int] = []

    for i, (vt, item) in enumerate(zip(VARIANT_TYPES, raw_variants)):
        if isinstance(item, Exception):
            failed_indices.append(i)
        else:
            result = validate_variant(vt, item, extraction)
            successful.append((i, result))
            (output_dir / f"variant_{i}.html").write_text(item)

    (output_dir / "claims.json").write_text(
        json.dumps(extraction.model_dump(), indent=2)
    )

    (output_dir / "compliance_report.json").write_text(
        json.dumps([r.model_dump(exclude={"html"}) for _, r in successful], indent=2)
    )

    (output_dir / "index.html").write_text(
        _generate_index_html(successful, failed_indices)
    )

    return [r for _, r in successful]
