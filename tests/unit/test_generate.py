"""Unit tests for generate_variant() and generate_all_variants()."""

from unittest.mock import patch

import pytest

from pipeline.generate import VARIANT_TYPES, generate_all_variants, generate_variant


def test_variant_types_values():
    assert VARIANT_TYPES == ["grouped_bar", "timeline", "spotlight_cards", "heatmap", "infographic"]


def test_generate_variant_invalid_type_raises(sample_extraction_result):
    with pytest.raises(ValueError, match="Unknown variant_type"):
        generate_variant(sample_extraction_result.claims, "nonexistent")


@pytest.mark.parametrize("variant_type", VARIANT_TYPES)
def test_generate_variant_returns_html(sample_extraction_result, variant_type):
    result = generate_variant(sample_extraction_result.claims, variant_type)
    assert isinstance(result, str)
    assert "<!DOCTYPE html>" in result


def test_generate_all_variants_returns_five(sample_extraction_result):
    results = generate_all_variants(sample_extraction_result.claims)
    assert len(results) == 5
    assert all(isinstance(s, str) for s in results)
    assert all("<!DOCTYPE html>" in s for s in results)


def test_generate_all_variants_return_exceptions_captures_errors(sample_extraction_result):
    def _boom(claims):
        raise RuntimeError("renderer failed")

    with patch.dict("pipeline.templates.VARIANT_RENDERERS", {"grouped_bar": _boom}):
        results = generate_all_variants(sample_extraction_result.claims, return_exceptions=True)

    assert len(results) == 5
    idx = VARIANT_TYPES.index("grouped_bar")
    assert isinstance(results[idx], Exception)
    assert all(isinstance(s, str) for s in results[:idx] + results[idx + 1:])
