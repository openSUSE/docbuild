#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["rich"]
# ///
"""audit_suite.py - Unified Metadata Audit & Parity Tooling."""

import argparse
from collections.abc import Sequence
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

# --- Path Configuration ---
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

if os.path.exists("/docserv-config"):
    LEGACY_BASE = Path("/docserv-config/json-portal-dsc")
    NEW_BASE = Path("/mnt/build/docbuild/cache/doc-example-com/meta")
    REPORT_DIR = Path("/mnt/build/docbuild/docbuild/audit_reports")
    ENV_CONFIG = Path("/mnt/build/docbuild/docbuild/env.development.toml")
    LEAN_LIST = Path("/mnt/build/docbuild/docbuild/lean_audit.txt")
else:
    LEGACY_BASE = Path(os.environ.get("LEGACY_BASE", ROOT_DIR.parent / "docserv-config/json-portal-dsc"))
    NEW_BASE = Path(os.environ.get("NEW_BASE", ROOT_DIR / "mnt/build/cache/doc-example-com/meta"))
    REPORT_DIR = ROOT_DIR / "audit_reports"
    ENV_CONFIG = ROOT_DIR / "env.development.toml"
    LEAN_LIST = ROOT_DIR / "lean_audit.txt"

console = Console()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Utility Functions ---

def normalize_lang(lang: str | None) -> str:
    """Fuzzy match languages by comparing only the first two chars (e.g., en == en-us)."""
    if not lang:
        return "unknown"
    return lang.split('-')[0].split('_')[0].lower()

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

def get_doc_map(data: dict[str, Any], fuzzy_lang: bool = False) -> dict[tuple, dict[str, Any]]:
    """Create a map of {(normalized_title, lang): doc_dict} for comparison."""
    doc_map = {}
    for doc_group in data.get("documents", []):
        for doc in doc_group.get("docs", []):
            lang = doc.get("lang", "unknown")
            if fuzzy_lang:
                lang = normalize_lang(lang)
            key = (normalize_text(doc.get("title")), lang)
            doc_map[key] = doc
    return doc_map

# --- Core Commands ---

def run_parity(args: argparse.Namespace) -> int:
    """Perform a deep-dive comparison between two specific JSON manifests."""
    p1, p2 = Path(args.legacy), Path(args.new)
    try:
        with open(p1, encoding='utf-8') as f:
            d1 = json.load(f)
        with open(p2, encoding='utf-8') as f:
            d2 = json.load(f)
    except Exception as e:
        console.print(f"[bold red]Load error:[/bold red] {e}")
        return 1

    # Use fuzzy lang matching if requested
    map1, map2 = get_doc_map(d1, fuzzy_lang=args.fuzzy), get_doc_map(d2, fuzzy_lang=args.fuzzy)

    table = Table(title=f"Parity Check: {p1.name} vs {p2.name}", header_style="bold blue")
    table.add_column("Language", justify="center")
    table.add_column("Document Title", style="italic")
    table.add_column("Field")
    table.add_column("Legacy (Baseline)", style="red")
    table.add_column("Generated (New)", style="green")

    fields = ["lang", "title", "description", "dcfile", "rootid"]
    diff_found = False

    for key, doc1 in map1.items():
        # key is (normalized_title, lang)
        title_text = doc1.get("title", "[NO TITLE]")
        lang_text = doc1.get("lang", "??")

        if key in map2:
            doc2 = map2[key]
            for f in fields:
                v1, v2 = str(doc1.get(f, "")).strip(), str(doc2.get(f, "")).strip()

                # Special check for lang if fuzzy is on
                if f == "lang" and args.fuzzy:
                    if normalize_lang(v1) == normalize_lang(v2):
                        continue

                if v1 != v2:
                    table.add_row(lang_text, title_text, f, v1, v2)
                    diff_found = True
        else:
            table.add_row(lang_text, title_text, "FILE", "MISSING", "")
            diff_found = True

    if not diff_found:
        console.print(f"[bold green]✅ 100% Parity found (Fuzzy Lang: {args.fuzzy})![/bold green]")
        return 0
    else:
        console.print(table)
        return 1

def run_mass_audit(args: argparse.Namespace | None = None, targets: list[str] | None = None) -> int:
    """Execute metadata builds for multiple product targets."""
    mode = "Mass"
    if targets or (args and hasattr(args, 'command') and args.command == 'lean'):
        mode = "Lean"

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
    return 0

def run_lean(args: argparse.Namespace) -> int:
    """Wrap run_mass_audit using a lean list file."""
    lean_path = Path(args.lean_list)
    if not lean_path.exists():
        console.print(f"[red]Error: {lean_path} not found.[/red]")
        return 1

    with open(lean_path, encoding='utf-8') as f:
        ts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return run_mass_audit(targets=ts)

def run_stats(args: argparse.Namespace) -> int:
    """Calculate Match Rate and Delta for the entire catalog."""
    results = []
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    for root, _, files in os.walk(LEGACY_BASE):
        for f in files:
            if f.endswith(".json"):
                lp = Path(root) / f
                rel_path = lp.relative_to(LEGACY_BASE)
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

    if not results:
        console.print("[yellow]No JSON files found for stats.[/yellow]")
        return 1

    results.sort(key=lambda x: float(x['Match_Rate'].replace('%','')))
    stats_file = REPORT_DIR / "stats_summary.csv"
    with open(stats_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    console.print(f"[bold green]✅ Stats saved to: {stats_file}[/bold green]")
    return 0

# --- CLI Parsing ---

def parsecli(args: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the audit suite."""
    parser = argparse.ArgumentParser(description="Audit Suite CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="The command to execute")

    subparsers.add_parser("mass", help="Run mass audit").set_defaults(func=run_mass_audit)

    lean_parser = subparsers.add_parser("lean", help="Run lean audit")
    lean_parser.add_argument("lean_list", type=str, default=str(LEAN_LIST), nargs='?', help="Path to lean list")
    lean_parser.set_defaults(func=run_lean)

    parity_parser = subparsers.add_parser("parity", help="Compare legacy and new JSON data")
    parity_parser.add_argument("legacy", type=str, help="Path to legacy JSON")
    parity_parser.add_argument("new", type=str, help="Path to new JSON")
    parity_parser.add_argument("--fuzzy", action="store_true", help="Enable fuzzy language matching (en-us == en)")
    parity_parser.set_defaults(func=run_parity)

    subparsers.add_parser("stats", help="View audit statistics").set_defaults(func=run_stats)

    return parser.parse_args(args)

def main() -> int:
    """Execute the main entry point for the audit suite CLI."""
    parsed_args = parsecli()
    return parsed_args.func(parsed_args)

if __name__ == "__main__":
    sys.exit(main())
