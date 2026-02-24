"""Unit tests for pipeline/templates.py shared helpers and HTML skeleton."""

import json

import pytest
from pipeline.schemas import ClinicalClaim


@pytest.fixture
def sample_claims():
    return [
        ClinicalClaim(
            statistic="36.2%",
            context="Non-AT/Non-AU patients",
            timepoint="Week 24",
            treatment_arm="Ritlecitinib 50 mg QD (n=130)",
            sample_size="n=130",
            citation="Zhang X, et al. EADV 2022.",
            qualifiers=["Post hoc analysis"],
            endpoint="SALT ≤20",
        ),
        ClinicalClaim(
            statistic="23.0%",
            context="AT patients",
            timepoint="Week 24",
            treatment_arm="Ritlecitinib 50 mg QD (n=43)",
            sample_size="n=43",
            citation="King B, et al. Lancet 2023.",
            qualifiers=["Subgroup analysis"],
            endpoint="SALT ≤20",
        ),
    ]


@pytest.fixture
def fabricated_claims():
    """Non-Ritlecitinib claims to verify no hardcoded domain values."""
    return [
        ClinicalClaim(
            statistic="55.1%",
            context="Mild severity",
            timepoint="Month 6",
            treatment_arm="Druganol 100 mg BID (n=200)",
            sample_size="n=200",
            citation="Smith J, et al. NEJM 2025.",
            qualifiers=["ITT population"],
            endpoint="ACR50",
        ),
        ClinicalClaim(
            statistic="12.8%",
            context="Moderate severity",
            timepoint="Month 6",
            treatment_arm="Placebo (n=100)",
            sample_size="n=100",
            citation="Smith J, et al. NEJM 2025.",
            qualifiers=["ITT population", "Exploratory"],
            endpoint="ACR50",
        ),
    ]


# --- _unique_values ---

class TestUniqueValues:
    def test_deduplicates(self, sample_claims):
        from pipeline.templates import _unique_values
        result = _unique_values(sample_claims, "timepoint")
        assert result == ["Week 24"]

    def test_preserves_insertion_order(self, sample_claims):
        from pipeline.templates import _unique_values
        result = _unique_values(sample_claims, "context")
        assert result == ["Non-AT/Non-AU patients", "AT patients"]

    def test_multiple_distinct_values(self, fabricated_claims):
        from pipeline.templates import _unique_values
        result = _unique_values(fabricated_claims, "context")
        assert result == ["Mild severity", "Moderate severity"]


# --- _parse_stat ---

class TestParseStat:
    def test_percentage(self):
        from pipeline.templates import _parse_stat
        assert _parse_stat("36.2%") == 36.2

    def test_plain_number(self):
        from pipeline.templates import _parse_stat
        assert _parse_stat("42") == 42.0

    def test_decimal_without_percent(self):
        from pipeline.templates import _parse_stat
        assert _parse_stat("3.5") == 3.5

    def test_not_reported_returns_none(self):
        from pipeline.templates import _parse_stat
        assert _parse_stat("not reported") is None

    def test_na_returns_none(self):
        from pipeline.templates import _parse_stat
        assert _parse_stat("N/A") is None

    def test_negative_number(self):
        from pipeline.templates import _parse_stat
        assert _parse_stat("-2.5%") == -2.5


# --- _collect_qualifiers ---

class TestCollectQualifiers:
    def test_returns_unique_qualifiers(self, sample_claims):
        from pipeline.templates import _collect_qualifiers
        result = _collect_qualifiers(sample_claims)
        assert set(result) == {"Post hoc analysis", "Subgroup analysis"}

    def test_deduplicates(self, fabricated_claims):
        from pipeline.templates import _collect_qualifiers
        result = _collect_qualifiers(fabricated_claims)
        assert "ITT population" in result
        assert result.count("ITT population") == 1

    def test_preserves_insertion_order(self, fabricated_claims):
        from pipeline.templates import _collect_qualifiers
        result = _collect_qualifiers(fabricated_claims)
        assert result[0] == "ITT population"


# --- _html_skeleton ---

