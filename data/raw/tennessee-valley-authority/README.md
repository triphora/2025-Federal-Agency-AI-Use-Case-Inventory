# Tennessee Valley Authority - Manual Download Instructions

TVA's AI inventory is published on a Cloudflare-protected webpage and cannot be downloaded automatically with curl.

## Steps to Update TVA Data

1. **Visit the page** in your web browser:
   https://www.tva.com/information/tva-ai-use-case-inventory

2. **Save the complete webpage**:
   - Right-click anywhere on the page
   - Select "Save Page As..." or "Save As..."
   - Choose "Webpage, Complete" or "Web Page, HTML Only"
   - Save as: `tva-page.html` in this directory

3. **Run consolidation** (automatically parses HTML):
   ```bash
   just consolidate
   ```

## How It Works

The consolidation script automatically:
- Detects if `tva-page.html` exists
- Parses the HTML table using BeautifulSoup
- Creates `tva-inventory.csv` with extracted data
- Includes it in the consolidated output

No separate parsing step needed!
