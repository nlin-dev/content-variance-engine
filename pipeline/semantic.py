"""Semantic compliance module — LLM-based review of generated variants."""

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from pipeline.schemas import ComplianceReport, ExtractionResult

SEMANTIC_SYSTEM_PROMPT = (
    "You are a pharmaceutical compliance reviewer. "
    "Compare the generated HTML variant against the source clinical claims. "
    "Flag any of the following issues:\n"
    "- claim_expansion: variant adds claims or data not in the source\n"
    "- superiority_implication: variant implies one treatment is better without source support\n"
    "- dropped_qualifier: variant omits important qualifiers from the source\n"
    "- tone_shift: variant uses promotional or exaggerated language not in the source\n"
    "- endpoint_misrepresentation: variant mischaracterizes the clinical endpoint\n\n"
    "For each flag, assign severity 'error' for factual issues or 'warning' for tone issues. "
    "If the variant is faithful to the source, return passed=True with an empty flags list."
)

_prompt = ChatPromptTemplate.from_messages([
    ("system", SEMANTIC_SYSTEM_PROMPT),
    ("human", "Source claims:\n{claims_json}\n\nHTML variant:\n{html_content}"),
])

_semantic_chain = None


def _get_chain():
    global _semantic_chain
    if _semantic_chain is None:
        _llm = ChatOpenAI(model="gpt-5")
        _semantic_chain = _prompt | _llm.with_structured_output(ComplianceReport)
    return _semantic_chain


def semantic_compliance(html_content: str, extraction: ExtractionResult) -> ComplianceReport:
    claims_json = json.dumps([c.model_dump() for c in extraction.claims])
    return _get_chain().invoke({
        "html_content": html_content,
        "claims_json": claims_json,
    })
