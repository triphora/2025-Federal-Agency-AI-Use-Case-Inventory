# 2025-Federal-Agency-AI-Use-Case-Inventory
This 2025 Federal Agency Artificial Intelligence (AI) Use Case Inventory repository consolidates AI use case inventories from across U.S. Federal agencies, consistent with Section 5 of Executive Order (EO) 13960, “Promoting the Use of Trustworthy Artificial Intelligence in the Federal Government,” and pursuant to the Advancing American AI Act and OMB Memorandum M-25-21, “Accelerating Federal Use of AI through Innovation, Governance, and Public Trust.” This repository demonstrates American leadership in AI and provides transparency into how Federal agencies are using AI technology to improve their services to the public.

## Overview
Federal agencies, with limited exceptions, are required to conduct annual inventories of their AI use cases and make this information publicly available. Federal agencies are to post a machine-readable CSV of all publicly releasable use cases on their agency’s website. For more information, please review the Reporting Instructions folder for OMB’s guidance to agencies.

## Consolidated Inventory Status
OMB is compiling publicly posted AI use case inventory submissions and will release a consolidated Federal resource on GitHub soon.

In the meantime, Kevin Schaul has started a similar consolidation project here. The main output is:

[/data/clean/2025_consolidated_ai_inventory.csv](/data/clean/2025_consolidated_ai_inventory.csv)


### Setup

```bash
# Clone the repository
git clone https://github.com/kevinschaul/2025-Federal-Agency-AI-Use-Case-Inventory.git
cd 2025-Federal-Agency-AI-Use-Case-Inventory

# Install dependencies
just install
# or: uv sync
```

### Usage

To add a new agency, find the url to the csv/excel file and add it to [data/raw/agencies.csv](data/raw/agencies.csv). Then:

```bash
# Download new files from agencies.csv
just download-missing

# Consolidate all AI inventory files into a single CSV
just consolidate

# Analyze use cases by stage (generates 2024/2025 comparison reports)
just analyze-stages
```

