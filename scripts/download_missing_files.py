#!/usr/bin/env python3
"""
Download AI inventory files for agencies that have URLs but no files yet.
Run this after updating agencies.csv with new file URLs.
"""

import csv
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import time

def slugify(text):
    """Convert text to a slug format"""
    text = text.lower().strip()
    text = text.replace(" ", "-")
    text = "".join(c if c.isalnum() or c == "-" else "" for c in text)
    while "--" in text:
        text = text.replace("--", "-")
    return text

def get_agency_name(agency_string):
    """Extract clean agency name from folder path"""
    return agency_string.replace('-', ' ').title()

def check_file_exists(agency_slug):
    """Check if files already exist for this agency"""
    agency_dir = Path(f'data/raw/{agency_slug}')
    if agency_dir.exists():
        files = list(agency_dir.glob('*'))
        # Filter out .DS_Store and other system files
        data_files = [f for f in files if not f.name.startswith('.')]
        return len(data_files) > 0
    return False

def download_file(url, output_path, timeout=30):
    """Download a file using curl with validation"""
    try:
        result = subprocess.run(
            ['curl', '-L', '--max-time', str(timeout), '-o', output_path, url],
            capture_output=True,
            timeout=timeout + 5
        )

        if result.returncode != 0 or not os.path.exists(output_path):
            return False

        # Check if file is too small or is HTML (common for blocked downloads)
        if os.path.getsize(output_path) < 100:
            return False

        # Check if downloaded content is HTML (Cloudflare block, 404, etc.)
        with open(output_path, 'rb') as f:
            first_bytes = f.read(200).lower()
            if b'<!doctype html' in first_bytes or b'<html' in first_bytes:
                # Check for Cloudflare or error pages
                if b'cloudflare' in first_bytes or b'just a moment' in first_bytes:
                    print(f"    (Blocked by Cloudflare)")
                    return False
                elif b'404' in first_bytes or b'not found' in first_bytes:
                    print(f"    (404 - File not found)")
                    return False

        return os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"    Error: {e}")
        return False

