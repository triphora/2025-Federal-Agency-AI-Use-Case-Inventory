#!/usr/bin/env python3
"""
Consolidates all AI inventory files from data/raw/ into a single CSV file.
Creates a log of any issues or confusing situations found.
"""

import pandas as pd
import os
from pathlib import Path
from typing import Optional, List, Dict
import re
from datetime import datetime
import csv
from bs4 import BeautifulSoup

class InventoryConsolidator:
    def __init__(self, data_dir: str = 'data/raw'):
        # Handle both running from project root and from scripts directory
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists() and Path(f'../{data_dir}').exists():
            self.data_dir = Path(f'../{data_dir}')

        self.all_data = []
        self.issues = []

        # Standard column mapping - what we're looking for
        self.key_fields = {
            'agency': ['Agency', 'agency'],
            'use_case_name': ['Use Case Name', 'use case name', 'Name'],
            'bureau': ['Bureau', 'Bureau/Component', 'Department', 'bureau/component'],
            'stage': ['Stage', 'Stage of Development', 'Status', 'stage of development', 'Stage of System Development Life Cycle', 'Deployment Phase'],
            'high_impact': ['High-impact', 'High Impact', 'high-impact', 'is the ai use case high-impact'],
            'justification': ['Justification', 'justification'],
            'topic_area': ['Topic Area', 'Use Case Topic Area', 'topic area'],
            'ai_classification': ['AI Classification', 'Classification', 'ai classification'],
            'problem_solved': ['Problem', 'What problem', 'problem is the ai intended to solve'],
            'benefits': ['Benefits', 'Expected Benefits', 'Outcomes', 'expected benefits', 'benefits and positive outcomes'],
            'outputs': ['Output', 'outputs', 'Describe the AI system', 'ai system outputs'],
            'operational_date': ['Date', 'Operational Date', 'operational or pilot start date'],
            'vendor_purchased': ['Purchased', 'developed under contract', 'vendor or developed', 'was the system involved'],
            'vendor_name': ['Vendor', 'Vendors', 'vendor name', "Vendor(s) Name"],
            'ato': ['Authorization to Operate', 'ATO', 'associated ato'],
            'system_name': ['System', 'System(s) Name', 'system name'],
            'training_data': ['Training data', 'data used to train', 'describe any data used'],
            'training_data_catalog': ['Federal Data Catalog', 'data catalog', 'federal data catalog'],
            'pii': ['PII', 'personally identifiable', 'pii that is maintained'],
            'pia': ['Privacy Impact Assessment', 'PIA', 'privacy impact assessment'],
            'demographic_variables': ['demographic', 'demographic variables'],
            'custom_code': ['custom-developed code', 'custom code', 'custom-developed'],
            'code_link': ['open source', 'source code', 'publicly available source code'],
            'pre_deployment_testing': ['pre-deployment testing', 'pre deployment'],
            'impact_assessment': ['AI impact assessment', 'impact assessment'],
            'impact_assessment_details': ['potential impacts', 'impacts of using the ai'],
            'independent_review': ['independent review', 'independent assessment'],
            'ongoing_monitoring': ['ongoing monitoring', 'adverse impacts', 'monitoring for performance'],
            'operator_training': ['operator training', 'periodic training', 'adequate human training'],
            'fail_safe': ['fail-safe', 'failsafe', 'minimize the risk'],
            'appeal_process': ['appeal process', 'appeal or contest'],
            'public_feedback': ['consult', 'incorporate feedback', 'feedback from end users'],
            'use_case_id': ['Use Case ID', 'use case id', 'ID'],
        }

    def _contains_any_keyword(self, text: str, keywords: list) -> bool:
        """Check if text contains any of the keywords."""
        return any(keyword in text for keyword in keywords)

    def normalize_stage_of_development(self, stage_str: str) -> str:
        """Normalize Stage of Development to 3-stage model.

        Maps various stage formats to simplified model:
        - In Development: Stages 1-3 (Initiation, Development/Acquisition, Implementation)
        - In Operation: Stage 4 (Operation and Maintenance)
        - Retired: Stage 5 (Discontinued)
        """
        if not isinstance(stage_str, str) or not stage_str.strip():
            return 'Unknown'

        # Normalize: remove option letters (a), b), c), d)), convert to lowercase
        stage_lower = stage_str.lower().strip()
        stage_lower = re.sub(r'^[a-d]\)\s*', '', stage_lower)
        stage_lower = re.sub(r'^[a-d]\s+', '', stage_lower)

        # Define keywords for each stage
        retired_keywords = ['retired', 'stage 5']
        in_operation_keywords = ['deployed', 'stage 4', 'operation and maintenance', 'in mission', 'production']
        in_development_keywords = [
            'stage 1', 'initiation', 'initiated',
            'stage 2', 'development', 'development and acquisition', 'acquisition and/or development',
            'sandbox', 'pre-deployment', 'pre deployment', 'acquisition',
            'stage 3', 'pilot', 'implementation'
        ]

        # Check in order
        if self._contains_any_keyword(stage_lower, retired_keywords):
            return 'Retired'
        elif self._contains_any_keyword(stage_lower, in_operation_keywords):
            return 'In Operation'
        elif self._contains_any_keyword(stage_lower, in_development_keywords):
            return 'In Development'
        else:
            return 'Unknown'

    def get_agency_name(self, folder_path: Path) -> str:
        """Extract agency name from folder name."""
        return folder_path.name.replace('-', ' ').title()

    def load_file(self, file_path: Path, has_other_files: bool = False, sheet_name: str = 0) -> Optional[pd.DataFrame]:
        """Load a file (CSV or XLSX) with proper error handling.

        Args:
            file_path: Path to the file to load
            has_other_files: If True, don't warn about PDFs (other files exist in folder)
            sheet_name: For XLSX files, which sheet to load (int for index, str for name)
        """
        try:
            if file_path.suffix == '.xlsx':
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            elif file_path.suffix == '.csv':
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
                except (UnicodeDecodeError, pd.errors.ParserError):
                    df = pd.read_csv(file_path, encoding='latin-1', on_bad_lines='skip')
            elif file_path.suffix == '.pdf':
                # Only warn about PDF if there are no other files in this folder
                if not has_other_files:
                    self.issues.append(f"PDF file skipped: {file_path.relative_to(self.data_dir)} (manual review needed)")
                return None
            else:
                return None
            return df
        except Exception as e:
            self.issues.append(f"Error loading {file_path.relative_to(self.data_dir)}: {str(e)}")
            return None

    def clean_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize column headers."""
        # First, check if the first row contains actual field names (header row)
        # Look for columns that are just "Unnamed" - this indicates the header is in the data
        has_unnamed = any('Unnamed' in str(col) for col in df.columns)

        if has_unnamed:
            # Check if row 0 has meaningful values in the Unnamed columns
            first_row_str = ' '.join(str(v).lower() for v in df.iloc[0] if pd.notna(v))

            # More strict check: look for multiple question-like patterns that match our governance fields
            header_keywords = ['stage of development', 'use case id', 'use case name', 'ai classification', 'authorization to operate']
            header_matches = sum(1 for kw in header_keywords if kw in first_row_str)

            # Only treat as header if we find 2+ header keywords (not just 1)
            if header_matches >= 2:
                # First row is a header - use it to rename all columns
                new_columns = []
                for i in range(len(df.columns)):
                    if i < len(df.iloc[0]) and pd.notna(df.iloc[0].iloc[i]):
                        # Use value from first row
                        header_val = str(df.iloc[0].iloc[i]).strip()
                        # Only use if it looks like a real header (not empty or too short)
                        if header_val and len(header_val) > 1:
                            new_columns.append(header_val)
                        else:
                            new_columns.append(df.columns[i])
                    else:
                        # Keep original if first row is empty
                        new_columns.append(df.columns[i])
                df.columns = new_columns

        # Clean up all column names
        df.columns = [col.replace('\n', ' ').strip() if isinstance(col, str) else col for col in df.columns]
        df.columns = [re.sub(r'\s+', ' ', col) if isinstance(col, str) else col for col in df.columns]

        # Don't remove Unnamed columns - they may have been renamed above and contain data
        return df

    def find_field_column(self, df: pd.DataFrame, field_key: str) -> Optional[str]:
        """Find the column that contains a specific field (checking both header and first data row)."""
        columns = list(df.columns)
        variants = self.key_fields.get(field_key, [])

        # For vendor_name, we need more specific matching to avoid matching vendor_purchased column
        # Try exact or very specific matches first
        if field_key == 'vendor_name':
            for col in columns:
                col_str = str(col).lower().strip()
                # Look for very specific patterns that clearly indicate vendor name
                if 'vendor(s) name' in col_str or 'vendors name' in col_str or col_str == 'vendor name' or col_str == 'vendor' or col_str == 'vendors':
                    return col

            # Check first data row for specific vendor name patterns
            if len(df) > 0:
                for col in columns:
                    cell_val = str(df.iloc[0][col]).lower().strip() if pd.notna(df.iloc[0][col]) else ''
                    if 'vendor(s) name' in cell_val or 'vendors name' in cell_val or cell_val == 'vendor name' or cell_val == 'vendor' or cell_val == 'vendors':
                        return col

        # Check column names (original logic for other fields)
        for col in columns:
            col_str = str(col).lower().strip()
            for variant in variants:
                if variant.lower() in col_str:
                    return col

        # Check first data row for header labels
        if len(df) > 0:
            for col in columns:
                cell_val = str(df.iloc[0][col]).lower().strip() if pd.notna(df.iloc[0][col]) else ''
                for variant in variants:
                    if variant.lower() in cell_val:
                        return col

        return None

    def extract_data(self, df: pd.DataFrame, agency: str, file_path: Path) -> List[dict]:
        """Extract relevant data from a dataframe."""
        results = []

        # Validate
        if df.shape[0] < 1 or df.shape[1] < 1:
            self.issues.append(f"Empty file: {file_path.relative_to(self.data_dir)}")
            return results

        df = df.dropna(how='all')
        if df.shape[0] < 1:
            self.issues.append(f"No data rows: {file_path.relative_to(self.data_dir)}")
            return results

        # Detect if first row is a header - be strict to avoid false positives like "Design Your Facility"
        first_row_str = ' '.join(str(v).lower() for v in df.iloc[0] if pd.notna(v))
        # Check for multiple header keywords to confirm it's a real header row
        header_keywords = ['stage of development', 'use case id', 'use case name', 'ai classification', 'authorization to operate', 'bureau/component']
        header_matches = sum(1 for kw in header_keywords if kw in first_row_str)
        start_row = 1 if header_matches >= 2 else 0

        # Find all columns
        use_case_id_col = self.find_field_column(df, 'use_case_id')
        use_case_name_col = self.find_field_column(df, 'use_case_name')
        bureau_col = self.find_field_column(df, 'bureau')
        stage_col = self.find_field_column(df, 'stage')
        high_impact_col = self.find_field_column(df, 'high_impact')
        justification_col = self.find_field_column(df, 'justification')
        topic_col = self.find_field_column(df, 'topic_area')
        ai_class_col = self.find_field_column(df, 'ai_classification')
        problem_col = self.find_field_column(df, 'problem_solved')
        benefits_col = self.find_field_column(df, 'benefits')
        outputs_col = self.find_field_column(df, 'outputs')
        operational_date_col = self.find_field_column(df, 'operational_date')
        vendor_purchased_col = self.find_field_column(df, 'vendor_purchased')
        vendor_name_col = self.find_field_column(df, 'vendor_name')
        ato_col = self.find_field_column(df, 'ato')
        system_name_col = self.find_field_column(df, 'system_name')
        training_data_col = self.find_field_column(df, 'training_data')
        training_data_catalog_col = self.find_field_column(df, 'training_data_catalog')
        pii_col = self.find_field_column(df, 'pii')
        pia_col = self.find_field_column(df, 'pia')
        demographic_col = self.find_field_column(df, 'demographic_variables')
        custom_code_col = self.find_field_column(df, 'custom_code')
        code_link_col = self.find_field_column(df, 'code_link')
        pre_deployment_col = self.find_field_column(df, 'pre_deployment_testing')
        impact_assess_col = self.find_field_column(df, 'impact_assessment')
        impact_assess_details_col = self.find_field_column(df, 'impact_assessment_details')
        independent_review_col = self.find_field_column(df, 'independent_review')
        ongoing_monitoring_col = self.find_field_column(df, 'ongoing_monitoring')
        operator_training_col = self.find_field_column(df, 'operator_training')
        fail_safe_col = self.find_field_column(df, 'fail_safe')
        appeal_process_col = self.find_field_column(df, 'appeal_process')
        public_feedback_col = self.find_field_column(df, 'public_feedback')

        # Track missing critical columns
        if not use_case_name_col:
            missing = []
            if not use_case_name_col:
                missing.append('use_case_name')
            self.issues.append(f"{agency} - {file_path.name}: Cannot find columns: {', '.join(missing)}")

        # Extract data rows
        for idx in range(start_row, len(df)):
            row = df.iloc[idx]

            # Get values
            uid = str(row[use_case_id_col]).strip() if use_case_id_col and pd.notna(row[use_case_id_col]) else ''
            uname = str(row[use_case_name_col]).strip() if use_case_name_col and pd.notna(row[use_case_name_col]) else ''

            # For Agriculture, extract ID and name separately if combined in one field
            if agency == 'Department Of Agriculture' and ':' in uname and uname.startswith('USDA-'):
                # Split "USDA-001: Name" into uid="USDA-001" and uname="Name"
                parts = uname.split(':', 1)
                if len(parts) == 2:
                    uid = parts[0].strip()
                    uname = parts[1].strip()

            # Skip empty or header-like rows
            if not uid and not uname:
                continue
            # Only skip rows where BOTH uid and uname look like headers (e.g., "Use Case ID" and "Use Case Name")
            # This prevents false positives where use case names legitimately contain "use case"
            if (uid.lower().startswith('use case') and uname.lower().startswith('use case')):
                continue
            # Skip placeholder rows (e.g., just "NSF" as use case name)
            if uname.strip().upper() in ['NSF']:
                continue

            # Extract raw stage value before normalization
            raw_stage = str(row[stage_col]).strip() if stage_col and pd.notna(row[stage_col]) else ''
            normalized_stage = self.normalize_stage_of_development(raw_stage)

            record = {
                'Agency': agency,
                'Use Case ID': uid,
                'Use Case Name': uname,
                'Bureau/Component': str(row[bureau_col]).strip() if bureau_col and pd.notna(row[bureau_col]) else '',
                'Stage of Development (Raw)': raw_stage,
                'Stage of Development': normalized_stage,
                'Is the AI use case high-impact?': str(row[high_impact_col]).strip() if high_impact_col and pd.notna(row[high_impact_col]) else '',
                'Justification': str(row[justification_col]).strip() if justification_col and pd.notna(row[justification_col]) else '',
                'Use Case Topic Area': str(row[topic_col]).strip() if topic_col and pd.notna(row[topic_col]) else '',
                'AI Classification': str(row[ai_class_col]).strip() if ai_class_col and pd.notna(row[ai_class_col]) else '',
                'What problem is the AI intended to solve?': str(row[problem_col]).strip() if problem_col and pd.notna(row[problem_col]) else '',
                'What are the expected benefits and positive outcomes from the AI for an agency\'s mission and/or the general public?': str(row[benefits_col]).strip() if benefits_col and pd.notna(row[benefits_col]) else '',
                'Describe the AI system\'s outputs.': str(row[outputs_col]).strip() if outputs_col and pd.notna(row[outputs_col]) else '',
                'Date when AI use case became operational or the pilot\'s start date': str(row[operational_date_col]).strip() if operational_date_col and pd.notna(row[operational_date_col]) else '',
                'Was the system involved in this use case purchased from a vendor or developed under contract(s) or in-house?': str(row[vendor_purchased_col]).strip() if vendor_purchased_col and pd.notna(row[vendor_purchased_col]) else '',
                'Vendor(s) Name': str(row[vendor_name_col]).strip() if vendor_name_col and pd.notna(row[vendor_name_col]) else '',
                'Does this AI use case have an associated Authorization to Operate (ATO)?': str(row[ato_col]).strip() if ato_col and pd.notna(row[ato_col]) else '',
                'System(s) Name': str(row[system_name_col]).strip() if system_name_col and pd.notna(row[system_name_col]) else '',
                'Describe any data used to train, fine-tune, and/or evaluate performance of the model(s) used in this use case.': str(row[training_data_col]).strip() if training_data_col and pd.notna(row[training_data_col]) else '',
                'If the data is required to be publicly disclosed as an open government data asset, provide a link to the entry on the Federal Data Catalog.': str(row[training_data_catalog_col]).strip() if training_data_catalog_col and pd.notna(row[training_data_catalog_col]) else '',
                'Does this AI use case involve personally identifiable information (PII) that is maintained by the agency?': str(row[pii_col]).strip() if pii_col and pd.notna(row[pii_col]) else '',
                'If publicly available, provide the link to the AI use case\'s associated Privacy Impact Assessment (PIA).': str(row[pia_col]).strip() if pia_col and pd.notna(row[pia_col]) else '',
                'Which, if any, demographic variables does the AI use case explicitly use as model features?': str(row[demographic_col]).strip() if demographic_col and pd.notna(row[demographic_col]) else '',
                'Does this project include custom-developed code?': str(row[custom_code_col]).strip() if custom_code_col and pd.notna(row[custom_code_col]) else '',
                'If the code is open source, provide the link for the publicly available source code.': str(row[code_link_col]).strip() if code_link_col and pd.notna(row[code_link_col]) else '',
                'Has pre-deployment testing been conducted for this AI use case?': str(row[pre_deployment_col]).strip() if pre_deployment_col and pd.notna(row[pre_deployment_col]) else '',
                'Has an AI impact assessment been completed for this AI use case?': str(row[impact_assess_col]).strip() if impact_assess_col and pd.notna(row[impact_assess_col]) else '',
                'What are the potential impacts of using the AI for this particular use case and how were they identified?': str(row[impact_assess_details_col]).strip() if impact_assess_details_col and pd.notna(row[impact_assess_details_col]) else '',
                'Has an independent review of the AI use case been conducted?': str(row[independent_review_col]).strip() if independent_review_col and pd.notna(row[independent_review_col]) else '',
                'Is there a process to conduct ongoing monitoring to identify any adverse impacts to the performance and security of the AI functionality, as well as to privacy, civil rights, and civil liberties?': str(row[ongoing_monitoring_col]).strip() if ongoing_monitoring_col and pd.notna(row[ongoing_monitoring_col]) else '',
                'Has the agency established sufficient and periodic training for operators of the AI to interpret and act on the its output and managed associated risks?': str(row[operator_training_col]).strip() if operator_training_col and pd.notna(row[operator_training_col]) else '',
                'Does this AI use case have an appropriate fail-safe that minimizes the risk of significant harm?': str(row[fail_safe_col]).strip() if fail_safe_col and pd.notna(row[fail_safe_col]) else '',
                'Is there an established appeal process in the event that an impacted individual would like to appeal or contest the AI system\'s outcome?': str(row[appeal_process_col]).strip() if appeal_process_col and pd.notna(row[appeal_process_col]) else '',
                'What steps has the agency taken to consult and incorporate feedback from end users of this AI use case and the public?': str(row[public_feedback_col]).strip() if public_feedback_col and pd.notna(row[public_feedback_col]) else '',
            }

            if uid or uname:
                results.append(record)

        return results

    def parse_tva_html_if_exists(self):
        """Check for and parse TVA HTML/text file if present."""
        tva_folder = self.data_dir / 'tennessee-valley-authority'
        html_file = tva_folder / 'tva-page.html'
        csv_file = tva_folder / 'tva-inventory.csv'

        if not html_file.exists():
            return

        # Check if CSV is newer than HTML (already parsed)
        if csv_file.exists() and csv_file.stat().st_mtime > html_file.stat().st_mtime:
            return

        print(f"Found TVA file, parsing data...")

        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()

            rows = []

            # Try HTML parsing first
            if '<table' in content:
                soup = BeautifulSoup(content, 'lxml')
                table = soup.find('table')
                if table:
                    for tr in table.find_all('tr'):
                        cells = tr.find_all(['th', 'td'])
                        row_data = [cell.get_text(strip=True) for cell in cells]
                        if row_data:
                            rows.append(row_data)

            # If no HTML table found, try parsing as tab-separated text
            if not rows:
                lines = content.split('\n')
                # Find the header line
                header_idx = None
                for i, line in enumerate(lines):
                    if 'Use Case Name\tBureau' in line or 'Use Case Name' in line and '\t' in line:
                        header_idx = i
                        break

                if header_idx is not None:
                    # Extract header and data rows
                    for line in lines[header_idx:]:
                        if '\t' in line:
                            row_data = line.split('\t')
                            # Clean up each cell
                            row_data = [cell.strip() for cell in row_data if cell.strip()]
                            if row_data and len(row_data) >= 3:  # At least 3 columns
                                rows.append(row_data)

            if len(rows) < 2:
                print(f"  ⚠ No data found in {html_file.name}")
                return

            # Save to CSV
            tva_folder.mkdir(parents=True, exist_ok=True)
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(rows)

            print(f"  ✓ Parsed {len(rows)-1} use cases → {csv_file.name}")

        except Exception as e:
            print(f"  ✗ Error parsing TVA file: {e}")

    def process_all_files(self):
        """Process all files in the data directory."""

        # Pre-process: Check for TVA HTML and parse if needed
        self.parse_tva_html_if_exists()

        print("Scanning for inventory files...")

        for agency_folder in sorted(self.data_dir.iterdir()):
            if not agency_folder.is_dir() or agency_folder.name.startswith('.'):
                continue

            # Skip non-agency folders (e.g., 2024 historical data)
            if agency_folder.name[0].isdigit():
                continue

            agency = self.get_agency_name(agency_folder)
            files = [f for f in agency_folder.glob('*') if f.suffix in ['.csv', '.xlsx', '.pdf']]

            if not files:
                self.issues.append(f"No files found in {agency}")
                continue

            # Check if there are non-PDF files
            has_non_pdf = any(f.suffix in ['.csv', '.xlsx'] for f in files)

            for file in files:
                print(f"Processing: {agency} - {file.name}")

                # Use specific sheet for Department of Justice
                sheet_name = "Reportable AI Use Cases" if agency == "Department Of Justice" else 0
                df = self.load_file(file, has_other_files=has_non_pdf, sheet_name=sheet_name)
                if df is None:
                    continue

                df = self.clean_headers(df)
                rows = self.extract_data(df, agency, file)

                if rows:
                    self.all_data.extend(rows)
                    print(f"  ✓ Extracted {len(rows)} use cases")
                else:
                    self.issues.append(f"No data extracted from {agency}: {file.name}")

        print(f"\nTotal use cases extracted: {len(self.all_data)}")

    def save_results(self, output_file: str = 'data/clean/2025_consolidated_ai_inventory.csv',
                     log_file: str = 'data/build/consolidation_log.txt'):
        """Save consolidated data and log to files."""
        if not self.all_data:
            print("No data to save!")
            return

        # Handle path
        out_path = Path(output_file)
        if not out_path.parent.exists() and Path(f'../{output_file}').parent.exists():
            out_path = Path(f'../{output_file}')

        log_path = Path(log_file)
        if not log_path.parent.exists() and Path(f'../{log_file}').parent.exists():
            log_path = Path(f'../{log_file}')

        # Create log directory if it doesn't exist
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Save CSV
        df = pd.DataFrame(self.all_data)
        df.to_csv(str(out_path), index=False)
        print(f"\n✓ Consolidated inventory saved to: {out_path}")
        print(f"  Total rows: {len(df)}")

        # Save log
        with open(str(log_path), 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("AI INVENTORY CONSOLIDATION LOG\n")
            f.write("=" * 80 + "\n\n")

            # Summary
            f.write(f"SUMMARY\n")
            f.write(f"Total use cases extracted: {len(self.all_data)}\n")
            f.write(f"Issues/Warnings found: {len(self.issues)}\n\n")

            # Group by agency
            f.write("USE CASES BY AGENCY\n")
            f.write("-" * 80 + "\n")
            by_agency = {}
            for record in self.all_data:
                agency = record.get('Agency', record.get('agency', ''))
                if agency not in by_agency:
                    by_agency[agency] = []
                by_agency[agency].append(record)

            for agency in sorted(by_agency.keys()):
                use_cases = by_agency[agency]
                f.write(f"\n{agency}: {len(use_cases)} use case(s)\n")
                for uc in use_cases[:3]:  # Show first 3
                    uc_name = uc.get('Use Case Name', '')[:60] or ''
                    f.write(f"  • {uc_name}\n")
                if len(use_cases) > 3:
                    f.write(f"  ... and {len(use_cases) - 3} more\n")

            # Issues
            if self.issues:
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("ISSUES AND WARNINGS - PLEASE DOUBLE CHECK\n")
                f.write("=" * 80 + "\n\n")
                for issue in sorted(set(self.issues)):
                    f.write(f"⚠ {issue}\n\n")

        print(f"✓ Consolidation log saved to: {log_path}")

        # Print summary
        if self.issues:
            print("\n" + "=" * 80)
            print(f"FOUND {len(set(self.issues))} ISSUES - PLEASE REVIEW:")
            print("=" * 80)
            for issue in sorted(set(self.issues))[:10]:
                print(f"⚠ {issue}")
            if len(set(self.issues)) > 10:
                print(f"... and {len(set(self.issues)) - 10} more (see log file)")


if __name__ == '__main__':
    consolidator = InventoryConsolidator()
    consolidator.process_all_files()
    consolidator.save_results()
