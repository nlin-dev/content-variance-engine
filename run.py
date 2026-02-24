import sys
from pathlib import Path

from pipeline.orchestrator import run_pipeline


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run.py <page_content_file> [output_dir]")
        sys.exit(1)
    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)
    page_content = input_path.read_text()
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("outputs")
    results = run_pipeline(page_content, output_dir)
    print(f"Pipeline complete. {len(results)} variants generated. Output: {output_dir}")


if __name__ == "__main__":
    main()
