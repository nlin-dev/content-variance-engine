"""Tests for Pydantic schemas."""

import pytest
from pipeline.schemas import (
    ComplianceFlag,
    ComplianceReport,
    VariantResult,
)


class TestVariantResult:
    def test_overall_passed_derived_from_sub_reports(self):
        """overall_passed is always programmatic.passed AND semantic.passed."""
        programmatic = ComplianceReport(passed=True, flags=[])
        semantic = ComplianceReport(passed=False, flags=[
            ComplianceFlag(
                flag_type="tone_shift",
                severity="warning",
                location="paragraph 1",
                description="Tone is promotional"
            )
        ])

        result = VariantResult(
            variant_type="patient-focused",
            html="<p>Test</p>",
            programmatic=programmatic,
            semantic=semantic,
            overall_passed=True,  # caller sets True, but should be overridden
        )

        assert result.overall_passed is False

    def test_overall_passed_true_when_both_reports_pass(self):
        programmatic = ComplianceReport(passed=True, flags=[])
        semantic = ComplianceReport(passed=True, flags=[])

        result = VariantResult(
            variant_type="clinical",
            html="<p>Test</p>",
            programmatic=programmatic,
            semantic=semantic,
            overall_passed=False,  # caller sets False, but should be overridden
        )

        assert result.overall_passed is True
