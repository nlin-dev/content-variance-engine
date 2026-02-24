"""Unit tests for generate_variant() and generate_all_variants().

All LLM calls are mocked — no API key required.
"""

import importlib
from unittest.mock import MagicMock, patch

from pipeline.generate import VARIANT_TYPES, generate_all_variants, generate_variant


def test_variant_types_values():
    assert VARIANT_TYPES == ["grouped_bar", "timeline", "spotlight_cards", "heatmap", "infographic"]


def test_generate_variant_returns_html_string(sample_extraction_result):
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "<html>mock</html>"

    with patch("pipeline.generate._get_chain", return_value=mock_chain):
        result = generate_variant(sample_extraction_result.claims, "grouped_bar")

    assert result == "<html>mock</html>"


def test_generate_variant_invokes_chain_with_correct_keys(sample_extraction_result):
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "<html>mock</html>"

    with patch("pipeline.generate._get_chain", return_value=mock_chain):
        generate_variant(sample_extraction_result.claims, "grouped_bar")

    call_input = mock_chain.invoke.call_args[0][0]
    assert "claims" in call_input
    assert "variant_type" in call_input


def test_generate_all_variants_returns_five_strings(sample_extraction_result):
    mock_chain = MagicMock()
    mock_chain.batch.return_value = [
        "<html>1</html>", "<html>2</html>", "<html>3</html>",
        "<html>4</html>", "<html>5</html>",
    ]

    with patch("pipeline.generate._get_chain", return_value=mock_chain):
        result = generate_all_variants(sample_extraction_result.claims)

    assert len(result) == 5
    assert all(isinstance(s, str) for s in result)


def test_generate_all_variants_calls_batch_with_five_inputs(sample_extraction_result):
    mock_chain = MagicMock()
    mock_chain.batch.return_value = ["<html></html>"] * 5

    with patch("pipeline.generate._get_chain", return_value=mock_chain):
        generate_all_variants(sample_extraction_result.claims)

    assert mock_chain.batch.call_count == 1
    assert len(mock_chain.batch.call_args[0][0]) == 5


def test_chain_not_instantiated_at_import():
    mock_chat_openai = MagicMock()

    with patch("pipeline.generate.ChatOpenAI", mock_chat_openai):
        import pipeline.generate
        importlib.reload(pipeline.generate)

    mock_chat_openai.assert_not_called()
    pipeline.generate._generation_chain = None