class TestHtmlSkeleton:
    def test_returns_complete_html(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test Title", "<p>hello</p>", "")
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result
        assert "<p>hello</p>" in result

    def test_includes_chart_js_cdn(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test", "<p>x</p>", "")
        assert "chart.js" in result.lower() or "Chart.js" in result or "cdn" in result.lower()

    def test_includes_viewport_meta(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test", "<p>x</p>", "")
        assert "viewport" in result

    def test_includes_css_custom_properties(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test", "<p>x</p>", "")
        assert "--" in result  # CSS custom properties use -- prefix

    def test_title_in_output(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("My Report", "<p>x</p>", "")
        assert "My Report" in result

    def test_max_width_centered(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test", "<p>x</p>", "")
        assert "1200px" in result or "1200" in result

    def test_includes_inter_font(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test", "<p>x</p>", "")
        assert "Inter" in result

    def test_no_external_stylesheets(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test", "<p>x</p>", "")
        # Should not have <link rel="stylesheet"> (except CDN fonts)
        assert 'rel="stylesheet"' not in result or "fonts.googleapis" in result

    def test_includes_print_rules(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test", "<p>x</p>", "")
        assert "@media print" in result

    def test_script_appended(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("Test", "<p>x</p>", "<script>alert(1)</script>")
        assert "<script>alert(1)</script>" in result


# --- Fixtures for Phase 2 ---

@pytest.fixture
def multi_timepoint_claims():
    return [
        ClinicalClaim(
            statistic="36.2%", context="All patients", timepoint="Week 12",
            treatment_arm="Drug A (n=100)", sample_size="n=100",
            citation="Author A. Journal 2024.", qualifiers=["Phase 3"],
            endpoint="Primary Endpoint",
        ),
        ClinicalClaim(
            statistic="45.8%", context="All patients", timepoint="Week 24",
            treatment_arm="Drug A (n=100)", sample_size="n=100",
            citation="Author A. Journal 2024.", qualifiers=["Phase 3"],
            endpoint="Primary Endpoint",
        ),
    ]


@pytest.fixture
def multi_endpoint_claims():
    return [
        ClinicalClaim(
            statistic="36.2%", context="All patients", timepoint="Week 24",
            treatment_arm="Drug A (n=100)", sample_size="n=100",
            citation="Author A. Journal 2024.", qualifiers=["Phase 3"],
            endpoint="Primary Endpoint",
        ),
        ClinicalClaim(
            statistic="22.1%", context="All patients", timepoint="Week 24",
            treatment_arm="Drug A (n=100)", sample_size="n=100",
            citation="Author A. Journal 2024.", qualifiers=["Phase 3"],
            endpoint="Secondary Endpoint",
        ),
    ]


def _unique_contexts(claims):
    seen = {}
    for c in claims:
        if c.context not in seen:
            seen[c.context] = True
    return list(seen)


def _strip_scripts(html: str) -> str:
    import re
    return re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)


# --- render_grouped_bar ---

class TestRenderGroupedBar:
    def test_returns_valid_html(self, sample_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(sample_claims)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result

    def test_statistics_in_visible_html(self, sample_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(sample_claims)
        visible = _strip_scripts(result)
        for claim in sample_claims:
            assert claim.statistic in visible

    def test_citations_present(self, sample_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(sample_claims)
        for claim in sample_claims:
            assert claim.citation in result

    def test_qualifiers_present(self, sample_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(sample_claims)
        for claim in sample_claims:
            for q in claim.qualifiers:
                assert q in result

    def test_endpoints_present(self, sample_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(sample_claims)
        for claim in sample_claims:
            assert claim.endpoint in result

    def test_works_with_sample_claims(self, sample_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(sample_claims)
        assert "<!DOCTYPE html>" in result

    def test_single_timepoint_no_crash(self, sample_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(sample_claims[:1])
        assert "<!DOCTYPE html>" in result

    def test_multiple_endpoints(self, multi_endpoint_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(multi_endpoint_claims)
        assert "Primary Endpoint" in result
        assert "Secondary Endpoint" in result

    def test_deterministic_output(self, sample_claims):
        from pipeline.templates import render_grouped_bar
        a = render_grouped_bar(sample_claims)
        b = render_grouped_bar(sample_claims)
        assert a == b

    def test_no_hardcoded_values(self, fabricated_claims):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar(fabricated_claims)
        visible = _strip_scripts(result)
        for claim in fabricated_claims:
            assert claim.statistic in visible
            assert claim.citation in result
            assert claim.endpoint in result
            for q in claim.qualifiers:
                assert q in result


# --- render_timeline ---

class TestRenderTimeline:
    def test_returns_valid_html(self, sample_claims):
        from pipeline.templates import render_timeline
        result = render_timeline(sample_claims)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result

    def test_statistics_in_visible_html(self, sample_claims):
        from pipeline.templates import render_timeline
        result = render_timeline(sample_claims)
        visible = _strip_scripts(result)
        for claim in sample_claims:
            assert claim.statistic in visible

    def test_citations_present(self, sample_claims):
        from pipeline.templates import render_timeline
        result = render_timeline(sample_claims)
        for claim in sample_claims:
            assert claim.citation in result

    def test_qualifiers_present(self, sample_claims):
        from pipeline.templates import render_timeline
        result = render_timeline(sample_claims)
        for claim in sample_claims:
            for q in claim.qualifiers:
                assert q in result

    def test_endpoints_present(self, sample_claims):
        from pipeline.templates import render_timeline
        result = render_timeline(sample_claims)
        for claim in sample_claims:
            assert claim.endpoint in result

    def test_deterministic_output(self, sample_claims):
        from pipeline.templates import render_timeline
        a = render_timeline(sample_claims)
        b = render_timeline(sample_claims)
        assert a == b

    def test_no_hardcoded_values(self, fabricated_claims):
        from pipeline.templates import render_timeline
        result = render_timeline(fabricated_claims)
        visible = _strip_scripts(result)
        for claim in fabricated_claims:
            assert claim.statistic in visible
            assert claim.citation in result
            assert claim.endpoint in result
            for q in claim.qualifiers:
                assert q in result

    def test_single_timepoint_renders_bar(self, sample_claims):
        from pipeline.templates import render_timeline
        result = render_timeline(sample_claims[:1])
        assert "'bar'" in result or '"bar"' in result

    def test_multi_timepoint_renders_line(self, multi_timepoint_claims):
        from pipeline.templates import render_timeline
        result = render_timeline(multi_timepoint_claims)
        assert "'line'" in result or '"line"' in result


# --- render_spotlight_cards ---

class TestRenderSpotlightCards:
    def test_statistics_in_visible_html(self, sample_claims):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards(sample_claims)
        visible = _strip_scripts(result)
        for claim in sample_claims:
            assert claim.statistic in visible

    def test_citations_present(self, sample_claims):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards(sample_claims)
        for claim in sample_claims:
            assert claim.citation in result

    def test_qualifiers_present(self, sample_claims):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards(sample_claims)
        for claim in sample_claims:
            for q in claim.qualifiers:
                assert q in result

    def test_endpoints_present(self, sample_claims):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards(sample_claims)
        for claim in sample_claims:
            assert claim.endpoint in result

    def test_works_with_fabricated_claims(self, fabricated_claims):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards(fabricated_claims)
        visible = _strip_scripts(result)
        for claim in fabricated_claims:
            assert claim.statistic in visible
            assert claim.citation in result
            assert claim.endpoint in result
            for q in claim.qualifiers:
                assert q in result

    def test_deterministic_output(self, sample_claims):
        from pipeline.templates import render_spotlight_cards
        a = render_spotlight_cards(sample_claims)
        b = render_spotlight_cards(sample_claims)
        assert a == b

    def test_one_card_per_context(self, sample_claims):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards(sample_claims)
        contexts = _unique_contexts(sample_claims)
        assert result.count('class="spotlight-card"') == len(contexts)

    def test_no_chart_js(self, sample_claims):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards(sample_claims)
        assert "cdn.jsdelivr.net/npm/chart.js" not in result


# --- render_heatmap ---

class TestRenderHeatmap:
    def test_statistics_in_visible_html(self, sample_claims):
        from pipeline.templates import render_heatmap
        result = render_heatmap(sample_claims)
        visible = _strip_scripts(result)
        for claim in sample_claims:
            assert claim.statistic in visible

    def test_citations_present(self, sample_claims):
        from pipeline.templates import render_heatmap
        result = render_heatmap(sample_claims)
        for claim in sample_claims:
            assert claim.citation in result

    def test_qualifiers_present(self, sample_claims):
        from pipeline.templates import render_heatmap
        result = render_heatmap(sample_claims)
        for claim in sample_claims:
            for q in claim.qualifiers:
                assert q in result

    def test_endpoints_present(self, sample_claims):
        from pipeline.templates import render_heatmap
        result = render_heatmap(sample_claims)
        for claim in sample_claims:
            assert claim.endpoint in result

    def test_works_with_fabricated_claims(self, fabricated_claims):
        from pipeline.templates import render_heatmap
        result = render_heatmap(fabricated_claims)
        visible = _strip_scripts(result)
        for claim in fabricated_claims:
            assert claim.statistic in visible
            assert claim.citation in result
            assert claim.endpoint in result
            for q in claim.qualifiers:
                assert q in result

    def test_deterministic_output(self, sample_claims):
        from pipeline.templates import render_heatmap
        a = render_heatmap(sample_claims)
        b = render_heatmap(sample_claims)
        assert a == b

    def test_no_chart_js(self, sample_claims):
        from pipeline.templates import render_heatmap
        result = render_heatmap(sample_claims)
        assert "cdn.jsdelivr.net/npm/chart.js" not in result

    def test_cell_colors_from_data(self, sample_claims):
        from pipeline.templates import render_heatmap
        result = render_heatmap(sample_claims)
        assert "background-color" in result


# --- render_infographic ---

class TestRenderInfographic:
    def test_statistics_in_visible_html(self, sample_claims):
        from pipeline.templates import render_infographic
        result = render_infographic(sample_claims)
        visible = _strip_scripts(result)
        for claim in sample_claims:
            assert claim.statistic in visible

    def test_citations_present(self, sample_claims):
        from pipeline.templates import render_infographic
        result = render_infographic(sample_claims)
        for claim in sample_claims:
            assert claim.citation in result

    def test_qualifiers_present(self, sample_claims):
        from pipeline.templates import render_infographic
        result = render_infographic(sample_claims)
        for claim in sample_claims:
            for q in claim.qualifiers:
                assert q in result

    def test_endpoints_present(self, sample_claims):
        from pipeline.templates import render_infographic
        result = render_infographic(sample_claims)
        for claim in sample_claims:
            assert claim.endpoint in result

    def test_works_with_fabricated_claims(self, fabricated_claims):
        from pipeline.templates import render_infographic
        result = render_infographic(fabricated_claims)
        visible = _strip_scripts(result)
        for claim in fabricated_claims:
            assert claim.statistic in visible
            assert claim.citation in result
            assert claim.endpoint in result
            for q in claim.qualifiers:
                assert q in result

    def test_deterministic_output(self, sample_claims):
        from pipeline.templates import render_infographic
        a = render_infographic(sample_claims)
        b = render_infographic(sample_claims)
        assert a == b

    def test_hero_section_present(self, sample_claims):
        from pipeline.templates import render_infographic
        result = render_infographic(sample_claims)
        assert 'class="hero"' in result

    def test_chart_js_present(self, sample_claims):
        from pipeline.templates import render_infographic
        result = render_infographic(sample_claims)
        assert "cdn.jsdelivr.net/npm/chart.js" in result


# ---------------------------------------------------------------------------
# New tests below — added by agent; do NOT modify tests above this line.
# ---------------------------------------------------------------------------

from html import escape as _html_escape


def _maybe_escaped(val: str) -> tuple[str, str]:
    """Return (raw, escaped) so assertions can tolerate either form."""
    return val, _html_escape(val)


# --- _sort_timepoint_key ---

class TestSortTimepointKey:
    def test_week_ordering(self):
        from pipeline.templates import _sort_timepoint_key
        assert _sort_timepoint_key("Week 12") < _sort_timepoint_key("Week 24")

    def test_day_before_week(self):
        from pipeline.templates import _sort_timepoint_key
        assert _sort_timepoint_key("Day 7") < _sort_timepoint_key("Week 1")

    def test_month_before_year(self):
        from pipeline.templates import _sort_timepoint_key
        assert _sort_timepoint_key("Month 6") < _sort_timepoint_key("Year 1")

    def test_unrecognized_falls_back(self):
        from pipeline.templates import _sort_timepoint_key
        # Unrecognized strings get (1, 0.0) — sorts after any recognized timepoint
        assert _sort_timepoint_key("Baseline") > _sort_timepoint_key("Week 1")


# --- _html_skeleton params ---

class TestHtmlSkeletonParams:
    def test_exclude_chart_js(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("T", "<p>x</p>", "", include_chart_js=False)
        assert "cdn.jsdelivr.net/npm/chart.js" not in result

    def test_include_chart_js_default(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("T", "<p>x</p>", "")
        assert "cdn.jsdelivr.net/npm/chart.js" in result

    def test_extra_css_injected(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("T", "<p>x</p>", "", extra_css=".custom { color: red; }")
        assert ".custom { color: red; }" in result

    def test_extra_css_empty_by_default(self):
        from pipeline.templates import _html_skeleton
        result = _html_skeleton("T", "<p>x</p>", "")
        # No extra_css means no additional style block beyond the base
        assert result.count("<style>") == 1


# --- _build_data_table ---

class TestBuildDataTable:
    def test_contains_all_fields(self, sample_claims):
        from pipeline.templates import _build_data_table
        result = _build_data_table(sample_claims)
        for c in sample_claims:
            assert any(v in result for v in _maybe_escaped(c.treatment_arm))
            assert any(v in result for v in _maybe_escaped(c.statistic))
            assert any(v in result for v in _maybe_escaped(c.context))
            assert any(v in result for v in _maybe_escaped(c.sample_size))

    def test_table_structure(self, sample_claims):
        from pipeline.templates import _build_data_table
        result = _build_data_table(sample_claims)
        assert "<table>" in result
        assert "<thead>" in result
        assert "<tbody>" in result
        # +1 for the header row in <thead>
        assert result.count("<tr>") == len(sample_claims) + 1

    def test_single_claim(self, sample_claims):
        from pipeline.templates import _build_data_table
        result = _build_data_table(sample_claims[:1])
        assert "<tr>" in result


# --- Empty claims ---

class TestEmptyClaims:
    def test_grouped_bar_empty(self):
        from pipeline.templates import render_grouped_bar
        result = render_grouped_bar([])
        assert "<!DOCTYPE html>" in result

    def test_timeline_empty(self):
        from pipeline.templates import render_timeline
        result = render_timeline([])
        assert "<!DOCTYPE html>" in result

    def test_spotlight_cards_empty(self):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards([])
        assert "<!DOCTYPE html>" in result

    def test_heatmap_empty(self):
        from pipeline.templates import render_heatmap
        result = render_heatmap([])
        assert "<!DOCTYPE html>" in result

    def test_infographic_empty(self):
        from pipeline.templates import render_infographic
        result = render_infographic([])
        assert "<!DOCTYPE html>" in result


# --- Phase 3 valid HTML ---

class TestPhase3ValidHtml:
    def test_spotlight_cards_valid_html(self, sample_claims):
        from pipeline.templates import render_spotlight_cards
        result = render_spotlight_cards(sample_claims)
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result

    def test_heatmap_valid_html(self, sample_claims):
        from pipeline.templates import render_heatmap
        result = render_heatmap(sample_claims)
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result

    def test_infographic_valid_html(self, sample_claims):
        from pipeline.templates import render_infographic
        result = render_infographic(sample_claims)
        assert "<!DOCTYPE html>" in result
        assert "</html>" in result


# --- HTML escaping (XSS prevention) ---

class TestHtmlEscaping:
    def test_xss_in_treatment_arm(self):
        from pipeline.templates import render_grouped_bar
        evil_claim = ClinicalClaim(
            statistic="50%", context="All", timepoint="Week 1",
            treatment_arm='<script>alert("xss")</script>',
            sample_size="n=100", citation="Test 2025.",
            qualifiers=["Phase 3"], endpoint="Primary",
        )
        result = render_grouped_bar([evil_claim])
        assert '<script>alert("xss")</script>' not in _strip_scripts(result)
        assert "&lt;script&gt;" in result

    def test_single_quote_in_endpoint_js(self):
        from pipeline.templates import render_grouped_bar
        claim = ClinicalClaim(
            statistic="50%", context="All", timepoint="Week 1",
            treatment_arm="Drug A (n=100)", sample_size="n=100",
            citation="Test 2025.", qualifiers=["Phase 3"],
            endpoint="Patient's Global Assessment",
        )
        result = render_grouped_bar([claim])
        # Should not break JS — endpoint should be JSON-encoded in script
        assert "<!DOCTYPE html>" in result


# --- Non-parseable statistics ---

class TestNonParseableStat:
    def test_not_reported_in_grouped_bar(self):
        from pipeline.templates import render_grouped_bar
        claim = ClinicalClaim(
            statistic="not reported", context="All", timepoint="Week 1",
            treatment_arm="Drug A (n=100)", sample_size="n=100",
            citation="Test 2025.", qualifiers=[], endpoint="Primary",
        )
        result = render_grouped_bar([claim])
        visible = _strip_scripts(result)
        assert "not reported" in visible
