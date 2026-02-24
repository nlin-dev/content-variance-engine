"""Orchestrator — wires extract -> generate -> validate and persists outputs."""

import json
from pathlib import Path

from pipeline.extract import extract_claims
from pipeline.generate import generate_all_variants, VARIANT_TYPES
from pipeline.schemas import VariantResult
from pipeline.validate import validate_variant


def run_pipeline(page_content: str, output_dir: Path) -> list[VariantResult]:
    extraction = extract_claims(page_content)

    if len(extraction.claims) < 20:
        raise ValueError(f"Expected >= 20 claims, got {len(extraction.claims)}")

    html_variants = generate_all_variants(extraction.claims)
    results = [
        validate_variant(vt, html, extraction)
        for vt, html in zip(VARIANT_TYPES, html_variants)
    ]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "claims.json").write_text(
        json.dumps(extraction.model_dump(), indent=2)
    )

    for i, html in enumerate(html_variants):
        (output_dir / f"variant_{i}.html").write_text(html)

    (output_dir / "compliance_report.json").write_text(
        json.dumps([r.model_dump(exclude={"html"}) for r in results], indent=2)
    )

    return results
