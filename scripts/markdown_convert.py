#!/usr/bin/env python3
"""
Convert Markdown files to HTML, PDF, DOCX, or Apple Pages with 9 customizable themes and Amil/Apple/Terminal Design fidelity.
Supports KaTeX math formulas, native Mermaid diagrams & graphs (with high-contrast dark & light themes), GitHub Flavored Markdown alerts, tables, and RTL/Persian.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

FORMATS = ("pages", "pdf", "html", "docx")

_HERE = Path(__file__).resolve().parent
VENDOR_DIR = _HERE.parent / "vendor"
if not VENDOR_DIR.exists():
    VENDOR_DIR = Path.home() / ".gemini/config/skills/markdown-tools/vendor"

THEME_ALIASES: dict[str, str] = {
    # Amil Design Light
    "amil-design": "amil-light",
    "amil": "amil-light",
    "light": "amil-light",
    "default": "amil-light",
    # Amil Design Dark
    "dark": "amil-dark",
    "midnight": "amil-dark",
    # Apple Cupertino Light
    "modern": "apple-light",
    "apple": "apple-light",
    "cupertino": "apple-light",
    "apple-design": "apple-light",
    # Apple Space Dark
    "space-dark": "apple-dark",
    "apple-dark-mode": "apple-dark",
    # VS Code Dark
    "vscode": "vscode-dark",
    "markdown-dark": "vscode-dark",
    "vs-dark": "vscode-dark",
    # GitHub Light
    "github": "github-light",
    "primer": "github-light",
    # Nord Frost
    "nord": "nord-frost",
    "arctic": "nord-frost",
    # Editorial Serif
    "classic": "editorial-serif",
    "academic": "editorial-serif",
    "editorial": "editorial-serif",
    "serif": "editorial-serif",
    "new-york": "editorial-serif",
    # Terminal / CLI Slate & Amber
    "terminal": "terminal-dark",
    "cli": "terminal-dark",
    "cli-dark": "terminal-dark",
    "slate-amber": "terminal-dark",
    "pallet": "terminal-dark",
    "palette": "terminal-dark",
}

DARK_THEMES = {"amil-dark", "apple-dark", "vscode-dark", "nord-frost", "terminal-dark"}

def normalize_theme_name(theme: str) -> str:
    """Normalize a theme alias or name into one of the canonical theme IDs."""
    lower = theme.strip().lower()
    return THEME_ALIASES.get(lower, lower)


THEME_CONFIGS: dict[str, dict[str, Any]] = {
    "amil-light": {
        "name": "Amil Light",
        "description": "Modern slate aesthetic with soft light-gray canvas, floating white container, royal blue accents, and macOS window dots.",
        "is_dark": False,
        "mermaid_theme": "neutral",
        "mermaid_vars": {
            "darkMode": False,
            "background": "#ffffff",
            "mainBkg": "#f1f4f8",
            "primaryColor": "#2563eb",
            "primaryTextColor": "#0f172a",
            "primaryBorderColor": "#2563eb",
            "lineColor": "#64748b",
            "secondaryColor": "#e2e8f0",
            "tertiaryColor": "#ffffff"
        },
        "css": """
        :root {
            --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-fa: "Vazirmatn", "Shabnam", "Sahel", "IRANSans", "B Yekan", -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
            --font-mono: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
            --bg-page: #eaedf2;
            --bg-card: #ffffff;
            --bg-subtle: #f1f4f8;
            --text-primary: #0f172a;
            --text-secondary: #334155;
            --text-muted: #64748b;
            --border-subtle: #cbd5e1;
            --border-card: #d8dfe8;
            --accent-primary: #2563eb;
            --accent-hover: #1d4ed8;
            --accent-subtle: #dbeafe;
            --code-bg: #0f172a;
            --code-header: #1e293b;
            --code-text: #e2e8f0;
            --inline-code-bg: #dbe4ee;
            --inline-code-color: #0f172a;
            --table-header: #dde3eb;
            --table-zebra: #f8fafc;
            --shadow-card: 0 4px 20px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
            --shadow-code: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
            --card-radius: 16px;
        }
        """
    },
    "amil-dark": {
        "name": "Amil Dark",
        "description": "Obsidian midnight slate canvas with elevated dark container, electric cyan/indigo accents, and glowing diagram rendering.",
        "is_dark": True,
        "mermaid_theme": "dark",
        "mermaid_vars": {
            "darkMode": True,
            "background": "#131b2e",
            "mainBkg": "#1c2742",
            "primaryColor": "#38bdf8",
            "primaryTextColor": "#f8fafc",
            "primaryBorderColor": "#38bdf8",
            "lineColor": "#818cf8",
            "secondaryColor": "#22314e",
            "tertiaryColor": "#0b0f19"
        },
        "css": """
        :root {
            --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-fa: "Vazirmatn", "Shabnam", "Sahel", "IRANSans", "B Yekan", -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
            --font-mono: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
            --bg-page: #0b0f19;
            --bg-card: #131b2e;
            --bg-subtle: #1c2742;
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --text-muted: #64748b;
            --border-subtle: #22314e;
            --border-card: #2c3e60;
            --accent-primary: #38bdf8;
            --accent-hover: #7dd3fc;
            --accent-subtle: rgba(56, 189, 248, 0.15);
            --code-bg: #070a10;
            --code-header: #101726;
            --code-text: #f1f5f9;
            --inline-code-bg: #1e293b;
            --inline-code-color: #38bdf8;
            --table-header: #1a243b;
            --table-zebra: #101726;
            --shadow-card: 0 8px 32px rgba(0, 0, 0, 0.4);
            --shadow-code: 0 12px 30px rgba(0, 0, 0, 0.5);
            --card-radius: 16px;
        }
        """
    },
    "terminal-dark": {
        "name": "Terminal Dark",
        "description": "CLI Slate & Amber palette with electric cyan commands (#38bdf8), golden amber keywords (#f59e0b), and terminal lime accents.",
        "is_dark": True,
        "mermaid_theme": "dark",
        "mermaid_vars": {
            "darkMode": True,
            "background": "#182230",
            "mainBkg": "#223044",
            "primaryColor": "#38bdf8",
            "primaryTextColor": "#f1f5f9",
            "primaryBorderColor": "#38bdf8",
            "lineColor": "#f59e0b",
            "secondaryColor": "#84cc16",
            "tertiaryColor": "#10161f"
        },
        "css": """
        :root {
            --font-sans: "SF Pro Text", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            --font-fa: "Vazirmatn", -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
            --font-mono: "SF Mono", Menlo, Monaco, Consolas, monospace;
            --bg-page: #10161f;
            --bg-card: #182230;
            --bg-subtle: #223044;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-subtle: #2d3e56;
            --border-card: #3b506e;
            --accent-primary: #38bdf8;
            --accent-hover: #7dd3fc;
            --accent-subtle: rgba(56, 189, 248, 0.16);
            --code-bg: #0c1219;
            --code-header: #151e2b;
            --code-text: #e2e8f0;
            --inline-code-bg: #223044;
            --inline-code-color: #f59e0b;
            --table-header: #202d40;
            --table-zebra: #141c27;
            --shadow-card: 0 10px 30px rgba(0, 0, 0, 0.45);
            --shadow-code: 0 12px 28px rgba(0, 0, 0, 0.55);
            --card-radius: 14px;
        }
        """
    },
    "apple-light": {
        "name": "Apple Light",
        "description": "Apple Human Interface Guidelines light aesthetic, #f5f5f7 canvas, pure white card, SF Pro typography, Apple blue accents.",
        "is_dark": False,
        "mermaid_theme": "neutral",
        "mermaid_vars": {
            "darkMode": False,
            "background": "#ffffff",
            "mainBkg": "#f5f5f7",
            "primaryColor": "#0071e3",
            "primaryTextColor": "#1d1d1f",
            "primaryBorderColor": "#0071e3",
            "lineColor": "#86868b",
            "secondaryColor": "#e8e8ed",
            "tertiaryColor": "#ffffff"
        },
        "css": """
        :root {
            --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif;
            --font-fa: "Vazirmatn", "Shabnam", -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
            --font-mono: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, monospace;
            --bg-page: #f5f5f7;
            --bg-card: #ffffff;
            --bg-subtle: #e8e8ed;
            --text-primary: #1d1d1f;
            --text-secondary: #515154;
            --text-muted: #86868b;
            --border-subtle: #d2d2d7;
            --border-card: rgba(0, 0, 0, 0.08);
            --accent-primary: #0071e3;
            --accent-hover: #0077ed;
            --accent-subtle: #f0f7ff;
            --code-bg: #f2f2f7;
            --code-header: #e5e5ea;
            --code-text: #1c1c1e;
            --inline-code-bg: #e5e5ea;
            --inline-code-color: #1c1c1e;
            --table-header: #fbfbfd;
            --table-zebra: #f5f5f7;
            --shadow-card: 0 4px 28px rgba(0, 0, 0, 0.06);
            --shadow-code: 0 4px 16px rgba(0, 0, 0, 0.06);
            --card-radius: 18px;
        }
        """
    },
    "apple-dark": {
        "name": "Apple Dark",
        "description": "Apple Space Black canvas (#000000), elevated dark card (#1c1c1e), vibrant Apple blue (#2997ff), iOS alert cards.",
        "is_dark": True,
        "mermaid_theme": "dark",
        "mermaid_vars": {
            "darkMode": True,
            "background": "#1c1c1e",
            "mainBkg": "#2c2c2e",
            "primaryColor": "#2997ff",
            "primaryTextColor": "#f5f5f7",
            "primaryBorderColor": "#2997ff",
            "lineColor": "#a1a1a6",
            "secondaryColor": "#3a3a3c",
            "tertiaryColor": "#000000"
        },
        "css": """
        :root {
            --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "Segoe UI", Roboto, Arial, sans-serif;
            --font-fa: "Vazirmatn", "Shabnam", -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
            --font-mono: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, monospace;
            --bg-page: #000000;
            --bg-card: #1c1c1e;
            --bg-subtle: #2c2c2e;
            --text-primary: #f5f5f7;
            --text-secondary: #a1a1a6;
            --text-muted: #86868b;
            --border-subtle: #3a3a3c;
            --border-card: rgba(255, 255, 255, 0.12);
            --accent-primary: #2997ff;
            --accent-hover: #47a3ff;
            --accent-subtle: rgba(41, 151, 255, 0.18);
            --code-bg: #121214;
            --code-header: #252528;
            --code-text: #f5f5f7;
            --inline-code-bg: #2c2c2e;
            --inline-code-color: #2997ff;
            --table-header: #2c2c2e;
            --table-zebra: #151516;
            --shadow-card: 0 8px 30px rgba(0, 0, 0, 0.7);
            --shadow-code: 0 10px 28px rgba(0, 0, 0, 0.8);
            --card-radius: 18px;
        }
        """
    },
    "vscode-dark": {
        "name": "VS Code Dark",
        "description": "Visual Studio Code editor dark theme with dark canvas (#181818), #007acc accents, and high-contrast dark diagram/graph rendering.",
        "is_dark": True,
        "mermaid_theme": "dark",
        "mermaid_vars": {
            "darkMode": True,
            "background": "#1e1e1e",
            "mainBkg": "#252526",
            "primaryColor": "#007acc",
            "primaryTextColor": "#d4d4d4",
            "primaryBorderColor": "#007acc",
            "lineColor": "#4ec9b0",
            "secondaryColor": "#2d2d2d",
            "tertiaryColor": "#181818"
        },
        "css": """
        :root {
            --font-sans: "Segoe UI", -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
            --font-fa: "Vazirmatn", "Segoe UI", Tahoma, sans-serif;
            --font-mono: Consolas, "SF Mono", Monaco, "Courier New", monospace;
            --bg-page: #181818;
            --bg-card: #1e1e1e;
            --bg-subtle: #252526;
            --text-primary: #d4d4d4;
            --text-secondary: #cccccc;
            --text-muted: #858585;
            --border-subtle: #333333;
            --border-card: #3c3c3c;
            --accent-primary: #007acc;
            --accent-hover: #1f8ad2;
            --accent-subtle: rgba(0, 122, 204, 0.2);
            --code-bg: #141414;
            --code-header: #252526;
            --code-text: #d4d4d4;
            --inline-code-bg: #2d2d2d;
            --inline-code-color: #ce9178;
            --table-header: #252526;
            --table-zebra: #181818;
            --shadow-card: 0 8px 24px rgba(0, 0, 0, 0.5);
            --shadow-code: 0 8px 24px rgba(0, 0, 0, 0.6);
            --card-radius: 12px;
        }
        """
    },
    "github-light": {
        "name": "GitHub Light",
        "description": "GitHub Primer modern light theme with clean #f6f8fa canvas, #ffffff card, #0969da blue, and authentic GitHub alerts.",
        "is_dark": False,
        "mermaid_theme": "default",
        "mermaid_vars": {
            "darkMode": False,
            "background": "#ffffff",
            "mainBkg": "#f6f8fa",
            "primaryColor": "#0969da",
            "primaryTextColor": "#1f2328",
            "primaryBorderColor": "#d0d7de",
            "lineColor": "#656d76",
            "secondaryColor": "#eaeef2",
            "tertiaryColor": "#ffffff"
        },
        "css": """
        :root {
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
            --font-fa: "Vazirmatn", "Segoe UI", Tahoma, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
            --bg-page: #f6f8fa;
            --bg-card: #ffffff;
            --bg-subtle: #eaeef2;
            --text-primary: #1f2328;
            --text-secondary: #656d76;
            --text-muted: #8c959f;
            --border-subtle: #d0d7de;
            --border-card: #d0d7de;
            --accent-primary: #0969da;
            --accent-hover: #0550ae;
            --accent-subtle: #ddf4ff;
            --code-bg: #f6f8fa;
            --code-header: #eaeef2;
            --code-text: #1f2328;
            --inline-code-bg: rgba(175, 184, 193, 0.2);
            --inline-code-color: #1f2328;
            --table-header: #f6f8fa;
            --table-zebra: #fbfcfd;
            --shadow-card: 0 3px 12px rgba(140, 149, 159, 0.15);
            --shadow-code: 0 2px 8px rgba(140, 149, 159, 0.1);
            --card-radius: 12px;
        }
        """
    },
    "nord-frost": {
        "name": "Nord Frost",
        "description": "Arctic Polar Night dark theme with Snow Storm text, Frost ice blue (#88c0d0), and Aurora green/purple accents.",
        "is_dark": True,
        "mermaid_theme": "dark",
        "mermaid_vars": {
            "darkMode": True,
            "background": "#2e3440",
            "mainBkg": "#3b4252",
            "primaryColor": "#88c0d0",
            "primaryTextColor": "#eceff4",
            "primaryBorderColor": "#88c0d0",
            "lineColor": "#81a1c1",
            "secondaryColor": "#434c5e",
            "tertiaryColor": "#242933"
        },
        "css": """
        :root {
            --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
            --font-fa: "Vazirmatn", -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
            --font-mono: "SF Mono", Menlo, Monaco, Consolas, monospace;
            --bg-page: #242933;
            --bg-card: #2e3440;
            --bg-subtle: #3b4252;
            --text-primary: #eceff4;
            --text-secondary: #d8dee9;
            --text-muted: #616e88;
            --border-subtle: #3b4252;
            --border-card: #434c5e;
            --accent-primary: #88c0d0;
            --accent-hover: #81a1c1;
            --accent-subtle: rgba(136, 192, 208, 0.18);
            --code-bg: #1e222a;
            --code-header: #2e3440;
            --code-text: #eceff4;
            --inline-code-bg: #3b4252;
            --inline-code-color: #88c0d0;
            --table-header: #3b4252;
            --table-zebra: #272c36;
            --shadow-card: 0 8px 30px rgba(0, 0, 0, 0.35);
            --shadow-code: 0 10px 25px rgba(0, 0, 0, 0.4);
            --card-radius: 16px;
        }
        """
    },
    "editorial-serif": {
        "name": "Editorial Serif",
        "description": "Apple Editorial / New York classic serif typography on warm ivory paper (#f7f4ed), deep espresso ink text, and royal crimson accents.",
        "is_dark": False,
        "mermaid_theme": "neutral",
        "mermaid_vars": {
            "darkMode": False,
            "background": "#fffefb",
            "mainBkg": "#f7f4ed",
            "primaryColor": "#9b111e",
            "primaryTextColor": "#26211e",
            "primaryBorderColor": "#9b111e",
            "lineColor": "#8c827a",
            "secondaryColor": "#efe9dc",
            "tertiaryColor": "#fffefb"
        },
        "css": """
        :root {
            --font-sans: "New York", "Charter", "Georgia", "Iowan Old Style", "Times New Roman", serif;
            --font-fa: "Sahel", "Vazirmatn", "Shabnam", serif;
            --font-mono: "SF Mono", ui-monospace, Menlo, Monaco, monospace;
            --bg-page: #f7f4ed;
            --bg-card: #fffefb;
            --bg-subtle: #efe9dc;
            --text-primary: #26211e;
            --text-secondary: #59524c;
            --text-muted: #8c827a;
            --border-subtle: #dfd6c7;
            --border-card: #e7e0d3;
            --accent-primary: #9b111e;
            --accent-hover: #7a0d17;
            --accent-subtle: #faeae8;
            --code-bg: #26211e;
            --code-header: #362e2a;
            --code-text: #f7f4ed;
            --inline-code-bg: #efe9dc;
            --inline-code-color: #9b111e;
            --table-header: #f2ece0;
            --table-zebra: #fbf9f4;
            --shadow-card: 0 4px 20px rgba(90, 70, 50, 0.07);
            --shadow-code: 0 6px 18px rgba(90, 70, 50, 0.15);
            --card-radius: 12px;
        }
        """
    }
}

CORE_CSS_TEMPLATE = """
        html, body {
            background-color: var(--bg-page) !important;
            color: var(--text-primary);
            font-family: var(--font-sans);
            line-height: 1.7;
            margin: 0;
            padding: 40px 24px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        body.rtl, body[dir="rtl"] {
            font-family: var(--font-fa), var(--font-sans);
            direction: rtl;
            text-align: right;
        }

        .document-container {
            max-width: 920px;
            margin: 0 auto;
            background-color: var(--bg-card);
            padding: 56px 64px;
            border-radius: var(--card-radius);
            border: 1px solid var(--border-card);
            box-shadow: var(--shadow-card);
        }

        @media (max-width: 768px) {
            .document-container {
                padding: 32px 24px;
            }
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: inherit;
            color: var(--text-primary);
            font-weight: 750;
            line-height: 1.3;
            letter-spacing: -0.02em;
            margin-top: 1.8em;
            margin-bottom: 0.6em;
        }

        h1 {
            font-size: 2.25em;
            letter-spacing: -0.03em;
            padding-bottom: 0.4em;
            border-bottom: 2px solid var(--border-subtle);
            margin-top: 0.2em;
        }

        h2 {
            font-size: 1.6em;
            letter-spacing: -0.02em;
            padding-bottom: 0.3em;
            border-bottom: 1.5px solid var(--border-subtle);
        }

        h3 { font-size: 1.28em; }
        h4 { font-size: 1.12em; color: var(--text-secondary); }
        h5 { font-size: 1.0em; color: var(--text-secondary); }
        h6 { font-size: 0.9em; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }

        p { margin: 1.0em 0; color: var(--text-secondary); }

        a {
            color: var(--accent-primary);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.15s ease;
        }
        a:hover { text-decoration: underline; color: var(--accent-hover); }

        code {
            font-family: var(--font-mono);
            background-color: var(--inline-code-bg);
            color: var(--inline-code-color);
            padding: 0.2em 0.45em;
            border-radius: 6px;
            font-size: 0.88em;
            font-weight: 600;
            border: 1px solid var(--border-subtle);
        }

        .code-block {
            margin: 1.8em 0;
            border-radius: 14px;
            background-color: var(--code-bg);
            color: var(--code-text);
            overflow: hidden;
            box-shadow: var(--shadow-code);
            border: 1px solid var(--border-card);
            direction: ltr !important;
            text-align: left !important;
        }

        .code-header {
            background: var(--code-header);
            padding: 10px 18px;
            font-size: 0.78em;
            font-family: var(--font-mono);
            color: var(--text-muted);
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-card);
        }

        .code-header-dots {
            display: flex;
            gap: 6px;
        }
        .code-header-dots span {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }
        .dot-red { background: #ff5f56; }
        .dot-yellow { background: #ffbd2e; }
        .dot-green { background: #27c93f; }

        .code-block pre {
            margin: 0;
            padding: 18px 22px;
            overflow-x: auto;
            background: transparent;
        }

        .code-block code {
            font-family: var(--font-mono);
            background: transparent;
            border: none;
            color: inherit;
            font-size: 0.92em;
            line-height: 1.6;
            padding: 0;
        }

        /* Mermaid diagram container */
        .mermaid-container {
            margin: 2.0em 0;
            padding: 24px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 16px;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: var(--shadow-card);
            direction: ltr !important;
            overflow-x: auto;
        }
        .mermaid-container svg {
            max-width: 100% !important;
            height: auto !important;
        }

        blockquote {
            margin: 1.6em 0;
            padding: 16px 24px;
            color: var(--text-secondary);
            background-color: var(--bg-subtle);
            border-left: 4px solid var(--accent-primary);
            border-radius: 0 12px 12px 0;
            border-top: 1px solid var(--border-card);
            border-right: 1px solid var(--border-card);
            border-bottom: 1px solid var(--border-card);
        }
        body.rtl blockquote, body[dir="rtl"] blockquote {
            border-left: 1px solid var(--border-card);
            border-right: 4px solid var(--accent-primary);
            border-radius: 12px 0 0 12px;
        }

        .callout {
            margin: 1.8em 0;
            padding: 18px 22px;
            border-radius: 14px;
            background-color: var(--bg-subtle);
            border: 1px solid var(--border-card);
            box-shadow: var(--shadow-card);
        }
        .callout-header {
            font-weight: 750;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            font-size: 0.98em;
        }

        .callout-note { border-left: 5px solid #2563eb; }
        .callout-note .callout-header { color: #2563eb; }
        .callout-note .callout-body { color: var(--text-primary); }

        .callout-tip { border-left: 5px solid #10b981; }
        .callout-tip .callout-header { color: #10b981; }
        .callout-tip .callout-body { color: var(--text-primary); }

        .callout-important { border-left: 5px solid #8b5cf6; }
        .callout-important .callout-header { color: #8b5cf6; }
        .callout-important .callout-body { color: var(--text-primary); }

        .callout-warning { border-left: 5px solid #f59e0b; }
        .callout-warning .callout-header { color: #f59e0b; }
        .callout-warning .callout-body { color: var(--text-primary); }

        .callout-caution { border-left: 5px solid #ef4444; }
        .callout-caution .callout-header { color: #ef4444; }
        .callout-caution .callout-body { color: var(--text-primary); }

        body.rtl .callout, body[dir="rtl"] .callout {
            border-left: 1px solid var(--border-card);
        }
        body.rtl .callout-note, body[dir="rtl"] .callout-note { border-right: 5px solid #2563eb; }
        body.rtl .callout-tip, body[dir="rtl"] .callout-tip { border-right: 5px solid #10b981; }
        body.rtl .callout-important, body[dir="rtl"] .callout-important { border-right: 5px solid #8b5cf6; }
        body.rtl .callout-warning, body[dir="rtl"] .callout-warning { border-right: 5px solid #f59e0b; }
        body.rtl .callout-caution, body[dir="rtl"] .callout-caution { border-right: 5px solid #ef4444; }

        .table-wrapper {
            margin: 2.0em 0;
            overflow-x: auto;
            border-radius: 14px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            box-shadow: var(--shadow-card);
        }
        table {
            border-collapse: collapse;
            width: 100%;
            font-size: 0.94em;
        }
        th, td {
            padding: 13px 18px;
            border: 1px solid var(--border-subtle);
            text-align: left;
        }
        body.rtl th, body.rtl td, body[dir="rtl"] th, body[dir="rtl"] td {
            text-align: right;
        }
        th {
            background-color: var(--table-header);
            font-weight: 700;
            color: var(--text-primary);
        }
        tr:nth-child(even) { background-color: var(--table-zebra); }

        ul, ol { padding-left: 28px; margin: 1.0em 0; }
        body.rtl ul, body.rtl ol, body[dir="rtl"] ul, body[dir="rtl"] ol {
            padding-left: 0;
            padding-right: 28px;
        }
        li { margin: 0.45em 0; color: var(--text-secondary); }

        .task-list { list-style: none; padding-left: 0 !important; padding-right: 0 !important; }
        .task-list-item { display: flex; align-items: center; gap: 8px; margin: 0.3em 0; }
        .task-list-item input[type="checkbox"] { margin: 0; }

        /* KaTeX Math formulas */
        .katex-display {
            margin: 1.6em 0 !important;
            padding: 14px 20px;
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            box-shadow: var(--shadow-card);
            overflow-x: auto;
            overflow-y: hidden;
            direction: ltr !important;
            text-align: center !important;
            color: var(--text-primary);
        }

        hr {
            border: 0;
            height: 1.5px;
            background: var(--border-subtle);
            margin: 2.5em 0;
        }

        img.md-img, img:not(.md-badge) {
            max-width: 100%;
            height: auto;
            border-radius: 14px;
            margin: 18px 0;
            box-shadow: var(--shadow-card);
        }

        @media print {
            @page {
                size: A4 portrait;
                margin: 0 !important;
            }
            html, body {
                margin: 0 !important;
                padding: 0 !important;
                background-color: var(--bg-page) !important;
                color: var(--text-primary) !important;
                font-size: 10pt;
                line-height: 1.6;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                width: 100% !important;
                min-height: 100% !important;
            }
            .document-container {
                max-width: 100% !important;
                width: 100% !important;
                box-sizing: border-box !important;
                padding: 16mm 18mm !important;
                margin: 0 !important;
                border: none !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                background-color: var(--bg-card) !important;
                min-height: 100vh !important;
            }
            .code-block, table, .table-wrapper, blockquote, .callout, .mermaid-container, .katex-display, img {
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
"""

def generate_theme_css(theme_name: str) -> str:
    """Combine root variable tokens with the core CSS template."""
    normalized = normalize_theme_name(theme_name)
    config = THEME_CONFIGS.get(normalized, THEME_CONFIGS["amil-light"])
    return f"{config['css']}\n{CORE_CSS_TEMPLATE}"


def is_persian_or_arabic(text: str) -> bool:
    """Detect if the text contains significant Persian/Arabic characters."""
    farsi_chars = len(re.findall(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]", text[:4000]))
    return farsi_chars > 50


def parse_markdown_to_html(
    md_text: str,
    title: str = "",
    theme: str = "amil-light",
    custom_css: str = "",
    force_rtl: Optional[bool] = None,
) -> str:
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
    list_type: str | None = None
    in_callout = False
    callout_type = ""
    callout_lines: list[str] = []
    in_blockquote = False
    blockquote_lines: list[str] = []
    slug_counts: dict[str, int] = {}

    is_rtl = force_rtl if force_rtl is not None else is_persian_or_arabic(md_text)

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
        code_spans: list[str] = []
        def save_code(m: re.Match[str]) -> str:
            code_spans.append(m.group(1))
            return f"__CODESPAN_{len(code_spans)-1}__"

        t = re.sub(r"`([^`]+)`", save_code, text)

        def replace_img(m: re.Match[str]) -> str:
            alt, src = m.group(1), m.group(2)
            is_badge = "shields.io" in src or "badge" in src.lower() or "height=" in src
            cls = "md-badge" if is_badge else "md-img"
            return f'<img src="{html.escape(src)}" alt="{html.escape(alt)}" class="{cls}">'

        t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_img, t)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
        t = re.sub(r"\*\*\*([^*]+)\*\*\*", r"<strong><em>\1</em></strong>", t)
        t = re.sub(r"___([^_]+)___", r"<strong><em>\1</em></strong>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
        t = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", t)
        t = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", t)
        t = re.sub(r"==([^=]+)==", r"<mark>\1</mark>", t)

        for idx, code_content in enumerate(code_spans):
            t = t.replace(f"__CODESPAN_{idx}__", f"<code>{html.escape(code_content)}</code>")
        return t

    def close_table() -> None:
        nonlocal in_table, table_headers, table_aligns, table_rows
        if in_table:
            res = ['<div class="table-wrapper"><table>']
            if table_headers:
                res.append("<thead><tr>")
                for col_idx, hdr in enumerate(table_headers):
                    align = f' style="text-align: {table_aligns[col_idx]}"' if col_idx < len(table_aligns) and table_aligns[col_idx] else ""
                    res.append(f"<th{align}>{inline_fmt(hdr)}</th>")
                res.append("</tr></thead>")
            if table_rows:
                res.append("<tbody>")
                for row in table_rows:
                    res.append("<tr>")
                    for col_idx, cell in enumerate(row):
                        align = f' style="text-align: {table_aligns[col_idx]}"' if col_idx < len(table_aligns) and table_aligns[col_idx] else ""
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
            icons = {"note": "ℹ️", "tip": "💡", "important": "❗", "warning": "⚠️", "caution": "🛑"}
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
        if line.startswith("```"):
            close_table(); close_list(); close_callout(); close_blockquote()
            if in_code:
                raw_code = "\n".join(code_lines)
                if code_lang.lower() == "mermaid":
                    out.append(f'<div class="mermaid-container"><div class="mermaid">{html.escape(raw_code)}</div></div>')
                else:
                    code_content = html.escape(raw_code)
                    lang_label = html.escape(code_lang) if code_lang else "CODE"
                    lang_header = (
                        f'<div class="code-header">'
                        f'<div class="code-header-dots"><span class="dot-red"></span><span class="dot-yellow"></span><span class="dot-green"></span></div>'
                        f'<span class="code-lang">{lang_label}</span>'
                        f'</div>'
                    )
                    out.append(f'<div class="code-block">{lang_header}<pre><code class="language-{html.escape(code_lang)}">{code_content}</code></pre></div>')
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

        # Check block math $$...$$
        if line.strip().startswith("$$") and line.strip().endswith("$$") and len(line.strip()) > 4:
            close_table(); close_list(); close_callout(); close_blockquote()
            formula = line.strip().strip("$").strip()
            out.append(f'<div class="katex-display" data-expr="{html.escape(formula)}">{line.strip()}</div>')
            idx += 1
            continue

        callout_m = re.match(r"^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$", line, re.IGNORECASE)
        if callout_m:
            close_table(); close_list(); close_blockquote()
            if in_callout: close_callout()
            in_callout = True
            callout_type = callout_m.group(1).lower()
            rest = callout_m.group(2).strip()
            if rest: callout_lines.append(rest)
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

        if line.startswith(">"):
            close_table(); close_list()
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
                        if c.startswith(":") and c.endswith(":"): table_aligns.append("center")
                        elif c.endswith(":"): table_aligns.append("right")
                        elif c.startswith(":"): table_aligns.append("left")
                        else: table_aligns.append("")
                    idx += 2
                    continue
            else:
                if not is_sep:
                    table_rows.append([c.strip() for c in line.strip().strip("|").split("|")])
                idx += 1
                continue

        if in_table:
            close_table()

        if re.match(r"^\s*<(div|p|center|section|article|header|footer|nav|details|summary|table|blockquote|figure|figcaption)\b", line, re.IGNORECASE) or \
           re.match(r"^\s*</(div|p|center|section|article|header|footer|nav|details|summary|table|blockquote|figure|figcaption)>", line, re.IGNORECASE):
            close_list()
            out.append(line)
            idx += 1
            continue

        if re.match(r"^\s*(\-{3,}|\*{3,}|_{3,})\s*$", line):
            close_list()
            out.append("<hr>")
            idx += 1
            continue

        head_m = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line)
        if head_m:
            close_list()
            level = len(head_m.group(1))
            h_text = head_m.group(2)
            slug = get_slug(h_text)
            out.append(f'<h{level} id="{slug}">{inline_fmt(h_text)}</h{level}>')
            idx += 1
            continue

        task_m = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+)$", line)
        if task_m:
            if not in_list or list_type != "ul":
                close_list(); in_list = True; list_type = "ul"
                out.append('<ul class="task-list">')
            checked = " checked" if task_m.group(1).lower() == "x" else ""
            out.append(f'<li class="task-list-item"><input type="checkbox" disabled{checked}> {inline_fmt(task_m.group(2))}</li>')
            idx += 1
            continue

        bullet_m = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if bullet_m:
            if not in_list or list_type != "ul":
                close_list(); in_list = True; list_type = "ul"
                out.append("<ul>")
            out.append(f"<li>{inline_fmt(bullet_m.group(1))}</li>")
            idx += 1
            continue

        num_m = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if num_m:
            if not in_list or list_type != "ol":
                close_list(); in_list = True; list_type = "ol"
                out.append("<ol>")
            out.append(f"<li>{inline_fmt(num_m.group(2))}</li>")
            idx += 1
            continue

        if in_list and not line.strip():
            if idx + 1 < len(lines) and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[idx + 1]):
                idx += 1
                continue
            close_list()

        if not line.strip():
            close_list()
            idx += 1
            continue

        close_list()
        out.append(f"<p>{inline_fmt(line)}</p>")
        idx += 1

    close_table(); close_list(); close_callout(); close_blockquote()

    body_html = "\n".join(out)
    
    # Resolve theme CSS & Mermaid config
    normalized_theme = normalize_theme_name(theme)
    theme_cfg = THEME_CONFIGS.get(normalized_theme, THEME_CONFIGS["amil-light"])

    if os.path.isfile(theme):
        with open(theme, "r", encoding="utf-8") as f:
            selected_css = f.read()
        mermaid_theme = "neutral"
        mermaid_vars = theme_cfg["mermaid_vars"]
    else:
        selected_css = generate_theme_css(normalized_theme)
        mermaid_theme = theme_cfg["mermaid_theme"]
        mermaid_vars = theme_cfg["mermaid_vars"]

    if custom_css:
        selected_css += f"\n/* Custom Overrides */\n{custom_css}\n"

    doc_title = title or "Document"
    dir_attr = 'dir="rtl" class="rtl"' if is_rtl else 'dir="ltr"'
    lang_code = "fa" if is_rtl else "en"

    # Local vendor script paths
    mermaid_vendor = VENDOR_DIR / "mermaid.js"
    katex_vendor_js = VENDOR_DIR / "katex.js"
    katex_vendor_css = VENDOR_DIR / "katex.min.css"

    mermaid_script_tag = f'<script src="file://{mermaid_vendor}"></script>' if mermaid_vendor.exists() else '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>'
    katex_css_tag = f'<link rel="stylesheet" href="file://{katex_vendor_css}">' if katex_vendor_css.exists() else '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">'
    katex_js_tag = f'<script src="file://{katex_vendor_js}"></script>' if katex_vendor_js.exists() else '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>'

    mermaid_cfg_json = json.dumps({
        "startOnLoad": True,
        "theme": mermaid_theme,
        "themeVariables": mermaid_vars,
        "flowchart": {"curve": "basis"},
        "fontFamily": "Inter, Vazirmatn, -apple-system, sans-serif"
    })

    return f"""<!DOCTYPE html>
<html lang="{lang_code}" {dir_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(doc_title)}</title>
<!-- KaTeX Math -->
{katex_css_tag}
{katex_js_tag}
<!-- Mermaid Config & Engine -->
<script>
window.mermaidConfig = {mermaid_cfg_json};
</script>
{mermaid_script_tag}
<!-- Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Vazirmatn:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
{selected_css}
</style>
</head>
<body {dir_attr}>
<div class="document-container">
{body_html}
</div>
<script>
document.addEventListener("DOMContentLoaded", function() {{
    if (window.katex) {{
        document.querySelectorAll('.katex-display').forEach(function(el) {{
            var expr = el.getAttribute('data-expr');
            if (expr) {{
                try {{
                    katex.render(expr, el, {{ displayMode: true, throwOnError: false }});
                }} catch(e) {{}}
            }}
        }});
    }}
    if (window.mermaid) {{
        try {{
            mermaid.initialize({mermaid_cfg_json});
        }} catch(e) {{}}
    }}
}});
</script>
</body>
</html>"""


def convert_markdown(
    source: Path,
    output_format: str,
    output: Path | None = None,
    theme: str = "amil-light",
    custom_css: str = "",
    rtl: Optional[bool] = None,
) -> Path:
    if output_format not in FORMATS:
        raise ValueError(f"Unsupported format '{output_format}'. Choose: {', '.join(FORMATS)}.")
    if source.suffix.lower() not in (".md", ".markdown"):
        raise ValueError(f"Input must be a Markdown file: {source}")
    if not source.is_file():
        raise FileNotFoundError(source)

    destination = output or source.with_suffix(f".{output_format}").expanduser().resolve()
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    content = source.read_text(encoding="utf-8")
    rendered_html = parse_markdown_to_html(content, title=source.stem, theme=theme, custom_css=custom_css, force_rtl=rtl)

    if output_format == "html":
        destination.write_text(rendered_html, encoding="utf-8")
        return destination

    if output_format == "pdf":
        with tempfile.TemporaryDirectory(prefix="convert-pdf-") as tmp_dir:
            tmp_html = Path(tmp_dir) / f"{source.stem}.html"
            tmp_html.write_text(rendered_html, encoding="utf-8")

            # Try Chrome Headless with local file access and compositor readiness
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
                        "--allow-file-access-from-files",
                        "--enable-local-file-accesses",
                        "--virtual-time-budget=3000",
                        "--run-all-compositor-stages-before-draw",
                        "--no-pdf-header-footer",
                        f"--print-to-pdf={destination}",
                        f"file://{tmp_html}"
                    ], capture_output=True, text=True)
                    if res.returncode == 0 and destination.is_file():
                        return destination

            # Fallback via cupsfilter
            if shutil.which("cupsfilter"):
                subprocess.run(f'cupsfilter "{tmp_html}" > "{destination}"', shell=True, check=True)
                return destination

        raise RuntimeError("PDF conversion requires Google Chrome or cupsfilter.")

    if output_format == "docx":
        with tempfile.TemporaryDirectory(prefix="convert-docx-") as tmp_dir:
            tmp_html = Path(tmp_dir) / f"{source.stem}.html"
            tmp_html.write_text(rendered_html, encoding="utf-8")
            subprocess.run(["textutil", "-convert", "docx", "-output", str(destination), str(tmp_html)], check=True)
        return destination

    if output_format == "pages":
        if sys.platform != "darwin" or not os.path.exists("/Applications/Pages.app"):
            raise RuntimeError("Pages output requires macOS with Apple Pages installed.")
        with tempfile.TemporaryDirectory(prefix="convert-pages-") as tmp_dir:
            tmp_html = Path(tmp_dir) / f"{source.stem}.html"
            tmp_html.write_text(rendered_html, encoding="utf-8")
            tmp_docx = Path(tmp_dir) / f"{source.stem}.docx"
            subprocess.run(["textutil", "-convert", "docx", "-output", str(tmp_docx), str(tmp_html)], check=True)

            if destination.exists():
                if destination.is_dir(): shutil.rmtree(destination)
                else: destination.unlink()

            applescript = f"""
            set docxFile to POSIX file "{tmp_docx}"
            set pagesFile to POSIX file "{destination}"
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
        return destination

    raise RuntimeError(f"Failed to convert {source} to {output_format}")


def main(argv: list[str] | None = None) -> int:
    theme_help = (
        "Theme name: " + ", ".join(f"'{k}'" for k in THEME_CONFIGS.keys()) +
        " (or aliases like 'amil-design', 'modern', 'dark', 'terminal', 'vscode', 'github', 'nord', 'classic') or CSS file path"
    )
    parser = argparse.ArgumentParser(description="Convert Markdown files to HTML, PDF, DOCX, or Pages with 9 beautiful themes.")
    parser.add_argument("files", nargs="+", type=Path, help="Markdown file(s) to convert")
    parser.add_argument("-f", "--format", choices=FORMATS, default="pdf", help="Output format (default: pdf)")
    parser.add_argument("-o", "--output", type=Path, help="Output path (only valid for one input file)")
    parser.add_argument("-t", "--theme", default="amil-light", help=theme_help)
    parser.add_argument("--css", default="", help="Custom CSS string override")
    parser.add_argument("--rtl", action="store_true", default=None, help="Force Right-to-Left (RTL) layout")
    parser.add_argument("--ltr", action="store_true", help="Force Left-to-Right (LTR) layout")
    args = parser.parse_args(argv)

    if args.output and len(args.files) != 1:
        parser.error("--output can only be used with one input file")

    force_rtl = True if args.rtl else (False if args.ltr else None)
    failures = 0
    for source in args.files:
        try:
            dest = convert_markdown(source, args.format, args.output, theme=args.theme, custom_css=args.css, rtl=force_rtl)
            print(f"✓ Generated [{args.format.upper()}] (theme: {args.theme}): {dest}")
        except Exception as exc:
            print(f"Error converting {source}: {exc}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
