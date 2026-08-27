#!/usr/bin/env python3
"""
Forma Document Engine (md_to_pages.py)
--------------------------------------
Converts Markdown (.md) documents into beautiful Apple-designed HTML, PDF,
Apple Pages (.pages), and Microsoft Word (.docx) documents on macOS.

Key Features:
- Apple Design Guidelines: Typography (SF Pro, New York, SF Mono), rounded cards,
  tinted callout banners, elegant tables, dark/light themes, print CSS.
- Full GitHub Flavored Markdown (GFM): Fenced code blocks with language tags,
  callouts ([!NOTE], [!TIP], [!IMPORTANT], [!WARNING], [!CAUTION]), tables with
  alignments, task lists, badge rows, hero images, blockquotes.
- Multi-Engine PDF Export: Headless Chrome / WebKit for pixel-perfect vector PDFs.
- High-Fidelity Pages Export: Styled Cocoa HTML -> DOCX -> native Apple Pages (.pages)
  via AppleScript automation.
- 100% Local Processing: Zero external network or API dependencies.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Helper: Pages Availability Detection ──────────────────────────────────────

def is_pages_available() -> bool:
    """Checks whether Apple Pages (or Pages Creator Studio) is available on macOS."""
    if sys.platform != "darwin":
        return False
    if os.path.exists("/Applications/Pages.app") or os.path.exists("/Applications/Pages Creator Studio.app"):
        return True
    if shutil.which("osascript"):
        res = subprocess.run(["osascript", "-e", 'id of application "Pages"'], capture_output=True, text=True)
        return res.returncode == 0
    return False


# ── Apple Design CSS Themes ───────────────────────────────────────────────────

THEME_CSS: dict[str, str] = {
    "modern": """
        :root {
            --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif;
            --font-mono: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", monospace;
            --bg-page: #f5f5f7;
            --bg-card: #ffffff;
            --text-primary: #1d1d1f;
            --text-secondary: #6e6e73;
            --border-subtle: #d2d2d7;
            --border-card: rgba(0, 0, 0, 0.08);
            --accent-blue: #0071e3;
            --accent-blue-bg: #f0f7ff;
            --code-bg: #1e1e24;
            --code-text: #e6edf3;
            --inline-code-bg: #f2f2f7;
            --table-header: #fbfbfd;
            --table-zebra: #fafafa;
        }

        body {
            font-family: var(--font-sans);
            background-color: var(--bg-page);
            color: var(--text-primary);
            line-height: 1.65;
            margin: 0;
            padding: 40px 20px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        .document-container {
            max-width: 880px;
            margin: 0 auto;
            background: var(--bg-card);
            padding: 56px 64px;
            border-radius: 16px;
            box-shadow: 0 4px 28px rgba(0, 0, 0, 0.06);
            border: 1px solid var(--border-card);
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: var(--font-sans);
            color: #111111;
            font-weight: 650;
            line-height: 1.25;
            letter-spacing: -0.015em;
            margin-top: 1.8em;
            margin-bottom: 0.6em;
        }

        h1 {
            font-size: 2.25em;
            letter-spacing: -0.025em;
            border-bottom: 1.5px solid #e5e5ea;
            padding-bottom: 0.35em;
            margin-top: 0.2em;
        }

        h2 {
            font-size: 1.6em;
            letter-spacing: -0.02em;
            border-bottom: 1px solid #f2f2f7;
            padding-bottom: 0.28em;
        }

        h3 { font-size: 1.3em; }
        h4 { font-size: 1.12em; }
        h5 { font-size: 1.0em; }
        h6 { font-size: 0.9em; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; }

        p {
            margin: 1.0em 0;
            font-size: 1.02em;
            letter-spacing: -0.005em;
        }

        a {
            color: var(--accent-blue);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.15s ease;
        }

        a:hover {
            text-decoration: underline;
        }

        /* Inline Code */
        code {
            font-family: var(--font-mono);
            background-color: var(--inline-code-bg);
            color: #bf2642;
            padding: 0.2em 0.45em;
            border-radius: 6px;
            font-size: 0.88em;
            border: 1px solid rgba(0, 0, 0, 0.05);
        }

        /* Fenced Code Blocks (macOS Terminal / Xcode aesthetic) */
        .code-block {
            margin: 1.5em 0;
            border-radius: 10px;
            background-color: var(--code-bg);
            color: var(--code-text);
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.09);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .code-header {
            background: #141418;
            padding: 8px 16px;
            font-size: 0.76em;
            font-family: var(--font-mono);
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            border-bottom: 1px solid #2a2a30;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .code-block pre {
            margin: 0;
            padding: 18px 20px;
            overflow-x: auto;
            background: transparent;
        }

        .code-block code {
            font-family: var(--font-mono);
            background: transparent;
            padding: 0;
            border: none;
            color: inherit;
            font-size: 0.9em;
            line-height: 1.55;
        }

        /* Blockquotes */
        blockquote {
            margin: 1.4em 0;
            padding: 12px 20px;
            color: #555558;
            background-color: #fbfbfd;
            border-left: 4px solid var(--accent-blue);
            border-radius: 0 8px 8px 0;
            font-style: italic;
        }

        /* Apple / GitHub Callout Banners */
        .callout {
            margin: 1.5em 0;
            padding: 16px 20px;
            border-radius: 10px;
            border-left: 5px solid;
            background: #ffffff;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
        }

        .callout-header {
            font-weight: 650;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
            font-size: 0.96em;
        }

        .callout-body {
            font-size: 0.96em;
            line-height: 1.6;
        }

        .callout-note { border-color: #0071e3; background-color: #f0f7ff; color: #0071e3; }
        .callout-note .callout-body { color: #1d1d1f; }
        .callout-tip { border-color: #34c759; background-color: #f2faf4; color: #248a3d; }
        .callout-tip .callout-body { color: #1d1d1f; }
        .callout-important { border-color: #af52de; background-color: #fcf4ff; color: #8936b8; }
        .callout-important .callout-body { color: #1d1d1f; }
        .callout-warning { border-color: #ff9500; background-color: #fff9f0; color: #b36b00; }
        .callout-warning .callout-body { color: #1d1d1f; }
        .callout-caution { border-color: #ff3b30; background-color: #fff2f1; color: #d70015; }
        .callout-caution .callout-body { color: #1d1d1f; }

        /* Tables (Numbers / macOS TableView style) */
        .table-wrapper {
            margin: 1.6em 0;
            overflow-x: auto;
            border-radius: 10px;
            border: 1px solid #d2d2d7;
            box-shadow: 0 1px 6px rgba(0, 0, 0, 0.02);
        }

        table {
            border-collapse: collapse;
            width: 100%;
            font-size: 0.95em;
        }

        th, td {
            padding: 12px 16px;
            border: 1px solid #e5e5ea;
            text-align: left;
        }

        th {
            background-color: var(--table-header);
            font-weight: 600;
            color: #1d1d1f;
        }

        tr:nth-child(even) { background-color: var(--table-zebra); }

        /* Images and Badges */
        img.md-badge {
            vertical-align: middle;
            margin: 3px 4px;
            display: inline-block;
            border-radius: 5px;
        }

        img.md-img, img:not(.md-badge) {
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            margin: 14px 0;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(0, 0, 0, 0.05);
        }

        div[align="center"], p[align="center"] {
            text-align: center;
            margin: 20px 0;
        }

        div[align="center"] img, p[align="center"] img {
            margin: 4px;
        }

        ul, ol {
            padding-left: 26px;
            margin: 0.9em 0;
        }

        li {
            margin: 0.4em 0;
        }

        .task-list {
            list-style: none;
            padding-left: 4px;
        }

        .task-list-item input {
            margin-right: 10px;
            accent-color: var(--accent-blue);
        }

        hr {
            border: 0;
            height: 1px;
            background: #e5e5ea;
            margin: 2.2em 0;
        }

        /* Print Media Styles */
        @media print {
            @page {
                size: A4 portrait;
                margin: 16mm 14mm;
            }
            body {
                background: #ffffff !important;
                padding: 0 !important;
                font-size: 10.5pt;
                line-height: 1.5;
            }
            .document-container {
                max-width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
                border: none !important;
                box-shadow: none !important;
            }
            .code-block, table, .table-wrapper, blockquote, .callout, img {
                break-inside: avoid;
                page-break-inside: avoid;
            }
            h1, h2, h3, h4, h5, h6 {
                break-after: avoid;
                page-break-after: avoid;
            }
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
        }
    """,
    "dark": """
        :root {
            --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
            --font-mono: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
            --bg-page: #0d1117;
            --bg-card: #161b22;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --border-card: #30363d;
            --accent-blue: #58a6ff;
            --code-bg: #0d1117;
            --code-text: #e6edf3;
            --inline-code-bg: #21262d;
            --table-header: #21262d;
            --table-zebra: #1b1f24;
        }
        body {
            font-family: var(--font-sans);
            background-color: var(--bg-page);
            color: var(--text-primary);
            line-height: 1.65;
            margin: 0;
            padding: 40px 20px;
        }
        .document-container {
            max-width: 880px;
            margin: 0 auto;
            background: var(--bg-card);
            padding: 56px 64px;
            border-radius: 16px;
            border: 1px solid var(--border-card);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }
        h1, h2, h3, h4, h5, h6 { color: #f0f6fc; font-weight: 650; margin-top: 1.8em; margin-bottom: 0.6em; }
        h1 { font-size: 2.25em; border-bottom: 1.5px solid #30363d; padding-bottom: 0.35em; margin-top: 0.2em; }
        h2 { font-size: 1.6em; border-bottom: 1px solid #30363d; padding-bottom: 0.28em; }
        a { color: var(--accent-blue); text-decoration: none; }
        a:hover { text-decoration: underline; }
        code { font-family: var(--font-mono); background-color: var(--inline-code-bg); color: #ff7b72; padding: 0.2em 0.45em; border-radius: 6px; font-size: 0.88em; }
        .code-block { margin: 1.5em 0; border-radius: 10px; background-color: var(--code-bg); border: 1px solid var(--border-card); overflow: hidden; }
        .code-header { background: #161b22; padding: 8px 16px; font-size: 0.76em; color: #8b949e; border-bottom: 1px solid var(--border-card); }
        .code-block pre { margin: 0; padding: 18px 20px; overflow-x: auto; }
        .code-block code { background: transparent; border: none; color: inherit; font-size: 0.9em; line-height: 1.55; }
        blockquote { margin: 1.4em 0; padding: 12px 20px; color: #8b949e; background-color: #21262d; border-left: 4px solid var(--accent-blue); border-radius: 0 8px 8px 0; }
        .callout { margin: 1.5em 0; padding: 16px 20px; border-radius: 10px; border-left: 5px solid; background: #21262d; }
        .callout-header { font-weight: 650; display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
        .callout-note { border-color: #58a6ff; color: #58a6ff; }
        .callout-note .callout-body { color: #e6edf3; }
        .callout-tip { border-color: #3fb950; color: #3fb950; }
        .callout-tip .callout-body { color: #e6edf3; }
        .callout-important { border-color: #bc8cff; color: #bc8cff; }
        .callout-important .callout-body { color: #e6edf3; }
        .callout-warning { border-color: #d29922; color: #d29922; }
        .callout-warning .callout-body { color: #e6edf3; }
        .callout-caution { border-color: #f85149; color: #f85149; }
        .callout-caution .callout-body { color: #e6edf3; }
        .table-wrapper { margin: 1.6em 0; overflow-x: auto; border-radius: 10px; border: 1px solid var(--border-card); }
        table { border-collapse: collapse; width: 100%; font-size: 0.95em; }
        th, td { padding: 12px 16px; border: 1px solid var(--border-card); text-align: left; }
        th { background-color: var(--table-header); color: #f0f6fc; font-weight: 600; }
        tr:nth-child(even) { background-color: var(--table-zebra); }
        img.md-badge { vertical-align: middle; margin: 3px 4px; display: inline-block; border-radius: 5px; }
        img.md-img, img:not(.md-badge) { max-width: 100%; height: auto; border-radius: 10px; margin: 14px 0; border: 1px solid var(--border-card); }
        div[align="center"], p[align="center"] { text-align: center; margin: 20px 0; }
        hr { border: 0; height: 1px; background: var(--border-card); margin: 2.2em 0; }
    """,
    "classic": """
        :root {
            --font-serif: "New York", "Iowan Old Style", Georgia, "Times New Roman", serif;
            --font-mono: "Courier New", Courier, monospace;
            --bg-page: #faf8f5;
            --bg-card: #ffffff;
            --text-primary: #2c2c2e;
            --accent-crimson: #9e2a2b;
        }
        body { font-family: var(--font-serif); background-color: var(--bg-page); color: var(--text-primary); line-height: 1.7; margin: 0; padding: 40px 20px; }
        .document-container { max-width: 860px; margin: 0 auto; background: var(--bg-card); padding: 56px 64px; border-radius: 12px; border: 1px solid #e8e4df; box-shadow: 0 4px 20px rgba(0,0,0,0.04); }
        h1, h2, h3, h4 { color: #1c1c1e; font-weight: 600; }
        h1 { font-size: 2.2em; border-bottom: 2px solid var(--accent-crimson); padding-bottom: 0.3em; text-align: center; }
        h2 { font-size: 1.55em; border-bottom: 1px solid #ddd6ce; padding-bottom: 0.25em; }
        a { color: var(--accent-crimson); text-decoration: underline; }
        code { font-family: var(--font-mono); background-color: #f4f0eb; padding: 0.2em 0.4em; border-radius: 4px; font-size: 0.9em; }
        .code-block { margin: 1.5em 0; border-radius: 8px; background: #262422; color: #fdfaf6; overflow: hidden; }
        .code-header { background: #1a1817; padding: 8px 16px; font-size: 0.78em; color: #baa798; }
        .code-block pre { margin: 0; padding: 16px 20px; overflow-x: auto; }
        .code-block code { background: transparent; color: inherit; }
        blockquote { margin: 1.4em 0; padding: 12px 20px; color: #5a544e; background: #faf6f0; border-left: 4px solid var(--accent-crimson); font-style: italic; }
        .callout { margin: 1.5em 0; padding: 16px 20px; border-radius: 8px; border-left: 4px solid var(--accent-crimson); background: #fdf9f4; }
        .callout-header { font-weight: 650; margin-bottom: 6px; }
        .table-wrapper { margin: 1.5em 0; overflow-x: auto; border: 1px solid #e0d9d0; border-radius: 8px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { padding: 10px 14px; border: 1px solid #e0d9d0; text-align: left; }
        th { background: #f5efe6; font-weight: 600; }
        img.md-badge { vertical-align: middle; margin: 3px; }
        img.md-img, img:not(.md-badge) { max-width: 100%; height: auto; border-radius: 8px; margin: 14px 0; }
        div[align="center"], p[align="center"] { text-align: center; }
        hr { border: 0; height: 1px; background: #e0d9d0; margin: 2em 0; }
    """,
    "academic": """
        :root {
            --font-serif: "Times New Roman", Times, "TeX Gyre Termes", Georgia, serif;
            --font-mono: "Courier New", Courier, monospace;
            --text-primary: #111111;
        }
        body { font-family: var(--font-serif); background: #ffffff; color: var(--text-primary); line-height: 1.7; margin: 0; padding: 50px 30px; }
        .document-container { max-width: 820px; margin: 0 auto; background: #ffffff; padding: 40px; }
        h1, h2, h3, h4 { color: #000000; font-weight: bold; }
        h1 { font-size: 2.1em; text-align: center; margin-bottom: 1em; }
        h2 { font-size: 1.5em; border-bottom: 1px solid #111; padding-bottom: 4px; }
        a { color: #003366; text-decoration: underline; }
        code { font-family: var(--font-mono); background: #f4f4f4; padding: 2px 4px; font-size: 90%; }
        .code-block { margin: 1.4em 0; border: 1px solid #ccc; background: #f8f8f8; color: #111; border-radius: 4px; }
        .code-header { background: #eaeaea; padding: 6px 12px; font-size: 0.8em; font-weight: bold; border-bottom: 1px solid #ccc; }
        .code-block pre { margin: 0; padding: 14px 16px; overflow-x: auto; }
        .code-block code { background: transparent; color: inherit; }
        blockquote { margin: 1em 2em; padding-left: 1em; border-left: 3px solid #666; font-style: italic; }
        .callout { margin: 1.4em 0; padding: 12px 16px; border: 1px solid #999; background: #fafafa; border-radius: 4px; }
        .callout-header { font-weight: bold; margin-bottom: 4px; }
        .table-wrapper { margin: 1.5em 0; width: 100%; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #444; padding: 8px 12px; text-align: left; }
        th { background: #f0f0f0; }
        img.md-badge { vertical-align: middle; margin: 2px; }
        img.md-img, img:not(.md-badge) { max-width: 100%; height: auto; margin: 12px 0; }
        div[align="center"], p[align="center"] { text-align: center; }
        hr { border: 0; height: 1px; background: #ccc; margin: 2em 0; }
    """
}

# ── Pure-Python High-Fidelity GFM Markdown Parser ─────────────────────────────

def parse_markdown_to_html(md_text: str, title: str = "", theme: str = "modern") -> str:
    """Parses full GitHub Flavored Markdown into a semantic, print-ready HTML document."""
    lines = md_text.replace("\r\n", "\n").split("\n")
    out: list[str] = []

    in_code = False
    code_lang = ""
    code_lines: list[str] = []

    in_table = False
    table_headers: list[str] = []
    table_aligns: list[str] = []
    table_rows: list[list[str]] = []

    in_list = False
    list_type: str | None = None  # "ul" or "ol"

    in_callout = False
    callout_type = ""
    callout_lines: list[str] = []

    in_blockquote = False
    blockquote_lines: list[str] = []

    slug_counts: dict[str, int] = {}

    def get_slug(text: str) -> str:
        clean = re.sub(r"<[^>]+>", "", text)
        slug = re.sub(r"[^\w\- ]", "", clean).strip().lower()
        slug = re.sub(r"[-\s]+", "-", slug) or "section"
        if slug in slug_counts:
            slug_counts[slug] += 1
            return f"{slug}-{slug_counts[slug]}"
        slug_counts[slug] = 0
        return slug

    def inline_fmt(text: str) -> str:
        if not text:
            return ""

        # Protect inline code spans first
        code_spans: list[str] = []
        def save_code(m: re.Match[str]) -> str:
            code_spans.append(m.group(1))
            return f"__FORMA_CODESPAN_{len(code_spans)-1}__"

        t = re.sub(r"`([^`]+)`", save_code, text)

        # Markdown Images: ![alt](url)
        def replace_img(m: re.Match[str]) -> str:
            alt, src = m.group(1), m.group(2)
            is_badge = "shields.io" in src or "badge" in src.lower() or "height=" in src
            cls = "md-badge" if is_badge else "md-img"
            return f'<img src="{html.escape(src)}" alt="{html.escape(alt)}" class="{cls}">'

        t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_img, t)

        # Markdown Links: [text](url)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)

        # Bold Italic: ***text*** or ___text___
        t = re.sub(r"\*\*\*([^*]+)\*\*\*", r"<strong><em>\1</em></strong>", t)
        t = re.sub(r"___([^_]+)___", r"<strong><em>\1</em></strong>", t)

        # Bold: **text** or __text__
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", t)

        # Italic: *text* or _text_
        t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
        t = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", t)

        # Strikethrough: ~~text~~
        t = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", t)

        # Highlight: ==text==
        t = re.sub(r"==([^=]+)==", r"<mark>\1</mark>", t)

        # Restore code spans
        for idx, code_content in enumerate(code_spans):
            t = t.replace(f"__FORMA_CODESPAN_{idx}__", f"<code>{html.escape(code_content)}</code>")

        return t

    def close_table() -> None:
        nonlocal in_table, table_headers, table_aligns, table_rows
        if in_table:
            res = ['<div class="table-wrapper"><table>']
            if table_headers:
                res.append("<thead><tr>")
                for col_idx, hdr in enumerate(table_headers):
                    align = (
                        f' style="text-align: {table_aligns[col_idx]}"'
                        if col_idx < len(table_aligns) and table_aligns[col_idx]
                        else ""
                    )
                    res.append(f"<th{align}>{inline_fmt(hdr)}</th>")
                res.append("</tr></thead>")
            if table_rows:
                res.append("<tbody>")
                for row in table_rows:
                    res.append("<tr>")
                    for col_idx, cell in enumerate(row):
                        align = (
                            f' style="text-align: {table_aligns[col_idx]}"'
                            if col_idx < len(table_aligns) and table_aligns[col_idx]
                            else ""
                        )
                        res.append(f"<td{align}>{inline_fmt(cell)}</td>")
                    res.append("</tr>")
                res.append("</tbody>")
            res.append("</table></div>")
            out.append("\n".join(res))
            in_table = False
            table_headers = []
            table_aligns = []
            table_rows = []

    def close_list() -> None:
        nonlocal in_list, list_type
        if in_list and list_type:
            out.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def close_callout() -> None:
        nonlocal in_callout, callout_type, callout_lines
        if in_callout:
            c_type = callout_type.lower()
            icons = {
                "note": "ℹ️",
                "tip": "💡",
                "important": "❗",
                "warning": "⚠️",
                "caution": "🛑",
            }
            icon = icons.get(c_type, "ℹ️")
            title_text = c_type.capitalize()
            body_text = "<br>".join(inline_fmt(line_text) for line_text in callout_lines)
            out.append(
                f'<div class="callout callout-{c_type}">'
                f'<div class="callout-header"><span class="callout-icon">{icon}</span><span class="callout-title">{title_text}</span></div>'
                f'<div class="callout-body">{body_text}</div>'
                f"</div>"
            )
            in_callout = False
            callout_type = ""
            callout_lines = []

    def close_blockquote() -> None:
        nonlocal in_blockquote, blockquote_lines
        if in_blockquote:
            body_text = "<br>".join(inline_fmt(line_text) for line_text in blockquote_lines)
            out.append(f"<blockquote>{body_text}</blockquote>")
            in_blockquote = False
            blockquote_lines = []

    idx = 0
    while idx < len(lines):
        line = lines[idx]

        # 1. Fenced Code Block
        if line.startswith("```"):
            close_table()
            close_list()
            close_callout()
            close_blockquote()
            if in_code:
                code_content = html.escape("\n".join(code_lines))
                lang_header = (
                    f'<div class="code-header"><span class="code-lang">{html.escape(code_lang)}</span></div>'
                    if code_lang
                    else ""
                )
                out.append(
                    f'<div class="code-block">{lang_header}<pre><code class="language-{html.escape(code_lang)}">{code_content}</code></pre></div>'
                )
                in_code = False
                code_lines = []
                code_lang = ""
            else:
                in_code = True
                code_lang = line[3:].strip()
            idx += 1
            continue

        if in_code:
            code_lines.append(line)
            idx += 1
            continue

        # 2. GitHub Alert Callout: > [!NOTE], > [!TIP], etc.
        callout_m = re.match(r"^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$", line, re.IGNORECASE)
        if callout_m:
            close_table()
            close_list()
            close_blockquote()
            if in_callout:
                close_callout()
            in_callout = True
            callout_type = callout_m.group(1).lower()
            rest = callout_m.group(2).strip()
            if rest:
                callout_lines.append(rest)
            idx += 1
            continue

        if in_callout:
            if line.startswith(">"):
                callout_lines.append(line[1:].strip())
                idx += 1
                continue
            elif not line.strip() and idx + 1 < len(lines) and lines[idx + 1].startswith(">"):
                idx += 1
                continue
            else:
                close_callout()

        # 3. Standard Blockquote >
        if line.startswith(">"):
            close_table()
            close_list()
            if not in_blockquote:
                in_blockquote = True
                blockquote_lines = []
            blockquote_lines.append(line[1:].strip())
            idx += 1
            continue
        elif in_blockquote:
            if not line.strip() and idx + 1 < len(lines) and lines[idx + 1].startswith(">"):
                idx += 1
                continue
            close_blockquote()

        # 4. Table Detection
        if "|" in line and not line.startswith("<"):
            is_sep = bool(re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", line))
            if not in_table:
                if idx + 1 < len(lines) and "|" in lines[idx + 1] and re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", lines[idx + 1]):
                    close_list()
                    in_table = True
                    table_headers = [c.strip() for c in line.strip().strip("|").split("|")]
                    sep_line = lines[idx + 1].strip().strip("|")
                    table_aligns = []
                    for col in sep_line.split("|"):
                        c = col.strip()
                        if c.startswith(":") and c.endswith(":"):
                            table_aligns.append("center")
                        elif c.endswith(":"):
                            table_aligns.append("right")
                        elif c.startswith(":"):
                            table_aligns.append("left")
                        else:
                            table_aligns.append("")
                    idx += 2
                    continue
            else:
                if not is_sep:
                    table_rows.append([c.strip() for c in line.strip().strip("|").split("|")])
                idx += 1
                continue

        if in_table:
            close_table()

        # 5. Raw HTML Block Pass-Through
        if re.match(r"^\s*<(div|p|center|section|article|header|footer|nav|details|summary|table|blockquote|figure|figcaption)\b", line, re.IGNORECASE) or \
           re.match(r"^\s*</(div|p|center|section|article|header|footer|nav|details|summary|table|blockquote|figure|figcaption)>", line, re.IGNORECASE):
            close_list()
            out.append(line)
            idx += 1
            continue

        # 6. Horizontal Rule
        if re.match(r"^\s*(\-{3,}|\*{3,}|_{3,})\s*$", line):
            close_list()
            out.append("<hr>")
            idx += 1
            continue

        # 7. Headings
        head_m = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line)
        if head_m:
            close_list()
            level = len(head_m.group(1))
            h_text = head_m.group(2)
            slug = get_slug(h_text)
            out.append(f'<h{level} id="{slug}">{inline_fmt(h_text)}</h{level}>')
            idx += 1
            continue

        # 8. Lists
        # Task List
        task_m = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+)$", line)
        if task_m:
            if not in_list or list_type != "ul":
                close_list()
                in_list = True
                list_type = "ul"
                out.append('<ul class="task-list">')
            checked = " checked" if task_m.group(1).lower() == "x" else ""
            out.append(f'<li class="task-list-item"><input type="checkbox" disabled{checked}> {inline_fmt(task_m.group(2))}</li>')
            idx += 1
            continue

        # Bullet List
        bullet_m = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if bullet_m:
            if not in_list or list_type != "ul":
                close_list()
                in_list = True
                list_type = "ul"
                out.append("<ul>")
            out.append(f"<li>{inline_fmt(bullet_m.group(1))}</li>")
            idx += 1
            continue

        # Numbered List
        num_m = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if num_m:
            if not in_list or list_type != "ol":
                close_list()
                in_list = True
                list_type = "ol"
                out.append("<ol>")
            out.append(f"<li>{inline_fmt(num_m.group(2))}</li>")
            idx += 1
            continue

        if in_list and not line.strip():
            if idx + 1 < len(lines) and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[idx + 1]):
                idx += 1
                continue
            close_list()

        # 9. Blank Line
        if not line.strip():
            close_list()
            idx += 1
            continue

        # 10. Regular Paragraph
        close_list()
        out.append(f"<p>{inline_fmt(line)}</p>")
        idx += 1

    close_table()
    close_list()
    close_callout()
    close_blockquote()

    body_html = "\n".join(out)
    selected_css = THEME_CSS.get(theme, THEME_CSS["modern"])
    doc_title = title or "Document"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(doc_title)}</title>
<style>
{selected_css}
</style>
</head>
<body>
<div class="document-container">
{body_html}
</div>
</body>
</html>
"""


# ── Conversion Functions ──────────────────────────────────────────────────────

def convert_md_to_html(md_path: str | Path, html_path: str | Path | None = None, theme: str = "modern", open_result: bool = False) -> str:
    """Converts a Markdown file into a standalone, styled HTML document."""
    md_file = Path(md_path).expanduser().resolve()
    if not md_file.is_file():
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    target_html = Path(html_path).expanduser().resolve() if html_path else md_file.with_suffix(".html")
    target_html.parent.mkdir(parents=True, exist_ok=True)

    content = md_file.read_text(encoding="utf-8")
    rendered_html = parse_markdown_to_html(content, title=md_file.stem, theme=theme)
    target_html.write_text(rendered_html, encoding="utf-8")

    if open_result:
        subprocess.run(["open", str(target_html)])

    print(f"Converted '{md_file.name}' → '{target_html.name}' [format: html, theme: {theme}]")
    return str(target_html)


def convert_md_to_pdf(md_path: str | Path, pdf_path: str | Path | None = None, theme: str = "modern", open_result: bool = False) -> str:
    """Converts a Markdown file into a crisp, vector PDF using Chrome Headless or native WebKit."""
    md_file = Path(md_path).expanduser().resolve()
    if not md_file.is_file():
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    target_pdf = Path(pdf_path).expanduser().resolve() if pdf_path else md_file.with_suffix(".pdf")
    target_pdf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="forma-pdf-") as tmp_dir:
        tmp_html = Path(tmp_dir) / f"{md_file.stem}.html"
        convert_md_to_html(md_file, tmp_html, theme=theme, open_result=False)

        # Engine 1: Headless Google Chrome (Best Quality: SVGs, Badges, CSS3, Print Media)
        chrome_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
        for chrome_bin in chrome_candidates:
            if os.path.exists(chrome_bin):
                res = subprocess.run([
                    chrome_bin,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-pdf-header-footer",
                    "--run-all-compositor-stages-before-draw",
                    f"--print-to-pdf={target_pdf}",
                    f"file://{tmp_html}"
                ], capture_output=True, text=True)
                if res.returncode == 0 and target_pdf.is_file():
                    if open_result:
                        subprocess.run(["open", str(target_pdf)])
                    print(f"Converted '{md_file.name}' → '{target_pdf.name}' [format: pdf, engine: chrome, theme: {theme}]")
                    return str(target_pdf)

        # Engine 2: Apple Pages PDF Export via textutil DOCX
        if is_pages_available() and shutil.which("textutil"):
            tmp_docx = Path(tmp_dir) / f"{md_file.stem}.docx"
            subprocess.run(["textutil", "-convert", "docx", "-output", str(tmp_docx), str(tmp_html)], check=True)
            applescript = f"""
            set docxFile to POSIX file "{tmp_docx}"
            set pdfFile to POSIX file "{target_pdf}"
            tell application "Pages"
                activate
                delay 1
                set doc to open docxFile
                delay 1
                export doc to pdfFile as PDF
                close doc saving no
            end tell
            """
            res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
            if res.returncode == 0 and target_pdf.is_file():
                if open_result:
                    subprocess.run(["open", str(target_pdf)])
                print(f"Converted '{md_file.name}' → '{target_pdf.name}' [format: pdf, engine: pages, theme: {theme}]")
                return str(target_pdf)

        # Engine 3: cupsfilter fallback
        if shutil.which("cupsfilter"):
            res = subprocess.run(f'cupsfilter "{tmp_html}" > "{target_pdf}"', shell=True, capture_output=True)
            if res.returncode == 0 and target_pdf.is_file():
                if open_result:
                    subprocess.run(["open", str(target_pdf)])
                print(f"Converted '{md_file.name}' → '{target_pdf.name}' [format: pdf, engine: cupsfilter, theme: {theme}]")
                return str(target_pdf)

    raise RuntimeError("Failed to generate PDF. Install Google Chrome or ensure Apple Pages is available.")


def convert_md_to_pages(md_path: str | Path, pages_path: str | Path | None = None, theme: str = "modern", open_result: bool = False) -> str:
    """Converts a Markdown file into a native Apple Pages (.pages) document with layout fidelity."""
    md_file = Path(md_path).expanduser().resolve()
    if not md_file.is_file():
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    target_pages = Path(pages_path).expanduser().resolve() if pages_path else md_file.with_suffix(".pages")
    target_pages.parent.mkdir(parents=True, exist_ok=True)

    if not is_pages_available():
        raise RuntimeError("Apple Pages is required on macOS.")

    with tempfile.TemporaryDirectory(prefix="forma-pages-") as tmp_dir:
        tmp_html = Path(tmp_dir) / f"{md_file.stem}.html"
        convert_md_to_html(md_file, tmp_html, theme=theme, open_result=False)

        tmp_docx = Path(tmp_dir) / f"{md_file.stem}.docx"
        subprocess.run(["textutil", "-convert", "docx", "-output", str(tmp_docx), str(tmp_html)], check=True)

        if target_pages.exists():
            if target_pages.is_dir():
                shutil.rmtree(target_pages)
            else:
                target_pages.unlink()

        applescript = f"""
        set docxFile to POSIX file "{tmp_docx}"
        set pagesFile to POSIX file "{target_pages}"
        tell application "Pages"
            activate
            delay 1
            set doc to open docxFile
            delay 1
            save doc in pagesFile
            close doc saving no
        end tell
        """
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"AppleScript error saving Pages document: {res.stderr}")

    if open_result:
        subprocess.run(["open", str(target_pages)])

    print(f"Converted '{md_file.name}' → '{target_pages.name}' [format: pages, theme: {theme}]")
    return str(target_pages)


def convert_md_to_docx(md_path: str | Path, docx_path: str | Path | None = None, theme: str = "modern", open_result: bool = False) -> str:
    """Converts a Markdown file into a Microsoft Word (.docx) document."""
    md_file = Path(md_path).expanduser().resolve()
    if not md_file.is_file():
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    target_docx = Path(docx_path).expanduser().resolve() if docx_path else md_file.with_suffix(".docx")
    target_docx.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="forma-docx-") as tmp_dir:
        tmp_html = Path(tmp_dir) / f"{md_file.stem}.html"
        convert_md_to_html(md_file, tmp_html, theme=theme, open_result=False)
        subprocess.run(["textutil", "-convert", "docx", "-output", str(target_docx), str(tmp_html)], check=True)

    if open_result:
        subprocess.run(["open", str(target_docx)])

    print(f"Converted '{md_file.name}' → '{target_docx.name}' [format: docx, theme: {theme}]")
    return str(target_docx)


def convert_md(md_path: str | Path, output_path: str | Path | None = None, target_format: str | None = None, theme: str = "modern", open_result: bool = False) -> str:
    """Universal Markdown converter dispatching to HTML, PDF, Pages, or DOCX."""
    md_file = Path(md_path).expanduser().resolve()
    if not md_file.is_file():
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    if not target_format:
        if output_path:
            ext = Path(output_path).suffix.lower().lstrip(".")
            target_format = ext if ext in ("pdf", "html", "pages", "docx") else "pages"
        else:
            target_format = "pages"

    fmt = target_format.lower()
    if fmt == "pdf":
        return convert_md_to_pdf(md_file, output_path, theme=theme, open_result=open_result)
    elif fmt == "html":
        return convert_md_to_html(md_file, output_path, theme=theme, open_result=open_result)
    elif fmt == "pages":
        return convert_md_to_pages(md_file, output_path, theme=theme, open_result=open_result)
    elif fmt == "docx":
        return convert_md_to_docx(md_file, output_path, theme=theme, open_result=open_result)
    else:
        raise ValueError(f"Unsupported format '{target_format}'. Choose: pages, pdf, html, docx.")


# ── CLI Interface ─────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Forma: Convert Markdown (.md) to Apple Pages, PDF, HTML, or DOCX with Apple Design fidelity"
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
        choices=["modern", "dark", "classic", "academic"],
        default="modern",
        help="Styling theme (default: modern)",
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
