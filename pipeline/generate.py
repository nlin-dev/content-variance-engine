"""Generation module — Stage 2 of the content variance pipeline."""

from pipeline.schemas import ClinicalClaim
from pipeline.templates import VARIANT_RENDERERS

VARIANT_TYPES = list(VARIANT_RENDERERS.keys())


def generate_variant(claims: list[ClinicalClaim], variant_type: str) -> str:
    if variant_type not in VARIANT_RENDERERS:
        raise ValueError(f"Unknown variant_type: {variant_type!r}")
    return VARIANT_RENDERERS[variant_type](claims)


def generate_all_variants(
    claims: list[ClinicalClaim], return_exceptions: bool = False
) -> list[str | Exception]:
    results: list[str | Exception] = []
    for vt in VARIANT_TYPES:
        try:
            results.append(generate_variant(claims, vt))
        except Exception as e:
            if return_exceptions:
                results.append(e)
            else:
                raise
    return results
