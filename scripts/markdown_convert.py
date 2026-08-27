import argparse
import base64
import html
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any
from xml.etree import ElementTree as ET

FORMATS = ("pages", "pdf", "html", "docx")

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WPNS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
ANS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PICNS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
ASVGNS = "http://schemas.microsoft.com/office/drawing/2016/SVG/main"

ET.register_namespace("w", WNS)
ET.register_namespace("r", RNS)
ET.register_namespace("wp", WPNS)
ET.register_namespace("a", ANS)
ET.register_namespace("pic", PICNS)
ET.register_namespace("asvg", ASVGNS)

_HERE = Path(__file__).resolve().parent
VENDOR_DIR = _HERE.parent / "vendor"
if not VENDOR_DIR.exists():
    VENDOR_DIR = Path.home() / ".gemini/config/skills/markdown-tools/vendor"
if not VENDOR_DIR.exists():
    VENDOR_DIR = Path.home() / ".gemini/config/skills/pages-tools/vendor"

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
            --code-bg: #1e1e24;
            --code-header: #2c2c34;
            --code-text: #f5f5f7;
            --inline-code-bg: #f2f2f7;
            --inline-code-color: #1d1d1f;
            --table-header: #fbfbfd;
            --table-zebra: #f5f5f7;
            --shadow-card: 0 4px 28px rgba(0, 0, 0, 0.06);
            --shadow-code: 0 8px 24px rgba(0, 0, 0, 0.12);
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



