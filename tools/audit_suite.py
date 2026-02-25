#!/usr/bin/env python3
"""audit_suite.py - Unified Metadata Audit & Parity Tooling.

This suite provides tools to benchmark automated metadata generation against
legacy manual manifests. It supports catalog-wide audits, targeted lean runs,
and granular field-level parity comparisons.
"""

import csv
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# --- Path Configuration (Environment Aware) ---
# Detect project root relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

if os.path.exists("/docserv-config"):
    # Standard paths for the SUSE Docker/CI environment
    LEGACY_BASE = Path("/docserv-config/json-portal-dsc")
    NEW_BASE = Path("/mnt/build/docbuild/cache/doc-example-com/meta")
    REPORT_DIR = Path("/mnt/build/docbuild/docbuild/audit_reports")
    ENV_CONFIG = Path("/mnt/build/docbuild/docbuild/env.development.toml")
    LEAN_LIST = Path("/mnt/build/docbuild/docbuild/lean_audit.txt")
else:
    # Portable fallback for local development (macOS/Generic Linux)
    LEGACY_BASE = Path(os.environ.get("LEGACY_BASE", ROOT_DIR.parent / "docserv-config/json-portal-dsc"))
    NEW_BASE = Path(os.environ.get("NEW_BASE", ROOT_DIR / "mnt/build/cache/doc-example-com/meta"))
    REPORT_DIR = ROOT_DIR / "audit_reports"
    ENV_CONFIG = ROOT_DIR / "env.development.toml"
    LEAN_LIST = ROOT_DIR / "lean_audit.txt"

console = Console()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Utility Functions ---

def normalize_text(text: str | None) -> str:
    """Lowercase and strip HTML/extra whitespace for fuzzy title matching."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", clean).strip().lower()

def get_titles(file_path: Path) -> set[str]:
    """Extract all unique document titles from a manifest JSON."""
    try:
        if not file_path.exists():
            return set()
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
            titles = set()
            for doc_group in data.get('documents', []):
                for doc in doc_group.get('docs', []):
                    t = doc.get('title')
                    titles.add(t if t is not None else "[MISSING TITLE]")
            return titles
    except Exception as e:
        logging.debug(f"Parsing failed for {file_path}: {e}")
        return set()

def get_doc_map(data: dict[str, Any]) -> dict[tuple, dict[str, Any]]:
    """Create a map of {(normalized_title, lang): doc_dict} for comparison."""
    doc_map = {}
    for doc_group in data.get("documents", []):
        for doc in doc_group.get("docs", []):
            key = (normalize_text(doc.get("title")), doc.get("lang", "unknown"))
            doc_map[key] = doc
    return doc_map

# --- Core Commands ---

def run_parity(path_a: str, path_b: str) -> None:
    """Perform a deep-dive comparison between two specific JSON manifests."""
    p1, p2 = Path(path_a), Path(path_b)
    try:
        with open(p1, encoding='utf-8') as f:
            d1 = json.load(f)
        with open(p2, encoding='utf-8') as f:
            d2 = json.load(f)
    except Exception as e:
        console.print(f"[bold red]Load error:[/bold red] {e}")
        return

    map1, map2 = get_doc_map(d1), get_doc_map(d2)
    table = Table(title=f"Parity Check: {p1.name} vs {p2.name}", header_style="bold blue")
    table.add_column("Document Title", style="italic")
    table.add_column("Field")
    table.add_column("Legacy (Baseline)", style="red")
    table.add_column("Generated (New)", style="green")

    fields = ["lang", "title", "description", "dcfile", "rootid"]
    diff_found = False

    for key, doc1 in map1.items():
        if key in map2:
            doc2 = map2[key]
            for f in fields:
                v1, v2 = str(doc1.get(f, "")).strip(), str(doc2.get(f, "")).strip()
                if v1 != v2:
                    table.add_row(doc1.get("title"), f, v1, v2)
                    diff_found = True
        else:
            table.add_row(doc1.get("title"), "FILE", "MISSING", "")
            diff_found = True

    if not diff_found:
        console.print("[bold green]✅ 100% Parity found![/bold green]")
    else:
        console.print(table)

def run_mass_audit(targets: list[str] | None = None) -> None:
    """Execute metadata builds for multiple product targets."""
    mode = "Lean" if targets else "Mass"
    output_base = REPORT_DIR / mode.lower()
    output_base.mkdir(parents=True, exist_ok=True)

    if not targets:
        targets = []
        for root, _, files in os.walk(LEGACY_BASE):
            for f in files:
                if f.endswith(".json"):
                    rel = Path(root).relative_to(LEGACY_BASE)
                    if str(rel) != ".":
                        targets.append(f"{rel}/{f.replace('.json', '')}/en-us")

    summary = []
    console.print(Panel(f"🚀 [bold cyan]Starting {mode} Audit[/bold cyan]\nTarget Count: {len(targets)}"))

    for doctype in targets:
        console.print(f"🔎 [blue]Processing:[/blue] {doctype}")
        log_dir = output_base / doctype.replace("/", "_")
        log_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["docbuild", "--env-config", str(ENV_CONFIG), "metadata", "--skip-repo-update", doctype]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            with open(log_dir / "stderr.log", "w", encoding="utf-8") as f:
                f.write(res.stderr)
            status = "SUCCESS" if res.returncode == 0 and "failed deliverables" not in res.stdout else "FAILED"
        except Exception as e:
            logging.error(f"Execution failed for {doctype}: {e}")
            status = "ERROR"

        summary.append([doctype, status])

    summary_file = output_base / "summary.csv"
    with open(summary_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Doctype", "Status"])
        writer.writerows(summary)
    console.print(f"[bold green]✅ {mode} Audit Finished. Summary: {summary_file}[/bold green]")

def run_stats() -> None:
    """Calculate Match Rate and Delta for the entire catalog."""
    results = []
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    for root, _, files in os.walk(LEGACY_BASE):
        for f in files:
            if f.endswith(".json"):
                lp = Path(root) / f
                rel_path = lp.relative_to(LEGACY_BASE)

                # Try direct structure, then flattened filename fallback
                np = NEW_BASE / rel_path
                if not np.exists():
                    np = NEW_BASE / str(rel_path).replace("/", "-")

                t1, t2 = get_titles(lp), get_titles(np)
                m_count, g_count = len(t1), len(t2)
                rate = (g_count / m_count * 100) if m_count > 0 else 0
                results.append({
                    "Path": str(rel_path),
                    "Match_Rate": f"{rate:.1f}%",
                    "Missing": len(t1 - t2)
                })

    results.sort(key=lambda x: float(x['Match_Rate'].replace('%','')))
    stats_file = REPORT_DIR / "stats_summary.csv"
    with open(stats_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    console.print(f"[bold green]✅ Stats saved to: {stats_file}[/bold green]")

# --- Entry Point ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[yellow]Usage: ./audit_suite.py [mass|lean|parity <legacy.json> <new.json>|stats][/yellow]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "mass":
        run_mass_audit()
    elif command == "lean":
        if not LEAN_LIST.exists():
            console.print(f"[red]Error: {LEAN_LIST} not found.[/red]")
        else:
            with open(LEAN_LIST, encoding='utf-8') as f:
                ts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            run_mass_audit(ts)
    elif command == "parity" and len(sys.argv) == 4:
        run_parity(sys.argv[2], sys.argv[3])
    elif command == "stats":
        run_stats()
    else:
        console.print("[red]Invalid command or arguments.[/red]")
