import json
import os
import re

import pytest
from dotenv import load_dotenv

from pipeline.orchestrator import run_pipeline
from tests.integration.test_extract_integration import (
    REQUIRED_CITATIONS,
    REQUIRED_STATISTICS,
    SALT_20_SOURCE_TEXT,
)

load_dotenv()


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_e2e_pipeline(tmp_path):
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    output_dir = tmp_path / "outputs"

    results = run_pipeline(SALT_20_SOURCE_TEXT, output_dir)

    # claims.json
    claims_path = output_dir / "claims.json"
    assert claims_path.exists()
    claims_data = json.loads(claims_path.read_text())
    claims = claims_data["claims"]
    assert 20 <= len(claims) <= 60, f"Unexpected claim count: {len(claims)}"

    statistics_set = {c["statistic"] for c in claims}
    found = [stat for stat in REQUIRED_STATISTICS if any(stat in s for s in statistics_set)]
    coverage = len(found) / len(REQUIRED_STATISTICS)
    assert coverage >= 0.80, (
        f"Only {len(found)}/{len(REQUIRED_STATISTICS)} required statistics found ({coverage:.0%}). "
        f"Missing: {[s for s in REQUIRED_STATISTICS if s not in found]}"
    )

    all_citations_text = " ".join(c["citation"] for c in claims)
    found_citations = [c for c in REQUIRED_CITATIONS if c in all_citations_text]
    assert len(found_citations) >= 2, (
        f"Only {len(found_citations)}/{len(REQUIRED_CITATIONS)} required citations found. "
        f"Missing: {[c for c in REQUIRED_CITATIONS if c not in found_citations]}"
    )

    # HTML variant files
    variant_files = sorted(output_dir.glob("variant_*.html"))
    assert len(variant_files) == len(results), (
        f"Expected {len(results)} variant files, found {len(variant_files)}"
    )
    assert len(results) >= 1, "Expected at least one successful variant"

    # Every variant must contain all statistics from claims.json
    claim_statistics = [c["statistic"] for c in claims]
    for vf in variant_files:
        html = vf.read_text()
        visible = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        visible = re.sub(r"<style[^>]*>.*?</style>", "", visible, flags=re.DOTALL)
        for stat in claim_statistics:
            assert stat in visible, (
                f"{vf.name} missing statistic {stat!r} in visible HTML"
            )
        citation_markers = ["Zhang", "King", "EADV", "Lancet"]
        assert any(m in html for m in citation_markers), (
            f"{vf.name} missing citations"
        )

    # compliance_report.json
    report_path = output_dir / "compliance_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert "compliance_methodology" in report
    assert len(report["results"]) == len(results)
    for entry in report["results"]:
        assert "programmatic" in entry

    # index.html
    index_path = output_dir / "index.html"
    assert index_path.exists()
    assert "Content Variance Engine" in index_path.read_text()
