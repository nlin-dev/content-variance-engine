from pipeline.compliance import (
    check_numbers, check_citations, check_unexpected_numbers,
    check_qualifiers, check_endpoints, run_programmatic_compliance,
)


class TestCheckNumbers:

    def test_flags_missing_statistic(self, sample_extraction_result):
        html = "<p>Some content without the number</p>"
        flags = check_numbers(html, sample_extraction_result.claims)
        assert any(f.flag_type == "number_missing" and "36.2" in f.location for f in flags)

    def test_finds_statistic_without_percent_sign(self, sample_extraction_result):
        html = "<p>Response rate was 36.2 and 23.0 in the group</p>"
        flags = check_numbers(html, sample_extraction_result.claims)
        assert not [f for f in flags if f.flag_type == "number_missing"]

    def test_finds_statistic_with_spaces(self, sample_extraction_result):
        html = "<p>Response rate was 36.2 % and 23.0 % in the group</p>"
        flags = check_numbers(html, sample_extraction_result.claims)
        assert not [f for f in flags if f.flag_type == "number_missing"]

    def test_normalizes_percentage_comparison(self, sample_extraction_result):
        html = "<p>36.20% and 23.00% response rate</p>"
        flags = check_numbers(html, sample_extraction_result.claims)
        assert not [f for f in flags if f.flag_type == "number_missing"]

    def test_ignores_numbers_in_style_blocks(self, sample_extraction_result):
        html = '<style>width: 36.2%</style><p>Some content</p>'
        flags = check_numbers(html, sample_extraction_result.claims)
        assert any(f.flag_type == "number_missing" for f in flags)


class TestCheckCitations:

    def test_flags_missing_citation(self, sample_extraction_result):
        html = "<p>No citations here</p>"
        flags = check_citations(html, sample_extraction_result.claims)
        assert any(f.flag_type == "citation_missing" for f in flags)

    def test_finds_citation_present(self, sample_extraction_result):
        html = "<p>Zhang X, et al. EADV 2022. King B, et al. Lancet 2023.</p>"
        flags = check_citations(html, sample_extraction_result.claims)
        assert not [f for f in flags if f.flag_type == "citation_missing"]


class TestCheckUnexpectedNumbers:

    def test_flags_hallucinated_percentage(self, sample_extraction_result):
        html = "<p>36.2% and 23.0% and 45.0% response</p>"
        flags = check_unexpected_numbers(html, sample_extraction_result.claims)
        assert any(f.flag_type == "unexpected_number" and "45.0" in f.location for f in flags)

    def test_ignores_100_and_0_percent(self, sample_extraction_result):
        html = "<p>36.2% and 23.0% and 100% and 0%</p>"
        flags = check_unexpected_numbers(html, sample_extraction_result.claims)
        assert not flags

    def test_strips_style_blocks(self, sample_extraction_result):
        html = "<style>width: 45.0%</style><p>36.2% and 23.0%</p>"
        flags = check_unexpected_numbers(html, sample_extraction_result.claims)
        assert not flags

    def test_strips_script_blocks(self, sample_extraction_result):
        html = "<script>var x = 45.0%</script><p>36.2% and 23.0%</p>"
        flags = check_unexpected_numbers(html, sample_extraction_result.claims)
        assert not flags


class TestCheckQualifiers:

    def test_flags_missing_qualifier(self, sample_extraction_result):
        html = "<p>36.2% response rate</p>"
        flags = check_qualifiers(html, sample_extraction_result.claims)
        assert any(f.flag_type == "qualifier_missing" and f.severity == "warning" for f in flags)

    def test_qualifier_present_no_flag(self, sample_extraction_result):
        html = "<p>Post hoc analysis and Subgroup analysis results</p>"
        flags = check_qualifiers(html, sample_extraction_result.claims)
        assert not flags

    def test_qualifier_case_insensitive(self, sample_extraction_result):
        html = "<p>post hoc analysis and subgroup analysis results</p>"
        flags = check_qualifiers(html, sample_extraction_result.claims)
        assert not flags

    def test_qualifier_mixed_case(self, sample_extraction_result):
        html = "<p>POST HOC ANALYSIS and SUBGROUP ANALYSIS results</p>"
        flags = check_qualifiers(html, sample_extraction_result.claims)
        assert not flags


class TestCheckEndpoints:

    def test_flags_missing_endpoint(self, sample_extraction_result):
        html = "<p>Some content without endpoint</p>"
        flags = check_endpoints(html, sample_extraction_result.claims)
        assert any(f.flag_type == "endpoint_missing" and f.severity == "warning" for f in flags)

    def test_endpoint_present_no_flag(self, sample_extraction_result):
        html = "<p>SALT ≤20 responder rate</p>"
        flags = check_endpoints(html, sample_extraction_result.claims)
        assert not flags

    def test_endpoint_case_insensitive(self, sample_extraction_result):
        html = "<p>salt ≤20 responder rate</p>"
        flags = check_endpoints(html, sample_extraction_result.claims)
        assert not flags


class TestRunProgrammaticCompliance:

    def test_full_compliance_pass(self, sample_extraction_result):
        html = (
            "<p>36.2% and 23.0% response rate. "
            "Zhang X, et al. EADV 2022. King B, et al. Lancet 2023. "
            "Post hoc analysis. Subgroup analysis. SALT ≤20</p>"
        )
        report = run_programmatic_compliance(html, sample_extraction_result)
        assert report.passed is True
        assert not report.flags

    def test_full_compliance_fail_on_error(self, sample_extraction_result):
        html = (
            "<p>Only 23.0% here. "
            "Zhang X, et al. EADV 2022. King B, et al. Lancet 2023. "
            "Post hoc analysis. Subgroup analysis. SALT ≤20</p>"
        )
        report = run_programmatic_compliance(html, sample_extraction_result)
        assert report.passed is False
        assert any(f.flag_type == "number_missing" for f in report.flags)

    def test_warnings_dont_fail(self, sample_extraction_result):
        html = (
            "<p>36.2% and 23.0% response rate. "
            "Zhang X, et al. EADV 2022. King B, et al. Lancet 2023. "
            "SALT ≤20</p>"
        )
        report = run_programmatic_compliance(html, sample_extraction_result)
        assert report.passed is True
        assert any(f.severity == "warning" for f in report.flags)

    def test_html_entity_decoding(self, sample_extraction_result):
        html = (
            "<p>36.2% and 23.0% response rate. "
            "Zhang X, et al. EADV 2022. King B, et al. Lancet 2023. "
            "Post hoc analysis. Subgroup analysis. SALT &le;20</p>"
        )
        report = run_programmatic_compliance(html, sample_extraction_result)
        assert report.passed is True
        assert not report.flags
