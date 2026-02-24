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
    mock_generate.assert_called_once_with(extraction.claims, return_exceptions=True)
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


@patch("pipeline.orchestrator.validate_variant")
@patch("pipeline.orchestrator.generate_all_variants")
@patch("pipeline.orchestrator.extract_claims")
def test_run_pipeline_handles_batch_exceptions(
    mock_extract, mock_generate, mock_validate, tmp_path
):
    from pipeline.generate import VARIANT_TYPES
    from pipeline.orchestrator import run_pipeline

    extraction = _make_extraction(20)
    html1 = "<html>grouped_bar</html>"
    html3 = "<html>spotlight_cards</html>"
    html4 = "<html>heatmap</html>"
    html_variants_with_errors = [
        html1,
        Exception("timeout"),
        html3,
        html4,
        Exception("rate limit"),
    ]

    successful_vts = [VARIANT_TYPES[0], VARIANT_TYPES[2], VARIANT_TYPES[3]]
    successful_htmls = [html1, html3, html4]
    variant_results = [_make_variant_result(vt, html) for vt, html in zip(successful_vts, successful_htmls)]

    mock_extract.return_value = extraction
    mock_generate.return_value = html_variants_with_errors
    mock_validate.side_effect = variant_results

    results = run_pipeline(page_content="test content", output_dir=tmp_path)

    assert len(results) == 3

    assert (tmp_path / "variant_0.html").exists()
    assert not (tmp_path / "variant_1.html").exists()
    assert (tmp_path / "variant_2.html").exists()
    assert (tmp_path / "variant_3.html").exists()
    assert not (tmp_path / "variant_4.html").exists()

    report_data = json.loads((tmp_path / "compliance_report.json").read_text())
    assert len(report_data) == 3


@patch("pipeline.orchestrator.validate_variant")
@patch("pipeline.orchestrator.generate_all_variants")
@patch("pipeline.orchestrator.extract_claims")
def test_run_pipeline_writes_index_html(
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

    index_file = tmp_path / "index.html"
    assert index_file.exists()
    index_content = index_file.read_text()
    assert "variant_0.html" in index_content
    assert "variant_1.html" in index_content


def test_generate_index_html_with_results():
    from pipeline.generate import VARIANT_TYPES
    from pipeline.orchestrator import _generate_index_html
    from pipeline.schemas import ComplianceReport, VariantResult

    passed_report = ComplianceReport(passed=True, flags=[])
    failed_report = ComplianceReport(passed=False, flags=[])

    results_with_index = [
        (0, VariantResult(variant_type=VARIANT_TYPES[0], html="<html/>", programmatic=passed_report, semantic=passed_report, overall_passed=True)),
        (1, VariantResult(variant_type=VARIANT_TYPES[1], html="<html/>", programmatic=failed_report, semantic=failed_report, overall_passed=False)),
        (2, VariantResult(variant_type=VARIANT_TYPES[2], html="<html/>", programmatic=passed_report, semantic=passed_report, overall_passed=True)),
    ]

    html = _generate_index_html(results_with_index, failed_indices=[])

    assert "variant_0.html" in html
    assert "variant_1.html" in html
    assert "variant_2.html" in html
    assert "PASSED" in html
    assert "FAILED" in html
    assert "#22c55e" in html or "green" in html.lower()
    assert "#ef4444" in html or "red" in html.lower()


def test_generate_index_html_with_failures():
    from pipeline.generate import VARIANT_TYPES
    from pipeline.orchestrator import _generate_index_html
    from pipeline.schemas import ComplianceReport, VariantResult

    passed_report = ComplianceReport(passed=True, flags=[])

    results_with_index = [
        (0, VariantResult(variant_type=VARIANT_TYPES[0], html="<html/>", programmatic=passed_report, semantic=passed_report, overall_passed=True)),
        (2, VariantResult(variant_type=VARIANT_TYPES[2], html="<html/>", programmatic=passed_report, semantic=passed_report, overall_passed=True)),
        (4, VariantResult(variant_type=VARIANT_TYPES[4], html="<html/>", programmatic=passed_report, semantic=passed_report, overall_passed=True)),
    ]

    html = _generate_index_html(results_with_index, failed_indices=[1, 3])

    assert "GENERATION FAILED" in html
    assert "variant_1.html" not in html
    assert "variant_3.html" not in html
    assert "variant_0.html" in html
