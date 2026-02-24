"""Shared test fixtures for the content variance engine."""

import pytest
from pipeline.schemas import ClinicalClaim


@pytest.fixture
def sample_clinical_claim():
    return ClinicalClaim(
        statistic="36.2%",
        context="Non-AT/Non-AU patients",
        timepoint="Week 24",
        treatment_arm="Ritlecitinib 50 mg QD (n=130)",
        sample_size="n=130",
        citation="Zhang X, et al. Poster #P0486 and Abstract #1511. Presented at the 31st Congress of the European Academy of Dermatology and Venereology (EADV). 7–10 September 2022; Milan, Italy.",
        qualifiers=[
            "Post hoc analysis",
            "Patients aged ≥12 years with >50% scalp hair loss",
            "AA includes AT and AU subgroups"
        ],
        endpoint="SALT ≤20"
    )
