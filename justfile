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

# Analyze use cases by stage (generates 2024, 2025, and combined reports)
analyze-stages:
    uv run python scripts/analyze_stages.py

