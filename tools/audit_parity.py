#!/usr/bin/env -S uv run --frozen python
"""Smart Audit Tool for Document Manifest Parity.

Compares a legacy (manual) JSON manifest against a generated JSON manifest
by matching documents based on normalized Titles and strict Languages.
"""

import json
from pathlib import Path
import re
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def normalize_text(text: str) -> str:
    """Lowercase and strip HTML/extra whitespace for fuzzy title matching."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple whitespaces into one
    return re.sub(r"\s+", " ", clean).strip().lower()


def get_doc_map(data: dict) -> dict:
    """Create a map of {(normalized_title, lang): doc_dict}.

    Use the raw language code to ensure that discrepancies like 'en' vs 'en-us'
    are caught and reported in the audit table.
    """
    doc_map = {}
    for doc_group in data.get("documents", []):
        for doc in doc_group.get("docs", []):
            title = doc.get("title", "Untitled")
            lang = doc.get("lang", "unknown")
            # Unique key: Normalized Title + Strict Language Code
            key = (normalize_text(title), lang)
            doc_map[key] = doc
    return doc_map


def run_audit(manual_path: str, generated_path: str) -> None:
    """Compare two manifest files and report discrepancies."""
    p_manual = Path(manual_path)
    p_generated = Path(generated_path)

    try:
        with open(manual_path, encoding="utf-8") as f:
            manual_data = json.load(f)
        with open(generated_path, encoding="utf-8") as f:
            gen_data = json.load(f)
    except Exception as e:
        console.print(f"[bold red]Error loading files:[/bold red] {e}")
        return

    manual_docs = get_doc_map(manual_data)
    gen_docs = get_doc_map(gen_data)

    console.print(
        Panel(
            f"Legacy:    [bold magenta]{p_manual.name}[/bold magenta]\n"
            f"Generated: [bold green]{p_generated.name}[/bold green]",
            title="[bold cyan]Manifest Comparison Audit[/bold cyan]",
            subtitle=f"Comparing {p_manual.parent.name} structure",
        )
    )

    # Fields to verify for structural and content parity
    fields_to_check = [
        "lang",
        "title",
        "description",
        "dateModified",
        "rank",
        "isGate",
        "dcfile",
        "rootid",
    ]

    table = Table(title="Field Discrepancies", show_header=True, header_style="bold blue")
    table.add_column("Document Match", style="italic")
    table.add_column("Field")
    table.add_column("Legacy Value", style="red")
    table.add_column("Generated Value", style="green")

    diff_found = False

    # Check for differences in matching documents
    for key, m_doc in manual_docs.items():
        if key in gen_docs:
            g_doc = gen_docs[key]
            for field in fields_to_check:
                # Normalize values to strings for comparison
                m_val = str(m_doc.get(field, "")).strip()
                g_val = str(g_doc.get(field, "")).strip()

                if m_val != g_val:
                    table.add_row(m_doc.get("title"), field, m_val, g_val)
                    diff_found = True
        else:
            # Document exists in Legacy but could not be matched in Generated
            table.add_row(m_doc.get("title"), "FILE", "MISSING", "")
            diff_found = True

    # Check for extra documents in Generated that aren't in Legacy
    for key, g_doc in gen_docs.items():
        if key not in manual_docs:
            table.add_row(g_doc.get("title"), "FILE", "", "NEW IN GENERATED")
            diff_found = True

    if not diff_found:
        console.print("[bold green]✅ 100% Parity found![/bold green]")
    else:
        console.print(table)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        console.print("[yellow]Usage:[/yellow] ./tools/audit_parity.py <legacy.json> <generated.json>")
        sys.exit(1)

    run_audit(sys.argv[1], sys.argv[2])
