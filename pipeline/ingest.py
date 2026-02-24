"""Ingest module — extracts text from a PDF for a given page range."""

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(pdf_path: Path, pages: list[int] | None = None) -> str:
    """Return the combined text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        pages: 1-based page numbers to extract. If None, all pages are extracted.

    Returns:
        Concatenated text from the requested pages, separated by newlines.
    """
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)

    if pages is None:
        indices = range(total)
    else:
        indices = [p - 1 for p in pages]
        out_of_range = [p for p, i in zip(pages, indices) if i < 0 or i >= total]
        if out_of_range:
            raise ValueError(
                f"Page(s) {out_of_range} out of range for PDF with {total} pages"
            )

    parts = [reader.pages[i].extract_text() or "" for i in indices]
    return "\n\n".join(parts).strip()
