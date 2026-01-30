#!/usr/bin/env python3
"""
Analyze AI use cases by agency and stage of development.
Generates combined 2024/2025 report and year-over-year comparison.
"""

import pandas as pd
import sys
import re
import os
from pathlib import Path


def normalize_agency_name(name):
    """Normalize agency name for consistent matching across datasets."""
    if not isinstance(name, str):
        return name
    return re.sub(r'\s+', ' ', name.strip().lower())


def get_stage_category_2024(stage_str):
    """Extract stage category for 2024 data (5-stage model)."""
    if not isinstance(stage_str, str) or not stage_str.strip():
        return 'Unknown'

    stage_lower = stage_str.lower()

    if 'retired' in stage_lower:
        return 'Retired'
    elif ('operation and maintenance' in stage_lower or 'in production' in stage_lower or
          'in mission' in stage_lower):
        return 'Deployed'
    elif 'implementation and assessment' in stage_lower:
        return 'Pilot'
    elif ('acquisition' in stage_lower or 'development' in stage_lower or
          'initiated' in stage_lower or 'planned' in stage_lower):
        return 'Pre-deployment'
    elif 'pre-deployment' in stage_lower or 'pre deployment' in stage_lower or 'pre-' in stage_lower:
        return 'Pre-deployment'
    elif 'pilot' in stage_lower:
        return 'Pilot'
    elif 'deployed' in stage_lower or 'active' in stage_lower:
        return 'Deployed'
    else:
        return 'Unknown'


