"""Validation — runs programmatic compliance checks against source claims."""

from pipeline.compliance import run_programmatic_compliance
from pipeline.schemas import ExtractionResult, VariantResult


def validate_variant(variant_type: str, html: str, extraction: ExtractionResult) -> VariantResult:
    programmatic = run_programmatic_compliance(html, extraction)
    return VariantResult(
        variant_type=variant_type,
        html=html,
        programmatic=programmatic,
    )
