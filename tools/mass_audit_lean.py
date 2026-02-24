"""mass_audit_lean.py - Targeted Metadata Verification Tool.

This is a lightweight version of the mass auditor, designed for rapid
verification of code changes. It reads a subset of product targets from
'lean_audit.txt' and performs a non-destructive, no-clone metadata build.

Use Case:
- Verifying Pydantic model resilience against known "broken" XML sources.
- Testing local changes in storage-constrained environments (Docker/Podman).
- Debugging specific product versions without running the full catalog.
"""

import csv
import logging
import os
from pathlib import Path
import subprocess

# --- Configuration ---
# File containing a list of specific doctypes to test (e.g., sles/12-SP5/en-us)
LEAN_LIST = "/mnt/build/docbuild/docbuild/lean_audit.txt"
# Destination for targeted audit logs
AUDIT_BASE = Path("/mnt/build/docbuild/audit_reports/lean_audit")
# Absolute path to the development environment configuration
ENV_CONFIG = "/mnt/build/docbuild/docbuild/env.development.toml"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_lean_audit() -> None:
    """Execute a targeted audit for specific product targets."""
    AUDIT_BASE.mkdir(parents=True, exist_ok=True)
    summary_data = []

    if not os.path.exists(LEAN_LIST):
        logging.error(f"❌ Target list not found: {LEAN_LIST}. Please create it with one doctype per line.")
        return

    with open(LEAN_LIST) as f:
        # Filter out empty lines and comments
        doctypes = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not doctypes:
        logging.warning("Target list is empty. Nothing to process.")
        return

    logging.info(f"🚀 Starting Lean Audit for {len(doctypes)} targets.")

    for doctype in doctypes:
        logging.info(f"🔎 Processing: {doctype}")

        # Construct the docbuild command.
        # We use --skip-repo-update to rely on local worktrees/symlinks.
        cmd = [
            "docbuild",
            "--env-config", ENV_CONFIG,
            "metadata",
            "--skip-repo-update",
            doctype
        ]

        try:
            # Execute with a 2-minute timeout per product for the lean run
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # Map doctype to a filesystem-safe folder name
            product_folder = doctype.replace("/", "_")
            log_dir = AUDIT_BASE / product_folder
            log_dir.mkdir(parents=True, exist_ok=True)

            # Persist logs for inspection of Pydantic behavior
            with open(log_dir / "stderr.log", "w", encoding="utf-8") as f:
                f.write(result.stderr)
            with open(log_dir / "stdout.log", "w", encoding="utf-8") as f:
                f.write(result.stdout)

            # Status determination: 0 return code means the resilience models held up.
            status = "SUCCESS" if result.returncode == 0 else "FAILED"
            summary_data.append([doctype, status])

        except subprocess.TimeoutExpired:
            logging.error(f"⏱️ Timeout: {doctype} took too long.")
            summary_data.append([doctype, "TIMEOUT"])
        except Exception as e:
            logging.error(f"💥 Critical Error on {doctype}: {e}")
            summary_data.append([doctype, "ERROR"])

    # Final summary generation
    summary_csv = AUDIT_BASE / "lean_summary.csv"
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Doctype", "Status"])
        writer.writerows(summary_data)

    logging.info(f"✅ Lean Audit Complete. Results at: {AUDIT_BASE}/lean_summary.csv")

if __name__ == "__main__":
    run_lean_audit()
