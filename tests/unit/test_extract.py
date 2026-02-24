"""Unit tests for the extract_claims() function.

All LLM calls are mocked — no API key required.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest

from pipeline.schemas import ClinicalClaim, ExtractionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_extract_with_mock_llm():
    """Reload pipeline.extract with ChatOpenAI mocked at the source module.

    Returns (mock_chat_openai, mock_llm, mock_structured, reloaded_module).
    """
    mock_structured = MagicMock()
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    mock_chat_openai = MagicMock(return_value=mock_llm)

    with patch("langchain_openai.ChatOpenAI", mock_chat_openai):
        import pipeline.extract
        importlib.reload(pipeline.extract)
        module = pipeline.extract

    return mock_chat_openai, mock_llm, mock_structured, module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_extract_claims_returns_extraction_result(sample_extraction_result):
    _mock_chat_openai, _mock_llm, _mock_structured, module = _reload_extract_with_mock_llm()

    with patch.object(module, "_extraction_chain") as mock_ec:
        mock_ec.invoke.return_value = sample_extraction_result
        result = module.extract_claims("some source text")

    assert isinstance(result, ExtractionResult)
    assert len(result.claims) == 2
    assert result.claims[0].statistic == "36.2%"
    assert result.claims[0].context == "Non-AT/Non-AU patients"
    assert result.claims[0].timepoint == "Week 24"
    assert result.claims[0].treatment_arm == "Ritlecitinib 50 mg QD (n=130)"
    assert result.claims[1].statistic == "23.0%"
    assert result.claims[1].endpoint == "SALT ≤20"


def test_extract_claims_passes_source_text_to_chain():
    mock_result = ExtractionResult(claims=[])
    _mock_chat_openai, _mock_llm, _mock_structured, module = _reload_extract_with_mock_llm()

    with patch.object(module, "_extraction_chain") as mock_ec:
        mock_ec.invoke.return_value = mock_result
        module.extract_claims("specific text here")

    mock_ec.invoke.assert_called_once_with({"source_text": "specific text here"})


def test_extract_claims_uses_correct_model_config():
    mock_chat_openai, _mock_llm, _mock_structured, _module = _reload_extract_with_mock_llm()

    mock_chat_openai.assert_called_once_with(model="gpt-5", temperature=0)


def test_extraction_chain_uses_structured_output():
    _mock_chat_openai, mock_llm, _mock_structured, _module = _reload_extract_with_mock_llm()

    mock_llm.with_structured_output.assert_called_once_with(ExtractionResult)
