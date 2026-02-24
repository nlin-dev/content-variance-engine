"""Unit tests for semantic_compliance() function.

All LLM calls are mocked — no API key required.
"""

from unittest.mock import MagicMock, patch

from pipeline.schemas import ComplianceReport, ExtractionResult


def test_semantic_compliance_returns_compliance_report(sample_extraction_result):
    expected = ComplianceReport(passed=True, flags=[])
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = expected

    with patch("pipeline.semantic._get_chain", return_value=mock_chain):
        from pipeline.semantic import semantic_compliance
        result = semantic_compliance("<html>variant</html>", sample_extraction_result)

    assert isinstance(result, ComplianceReport)
    assert result.passed is True
    assert result.flags == []


def test_semantic_compliance_passes_html_and_claims_to_chain(sample_extraction_result):
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = ComplianceReport(passed=True, flags=[])

    with patch("pipeline.semantic._get_chain", return_value=mock_chain):
        from pipeline.semantic import semantic_compliance
        semantic_compliance("<html>test</html>", sample_extraction_result)

    call_args = mock_chain.invoke.call_args[0][0]
    assert call_args["html_content"] == "<html>test</html>"
    assert "claims_json" in call_args


def test_semantic_chain_uses_structured_output():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = MagicMock()
    mock_chat_openai = MagicMock(return_value=mock_llm)

    import pipeline.semantic
    pipeline.semantic._semantic_chain = None

    with patch("pipeline.semantic.ChatOpenAI", mock_chat_openai):
        pipeline.semantic._get_chain()

    mock_llm.with_structured_output.assert_called_once_with(ComplianceReport)
    pipeline.semantic._semantic_chain = None


def test_semantic_chain_lazy_init():
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = MagicMock()
    mock_chat_openai = MagicMock(return_value=mock_llm)

    import pipeline.semantic
    pipeline.semantic._semantic_chain = None

    with patch("pipeline.semantic.ChatOpenAI", mock_chat_openai):
        pipeline.semantic._get_chain()
        pipeline.semantic._get_chain()

    mock_chat_openai.assert_called_once()
    pipeline.semantic._semantic_chain = None
