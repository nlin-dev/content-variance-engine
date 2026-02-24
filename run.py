import sys
from pathlib import Path

from pipeline.orchestrator import run_pipeline


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run.py <page_content_file> [output_dir]")
        sys.exit(1)
    page_content = Path(sys.argv[1]).read_text()
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    results = run_pipeline(page_content, output_dir)
    print(f"Pipeline complete. {len(results)} variants generated. Output: {output_dir}")


if __name__ == "__main__":
    main()