def render_mermaid_to_svg_and_png(code: str, vendor_dir: Path) -> tuple[str, bytes, int, int]:
    """Renders a Mermaid diagram string into pure vector SVG and high-res PNG bytes with EMU dimensions."""
    mermaid_js = vendor_dir / "mermaid.js"
    if not mermaid_js.exists():
        mermaid_js = Path.home() / ".gemini/config/skills/markdown-tools/vendor/mermaid.js"
    if not mermaid_js.exists():
        mermaid_js = Path.home() / ".gemini/config/skills/pages-tools/vendor/mermaid.js"
        
    json_code = json.dumps(code)
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="file://{mermaid_js}"></script>
<style>
body {{ margin: 0; padding: 24px; background: #ffffff; display: inline-block; }}
#container {{ display: inline-block; }}
</style>
</head>
<body>
<div id="container"></div>
<script>
window.addEventListener('DOMContentLoaded', async () => {{
    try {{
        mermaid.initialize({{ startOnLoad: false, theme: 'default', flowchart: {{ useMaxWidth: false, htmlLabels: true }} }});
        const {{ svg }} = await mermaid.render('m_diag', {json_code});
        document.getElementById('container').innerHTML = svg;
    }} catch (e) {{
        console.error(e);
    }}
}});
</script>
</body>
</html>"""

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_html = Path(tmp_dir) / "diag.html"
        tmp_png = Path(tmp_dir) / "diag.png"
        tmp_html.write_text(html_content, encoding="utf-8")
        
        chrome_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        ]
        chrome_bin = next((c for c in chrome_candidates if os.path.exists(c)), None)
        if not chrome_bin:
            raise RuntimeError("Headless Chrome is required to render Mermaid diagrams to vector layout.")
            
        res = subprocess.run([
            chrome_bin,
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--enable-local-file-accesses",
            "--virtual-time-budget=3000",
            "--window-size=1400,900",
            f"--screenshot={tmp_png}",
            "--dump-dom",
            f"file://{tmp_html}"
        ], capture_output=True, text=True)
        
        m = re.search(r"(<svg[\s\S]*?</svg>)", res.stdout)
        svg_code = m.group(1) if m else ""
        png_data = tmp_png.read_bytes() if tmp_png.exists() else b""
        
        w_px, h_px = 600, 400
        if svg_code:
            vb_m = re.search(r'viewBox="([^"]+)"', svg_code)
            if vb_m:
                parts = [float(x) for x in vb_m.group(1).split()]
                if len(parts) == 4:
                    w_px, h_px = parts[2], parts[3]
        
        max_w_emu = 5029200
        aspect = h_px / max(w_px, 1)
        w_emu = min(int(w_px * 9525 * 1.2), max_w_emu)
        h_emu = int(w_emu * aspect)
        
        return svg_code, png_data, w_emu, h_emu


def build_ooxml_table(headers: list[str], aligns: list[str], rows: list[list[str]]) -> ET.Element:
    """Builds a fully native, styled OOXML <w:tbl> table object."""
    num_cols = max(len(headers), max((len(r) for r in rows), default=1))
    col_w = int(9000 / max(num_cols, 1))
    
    tbl = ET.Element(f"{{{WNS}}}tbl")
    tblPr = ET.SubElement(tbl, f"{{{WNS}}}tblPr")
    tblW = ET.SubElement(tblPr, f"{{{WNS}}}tblW")
    tblW.set(f"{{{WNS}}}w", "5000")
    tblW.set(f"{{{WNS}}}type", "pct")
    
    tblBorders = ET.SubElement(tblPr, f"{{{WNS}}}tblBorders")
    for b_name, b_sz, b_col in [("top", "8", "D2D2D7"), ("bottom", "12", "D2D2D7"), ("insideH", "4", "E5E5EA")]:
        b = ET.SubElement(tblBorders, f"{{{WNS}}}{b_name}")
        b.set(f"{{{WNS}}}val", "single")
        b.set(f"{{{WNS}}}sz", b_sz)
        b.set(f"{{{WNS}}}space", "0")
        b.set(f"{{{WNS}}}color", b_col)
    for b_name in ["left", "right", "insideV"]:
        b = ET.SubElement(tblBorders, f"{{{WNS}}}{b_name}")
        b.set(f"{{{WNS}}}val", "none")
        
    tblGrid = ET.SubElement(tbl, f"{{{WNS}}}tblGrid")
    for _ in range(num_cols):
        gc = ET.SubElement(tblGrid, f"{{{WNS}}}gridCol")
        gc.set(f"{{{WNS}}}w", str(col_w))
        
    if headers:
        tr = ET.SubElement(tbl, f"{{{WNS}}}tr")
        trPr = ET.SubElement(tr, f"{{{WNS}}}trPr")
        ET.SubElement(trPr, f"{{{WNS}}}tblHeader")
        for idx, h_text in enumerate(headers):
            align = aligns[idx] if idx < len(aligns) and aligns[idx] else "left"
            tc = ET.SubElement(tr, f"{{{WNS}}}tc")
            tcPr = ET.SubElement(tc, f"{{{WNS}}}tcPr")
            shd = ET.SubElement(tcPr, f"{{{WNS}}}shd")
            shd.set(f"{{{WNS}}}val", "clear")
            shd.set(f"{{{WNS}}}color", "auto")
            shd.set(f"{{{WNS}}}fill", "F4F4F6")
            
            p = ET.SubElement(tc, f"{{{WNS}}}p")
            pPr = ET.SubElement(p, f"{{{WNS}}}pPr")
            jc = ET.SubElement(pPr, f"{{{WNS}}}jc")
            jc.set(f"{{{WNS}}}val", align)
            sp = ET.SubElement(pPr, f"{{{WNS}}}spacing")
            sp.set(f"{{{WNS}}}before", "80")
            sp.set(f"{{{WNS}}}after", "80")
            
            r = ET.SubElement(p, f"{{{WNS}}}r")
            rPr = ET.SubElement(r, f"{{{WNS}}}rPr")
            ET.SubElement(rPr, f"{{{WNS}}}b")
            rFonts = ET.SubElement(rPr, f"{{{WNS}}}rFonts")
            rFonts.set(f"{{{WNS}}}ascii", "Helvetica Neue")
            rFonts.set(f"{{{WNS}}}hAnsi", "Helvetica Neue")
            sz = ET.SubElement(rPr, f"{{{WNS}}}sz")
            sz.set(f"{{{WNS}}}val", "21")
            
            clean_h = re.sub(r"<[^>]+>", "", h_text).strip()
            t = ET.SubElement(r, f"{{{WNS}}}t")
            t.text = clean_h
            
    for row in rows:
        tr = ET.SubElement(tbl, f"{{{WNS}}}tr")
        for idx in range(num_cols):
            cell_text = row[idx] if idx < len(row) else ""
            align = aligns[idx] if idx < len(aligns) and aligns[idx] else "left"
            tc = ET.SubElement(tr, f"{{{WNS}}}tc")
            p = ET.SubElement(tc, f"{{{WNS}}}p")
            pPr = ET.SubElement(p, f"{{{WNS}}}pPr")
            jc = ET.SubElement(pPr, f"{{{WNS}}}jc")
            jc.set(f"{{{WNS}}}val", align)
            sp = ET.SubElement(pPr, f"{{{WNS}}}spacing")
            sp.set(f"{{{WNS}}}before", "60")
            sp.set(f"{{{WNS}}}after", "60")
            
            clean_text = re.sub(r"<[^>]+>", "", cell_text).strip()
            is_bold = "**" in cell_text or "__" in cell_text or "<strong>" in cell_text or "PASSED" in cell_text
            is_italic = "*" in clean_text and not is_bold
            clean_text = clean_text.replace("**", "").replace("__", "").replace("*", "")
            
            r = ET.SubElement(p, f"{{{WNS}}}r")
            rPr = ET.SubElement(r, f"{{{WNS}}}rPr")
            rFonts = ET.SubElement(rPr, f"{{{WNS}}}rFonts")
            rFonts.set(f"{{{WNS}}}ascii", "Helvetica Neue")
            rFonts.set(f"{{{WNS}}}hAnsi", "Helvetica Neue")
            sz = ET.SubElement(rPr, f"{{{WNS}}}sz")
            sz.set(f"{{{WNS}}}val", "20")
            if is_bold:
                ET.SubElement(rPr, f"{{{WNS}}}b")
            if is_italic:
                ET.SubElement(rPr, f"{{{WNS}}}i")
            if "color: #059669" in cell_text or "PASSED" in cell_text:
                col = ET.SubElement(rPr, f"{{{WNS}}}color")
                col.set(f"{{{WNS}}}val", "059669")
            elif "color: #2563eb" in cell_text:
                col = ET.SubElement(rPr, f"{{{WNS}}}color")
                col.set(f"{{{WNS}}}val", "2563EB")
                
            t = ET.SubElement(r, f"{{{WNS}}}t")
            t.text = clean_text
            
    return tbl


def build_ooxml_drawing(r_id_svg: str, r_id_png: str, cx: int, cy: int, desc: str = "Diagram") -> ET.Element:
    """Builds a DrawingML <w:p> containing an embedded vector diagram with SVG and high-res PNG fallback."""
    p = ET.Element(f"{{{WNS}}}p")
    pPr = ET.SubElement(p, f"{{{WNS}}}pPr")
    jc = ET.SubElement(pPr, f"{{{WNS}}}jc")
    jc.set(f"{{{WNS}}}val", "center")
    sp = ET.SubElement(pPr, f"{{{WNS}}}spacing")
    sp.set(f"{{{WNS}}}before", "140")
    sp.set(f"{{{WNS}}}after", "140")
    
    r = ET.SubElement(p, f"{{{WNS}}}r")
    drawing = ET.SubElement(r, f"{{{WNS}}}drawing")
    inline = ET.SubElement(drawing, f"{{{WPNS}}}inline")
    inline.set("distT", "0"); inline.set("distB", "0"); inline.set("distL", "0"); inline.set("distR", "0")
    
    extent = ET.SubElement(inline, f"{{{WPNS}}}extent")
    extent.set("cx", str(cx)); extent.set("cy", str(cy))
    
    docPr = ET.SubElement(inline, f"{{{WPNS}}}docPr")
    docPr.set("id", "100"); docPr.set("name", desc)
    
    graphic = ET.SubElement(inline, f"{{{ANS}}}graphic")
    gdata = ET.SubElement(graphic, f"{{{ANS}}}graphicData")
    gdata.set("uri", "http://schemas.openxmlformats.org/drawingml/2006/picture")
    
    pic = ET.SubElement(gdata, f"{{{PICNS}}}pic")
    nvPicPr = ET.SubElement(pic, f"{{{PICNS}}}nvPicPr")
    cNvPr = ET.SubElement(nvPicPr, f"{{{PICNS}}}cNvPr")
    cNvPr.set("id", "100"); cNvPr.set("name", desc)
    ET.SubElement(nvPicPr, f"{{{PICNS}}}cNvPicPr")
    
    blipFill = ET.SubElement(pic, f"{{{PICNS}}}blipFill")
    blip = ET.SubElement(blipFill, f"{{{ANS}}}blip")
    # For Apple Pages, direct SVG embedding works seamlessly; for Word, use SVG extension
    blip.set(f"{{{RNS}}}embed", r_id_svg)
    extLst = ET.SubElement(blip, f"{{{ANS}}}extLst")
    ext = ET.SubElement(extLst, f"{{{ANS}}}ext")
    ext.set("uri", "{96DAC542-7CC2-4438-873DA00B022F820E}")
    svgBlip = ET.SubElement(ext, f"{{{ASVGNS}}}svgBlip")
    svgBlip.set(f"{{{RNS}}}embed", r_id_svg)
    
    stretch = ET.SubElement(blipFill, f"{{{ANS}}}stretch")
    ET.SubElement(stretch, f"{{{ANS}}}fillRect")
    
    spPr = ET.SubElement(pic, f"{{{PICNS}}}spPr")
    xfrm = ET.SubElement(spPr, f"{{{ANS}}}xfrm")
    off = ET.SubElement(xfrm, f"{{{ANS}}}off")
    off.set("x", "0"); off.set("y", "0")
    ext_s = ET.SubElement(xfrm, f"{{{ANS}}}ext")
    ext_s.set("cx", str(cx)); ext_s.set("cy", str(cy))
    prstGeom = ET.SubElement(spPr, f"{{{ANS}}}prstGeom")
    prstGeom.set("prst", "rect")
    ET.SubElement(prstGeom, f"{{{ANS}}}avLst")
    
    return p


def parse_markdown_to_html(
    md_text: str,
    title: str = "",
    theme: str = "amil-light",
    custom_css: str = "",
    force_rtl: Optional[bool] = None,
    for_textutil: bool = False,
) -> tuple[str, dict]:
    lines = md_text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_lines: list[str] = []
    in_table = False
    table_headers: list[str] = []
    table_aligns: list[str] = []
    table_rows: list[list[str]] = []
    tables_meta: list[tuple[list[str], list[str], list[list[str]]]] = []
    diagrams_meta: list[str] = []
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
            if for_textutil:
                tbl_idx = len(tables_meta)
                tables_meta.append((table_headers, table_aligns, table_rows))
                out.append(f'<p style="font-family: Arial; font-size: 10pt;">__FORMA_TABLE_START_{tbl_idx}__</p>')
            else:
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
                    if for_textutil:
                        diag_idx = len(diagrams_meta)
                        diagrams_meta.append(raw_code)
                        out.append(f'<p style="font-family: Arial; font-size: 10pt;">__FORMA_DIAGRAM_START_{diag_idx}__</p>')
                    else:
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
            if idx + 1 < len(lines) and re.match(r"^\s*([*+]|\d+\.)\s+", lines[idx + 1]):
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

    full_html = f"""<!DOCTYPE html>
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
    return full_html, {"tables": tables_meta, "diagrams": diagrams_meta}


def get_theme_styles_xml(theme: str = "amil-light") -> str:
    font_main = "Helvetica Neue"
    font_code = "Menlo"
    col_title = "0D121F"
    col_body = "273143"
    col_muted = "4B5563"
    col_accent = "2563EB"
    bg_code = "F3F4F6"
    
    norm = normalize_theme_name(theme)
    if "dark" in norm or "midnight" in norm:
        col_title = "F8FAFC"
        col_body = "CBD5E1"
        col_muted = "94A3B8"
        col_accent = "38BDF8"
        bg_code = "1E293B"
    elif "serif" in norm or "editorial" in norm or "classic" in norm:
        font_main = "New York"
        font_code = "Menlo"
        col_title = "26211E"
        col_body = "3A322D"
        col_muted = "6E6259"
        col_accent = "9B111E"
        
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="0" w:after="140" w:line="276" w:lineRule="auto"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:sz w:val="22"/>
      <w:color w:val="{col_body}"/>
    </w:rPr>
  </w:style>
  
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="240" w:after="120" w:line="280" w:lineRule="auto"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:b/>
      <w:sz w:val="56"/>
      <w:color w:val="{col_title}"/>
    </w:rPr>
  </w:style>
  
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="Heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="360" w:after="120"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:b/>
      <w:sz w:val="40"/>
      <w:color w:val="{col_title}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="Heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="280" w:after="100"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:b/>
      <w:sz w:val="32"/>
      <w:color w:val="{col_title}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="Heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="220" w:after="80"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:b/>
      <w:sz w:val="26"/>
      <w:color w:val="{col_title}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="Heading4">
    <w:name w:val="Heading 4"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="180" w:after="60"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:b/>
      <w:sz w:val="22"/>
      <w:color w:val="{col_title}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="Heading5">
    <w:name w:val="Heading 5"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="140" w:after="40"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:b/>
      <w:sz w:val="20"/>
      <w:color w:val="{col_title}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="Heading6">
    <w:name w:val="Heading 6"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="120" w:after="40"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:b/>
      <w:sz w:val="18"/>
      <w:color w:val="{col_title}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="Body">
    <w:name w:val="Body"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="0" w:after="140" w:line="276" w:lineRule="auto"/>
      <w:jc w:val="left"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:sz w:val="22"/>
      <w:color w:val="{col_body}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="BlockQuote">
    <w:name w:val="Block Quote"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="140" w:after="140" w:line="276" w:lineRule="auto"/>
      <w:ind w:left="360"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:i/>
      <w:sz w:val="22"/>
      <w:color w:val="{col_muted}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="80" w:after="80" w:line="240" w:lineRule="auto"/>
      <w:shd w:val="clear" w:color="auto" w:fill="{bg_code}"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_code}" w:hAnsi="{font_code}"/>
      <w:sz w:val="20"/>
      <w:color w:val="{col_title}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="BulletList">
    <w:name w:val="Bullet List"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="40" w:after="40"/>
      <w:ind w:left="360" w:hanging="240"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:sz w:val="22"/>
      <w:color w:val="{col_body}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="paragraph" w:styleId="NumberedList">
    <w:name w:val="Numbered List"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr>
      <w:spacing w:before="40" w:after="40"/>
      <w:ind w:left="360" w:hanging="240"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="{font_main}" w:hAnsi="{font_main}"/>
      <w:sz w:val="22"/>
      <w:color w:val="{col_body}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="character" w:styleId="Bold">
    <w:name w:val="Bold"/>
    <w:rPr><w:b/></w:rPr>
  </w:style>

  <w:style w:type="character" w:styleId="Italic">
    <w:name w:val="Italic"/>
    <w:rPr><w:i/></w:rPr>
  </w:style>

  <w:style w:type="character" w:styleId="BoldItalic">
    <w:name w:val="Bold Italic"/>
    <w:rPr><w:b/><w:i/></w:rPr>
  </w:style>

  <w:style w:type="character" w:styleId="InlineCode">
    <w:name w:val="Inline Code"/>
    <w:rPr>
      <w:rFonts w:ascii="{font_code}" w:hAnsi="{font_code}"/>
      <w:color w:val="{col_accent}"/>
      <w:shd w:val="clear" w:color="auto" w:fill="{bg_code}"/>
    </w:rPr>
  </w:style>

  <w:style w:type="character" w:styleId="Underline">
    <w:name w:val="Underline"/>
    <w:rPr><w:u w:val="single"/></w:rPr>
  </w:style>

  <w:style w:type="character" w:styleId="Strikethrough">
    <w:name w:val="Strikethrough"/>
    <w:rPr><w:strike/></w:rPr>
  </w:style>

  <w:style w:type="character" w:styleId="Highlight">
    <w:name w:val="Highlight"/>
    <w:rPr><w:highlight w:val="yellow"/></w:rPr>
  </w:style>

  <w:style w:type="character" w:styleId="Hyperlink">
    <w:name w:val="Hyperlink"/>
    <w:rPr>
      <w:color w:val="{col_accent}"/>
      <w:u w:val="single"/>
    </w:rPr>
  </w:style>
</w:styles>"""


def postprocess_docx_styles(
    docx_path: str | Path,
    tables: list | None = None,
    diagrams: list | None = None,
    vendor_dir: Path | None = None,
    theme: str = "amil-light",
) -> None:
    """
    Post-processes a DOCX file produced by textutil to inject:
    1. Rich, visual theme definitions for all named paragraph styles & character styles in word/styles.xml
    2. Genuine OOXML tables (<w:tbl>) with header and cell styling
    3. Embedded vector diagrams (<w:drawing>) with SVG and Retina PNG fallback
    4. Pure named paragraph style bindings without redundant direct formatting overrides
    """
    docx_p = Path(docx_path)
    if not docx_p.is_file():
        return

    try:
        with zipfile.ZipFile(docx_p, "r") as zin:
            files = {name: zin.read(name) for name in zin.namelist()}
    except Exception:
        return

    if "word/document.xml" not in files:
        return

    # Injected styles.xml with full visual specifications
    files["word/styles.xml"] = get_theme_styles_xml(theme).encode("utf-8")

    ct_str = files.get("[Content_Types].xml", b"").decode("utf-8", errors="ignore")
    if ct_str and "word/styles.xml" not in ct_str:
        ct_str = ct_str.replace("</Types>", '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    if ct_str and 'Extension="svg"' not in ct_str:
        ct_str = ct_str.replace("</Types>", '<Default Extension="svg" ContentType="image/svg+xml"/><Default Extension="png" ContentType="image/png"/></Types>')
    files["[Content_Types].xml"] = ct_str.encode("utf-8")

    rels_str = files.get("word/_rels/document.xml.rels", b"").decode("utf-8", errors="ignore")
    if not rels_str:
        rels_str = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
    if "styles.xml" not in rels_str:
        rels_str = rels_str.replace("</Relationships>", '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')

    # Process Diagrams
    rendered_diagrams: dict[int, tuple[int, int]] = {}
    v_dir = vendor_dir or VENDOR_DIR
    if diagrams:
        for d_idx, d_code in enumerate(diagrams):
            try:
                svg_data, png_data, cx, cy = render_mermaid_to_svg_and_png(d_code, v_dir)
                svg_name = f"media/diagram_{d_idx}.svg"
                png_name = f"media/diagram_{d_idx}.png"
                files[f"word/{svg_name}"] = svg_data.encode("utf-8")
                files[f"word/{png_name}"] = png_data
                
                r_svg = f"rIdSvg{d_idx}"
                r_png = f"rIdImg{d_idx}"
                if r_svg not in rels_str:
                    rels_str = rels_str.replace("</Relationships>", f'<Relationship Id="{r_svg}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{svg_name}"/><Relationship Id="{r_png}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{png_name}"/></Relationships>')
                rendered_diagrams[d_idx] = (cx, cy)
            except Exception as e:
                print(f"Warning: Diagram {d_idx} render skipped: {e}", file=sys.stderr)

    files["word/_rels/document.xml.rels"] = rels_str.encode("utf-8")

    try:
        doc_tree = ET.fromstring(files["word/document.xml"])
    except Exception:
        return

    body = doc_tree.find(f"{{{WNS}}}body")
    if body is None:
        return

    first_heading_seen = False
    children = list(body)

    for elem in children:
        if elem.tag != f"{{{WNS}}}p":
            continue
            
        p = elem
        text = "".join(p.itertext()).strip()
        if not text:
            continue

        # Check Table Marker
        tbl_m = re.match(r"^__FORMA_TABLE_START_(\d+)__$", text)
        if tbl_m:
            tbl_idx = int(tbl_m.group(1))
            if tables and tbl_idx < len(tables):
                headers, aligns, rows = tables[tbl_idx]
                tbl_node = build_ooxml_table(headers, aligns, rows)
                idx_in_body = list(body).index(p)
                body.remove(p)
                body.insert(idx_in_body, tbl_node)
                continue

        # Check Diagram Marker
        diag_m = re.match(r"^__FORMA_DIAGRAM_START_(\d+)__$", text)
        if diag_m:
            diag_idx = int(diag_m.group(1))
            if diag_idx in rendered_diagrams:
                cx, cy = rendered_diagrams[diag_idx]
                draw_node = build_ooxml_drawing(f"rIdSvg{diag_idx}", f"rIdImg{diag_idx}", cx, cy, f"Diagram {diag_idx}")
                idx_in_body = list(body).index(p)
                body.remove(p)
                body.insert(idx_in_body, draw_node)
                continue

        # Classification of Paragraph Style
        rPr_first = p.find(f".//{{{WNS}}}rPr")
        font_name = ""
        sz_val = 0
        is_bold = False
        is_italic = False
        if rPr_first is not None:
            rFonts = rPr_first.find(f"{{{WNS}}}rFonts")
            if rFonts is not None:
                font_name = rFonts.get(f"{{{WNS}}}ascii", "") or rFonts.get(f"{{{WNS}}}hAnsi", "")
            sz = rPr_first.find(f"{{{WNS}}}sz")
            if sz is not None:
                try:
                    sz_val = int(sz.get(f"{{{WNS}}}val", "0"))
                except ValueError:
                    pass
            is_bold = rPr_first.find(f"{{{WNS}}}b") is not None
            is_italic = rPr_first.find(f"{{{WNS}}}i") is not None

        pPr = p.find(f"{{{WNS}}}pPr")
        has_ind = False
        if pPr is not None:
            ind = pPr.find(f"{{{WNS}}}ind")
            if ind is not None:
                has_ind = True

        style_id = "Body"
        is_heading = False
        if any(f in font_name for f in ["Courier", "Mono", "Consolas", "Menlo", "Code"]):
            style_id = "Code"
        elif text.startswith("•") or text.startswith("- ") or text.startswith("* ") or (has_ind and text.startswith("•")):
            style_id = "BulletList"
        elif (has_ind or text.strip()[:1].isdigit()) and any(text.startswith(f"{n}") for n in range(10)) and ("." in text[:5] or ")" in text[:5]):
            style_id = "NumberedList"
        elif is_italic and not is_bold and sz_val == 24:
            style_id = "BlockQuote"
        elif is_bold and sz_val >= 44:
            if not first_heading_seen:
                style_id = "Title"
                first_heading_seen = True
            else:
                style_id = "Heading1"
            is_heading = True
        elif is_bold and sz_val >= 34:
            style_id = "Heading1"
            first_heading_seen = True
            is_heading = True
        elif is_bold and sz_val >= 27:
            style_id = "Heading2"
            first_heading_seen = True
            is_heading = True
        elif is_bold and sz_val >= 23:
            style_id = "Heading3"
            is_heading = True
        elif is_bold and sz_val >= 19:
            style_id = "Heading4"
            is_heading = True
        elif is_bold and sz_val >= 17:
            style_id = "Heading5"
            is_heading = True
        elif is_bold:
            style_id = "Heading6"
            is_heading = True

        if pPr is None:
            pPr = ET.Element(f"{{{WNS}}}pPr")
            p.insert(0, pPr)

        existing_pstyle = pPr.find(f"{{{WNS}}}pStyle")
        if existing_pstyle is not None:
            pPr.remove(existing_pstyle)

        pstyle = ET.Element(f"{{{WNS}}}pStyle")
        pstyle.set(f"{{{WNS}}}val", style_id)
        pPr.insert(0, pstyle)

        # For headings: clean direct formatting overrides on runs so style defines all visual features
        for r in p.findall(f".//{{{WNS}}}r"):
            rPr_r = r.find(f"{{{WNS}}}rPr")
            if rPr_r is not None:
                if is_heading:
                    for tag in ["sz", "sz-cs", "color", "rFonts", "spacing"]:
                        el = rPr_r.find(f"{{{WNS}}}{tag}")
                        if el is not None:
                            rPr_r.remove(el)
                else:
                    f_name = ""
                    rFonts_r = rPr_r.find(f"{{{WNS}}}rFonts")
                    if rFonts_r is not None:
                        f_name = rFonts_r.get(f"{{{WNS}}}ascii", "")
                    r_b = rPr_r.find(f"{{{WNS}}}b") is not None
                    r_i = rPr_r.find(f"{{{WNS}}}i") is not None
                    r_u = rPr_r.find(f"{{{WNS}}}u") is not None
                    r_strike = rPr_r.find(f"{{{WNS}}}strike") is not None or rPr_r.find(f"{{{WNS}}}dstrike") is not None
                    r_hl = rPr_r.find(f"{{{WNS}}}highlight") is not None

                    c_id = None
                    if any(m in f_name for m in ["Menlo", "Courier", "Consolas", "Mono"]):
                        c_id = "InlineCode"
                    elif r_b and r_i:
                        c_id = "BoldItalic"
                    elif r_b:
                        c_id = "Bold"
                    elif r_i:
                        c_id = "Italic"
                    elif r_u:
                        c_id = "Underline"
                    elif r_strike:
                        c_id = "Strikethrough"
                    elif r_hl:
                        c_id = "Highlight"

                    if c_id:
                        existing_rstyle = rPr_r.find(f"{{{WNS}}}rStyle")
                        if existing_rstyle is not None:
                            rPr_r.remove(existing_rstyle)
                        rstyle_elem = ET.Element(f"{{{WNS}}}rStyle")
                        rstyle_elem.set(f"{{{WNS}}}val", c_id)
                        rPr_r.insert(0, rstyle_elem)

    files["word/document.xml"] = ET.tostring(doc_tree, encoding="utf-8", xml_declaration=True)

    try:
        with zipfile.ZipFile(docx_p, "w") as zout:
            for name, data in files.items():
                zout.writestr(name, data)
    except Exception as e:
        print(f"Error packing DOCX: {e}", file=sys.stderr)


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

    if output_format == "html":
        rendered_html, _ = parse_markdown_to_html(content, title=source.stem, theme=theme, custom_css=custom_css, force_rtl=rtl, for_textutil=False)
        destination.write_text(rendered_html, encoding="utf-8")
        return destination

    if output_format == "pdf":
        rendered_html, _ = parse_markdown_to_html(content, title=source.stem, theme=theme, custom_css=custom_css, force_rtl=rtl, for_textutil=False)
        with tempfile.TemporaryDirectory(prefix="convert-pdf-") as tmp_dir:
            tmp_html = Path(tmp_dir) / f"{source.stem}.html"
            tmp_html.write_text(rendered_html, encoding="utf-8")

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

            if shutil.which("cupsfilter"):
                subprocess.run(f'cupsfilter "{tmp_html}" > "{destination}"', shell=True, check=True)
                return destination

        raise RuntimeError("PDF conversion requires Google Chrome or cupsfilter.")

    if output_format == "docx":
        rendered_html, meta = parse_markdown_to_html(content, title=source.stem, theme=theme, custom_css=custom_css, force_rtl=rtl, for_textutil=True)
        with tempfile.TemporaryDirectory(prefix="convert-docx-") as tmp_dir:
            tmp_html = Path(tmp_dir) / f"{source.stem}.html"
            tmp_html.write_text(rendered_html, encoding="utf-8")
            subprocess.run(["textutil", "-convert", "docx", "-output", str(destination), str(tmp_html)], check=True)
            postprocess_docx_styles(destination, tables=meta["tables"], diagrams=meta["diagrams"], vendor_dir=VENDOR_DIR)
        return destination

    if output_format == "pages":
        has_pages = sys.platform == "darwin" and (os.path.exists("/Applications/Pages.app") or os.path.exists("/Applications/Pages Creator Studio.app"))
        if not has_pages:
            raise RuntimeError("Pages output requires macOS with Apple Pages installed.")
        rendered_html, meta = parse_markdown_to_html(content, title=source.stem, theme=theme, custom_css=custom_css, force_rtl=rtl, for_textutil=True)
        with tempfile.TemporaryDirectory(prefix="convert-pages-") as tmp_dir:
            tmp_html = Path(tmp_dir) / f"{source.stem}.html"
            tmp_html.write_text(rendered_html, encoding="utf-8")
            tmp_docx = Path(tmp_dir) / f"{source.stem}.docx"
            subprocess.run(["textutil", "-convert", "docx", "-output", str(tmp_docx), str(tmp_html)], check=True)
            postprocess_docx_styles(tmp_docx, tables=meta["tables"], diagrams=meta["diagrams"], vendor_dir=VENDOR_DIR)

            if destination.exists():
                if destination.is_dir(): shutil.rmtree(destination)
                else: destination.unlink()

            applescript = f"""
            set docxFile to POSIX file "{tmp_docx}"
            set pagesFile to POSIX file "{destination}"
            tell application "Pages"
                launch
                activate
                delay 2
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
