import html as html_module
import re
from decimal import Decimal, InvalidOperation

from pipeline.schemas import ClinicalClaim, ComplianceFlag, ComplianceReport, ExtractionResult


def _normalize_number(s: str) -> Decimal | None:
    stripped = s.strip().replace("%", "").strip()
    try:
        return Decimal(stripped)
    except InvalidOperation:
        return None


def _strip_tags(text: str, tags: list[str]) -> str:
    for tag in tags:
        text = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text


def _visible_text(html_content: str) -> str:
    return _strip_tags(html_content, ["style", "script"])


def _extract_percentages(text: str) -> set[Decimal]:
    cleaned = _visible_text(text)
    matches = re.findall(r"(\d+\.?\d*)\s*%", cleaned)
    # 0% and 100% are layout/CSS values, not clinical data
    return {Decimal(m) for m in matches if Decimal(m) not in (Decimal("0"), Decimal("100"))}


def _check_field_present(
    html_content: str,
    claims: list[ClinicalClaim],
    field: str,
    flag_type: str,
    severity: str,
) -> list[ComplianceFlag]:
    seen: set[str] = set()
    flags = []
    for claim in claims:
        value = getattr(claim, field)
        values = value if isinstance(value, list) else [value]
        for v in values:
            if v in seen:
                continue
            seen.add(v)
            if v.lower() not in html_content.lower():
                flags.append(ComplianceFlag(
                    flag_type=flag_type,
                    severity=severity,
                    location=v,
                    description=f"{field.capitalize()} not found in HTML: {v}",
                ))
    return flags


def check_numbers(html_content: str, claims: list[ClinicalClaim]) -> list[ComplianceFlag]:
    visible = _visible_text(html_content)
    flags = []
    for claim in claims:
        stat = claim.statistic
        norm = _normalize_number(stat)
        raw_num = stat.replace("%", "").strip()

        found = raw_num in visible or stat in visible

        if not found and norm is not None:
            for match in re.findall(r"\b(\d+\.?\d*)\s*%?", visible):
                if _normalize_number(match) == norm:
                    found = True
                    break

        if not found:
            flags.append(ComplianceFlag(
                flag_type="number_missing",
                severity="error",
                location=stat,
                description=f"Source statistic {stat} not found in HTML",
            ))
    return flags


def check_citations(html_content: str, claims: list[ClinicalClaim]) -> list[ComplianceFlag]:
    return _check_field_present(html_content, claims, "citation", "citation_missing", "error")


def check_unexpected_numbers(html_content: str, claims: list[ClinicalClaim]) -> list[ComplianceFlag]:
    html_pcts = _extract_percentages(html_content)
    known = {n for c in claims if (n := _normalize_number(c.statistic)) is not None}

    return [
        ComplianceFlag(
            flag_type="unexpected_number",
            severity="error",
            location=f"{pct}%",
            description=f"Percentage {pct}% in HTML not found in source claims",
        )
        for pct in html_pcts if pct not in known
    ]


def check_qualifiers(html_content: str, claims: list[ClinicalClaim]) -> list[ComplianceFlag]:
    return _check_field_present(html_content, claims, "qualifiers", "qualifier_missing", "warning")


def check_endpoints(html_content: str, claims: list[ClinicalClaim]) -> list[ComplianceFlag]:
    return _check_field_present(html_content, claims, "endpoint", "endpoint_missing", "warning")


def run_programmatic_compliance(html_content: str, extraction: ExtractionResult) -> ComplianceReport:
    decoded = html_module.unescape(html_content)
    claims = extraction.claims
    all_flags = (
        check_numbers(decoded, claims)
        + check_citations(decoded, claims)
        + check_unexpected_numbers(decoded, claims)
        + check_qualifiers(decoded, claims)
        + check_endpoints(decoded, claims)
    )
    passed = not any(f.severity == "error" for f in all_flags)
    return ComplianceReport(passed=passed, flags=all_flags)
