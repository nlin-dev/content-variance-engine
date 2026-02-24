"""Shared test fixtures for the content variance engine."""

import pytest
from pipeline.schemas import ClinicalClaim, ExtractionResult


@pytest.fixture
def sample_extraction_result():
    return ExtractionResult(claims=[
        ClinicalClaim(
            statistic="36.2%",
            context="Non-AT/Non-AU patients",
            timepoint="Week 24",
            treatment_arm="Ritlecitinib 50 mg QD (n=130)",
            sample_size="n=130",
            citation="Zhang X, et al. EADV 2022.",
            qualifiers=["Post hoc analysis"],
            endpoint="SALT ≤20"
        ),
        ClinicalClaim(
            statistic="23.0%",
            context="AT patients",
            timepoint="Week 24",
            treatment_arm="Ritlecitinib 50 mg QD (n=43)",
            sample_size="n=43",
            citation="King B, et al. Lancet 2023.",
            qualifiers=["Subgroup analysis"],
            endpoint="SALT ≤20"
        ),
    ])
