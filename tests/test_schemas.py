"""Tests for Pydantic schemas."""

from pipeline.schemas import (
    ComplianceFlag,
    ComplianceReport,
    VariantResult,
)


class TestVariantResult:
    def test_overall_passed_derived_from_programmatic(self):
        """overall_passed is derived from programmatic.passed."""
        programmatic = ComplianceReport(passed=False, flags=[
            ComplianceFlag(
                flag_type="number_missing",
                severity="error",
                location="36.2%",
                description="Missing statistic"
            )
        ])

        result = VariantResult(
            variant_type="grouped_bar",
            html="<p>Test</p>",
            programmatic=programmatic,
        )

        assert result.overall_passed is False

    def test_overall_passed_true_when_programmatic_passes(self):
        programmatic = ComplianceReport(passed=True, flags=[])

        result = VariantResult(
            variant_type="timeline",
            html="<p>Test</p>",
            programmatic=programmatic,
        )

        assert result.overall_passed is True

    def test_overall_passed_in_model_dump(self):
        programmatic = ComplianceReport(passed=True, flags=[])
        result = VariantResult(
            variant_type="timeline",
            html="<p>Test</p>",
            programmatic=programmatic,
        )
        dumped = result.model_dump()
        assert "overall_passed" in dumped
        assert dumped["overall_passed"] is True
