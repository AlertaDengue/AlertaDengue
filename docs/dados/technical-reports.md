# Technical Reports

Technical reports are no longer hardcoded inside the application. Instead, report metadata is loaded from a JSON manifest located inside `TECHNICAL_REPORTS_ROOT`.

This allows new reports to be published without modifying or versioning Django application code.

# Environment configuration

The system requires the following environment variable:

`TECHNICAL_REPORTS_ROOT`

This variable points to the directory containing:
- `technical_reports.json`
- All PDF files associated with the reports.

It is configured through `.envs/.env` (or the deployment environment).

# Directory layout

The expected directory structure is as follows:

```
TECHNICAL_REPORTS_ROOT/
├── technical_reports.json
├── technical-report.pdf
├── epidemiological-situation-analysis-01-2026.pdf
└── epidemiological-situation-analysis-02-2026.pdf
```

The manifest and every referenced PDF must coexist inside this directory.

# Manifest format

The manifest is a JSON object where each key is a logical identifier for a report.

Example:

```json
{
  "default": {
    "filename": "epidemiological-situation-analysis-02-2026.pdf",
    "output_filename": "RELATÓRIO TÉCNICO 02_2026.pdf"
  },
  "epidemiological-situation-analysis-2026": {
    "filename": "epidemiological-situation-analysis-02-2026.pdf",
    "output_filename": "RELATÓRIO TÉCNICO 02_2026.pdf"
  },
  "technical-report-2023": {
    "filename": "technical-report.pdf",
    "output_filename": "RELATÓRIO TÉCNICO 02_23 clima e arboviroses - projeções para 2024-26out2023.pdf"
  }
}
```

### Field Descriptions:

- **Manifest key**: Logical identifier used by the endpoint to retrieve the report.
- **filename**: Relative filename of the PDF inside `TECHNICAL_REPORTS_ROOT`.
- **output_filename**: The filename presented to the browser when opening or downloading the PDF.

### Rules:

- Filenames must always be relative.
- Absolute paths are rejected.
- Path traversal (`../`) is rejected.
- Only `.pdf` files are accepted.
- Every report must define both `filename` and `output_filename`.

A complete example manifest is available in: `docs/dados/examples/technical_reports.example.json`.

# Public endpoint

The following endpoints are available to access the reports:

- `GET /download_technical_report_pdf/`
  Returns the report configured as `default`.

- `GET /download_technical_report_pdf/<report_key>/`
  Returns the report associated with the specified `<report_key>`.

**Note:**
- Unknown report keys return HTTP 404.
- Missing PDF files return HTTP 404.

# Example request flow

`technical_reports.json` $ightarrow$ `"default"` $ightarrow$ `epidemiological-situation-analysis-02-2026.pdf` $ightarrow$ `GET /download_technical_report_pdf/` $ightarrow$ Browser receives: `RELATÓRIO TÉCNICO 02_2026.pdf`

# Adding a new report

1. Copy the PDF into `TECHNICAL_REPORTS_ROOT`.
2. Add a new entry to `technical_reports.json`.
3. Access it using: `/download_technical_report_pdf/<report_key>/`

No Django code changes or application deployments are required unless dictated by deployment policy.

# Updating an existing report

1. Replace the PDF or copy a new version.
2. Update `technical_reports.json` if the `filename` or `output_filename` changes.
3. Update the `default` entry if the new report should become the default.

No Django code changes are required.

# Security

The subsystem implements the following protections:

- Files are always resolved relative to `TECHNICAL_REPORTS_ROOT`.
- Path traversal protection is active to prevent access to files outside the root.
- Only `.pdf` files may be served.
- Invalid manifest configurations raise `ImproperlyConfigured`.

# Troubleshooting

## Technical reports manifest not found
**Possible causes:**
- Missing `technical_reports.json`.
- Incorrect `TECHNICAL_REPORTS_ROOT` environment variable.
- Deployment process copied PDFs but missed the manifest.

## Technical Report PDF not found
**Possible causes:**
- Unknown report key requested.
- Missing PDF file in the root directory.
- Filename mismatch between manifest and filesystem.
- Invalid manifest entry.
- Non-PDF file referenced.

# Tests

The focused test suite can be run using:

```bash
pytest AlertaDengue/tests/dados/test_technical_report.py -q
```

These tests validate:
- Manifest loading.
- Path validation.
- `FileResponse` behavior.
- HTTP error handling.
- Configuration errors.
