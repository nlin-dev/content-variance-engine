import importlib
import os

import pytest
from dotenv import load_dotenv

load_dotenv()

SALT_20_SOURCE_TEXT = """
SALT ≤20 Efficacy Results — Ritlecitinib Phase 2b/3 (ALLEGRO) Trial

Dose/Subgroup data (SALT ≤20 response rates):

Ritlecitinib 50 mg QD:
  Non-AT/AU: Week 24 = 36.2%, Week 48 = 52.9%
  AT: Week 24 = 7.4%, Week 48 = 22.2%
  AU: Week 24 = 9.1%, Week 48 = 40.9%

Ritlecitinib 30 mg QD:
  Non-AT/AU: Week 24 = 20.6%, Week 48 = 45.3%
  AT: Week 24 = 7.7%, Week 48 = 19.2%
  AU: Week 24 = 8.0%, Week 48 = 11.5%

Ritlecitinib 200/50 mg QD:
  Non-AT/AU: Week 24 = 44.8%, Week 48 = 54.3%
  AT: Week 24 = 20.8%, Week 48 = 20.0%
  AU: Week 24 = 4.2%, Week 48 = 20.0%

Ritlecitinib 200/30 mg QD:
  Non-AT/AU: Week 24 = 31.3%, Week 48 = 41.8%
  AT: Week 24 = 9.7%, Week 48 = 26.7%
  AU: Week 24 = 9.5%, Week 48 = 20.0%

Primary endpoint (SALT ≤20 at Week 24):
  50 mg = 23%, 30 mg = 14%, 200/50 mg = 31%, 200/30 mg = 22%

Episode duration subgroup (SALT ≤20 at Week 48):
  50 mg: <1 year = 50.0% (N=30), ≥1 year = 39.0% (N=100)
  30 mg: <1 year = 42.3% (N=26), ≥1 year = 23.6% (N=106)
  200/50 mg: <1 year = 59.4% (N=32), ≥1 year = 32.3% (N=99)
  200/30 mg: <1 year = 35.7% (N=28), ≥1 year = 31.7% (N=101)

Citations:
Zhang X, et al. Poster #P0486 and Abstract #1511. EADV 31st Congress. 7–10 September 2022; Milan, Italy.
King B, et al. Lancet. 2023 [In Press, doi: 10.1016/S0140-6736(23)00222-2].
King B, et al. Poster #P0485. EADV 31st Congress. 7–10 September 2022; Milan, Italy.

Qualifiers: Post hoc analysis. Patients aged ≥12 years. AT = alopecia totalis; AU = alopecia universalis.
"""

REQUIRED_STATISTICS = [
    "36.2%", "52.9%", "7.4%", "22.2%", "9.1%", "40.9%",
    "20.6%", "45.3%", "7.7%", "19.2%", "8.0%", "11.5%",
    "44.8%", "54.3%", "20.8%", "20.0%", "4.2%",
    "31.3%", "41.8%", "9.7%", "26.7%", "9.5%",
    "23%", "14%", "31%", "22%",
]

REQUIRED_CITATIONS = [
    "Zhang X, et al. Poster #P0486 and Abstract #1511. EADV 31st Congress. 7–10 September 2022; Milan, Italy.",
    "King B, et al. Lancet. 2023 [In Press, doi: 10.1016/S0140-6736(23)00222-2].",
    "King B, et al. Poster #P0485. EADV 31st Congress. 7–10 September 2022; Milan, Italy.",
]


@pytest.mark.integration
def test_extract_claims_integration():
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    extract_mod = importlib.import_module("pipeline.extract")
    schemas_mod = importlib.import_module("pipeline.schemas")
    extract_claims = extract_mod.extract_claims
    ExtractionResult = schemas_mod.ExtractionResult

    result = extract_claims(SALT_20_SOURCE_TEXT)

    assert isinstance(result, ExtractionResult)
    # GPT-5 extracts one claim per data point; empirically returns 40-55 for this source text
    assert 20 <= len(result.claims) <= 60

    for claim in result.claims:
        assert claim.statistic, f"Empty statistic in claim: {claim}"
        assert claim.citation, f"Empty citation in claim: {claim}"
        assert claim.endpoint, f"Empty endpoint in claim: {claim}"
        assert claim.qualifiers, f"Empty qualifiers in claim: {claim}"

    all_statistics = {claim.statistic for claim in result.claims}
    for stat in REQUIRED_STATISTICS:
        assert any(stat in s for s in all_statistics), f"Required statistic not found: {stat}"

    all_citations = " ".join(claim.citation for claim in result.claims)
    for citation in REQUIRED_CITATIONS:
        assert citation in all_citations, f"Required citation not found: {citation}"
