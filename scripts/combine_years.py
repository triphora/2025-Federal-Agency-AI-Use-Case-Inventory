#!/usr/bin/env python3
"""
Combine 2024 and 2025 consolidated inventories with specific columns.
Adds a 'Year' column to track source year.

Keeps these columns:
- Year
- Agency
- Use Case Name
- Retired (Yes/No)
"""

import pandas as pd
from pathlib import Path


def normalize_agency_name(agency):
    """Normalize agency names to consistent title case.

    Converts variations like 'Department Of Agriculture' to 'Department of Agriculture'.
    Preserves acronyms and proper nouns.
    """
    if pd.isna(agency) or agency == '':
        return agency

    # Words that should be lowercase in title case
    lowercase_words = {'of', 'the', 'and', 'for', 'on', 'to'}

    # Split into words
    words = str(agency).split()

    # Capitalize first word, then apply title case rules
    normalized = []
    for i, word in enumerate(words):
        if i == 0:
            # Always capitalize first word
            normalized.append(word.capitalize())
        elif word.lower() in lowercase_words:
            # Lowercase articles, prepositions, conjunctions
            normalized.append(word.lower())
        else:
            # Capitalize other words
            normalized.append(word.capitalize())

    return ' '.join(normalized)


def normalize_2025_stage(raw_stage):
    """Map 2025 raw stages to 2024 stage format."""
    if pd.isna(raw_stage) or raw_stage == '':
        return 'Unknown'

    stage_lower = str(raw_stage).lower().strip()

    # Map to 2024 categories
    if 'retired' in stage_lower:
        return 'Retired'
    elif 'deployed' in stage_lower or 'operation and maintenance' in stage_lower or 'production' in stage_lower:
        return 'Operation and Maintenance'
    elif 'pilot' in stage_lower or 'implementation' in stage_lower:
        return 'Implementation and Assessment'
    elif 'pre-deployment' in stage_lower or 'acquisition' in stage_lower or 'development' in stage_lower or 'sandbox' in stage_lower:
        return 'Acquisition and/or Development'
    elif 'initiated' in stage_lower or 'ideation' in stage_lower or 'planned' in stage_lower:
        return 'Initiated'
    else:
        return 'Unknown'


def combine_years():
    """Combine 2024_v2 and 2025 inventories with selected columns."""

    print("=" * 80)
    print("COMBINING 2024 AND 2025 AI INVENTORIES")
    print("=" * 80)
    print()

    # Load both files
    print("Loading files...")
    df_2024 = pd.read_csv('data/clean/2024_consolidated_ai_inventory_raw_v2.csv', encoding='latin-1')
    df_2025 = pd.read_csv('data/clean/2025_consolidated_ai_inventory.csv')

    print(f"  2024: {len(df_2024):,} rows, {len(df_2024.columns)} columns")
    print(f"  2025: {len(df_2025):,} rows, {len(df_2025.columns)} columns")

    # Extract columns for 2024
    print("\nExtracting columns...")
    print("  Normalizing agency names...")

    # Check if retired based on stage
    df_2024_retired = df_2024['Stage of Development'].str.lower().str.contains('retired', na=False)

    df_2024_selected = pd.DataFrame({
        'Year': 2024,
        'Agency': df_2024['Agency'].apply(normalize_agency_name),
        'Use Case Name': df_2024['Use Case Name'],
        'Retired': df_2024_retired,
    })

    # Extract columns for 2025
    df_2025_retired = df_2025['Stage of Development'].str.lower().str.contains('retired', na=False)

    df_2025_selected = pd.DataFrame({
        'Year': 2025,
        'Agency': df_2025['Agency'].apply(normalize_agency_name),
        'Use Case Name': df_2025['Use Case Name'],
        'Retired': df_2025_retired,
    })

    # Combine
    print("\nCombining datasets...")
    df_combined = pd.concat([df_2024_selected, df_2025_selected], ignore_index=True)

    # Save
    output_file = Path('data/clean/combined_2024_2025_ai_inventory.csv')
    df_combined.to_csv(output_file, index=False)

    print(f"\n✓ Combined file saved: {output_file}")
    print(f"  Total rows: {len(df_combined):,}")
    print(f"  Total columns: {len(df_combined.columns)}")
    print(f"  2024 records: {len(df_2024_selected):,}")
    print(f"  2025 records: {len(df_2025_selected):,}")

    # Show column completeness
    print("\nColumn completeness:")
    print("-" * 80)
    for col in df_combined.columns:
        if col == 'Year':
            continue
        non_empty_2024 = (df_combined[df_combined['Year'] == 2024][col].notna() &
                          (df_combined[df_combined['Year'] == 2024][col] != '')).sum()
        non_empty_2025 = (df_combined[df_combined['Year'] == 2025][col].notna() &
                          (df_combined[df_combined['Year'] == 2025][col] != '')).sum()
        total_2024 = len(df_2024_selected)
        total_2025 = len(df_2025_selected)

        pct_2024 = (non_empty_2024 / total_2024 * 100) if total_2024 > 0 else 0
        pct_2025 = (non_empty_2025 / total_2025 * 100) if total_2025 > 0 else 0

        print(f"  {col:<45} 2024: {pct_2024:5.1f}%  2025: {pct_2025:5.1f}%")

    # Summary stats by year
    print("\nRecords by year and agency:")
    print("-" * 80)
    summary = df_combined.groupby(['Year', 'Agency']).size().reset_index(name='Count')

    for year in [2024, 2025]:
        year_data = summary[summary['Year'] == year]
        print(f"\n{year}: {year_data['Count'].sum():,} total records across {len(year_data)} agencies")
        top_5 = year_data.nlargest(5, 'Count')
        print("  Top 5 agencies:")
        for _, row in top_5.iterrows():
            print(f"    {row['Agency']:<50} {row['Count']:>4} use cases")

    print("\n" + "=" * 80)
    print("✓ COMBINATION COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    # Handle running from project root or scripts directory
    if not Path('data').exists() and Path('../data').exists():
        import os
        os.chdir('..')

    combine_years()