def get_filename_from_redirect(url, timeout=30):
    """Get filename from content-disposition header after redirect"""
    try:
        result = subprocess.run(
            ['curl', '-L', '--max-time', str(timeout), '-I', url],
            capture_output=True,
            timeout=timeout + 5,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'content-disposition' in line.lower():
                    # Extract filename from header like: content-disposition: attachment; filename="file.xlsx"
                    if 'filename=' in line:
                        filename = line.split('filename=')[1].strip('"')
                        return filename
    except Exception:
        pass
    return None

def get_filename_from_url(url):
    """Extract filename from URL or content-disposition header"""
    from urllib.parse import unquote
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    filename = unquote(filename)

    # If no filename or just a generic endpoint (like /dl), try redirect header
    if not filename or '?' in filename or filename in ['dl', 'download']:
        # Try to get filename from content-disposition header after redirect
        header_filename = get_filename_from_redirect(url)
        if header_filename:
            return header_filename

        # Fallback to extension-based naming
        if '.csv' in url:
            return 'inventory.csv'
        elif '.xlsx' in url:
            return 'inventory.xlsx'
        elif '.pdf' in url:
            return 'inventory.pdf'
        else:
            return 'inventory'

    return filename

class FileDownloader:
    def __init__(self, csv_file='data/raw/agencies.csv'):
        self.csv_file = Path(csv_file)
        if not self.csv_file.exists() and Path(f'../{csv_file}').exists():
            self.csv_file = Path(f'../{csv_file}')

        self.to_download = []
        self.downloaded = []
        self.failed = []
        self.skipped = []

    def scan_agencies(self):
        """Scan CSV for agencies with URLs but no files"""
        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                agency_name = row['agency']
                url = row['inventory_2025_file_url']

                # Skip if no URL
                if not url or url.strip() == '':
                    continue

                # Special handling for agencies requiring manual download
                if 'Tennessee Valley Authority' in agency_name:
                    slug = slugify(agency_name)
                    if not check_file_exists(slug):
                        self.skipped.append({
                            'agency': agency_name,
                            'reason': 'Requires manual HTML download (see README)'
                        })
                    else:
                        self.skipped.append({'agency': agency_name, 'reason': 'File already exists'})
                    continue

                # Check if file already exists
                slug = slugify(agency_name)
                if check_file_exists(slug):
                    self.skipped.append({'agency': agency_name, 'reason': 'File already exists'})
                    continue

                self.to_download.append({
                    'agency': agency_name,
                    'slug': slug,
                    'url': url
                })

    def download_all(self):
        """Download all missing files"""
        print("=" * 80)
        print("DOWNLOADING MISSING AI INVENTORY FILES")
        print("=" * 80)
        print(f"\nFound {len(self.to_download)} agencies to download")
        print(f"Skipped {len(self.skipped)} (files already exist)\n")

        for i, item in enumerate(self.to_download, 1):
            agency = item['agency']
            slug = item['slug']
            url = item['url']

            print(f"[{i}/{len(self.to_download)}] {agency}")
            print(f"  URL: {url}")

            # Create directory
            dir_path = Path(f'data/raw/{slug}')
            dir_path.mkdir(parents=True, exist_ok=True)

            # Get filename
            filename = get_filename_from_url(url)
            file_path = dir_path / filename

            # Download
            print(f"  Downloading...", end='', flush=True)
            time.sleep(0.5)  # Be polite to servers

            if download_file(url, str(file_path)):
                file_size = os.path.getsize(file_path) / 1024 / 1024
                print(f" ✓ ({file_size:.1f} MB)")
                self.downloaded.append({'agency': agency, 'file': filename, 'size_mb': file_size})
            else:
                print(f" ✗ Failed")
                self.failed.append({'agency': agency, 'url': url})
                if file_path.exists():
                    os.remove(file_path)

    def print_summary(self):
        """Print download summary"""
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        print(f"\nDownloaded: {len(self.downloaded)}")
        for item in self.downloaded:
            print(f"  ✓ {item['agency']} - {item['file']} ({item['size_mb']:.1f} MB)")

        if self.skipped:
            print(f"\nSkipped: {len(self.skipped)}")
            for item in self.skipped:
                print(f"  - {item['agency']} ({item['reason']})")

        if self.failed:
            print(f"\nFailed: {len(self.failed)}")
            for item in self.failed:
                print(f"  ✗ {item['agency']}")
                print(f"    URL: {item['url']}")

        # Save log
        self.save_log()

    def save_log(self):
        """Save download log"""
        log_file = Path('data/build/download_log.txt')
        if not log_file.parent.exists():
            log_file = Path('../data/build/download_log.txt')

        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("FILE DOWNLOAD LOG\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Downloaded: {len(self.downloaded)}\n")
            for item in self.downloaded:
                f.write(f"  ✓ {item['agency']} - {item['file']}\n")

            if self.skipped:
                f.write(f"\nSkipped: {len(self.skipped)}\n")
                for item in self.skipped:
                    f.write(f"  - {item['agency']}: {item['reason']}\n")

            if self.failed:
                f.write(f"\nFailed: {len(self.failed)}\n")
                for item in self.failed:
                    f.write(f"  ✗ {item['agency']}\n")
                    f.write(f"    URL: {item['url']}\n")

        print(f"\n✓ Log saved to: {log_file}")

if __name__ == '__main__':
    downloader = FileDownloader()
    downloader.scan_agencies()

    if downloader.to_download:
        downloader.download_all()
        downloader.print_summary()
    else:
        print("\n" + "=" * 80)
        print("NO NEW FILES TO DOWNLOAD")
        print("=" * 80)
        print("\nAll agencies either have files or no URLs.")
        if downloader.skipped:
            print(f"\n{len(downloader.skipped)} agencies already have files.")