def main():
    """Generate stage analysis reports."""
    print("="*104)
    print("ANALYZING AI USE CASES BY AGENCY AND STAGE OF DEVELOPMENT")
    print("="*104 + "\n")

    # Load 2024 data
    print("Loading 2024 data...")
    data_file_2024 = 'data/clean/2024_consolidated_ai_inventory_raw_v2.csv'
    try:
        df_2024 = pd.read_csv(data_file_2024, encoding='latin1')
    except FileNotFoundError:
        print(f"Error: {data_file_2024} not found")
        sys.exit(1)

    # Load 2025 data
    print("Loading 2025 data...")
    data_file_2025 = 'data/clean/2025_consolidated_ai_inventory.csv'
    try:
        df_2025 = pd.read_csv(data_file_2025)
    except FileNotFoundError:
        print(f"Error: {data_file_2025} not found. Run 'just consolidate' first.")
        sys.exit(1)

    # Process 2024 data
    print("\nProcessing 2024 data (5-stage model → 3-stage model)...")
    df_2024['Stage_Category'] = df_2024['Stage of Development'].apply(get_stage_category_2024)
    agencies_2024 = sorted(df_2024['Agency'].dropna().unique())

    data_2024 = []
    for agency in agencies_2024:
        agency_df = df_2024[df_2024['Agency'] == agency]

        pre_dev = len(agency_df[agency_df['Stage_Category'] == 'Pre-deployment'])
        pilot = len(agency_df[agency_df['Stage_Category'] == 'Pilot'])
        deployed = len(agency_df[agency_df['Stage_Category'] == 'Deployed'])
        retired = len(agency_df[agency_df['Stage_Category'] == 'Retired'])
        unknown = len(agency_df[agency_df['Stage_Category'] == 'Unknown'])

        # Normalize to 3-stage model: Pre-deployment + Pilot = In Development, Deployed = In Operation
        in_dev = pre_dev + pilot
        in_op = deployed

        data_2024.append({
            'Year': 2024,
            'Agency': agency,
            'In Development': in_dev,
            'In Operation': in_op,
            'Retired': retired,
            'Unknown': unknown,
            'Total': len(agency_df)
        })

    # Process 2025 data
    print("Processing 2025 data (3-stage model)...")
    df_2025['Stage_Category'] = df_2025['Stage of Development']
    agencies_2025 = sorted(df_2025['Agency'].unique())

    data_2025 = []
    for agency in agencies_2025:
        agency_df = df_2025[df_2025['Agency'] == agency]

        in_dev = len(agency_df[agency_df['Stage_Category'] == 'In Development'])
        in_op = len(agency_df[agency_df['Stage_Category'] == 'In Operation'])
        retired = len(agency_df[agency_df['Stage_Category'] == 'Retired'])
        unknown = len(agency_df[agency_df['Stage_Category'] == 'Unknown'])

        data_2025.append({
            'Year': 2025,
            'Agency': agency,
            'In Development': in_dev,
            'In Operation': in_op,
            'Retired': retired,
            'Unknown': unknown,
            'Total': len(agency_df)
        })

    # Combine into single dataframe
    combined_df = pd.DataFrame(data_2024 + data_2025)

    # Create output directory
    output_dir = Path('data/clean/summary')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save combined data
    output_file = output_dir / 'by_stage.csv'
    combined_df.to_csv(output_file, index=False)
    print(f"\n✓ Combined stage data saved to: {output_file}")

    # Generate year-over-year comparison
    print("\nGenerating year-over-year comparison...")

    # Normalize agency names for matching
    df_2024_summary = pd.DataFrame(data_2024)
    df_2025_summary = pd.DataFrame(data_2025)

    df_2024_summary['Agency_Normalized'] = df_2024_summary['Agency'].apply(normalize_agency_name)
    df_2025_summary['Agency_Normalized'] = df_2025_summary['Agency'].apply(normalize_agency_name)

    # Get all unique agencies
    all_agencies = sorted(set(df_2024_summary['Agency_Normalized'].unique()) |
                         set(df_2025_summary['Agency_Normalized'].unique()))

    comparison_data = []
    for agency_norm in all_agencies:
        row_2024 = df_2024_summary[df_2024_summary['Agency_Normalized'] == agency_norm]
        row_2025 = df_2025_summary[df_2025_summary['Agency_Normalized'] == agency_norm]

        # Get original agency name (prefer 2025)
        agency_name = (row_2025['Agency'].values[0] if len(row_2025) > 0
                      else row_2024['Agency'].values[0] if len(row_2024) > 0
                      else agency_norm)

        # Get totals (excluding Retired from active count)
        total_2024 = (row_2024['In Development'].values[0] + row_2024['In Operation'].values[0]
                     if len(row_2024) > 0 else 0)
        total_2025 = (row_2025['In Development'].values[0] + row_2025['In Operation'].values[0]
                     if len(row_2025) > 0 else 0)

        comparison_data.append({
            'Agency': agency_name,
            '2024': int(total_2024),
            '2025': int(total_2025)
        })

    comparison_df = pd.DataFrame(comparison_data)

    # Calculate change for sorting and display only
    comparison_df['_change'] = comparison_df['2025'] - comparison_df['2024']
    comparison_df = comparison_df[comparison_df['2025'] > 0].sort_values('2025', ascending=False)

    # Save comparison (without the temporary _change column)
    comparison_file = output_dir / 'by_stage_comparison.csv'
    comparison_df[['Agency', '2024', '2025']].to_csv(comparison_file, index=False)
    print(f"✓ Year-over-year comparison saved to: {comparison_file}")

    # Print summary statistics
    print("\n" + "="*104)
    print("SUMMARY STATISTICS")
    print("="*104)

    total_2024 = combined_df[(combined_df['Year'] == 2024)][['In Development', 'In Operation']].sum().sum()
    total_2025 = combined_df[(combined_df['Year'] == 2025)][['In Development', 'In Operation']].sum().sum()

    print(f"\n2024 Active Use Cases (In Development + In Operation): {int(total_2024)}")
    print(f"2025 Active Use Cases (In Development + In Operation): {int(total_2025)}")
    print(f"Net Growth: +{int(total_2025 - total_2024)} use cases (+{(total_2025 - total_2024)/total_2024*100:.1f}%)")

    # Show breakdown by stage
    print("\n2024 Breakdown:")
    dev_2024 = combined_df[(combined_df['Year'] == 2024)]['In Development'].sum()
    op_2024 = combined_df[(combined_df['Year'] == 2024)]['In Operation'].sum()
    print(f"  • In Development: {int(dev_2024)} ({dev_2024/total_2024*100:.1f}%)")
    print(f"  • In Operation:   {int(op_2024)} ({op_2024/total_2024*100:.1f}%)")

    print("\n2025 Breakdown:")
    dev_2025 = combined_df[(combined_df['Year'] == 2025)]['In Development'].sum()
    op_2025 = combined_df[(combined_df['Year'] == 2025)]['In Operation'].sum()
    print(f"  • In Development: {int(dev_2025)} ({dev_2025/total_2025*100:.1f}%)")
    print(f"  • In Operation:   {int(op_2025)} ({op_2025/total_2025*100:.1f}%)")

    # Top agencies by growth
    print("\n" + "-"*104)
    print("TOP 10 AGENCIES BY USE CASE GROWTH (2024 → 2025):")
    print("-"*104)

    top_growth = comparison_df.sort_values('_change', ascending=False).head(10)
    for i, (idx, row) in enumerate(top_growth.iterrows(), 1):
        change = int(row['_change'])
        print(f"{i:2d}. {row['Agency']:<50} {row['2024']:>4} → {row['2025']:>4} ({change:>+4})")

    print("\n" + "="*104 + "\n")


if __name__ == '__main__':
    main()
