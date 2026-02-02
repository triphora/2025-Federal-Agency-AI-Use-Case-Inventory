# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Context

This repository consolidates AI use case inventories from U.S. Federal agencies. It downloads, parses, normalizes, and consolidates diverse agency-submitted files (CSV, XLSX) into a unified dataset.

**See [README.md](README.md) for full architecture and pipeline details.**

## Quick Commands

All commands use `uv` for Python and `just` for task running:

```bash
just install           # Install dependencies
just consolidate      # Run main consolidation script
just download-missing # Download new agency files
```

## Key Implementation Details

### Script Locations
- `scripts/consolidate_inventories.py` - Main consolidation logic (400+ lines, includes TVA HTML parser)
- `scripts/download_missing_files.py` - Agency file downloader

### Important Code Patterns

**Field Mapping** (`consolidate_inventories.py:25-50`)
- The `key_fields` dict maps standardized field names to possible column name variations
- Field detection checks both headers AND first data row (handles inconsistent formats)
- Add new field variations by extending the lists in `key_fields`

**Stage Normalization** (`consolidate_inventories.py:normalize_stage_of_development()`)
- Converts 5-stage SDLC model to 3-stage model via keyword matching
- Keywords defined inline: "retired", "deployed", "pilot", "development", etc.
- Falls back to "Unknown" if no keywords match
- Both raw and normalized stages preserved in output

**Special Cases**
- TVA: Auto-parses `tva-page.html` if present (Cloudflare blocks curl, must manually save page)
- Justice Dept: Uses sheet "Reportable AI Use Cases" (line ~300)
- Agriculture: Splits "USDA-001: Name" format into separate ID and name (line ~200)
- Header detection: Looks for 2+ header keywords to identify header rows (line ~150)

### Data Flow
```
agencies.csv → download_missing_files.py → data/raw/[agency]/
                                              ↓
                                    consolidate_inventories.py
                                              ↓
                            data/clean/2025_consolidated_ai_inventory.csv
```

### Logs and Debugging
- Consolidation log: `data/build/consolidation_log.txt`
- Script outputs progress to stdout with ✓/✗ indicators
- CSV encoding: tries UTF-8 first, falls back to latin-1

## Development Guidelines

**When modifying consolidation logic:**
1. Read the script first to understand field mapping structure
2. Test changes by running `just consolidate` on full dataset
3. Check `data/build/consolidation_log.txt` for issues
4. Verify output CSV columns haven't changed unexpectedly

**When adding new agency files:**
1. Add entry to `data/raw/agencies.csv`
2. Run `just download-missing` to fetch
3. Run `just consolidate` and check logs for parsing issues
4. Common issues: unusual column names, header rows in data, encoding problems

**When modifying scripts:**
- All scripts support running from project root or `scripts/` directory
- Use `uv run python scripts/[script].py` for execution
- Scripts expect `.venv/` managed by `uv`

## Environment

- Python 3.11+ via `.python-version`
- Dependencies in `pyproject.toml` (pandas, openpyxl, requests)
- Virtual env: `.venv/` (managed by uv, gitignored)
- Package mode: disabled (`package = false` in pyproject.toml)
