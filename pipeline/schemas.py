"""Pydantic schemas for the content variance engine pipeline."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClinicalClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    statistic: str = Field(description="The numerical value or percentage")
    context: str = Field(description="The patient population or subgroup")
    timepoint: str = Field(description="When the measurement was taken")
    treatment_arm: str = Field(description="The treatment group including dosage and sample size")
    sample_size: str = Field(description="The number of patients in the group")
    citation: str = Field(description="Full citation for the source of this claim")
    qualifiers: list[str] = Field(description="List of study qualifiers")
    endpoint: str = Field(description="The clinical endpoint measured")


class ExtractionResult(BaseModel):
    claims: list[ClinicalClaim] = Field(
        description="List of ClinicalClaim objects extracted from the source"
    )


class ComplianceFlag(BaseModel):
    model_config = ConfigDict(frozen=True)

    flag_type: Literal[
        # Semantic flags (human review)
        "claim_expansion",
        "superiority_implication",
        "dropped_qualifier",
        "tone_shift",
        "endpoint_misrepresentation",
        # Programmatic flags (automated checks)
        "number_missing",
        "citation_missing",
        "unexpected_number",
        "qualifier_missing",
        "endpoint_missing"
    ] = Field(description="The category of compliance issue")

    severity: Literal["error", "warning"] = Field(
        description="'error' blocks approval, 'warning' flags for review"
    )

    location: str = Field(description="Where in the variant the issue was found")
    description: str = Field(description="Human-readable explanation of the issue")


class ComplianceReport(BaseModel):
    passed: bool = Field(description="Whether the variant passed all compliance checks")
    flags: list[ComplianceFlag] = Field(
        description="List of compliance issues found"
    )


class VariantResult(BaseModel):
    variant_type: str = Field(description="The type of variant generated")
    html: str = Field(description="The generated HTML content")
    programmatic: ComplianceReport = Field(
        description="Results from automated compliance checks"
    )
    semantic: ComplianceReport = Field(
        description="Results from LLM-based semantic review"
    )
    overall_passed: bool = Field(
        description="Whether the variant passed both programmatic and semantic checks"
    )

    @model_validator(mode="after")
    def derive_overall_passed(self) -> "VariantResult":
        object.__setattr__(
            self, "overall_passed", self.programmatic.passed and self.semantic.passed
        )
        return self
