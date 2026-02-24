"""Combined validation — runs programmatic and semantic compliance."""

from pipeline.compliance import run_programmatic_compliance
from pipeline.schemas import ExtractionResult, VariantResult
from pipeline.semantic import semantic_compliance


def validate_variant(variant_type: str, html: str, extraction: ExtractionResult) -> VariantResult:
    programmatic = run_programmatic_compliance(html, extraction)
    semantic = semantic_compliance(html, extraction)
    return VariantResult(
        variant_type=variant_type,
        html=html,
        programmatic=programmatic,
        semantic=semantic,
        overall_passed=False,  # derived by model_validator
    )
