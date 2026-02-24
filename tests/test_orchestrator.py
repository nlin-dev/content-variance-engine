"""Unit tests for the pipeline orchestrator."""

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from pipeline.schemas import (
    ClinicalClaim,
    ComplianceFlag,
    ComplianceReport,
    ExtractionResult,
    VariantResult,
)


def _make_extraction(n_claims: int) -> ExtractionResult:
    base_claim = ClinicalClaim(
        statistic="36.2%",
        context="Non-AT/Non-AU patients",
        timepoint="Week 24",
        treatment_arm="Ritlecitinib 50 mg QD (n=130)",
        sample_size="n=130",
        citation="Zhang X, et al. EADV 2022.",
        qualifiers=["Post hoc analysis"],
        endpoint="SALT ≤20",
    )
    return ExtractionResult(claims=[base_claim] * n_claims)


def _make_variant_result(variant_type: str, html: str) -> VariantResult:
    report = ComplianceReport(passed=True, flags=[])
    return VariantResult(
        variant_type=variant_type,
        html=html,
        programmatic=report,
        semantic=report,
        overall_passed=True,
    )


@patch("pipeline.orchestrator.validate_variant")
@patch("pipeline.orchestrator.generate_all_variants")
@patch("pipeline.orchestrator.extract_claims")
def test_run_pipeline_calls_stages_in_order(
    mock_extract, mock_generate, mock_validate, tmp_path
):
    from pipeline.generate import VARIANT_TYPES
    from pipeline.orchestrator import run_pipeline

    extraction = _make_extraction(20)
    html_variants = [f"<html>{vt}</html>" for vt in VARIANT_TYPES]
    variant_results = [_make_variant_result(vt, html) for vt, html in zip(VARIANT_TYPES, html_variants)]

    mock_extract.return_value = extraction
    mock_generate.return_value = html_variants
    mock_validate.side_effect = variant_results

    run_pipeline(page_content="test content", output_dir=tmp_path)

    mock_extract.assert_called_once_with("test content")
    mock_generate.assert_called_once_with(extraction.claims)
    assert mock_validate.call_count == 5
    for i, (vt, html) in enumerate(zip(VARIANT_TYPES, html_variants)):
        assert mock_validate.call_args_list[i] == call(vt, html, extraction)


@patch("pipeline.orchestrator.validate_variant")
@patch("pipeline.orchestrator.generate_all_variants")
@patch("pipeline.orchestrator.extract_claims")
def test_run_pipeline_writes_output_files(
    mock_extract, mock_generate, mock_validate, tmp_path
):
    from pipeline.generate import VARIANT_TYPES
    from pipeline.orchestrator import run_pipeline

    extraction = _make_extraction(20)
    html_variants = [f"<html>{vt} content</html>" for vt in VARIANT_TYPES]
    variant_results = [_make_variant_result(vt, html) for vt, html in zip(VARIANT_TYPES, html_variants)]

    mock_extract.return_value = extraction
    mock_generate.return_value = html_variants
    mock_validate.side_effect = variant_results

    run_pipeline(page_content="test content", output_dir=tmp_path)

    # claims.json
    claims_file = tmp_path / "claims.json"
    assert claims_file.exists()
    claims_data = json.loads(claims_file.read_text())
    assert claims_data == extraction.model_dump()

    # variant HTML files
    for i, (vt, html) in enumerate(zip(VARIANT_TYPES, html_variants)):
        variant_file = tmp_path / f"variant_{i}.html"
        assert variant_file.exists()
        assert variant_file.read_text() == html

    # compliance_report.json
    report_file = tmp_path / "compliance_report.json"
    assert report_file.exists()
    report_data = json.loads(report_file.read_text())
    assert len(report_data) == 5
    for entry in report_data:
        assert "html" not in entry


@patch("pipeline.orchestrator.validate_variant")
@patch("pipeline.orchestrator.generate_all_variants")
@patch("pipeline.orchestrator.extract_claims")
def test_run_pipeline_raises_on_few_claims(
    mock_extract, mock_generate, mock_validate, tmp_path
):
    from pipeline.orchestrator import run_pipeline

    extraction = _make_extraction(2)
    mock_extract.return_value = extraction

    with pytest.raises(ValueError, match="2"):
        run_pipeline(page_content="test content", output_dir=tmp_path)

    mock_generate.assert_not_called()
