"""Unit tests for validate_variant() — combined compliance orchestrator.

Both compliance functions are mocked.
"""

from unittest.mock import patch

from pipeline.schemas import ComplianceFlag, ComplianceReport, VariantResult


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


def test_both_pass_overall_passed_true(sample_extraction_result):
    with patch("pipeline.validate.run_programmatic_compliance", return_value=_make_report(True)), \
         patch("pipeline.validate.semantic_compliance", return_value=_make_report(True)):
        from pipeline.validate import validate_variant
        result = validate_variant("grouped_bar", "<html></html>", sample_extraction_result)

    assert isinstance(result, VariantResult)
    assert result.overall_passed is True


def test_programmatic_fails_overall_false(sample_extraction_result):
    with patch("pipeline.validate.run_programmatic_compliance", return_value=_failing_report()), \
         patch("pipeline.validate.semantic_compliance", return_value=_make_report(True)):
        from pipeline.validate import validate_variant
        result = validate_variant("grouped_bar", "<html></html>", sample_extraction_result)

    assert result.overall_passed is False


def test_semantic_fails_overall_false(sample_extraction_result):
    with patch("pipeline.validate.run_programmatic_compliance", return_value=_make_report(True)), \
         patch("pipeline.validate.semantic_compliance", return_value=_failing_report()):
        from pipeline.validate import validate_variant
        result = validate_variant("grouped_bar", "<html></html>", sample_extraction_result)

    assert result.overall_passed is False


def test_both_fail_overall_false(sample_extraction_result):
    with patch("pipeline.validate.run_programmatic_compliance", return_value=_failing_report()), \
         patch("pipeline.validate.semantic_compliance", return_value=_failing_report()):
        from pipeline.validate import validate_variant
        result = validate_variant("grouped_bar", "<html></html>", sample_extraction_result)

    assert result.overall_passed is False


def test_passes_correct_args_to_both(sample_extraction_result):
    with patch("pipeline.validate.run_programmatic_compliance", return_value=_make_report(True)) as mock_prog, \
         patch("pipeline.validate.semantic_compliance", return_value=_make_report(True)) as mock_sem:
        from pipeline.validate import validate_variant
        validate_variant("timeline", "<div>test</div>", sample_extraction_result)

    mock_prog.assert_called_once_with("<div>test</div>", sample_extraction_result)
    mock_sem.assert_called_once_with("<div>test</div>", sample_extraction_result)
