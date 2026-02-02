help:
    @just --list

# Install dependencies using uv
install:
    uv sync

# Consolidate AI inventory files into single CSV
consolidate:
    uv run python scripts/consolidate_inventories.py

# Download new files added to agencies.csv
download-missing:
    uv run python scripts/download_missing_files.py

# Combine 2024 and 2025 inventories (common columns only)
combine-years:
    uv run python scripts/combine_years.py

