"""Unit tests for validate_variant() — programmatic compliance orchestrator."""

from unittest.mock import patch

from pipeline.schemas import ComplianceFlag, ComplianceReport, VariantResult
from pipeline.validate import validate_variant


def _make_report(passed: bool, flags=None) -> ComplianceReport:
    return ComplianceReport(passed=passed, flags=flags or [])


def _failing_report() -> ComplianceReport:
    return ComplianceReport(passed=False, flags=[
        ComplianceFlag(
            flag_type="number_missing",
            severity="error",
            location="36.2%",
            description="Missing statistic",
        )
    ])


def test_programmatic_pass_overall_passed_true(sample_extraction_result):
    with patch("pipeline.validate.run_programmatic_compliance", return_value=_make_report(True)):
        result = validate_variant("grouped_bar", "<html></html>", sample_extraction_result)

    assert isinstance(result, VariantResult)
    assert result.overall_passed is True


def test_programmatic_fails_overall_false(sample_extraction_result):
    with patch("pipeline.validate.run_programmatic_compliance", return_value=_failing_report()):
        result = validate_variant("grouped_bar", "<html></html>", sample_extraction_result)

    assert result.overall_passed is False


def test_passes_correct_args(sample_extraction_result):
    with patch("pipeline.validate.run_programmatic_compliance", return_value=_make_report(True)) as mock_prog:
        validate_variant("timeline", "<div>test</div>", sample_extraction_result)

    mock_prog.assert_called_once_with("<div>test</div>", sample_extraction_result)
