"""Unit tests for the extract_claims() function.

All LLM calls are mocked — no API key required.
"""

import importlib
from unittest.mock import MagicMock, call, patch

import pytest

from pipeline.schemas import ClinicalClaim, ExtractionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_extract_with_mock_llm():
    """Reload pipeline.extract with ChatOpenAI mocked at the source module.

    Returns (mock_chat_openai, mock_llm, mock_chain, reloaded_module).
    """
    mock_chain = MagicMock()
    mock_structured = MagicMock()
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    mock_chat_openai = MagicMock(return_value=mock_llm)

    with patch.dict("sys.modules", {}):
        with patch("langchain_openai.ChatOpenAI", mock_chat_openai):
            import pipeline.extract
            importlib.reload(pipeline.extract)
            module = pipeline.extract

    return mock_chat_openai, mock_llm, mock_structured, module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_extract_claims_returns_extraction_result(sample_extraction_result):
    """extract_claims() returns an ExtractionResult with the expected claims."""
    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = sample_extraction_result

        # Pipe operator returns mock_chain when prompt | llm.with_structured_output()
        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        # _prompt | mock_structured -> need to intercept the pipe
        # Easier: patch extraction_chain after module reload
        import pipeline.extract
        importlib.reload(pipeline.extract)

    with patch("pipeline.extract.extraction_chain") as mock_ec:
        mock_ec.invoke.return_value = sample_extraction_result
        from pipeline.extract import extract_claims
        result = extract_claims("some source text")

    assert isinstance(result, ExtractionResult)
    assert len(result.claims) == 2
    assert result.claims[0].statistic == "36.2%"
    assert result.claims[0].context == "Non-AT/Non-AU patients"
    assert result.claims[0].timepoint == "Week 24"
    assert result.claims[0].treatment_arm == "Ritlecitinib 50 mg QD (n=130)"
    assert result.claims[1].statistic == "23.0%"
    assert result.claims[1].endpoint == "SALT ≤20"


def test_extract_claims_passes_source_text_to_chain():
    """extract_claims() passes the source text to chain.invoke() as 'source_text' key."""
    mock_result = ExtractionResult(claims=[])

    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        mock_llm.with_structured_output.return_value = MagicMock()

        import pipeline.extract
        importlib.reload(pipeline.extract)

    with patch("pipeline.extract.extraction_chain") as mock_ec:
        mock_ec.invoke.return_value = mock_result
        from pipeline.extract import extract_claims
        extract_claims("specific text here")

    mock_ec.invoke.assert_called_once()
    call_args = mock_ec.invoke.call_args
    assert call_args[0][0]["source_text"] == "specific text here"


def test_extract_claims_uses_correct_model_config():
    """extraction_chain is built with model='gpt-5' and temperature=0."""
    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        mock_llm.with_structured_output.return_value = MagicMock()

        import pipeline.extract
        importlib.reload(pipeline.extract)

    mock_chat_openai.assert_called_once_with(model="gpt-5", temperature=0)


def test_extraction_chain_uses_structured_output():
    """extraction_chain calls .with_structured_output(ExtractionResult)."""
    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        mock_llm.with_structured_output.return_value = MagicMock()

        import pipeline.extract
        importlib.reload(pipeline.extract)

    mock_llm.with_structured_output.assert_called_once_with(ExtractionResult)
