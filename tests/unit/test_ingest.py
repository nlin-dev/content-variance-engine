"""Unit tests for pipeline.ingest."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.ingest import extract_pdf_text
from run import _parse_pages


# ---------------------------------------------------------------------------
# _parse_pages
# ---------------------------------------------------------------------------

def test_parse_pages_single():
    assert _parse_pages("3") == [3]


def test_parse_pages_comma_list():
    assert _parse_pages("3,4,5") == [3, 4, 5]


def test_parse_pages_range():
    assert _parse_pages("3-6") == [3, 4, 5, 6]


def test_parse_pages_mixed():
    assert _parse_pages("3-5,9,11") == [3, 4, 5, 9, 11]


# ---------------------------------------------------------------------------
# extract_pdf_text
# ---------------------------------------------------------------------------

def _mock_reader(texts: list[str]):
    """Return a MagicMock PdfReader whose pages return given texts."""
    pages = []
    for t in texts:
        page = MagicMock()
        page.extract_text.return_value = t
        pages.append(page)
    reader = MagicMock()
    reader.pages = pages
    return reader


@patch("pipeline.ingest.PdfReader")
def test_extract_all_pages(mock_reader_cls):
    mock_reader_cls.return_value = _mock_reader(["page one", "page two", "page three"])
    result = extract_pdf_text(Path("dummy.pdf"))
    assert "page one" in result
    assert "page two" in result
    assert "page three" in result


@patch("pipeline.ingest.PdfReader")
def test_extract_specific_pages(mock_reader_cls):
    mock_reader_cls.return_value = _mock_reader(["page one", "page two", "page three"])
    result = extract_pdf_text(Path("dummy.pdf"), pages=[1, 3])
    assert "page one" in result
    assert "page three" in result
    assert "page two" not in result


@patch("pipeline.ingest.PdfReader")
def test_extract_out_of_range_raises(mock_reader_cls):
    mock_reader_cls.return_value = _mock_reader(["only page"])
    with pytest.raises(ValueError, match="out of range"):
        extract_pdf_text(Path("dummy.pdf"), pages=[2])


@patch("pipeline.ingest.PdfReader")
def test_extract_handles_none_text(mock_reader_cls):
    """Pages that return None from extract_text should not raise."""
    page = MagicMock()
    page.extract_text.return_value = None
    reader = MagicMock()
    reader.pages = [page]
    mock_reader_cls.return_value = reader
    result = extract_pdf_text(Path("dummy.pdf"))
    assert result == ""
