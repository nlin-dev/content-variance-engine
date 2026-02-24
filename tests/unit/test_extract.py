"""Unit tests for the extract_claims() function.

All LLM calls are mocked — no API key required.
"""

from unittest.mock import MagicMock, patch

from pipeline.schemas import ExtractionResult


def test_extract_claims_returns_extraction_result(sample_extraction_result):
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = sample_extraction_result

    with patch("pipeline.extract._get_chain", return_value=mock_chain):
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
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = ExtractionResult(claims=[])

    with patch("pipeline.extract._get_chain", return_value=mock_chain):
        from pipeline.extract import extract_claims
        extract_claims("specific text here")

    mock_chain.invoke.assert_called_once_with({"source_text": "specific text here"})


def test_extract_claims_uses_correct_model_config():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = MagicMock()
    mock_chat_openai = MagicMock(return_value=mock_llm)

    import pipeline.extract
    pipeline.extract._extraction_chain = None

    with patch("pipeline.extract.ChatOpenAI", mock_chat_openai):
        pipeline.extract._get_chain()

    mock_chat_openai.assert_called_once_with(model="gpt-5-nano")
    pipeline.extract._extraction_chain = None


def test_extraction_chain_uses_structured_output():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = MagicMock()
    mock_chat_openai = MagicMock(return_value=mock_llm)

    import pipeline.extract
    pipeline.extract._extraction_chain = None

    with patch("pipeline.extract.ChatOpenAI", mock_chat_openai):
        pipeline.extract._get_chain()

    mock_llm.with_structured_output.assert_called_once_with(ExtractionResult)
    pipeline.extract._extraction_chain = None
