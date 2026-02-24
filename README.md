# Content Variance Engine

Pharma compliance pipeline that extracts structured clinical claims from source documents, renders them into multiple HTML visualization formats, and validates each output against the source data through programmatic compliance checks.

The core design choice: all HTML generation uses deterministic template rendering rather than generative prose. This eliminates the semantic drift surface entirely. The LLM is only used once, at the extraction boundary, to pull structured data from unstructured text. Everything downstream is pure computation.

## Architecture

```
PDF or .txt
    |
    v
[Ingest] -- pypdf page extraction --> raw text
    |
    v
[Extract] -- GPT-5-nano w/ structured output --> ExtractionResult (list[ClinicalClaim])
    |
    v
[Generate] -- 5 template renderers --> HTML strings (no LLM involved)
    |
    v
[Validate] -- programmatic checks --> ComplianceReport per variant
    |
    v
[Orchestrate] -- persist outputs, handle partial failures --> outputs/
```

### Pipeline Stages

**Ingest** (`pipeline/ingest.py`): Extracts raw text from a PDF using `pypdf`. Accepts an optional list of 1-based page numbers so you can scope ingestion to a specific section rather than processing the whole document. Passing a `.txt` file skips this stage entirely.

**Extract** (`pipeline/extract.py`): Calls GPT-5-nano via LangChain's `with_structured_output` to parse source text into `ClinicalClaim` Pydantic models. Each claim captures statistic, context, timepoint, treatment arm, sample size, citation, qualifiers, and endpoint. The orchestrator enforces a minimum of 20 claims as a completeness gate.

**Generate** (`pipeline/generate.py`, `pipeline/templates.py`): Pure Python template renderers, one per variant type. No LLM calls. The five variant types:

| Variant | Visualization | Best for |
|---------|--------------|----------|
| `grouped_bar` | Bar charts by timepoint x endpoint | Treatment arm comparison |
| `timeline` | Line charts over time | Temporal response trends |
| `spotlight_cards` | Card grid with colored borders | Subgroup narratives |
| `heatmap` | Color-coded efficacy matrix | Dense cross-tabulation |
| `infographic` | Hero stat + detail grid + chart | Executive overview |

All variants use Chart.js (CDN), responsive CSS grid, and include raw data tables for transparency.

**Validate** (`pipeline/validate.py`, `pipeline/compliance.py`): Runs five checks against each HTML variant:

| Check | Severity | What it catches |
|-------|----------|----------------|
| `check_numbers` | error | Source statistics missing from output |
| `check_citations` | error | Citations dropped during rendering |
| `check_unexpected_numbers` | error | Percentages in HTML not traceable to source (hallucination detection) |
| `check_qualifiers` | warning | Study limitations not surfaced |
| `check_endpoints` | warning | Clinical endpoints omitted |

A variant passes if it has zero error-severity flags. Warnings are logged but don't block.

**Orchestrate** (`pipeline/orchestrator.py`): Wires the stages together. Handles partial failures: if variant 3 throws during generation or validation, variants 0-2 and 4 still get written. Produces `index.html` as a status dashboard linking to each variant with compliance status.

## Data Model

```python
ClinicalClaim      # frozen Pydantic model, one per extracted data point
ExtractionResult   # wrapper holding list[ClinicalClaim]
ComplianceFlag     # typed flag with severity (error|warning) and location
ComplianceReport   # passed: bool + flags: list[ComplianceFlag]
VariantResult      # variant_type + html + ComplianceReport, computed overall_passed
```

All models in `pipeline/schemas.py`. `ClinicalClaim` is frozen (immutable) to prevent accidental mutation between pipeline stages.

## Outputs

```
outputs/
  variant_0.html           # grouped_bar
  variant_1.html           # timeline
  variant_2.html           # spotlight_cards
  variant_3.html           # heatmap
  variant_4.html           # infographic
  claims.json              # serialized ExtractionResult
  compliance_report.json   # per-variant compliance results + methodology
  index.html               # dashboard with links and status
```

## Usage

Requires `OPENAI_API_KEY` in environment or `.env`. `output_dir` defaults to `outputs/`.

**Run against a PDF, scoped to specific pages:**

```
python run.py source/ritlecitinib-fast-facts.pdf --pages 3-6
```

Page ranges follow standard notation: `3-6` expands to pages 3, 4, 5, 6. Comma-separated values and mixed formats also work:

```
python run.py source/ritlecitinib-fast-facts.pdf --pages 3-6,9,11
```

Omitting `--pages` processes the entire PDF.

**Run against pre-extracted text:**

```
python run.py source/page_content.txt
```

**Specify a custom output directory:**

```
python run.py source/ritlecitinib-fast-facts.pdf --pages 3-6 outputs/salt-section
```

## Source files

```
source/
  ritlecitinib-fast-facts.pdf   # Pfizer Dermatology Fast Facts (full document)
  page_content.txt               # pre-extracted SALT ≤20 section (pages 3-6)
```

## Testing

```
pytest                          # unit tests only (LLM calls mocked)
pytest -m integration           # integration tests (requires API key)
```

Test layout mirrors the pipeline: `tests/unit/test_extract.py`, `test_generate.py`, `test_validate.py`, `test_templates.py`, `test_ingest.py`. Integration tests in `tests/integration/`. Shared fixtures in `tests/conftest.py`.

## Dependencies

**Runtime**: pydantic, langchain-core, langchain-openai, python-dotenv, pypdf

**Dev**: pytest, pytest-timeout
