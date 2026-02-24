"""mass_audit.py - Catalog-Wide Metadata Generation & Audit Runner.

This tool automates the 'docbuild metadata' command for every product/version
pair defined in the legacy manual configuration. It serves as the primary
driver for benchmarking the automated pipeline against the existing catalog.

Key Features:
- Automatic discovery of product/version pairs from the manual JSON directory.
- Isolated logging (stdout/stderr) for every audit target.
- Non-blocking execution: captures failures without halting the mass run.
- Integrated 'Success' detection based on return codes and deliverable status.
"""

import csv
import logging
import os
from pathlib import Path
import subprocess

# --- Configuration ---
# Where the "Gold Standard" manual manifests live
MANUAL_JSON_DIR = "/docserv-config/json-portal-dsc"
# Where to store the generated logs and CSV summary
AUDIT_BASE = Path("/mnt/build/docbuild/audit_reports/products")
# The environment configuration file (absolute path recommended)
ENV_CONFIG = "/mnt/build/docbuild/docbuild/env.development.toml"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_mass_audit() -> None:
    """Orchestrates the metadata build for the entire product catalog."""
    AUDIT_BASE.mkdir(parents=True, exist_ok=True)
    summary_data = []

    logging.info(f"🚀 Starting Mass Audit using config: {ENV_CONFIG}")

    # Discover all product/release pairs from the manual directory structure
    for root, _dirs, files in os.walk(MANUAL_JSON_DIR):
        for file in files:
            if not file.endswith(".json"):
                continue

            # Calculate the product and version from the file path
            rel_path = Path(root).relative_to(MANUAL_JSON_DIR)
            product = str(rel_path)
            version = file.replace(".json", "")

            # Skip top-level files that aren't product-specific
            if product == ".":
                continue

            doctype = f"{product}/{version}/en-us"
            logging.info(f"🔎 Processing: {doctype}")

            # Define the log directory for this specific doctype
            log_dir = AUDIT_BASE / product / version
            log_dir.mkdir(parents=True, exist_ok=True)

            # Build the docbuild command
            # Added '--skip-repo-update' to prevent massive disk usage/cloning
            cmd = [
                "docbuild",
                "--env-config", ENV_CONFIG,
                "metadata",
                "--skip-repo-update",
                doctype
            ]

            try:
                # Execute the build
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                # Capture logs regardless of success/failure
                with open(log_dir / "stderr.log", "w", encoding="utf-8") as f:
                    f.write(result.stderr)
                with open(log_dir / "stdout.log", "w", encoding="utf-8") as f:
                    f.write(result.stdout)

                # Determine status
                # A run is successful only if return code is 0 AND no deliverables failed
                if result.returncode == 0 and "failed deliverables" not in result.stdout:
                    status = "SUCCESS"
                else:
                    status = "FAILED"

            except subprocess.TimeoutExpired:
                status = "TIMEOUT"
                logging.error(f"❌ {doctype} timed out after 5 minutes.")
            except Exception as e:
                status = "ERROR"
                logging.error(f"❌ Error processing {doctype}: {e}")

            summary_data.append([doctype, status])

    # Generate the Audit Summary CSV
    summary_csv = AUDIT_BASE / "audit_summary.csv"
    try:
        with open(summary_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Doctype", "Status"])
            writer.writerows(summary_data)
        logging.info(f"✅ Mass Audit Complete. Summary saved to: {summary_csv}")
    except Exception as e:
        logging.error(f"Failed to write summary CSV: {e}")

if __name__ == "__main__":
    run_mass_audit()
