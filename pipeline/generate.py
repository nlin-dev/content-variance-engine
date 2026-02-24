"""Generation module — Stage 2 of the content variance pipeline."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from pipeline.schemas import ClinicalClaim

VARIANT_TYPES = ["grouped_bar", "timeline", "spotlight_cards", "heatmap", "infographic"]

GENERATION_SYSTEM_PROMPT = (
    "You are a medical content designer creating self-contained HTML presentations "
    "of clinical trial data for healthcare professionals. "
    "Generate a single, complete HTML page with inline CSS and Chart.js via CDN. "
    "Requirements:\n"
    "- Visible title describing the data and visualization type\n"
    "- All statistics rendered exactly as provided — do not alter any numbers\n"
    "- All qualifiers displayed (e.g. 'Post hoc analysis', patient subgroup notes)\n"
    "- Citations as numbered footnotes at the bottom\n"
    "- No hallucinated statistics, no unsupported claims\n"
    "- Chart.js loaded from: https://cdn.jsdelivr.net/npm/chart.js\n"
)

_prompt = ChatPromptTemplate.from_messages([
    ("system", GENERATION_SYSTEM_PROMPT),
    ("human", "Variant type: {variant_type}\n\nClinical claims (JSON):\n{claims}"),
])

_generation_chain = None


def _get_chain():
    global _generation_chain
    if _generation_chain is None:
        _llm = ChatOpenAI(model="gpt-5")
        _generation_chain = _prompt | _llm | StrOutputParser()
    return _generation_chain


def generate_variant(claims: list[ClinicalClaim], variant_type: str) -> str:
    if variant_type not in VARIANT_TYPES:
        raise ValueError(f"Unknown variant_type: {variant_type!r}")
    return _get_chain().invoke({
        "claims": [c.model_dump() for c in claims],
        "variant_type": variant_type,
    })


def generate_all_variants(
    claims: list[ClinicalClaim], return_exceptions: bool = False
) -> list[str | Exception]:
    inputs = [
        {"claims": [c.model_dump() for c in claims], "variant_type": vt}
        for vt in VARIANT_TYPES
    ]
    return _get_chain().batch(inputs, return_exceptions=return_exceptions)
