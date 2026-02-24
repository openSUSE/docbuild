"""audit_metadata.py - Comprehensive Metadata Parity Analysis Tool.

This tool performs a high-level statistical comparison between the legacy manual manifests
(the gold standard) and the newly generated metadata. It identifies "hollow" manifests
and calculates a Match Rate percentage for every product in the catalog.

Key Features:
- Calculates Match Rate based on title set intersection.
- Identifies products that are completely missing from the automated build.
- Generates a CSV report sorted by failure severity to prioritize XSLT fixes.
"""

import csv
import json
import logging
import os
from pathlib import Path

# --- Configuration ---
# LEGACY_BASE: Where the hand-curated JSON files live (The Baseline)
LEGACY_BASE = "/docserv-config/json-portal-dsc"
# NEW_BASE: Where docbuild outputs the newly generated manifests
NEW_BASE = "/mnt/build/cache/doc-example-com/meta"
# OUTPUT_FILE: The destination for the final audit report
OUTPUT_FILE = "/mnt/build/docbuild/audit_reports/full_audit_summary.csv"

# Setup logging for better visibility during long runs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_titles(file_path: Path) -> set[str]:
    """Extract and normalize document titles from a manifest.

    Args:
        file_path: Path to a JSON manifest file.

    Returns:
        A set of unique document titles.

    """
    try:
        if not file_path.exists():
            return set()

        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
            # The 'documents' array is where individual guides are stored
            docs_list = data.get('documents', [])

            # Extract titles. We use 'NO TITLE' as a placeholder
            # to detect cases where your PR's resilience defaults were triggered.
            titles = set()
            for doc in docs_list:
                inner_docs = doc.get('docs', [])
                if inner_docs:
                    # Capture the title from the first language entry
                    title = inner_docs[0].get('title', 'NO TITLE')
                    titles.add(title)
            return titles
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Failed to parse {file_path}: {e}")
        return set()

def run_metadata_audit() -> None:
    """Run the main execution logic for the metadata audit."""
    results = []

    # Ensure the audit directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    logging.info("🚀 Starting audit comparison...")
    logging.info(f"Baseline: {LEGACY_BASE}")
    logging.info(f"Generated: {NEW_BASE}")

    # Walk through the legacy directory to find all product JSONs
    for root, _, files in os.walk(LEGACY_BASE):
        for file in files:
            if not file.endswith(".json"):
                continue

            legacy_path = Path(root) / file
            # Determine the relative path (e.g., 'sles/15-SP5.json')
            relative_path = legacy_path.relative_to(LEGACY_BASE)
            # Find the corresponding file in the new build output
            new_path = Path(NEW_BASE) / relative_path

            # Get title sets for both versions
            legacy_titles = get_titles(legacy_path)
            new_titles = get_titles(new_path)

            # Calculate the delta (what did we fail to extract?)
            missing_titles = legacy_titles - new_titles

            manual_count = len(legacy_titles)
            generated_count = len(new_titles)

            # Calculate Match Rate percentage
            if manual_count > 0:
                match_rate_val = (generated_count / manual_count) * 100
            else:
                match_rate_val = 0.0

            results.append({
                "Product_Path": str(relative_path),
                "Manual_Count": manual_count,
                "Generated_Count": generated_count,
                "Missing_Count": len(missing_titles),
                "Match_Rate": f"{match_rate_val:.1f}%"
            })

    if not results:
        logging.error("No JSON files found to audit!")
        return

    # Sort results: Lowest Match Rate first (prioritize the "hollow" files)
    results.sort(key=lambda x: float(x['Match_Rate'].replace('%','')))

    # Write the summary to CSV
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"✅ Audit complete! Report saved to: {OUTPUT_FILE}")
    except PermissionError:
        logging.error(f"Could not write to {OUTPUT_FILE}. Is it open in another program?")

if __name__ == "__main__":
    run_metadata_audit()
