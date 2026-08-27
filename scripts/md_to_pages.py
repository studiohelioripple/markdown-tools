#!/usr/bin/env python3
"""
Forma Document Engine (md_to_pages.py)
---------------------------------------
Converts Markdown documents into styled Apple Pages (.pages), PDF, HTML, or DOCX documents.
Supports 8 customizable themes with Amil and Apple Design systems.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import markdown_convert as mc
from markdown_convert import (
    THEME_CONFIGS,
    THEME_ALIASES,
    DARK_THEMES,
    normalize_theme_name,
    generate_theme_css,
    is_persian_or_arabic,
    parse_markdown_to_html,
    convert_markdown,
)

THEME_CSS: dict[str, str] = {
    name: generate_theme_css(name) for name in THEME_CONFIGS.keys()
}


def is_pages_available() -> bool:
    """Checks if Apple Pages is installed and scriptable on macOS."""
    if sys.platform != "darwin":
        return False
    has_app = os.path.exists("/Applications/Pages.app") or os.path.exists("/Applications/Pages Creator Studio.app")
    if not has_app:
        return False
    if shutil.which("osascript"):
        res = subprocess.run(["osascript", "-e", 'id of application "Pages"'], capture_output=True, text=True)
        return res.returncode == 0
    return False


def convert_md_to_html(md_path: str | Path, html_path: str | Path | None = None, theme: str = "amil-light", open_result: bool = False) -> str:
    """Converts a Markdown file into a standalone, styled HTML document."""
    source = Path(md_path)
    output = Path(html_path) if html_path else None
    dest = convert_markdown(source, "html", output, theme=theme)
    if open_result:
        subprocess.run(["open", str(dest)])
    return str(dest)


def convert_md_to_pdf(md_path: str | Path, pdf_path: str | Path | None = None, theme: str = "amil-light", open_result: bool = False) -> str:
    """Converts a Markdown file into a vector-crisp PDF."""
    source = Path(md_path)
    output = Path(pdf_path) if pdf_path else None
    dest = convert_markdown(source, "pdf", output, theme=theme)
    if open_result:
        subprocess.run(["open", str(dest)])
    return str(dest)


def convert_md_to_pages(md_path: str | Path, pages_path: str | Path | None = None, theme: str = "amil-light", open_result: bool = False) -> str:
    """Converts a Markdown file into a native Apple Pages document."""
    source = Path(md_path)
    output = Path(pages_path) if pages_path else None
    dest = convert_markdown(source, "pages", output, theme=theme)
    if open_result:
        subprocess.run(["open", str(dest)])
    return str(dest)


def convert_md_to_docx(md_path: str | Path, docx_path: str | Path | None = None, theme: str = "amil-light", open_result: bool = False) -> str:
    """Converts a Markdown file into a Microsoft Word document."""
    source = Path(md_path)
    output = Path(docx_path) if docx_path else None
    dest = convert_markdown(source, "docx", output, theme=theme)
    if open_result:
        subprocess.run(["open", str(dest)])
    return str(dest)


def convert_md(md_path: str | Path, output_path: str | Path | None = None, target_format: str | None = None, theme: str = "amil-light", open_result: bool = False) -> str:
    """Universal Markdown converter dispatching to HTML, PDF, Pages, or DOCX."""
    source = Path(md_path)
    if not target_format:
        if output_path:
            ext = Path(output_path).suffix.lower().lstrip(".")
            target_format = ext if ext in ("pdf", "html", "pages", "docx") else "pages"
        else:
            target_format = "pages"

    fmt = target_format.lower()
    dest = convert_markdown(source, fmt, Path(output_path) if output_path else None, theme=theme)
    if open_result:
        subprocess.run(["open", str(dest)])
    return str(dest)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Forma: Convert Markdown (.md) to Apple Pages, PDF, HTML, or DOCX with 8 customizable themes"
    )
    parser.add_argument("input", help="Path to input Markdown file (.md)")
    parser.add_argument("-o", "--output", help="Path to output file (.pages, .pdf, .html, .docx)")
    parser.add_argument(
        "-f", "--format",
        choices=["pages", "pdf", "html", "docx"],
        help="Target format (default: inferred from output extension or 'pages')"
    )
    parser.add_argument(
        "-t", "--theme",
        default="amil-light",
        help="Styling theme (amil-light, amil-dark, apple-light, apple-dark, vscode-dark, github-light, nord-frost, editorial-serif)",
    )
    parser.add_argument("--open", action="store_true", help="Open output file when done")

    args = parser.parse_args()
    try:
        convert_md(args.input, output_path=args.output, target_format=args.format, theme=args.theme, open_result=args.open)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
