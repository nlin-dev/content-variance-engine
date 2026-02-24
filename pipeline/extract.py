"""Extraction module — Stage 1 of the content variance pipeline."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from pipeline.schemas import ExtractionResult

EXTRACTION_SYSTEM_PROMPT = (
    "You are a clinical data extraction specialist. "
    "Extract ALL clinical claims from the provided pharmaceutical source text. "
    "For each claim, extract the following fields:\n"
    "- statistic: the exact numerical value or percentage (e.g. '36.2%')\n"
    "- context: the patient population or subgroup described\n"
    "- timepoint: when the measurement was taken (e.g. 'Week 24')\n"
    "- treatment_arm: the treatment group including dosage and sample size notation "
    "(e.g. 'Ritlecitinib 50 mg QD (n=130)')\n"
    "- sample_size: the number of patients in the group (e.g. 'n=130')\n"
    "- citation: the full reference for the source of this claim\n"
    "- qualifiers: list of study limitations, conditions, or qualifiers "
    "(e.g. ['Post hoc analysis', 'Patients aged ≥12 years'])\n"
    "- endpoint: the clinical endpoint measured (e.g. 'SALT ≤20')\n\n"
    "Return ALL claims found — do not summarize or omit any. "
    "Preserve exact numbers and wording from the source text."
)

_prompt = ChatPromptTemplate.from_messages([
    ("system", EXTRACTION_SYSTEM_PROMPT),
    ("human", "{source_text}"),
])

_extraction_chain = None


def _get_chain():
    global _extraction_chain
    if _extraction_chain is None:
        _llm = ChatOpenAI(model="gpt-5-nano")
        _extraction_chain = _prompt | _llm.with_structured_output(ExtractionResult)
    return _extraction_chain


def extract_claims(source_text: str) -> ExtractionResult:
    return _get_chain().invoke({
        "source_text": source_text,
    })
