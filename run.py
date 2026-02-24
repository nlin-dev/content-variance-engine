import argparse
import sys
from pathlib import Path

from pipeline.ingest import extract_pdf_text
from pipeline.orchestrator import run_pipeline


def _parse_pages(pages_str: str) -> list[int]:
    """Parse a comma-separated and/or range page spec like '3-6,9,11' into a list of ints."""
    pages: list[int] = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return pages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Content Variance Engine — generate compliant visual variants from pharma content."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input file: a .pdf (with optional --pages) or a .txt of pre-extracted content.",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        default=Path("outputs"),
        help="Directory to write variant HTML files and reports (default: outputs/).",
    )
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help=(
            "Pages to extract from a PDF input, e.g. '3-6' or '3,4,5,6' or '3-6,9'. "
            "1-based. Ignored for .txt inputs."
        ),
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    suffix = args.input.suffix.lower()

    if suffix == ".pdf":
        pages = _parse_pages(args.pages) if args.pages else None
        print(
            f"Extracting text from {args.input}"
            + (f" (pages {args.pages})" if pages else " (all pages)")
        )
        page_content = extract_pdf_text(args.input, pages=pages)
    elif suffix == ".txt":
        if args.pages:
            print("Warning: --pages is ignored for .txt inputs.")
        page_content = args.input.read_text()
    else:
        print(f"Error: unsupported file type '{suffix}'. Provide a .pdf or .txt file.")
        sys.exit(1)

    results = run_pipeline(page_content, args.output_dir)
    print(f"Pipeline complete. {len(results)} variants generated. Output: {args.output_dir}")


if __name__ == "__main__":
    main()
