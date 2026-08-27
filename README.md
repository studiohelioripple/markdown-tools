# Markdown Tools & Dual-State Conversion Engine (`forma`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)](https://apple.com)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://python.org)

A comprehensive suite and agent skill for Markdown processing, multi-target compilation (PDF, HTML, Apple Pages, Microsoft Word), and native visual rendering on macOS. Includes **9 curated design themes**, native **Mermaid** diagram processing, **KaTeX** math formulas, GFM **callout banners**, and macOS **Finder Quick Actions**.

---

## 🎨 9 Curated Design Themes

| Theme ID | Aesthetic / Inspiration | Best Use Cases |
| :--- | :--- | :--- |
| `apple-light` | Apple HIG Cupertino canvas (`#f5f5f7`), white card, SF Pro typography, light gray code blocks (`#f2f2f7`). | Executive briefs, proposals, whitepapers |
| `amil-light` *(default)* | Soft light-gray canvas (`#eaedf2`), royal blue accents (`#2563eb`), macOS window card style. | Technical documentation, user manuals |
| `amil-dark` | Midnight obsidian slate (`#0b0f19`), electric cyan/sky accents (`#38bdf8`), neon alerts. | Dark mode technical specs, engineering docs |
| `terminal-dark` | CLI Slate & Amber palette (`#10161f`), electric cyan commands (`#38bdf8`), golden amber keywords (`#f59e0b`). | Terminal guides, CLI logs, developer notes |
| `vscode-dark` | Authentic VS Code dark editor style (`#181818`), high-contrast syntax, glowing Mermaid graphs. | Code walkthroughs, system architecture diagrams |
| `apple-dark` | Apple Space Black (`#000000`), dark card (`#1c1c1e`), vibrant Apple blue accents. | Dark presentations, developer specifications |
| `github-light` | GitHub Primer light canvas (`#f6f8fa`), GitHub blue (`#0969da`), GFM alert cards. | Open-source guides, GFM README exports |
| `nord-frost` | Arctic Polar Night (`#242933`), Snow Storm text, Frost ice blue (`#88c0d0`), Aurora highlights. | Minimalist dark documentation |
| `editorial-serif` | Warm ivory bookish paper (`#f7f4ed`), deep espresso ink (`#26211e`), New York serif typography. | Academic papers, essays, legal texts |

---

## ✨ Features

- 📄 **Multi-Target Conversion**: Convert Markdown into styled **PDF**, **HTML**, **Apple Pages (`.pages`)**, or **Word (`.docx`)**.
- 📊 **Native Mermaid Diagrams**: Render flowcharts, sequence diagrams, and architecture graphs in dark or light mode.
- 📐 **KaTeX Mathematical Equations**: Full rendering for both inline ($\alpha = 0.05$) and block math equations.
- 💡 **GFM Callout Banners**: Full support for `> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, and `> [!CAUTION]`.
- 🖥️ **macOS Finder Quick Actions**: Right-click any `.md` file in Finder to convert with interactive theme selection and sound notification.
- 🤖 **Agentic Skill Integration**: Equipped with `SKILL.md` for seamless integration into Antigravity and AI coding agents.

---

## 🛠️ Quick Installation

### Option 1: Install CLI Tools (`forma` and `md-convert`)

Clone this repository and run the installation script:

```bash
git clone https://github.com/studiohelioripple/markdown-tools.git ~/.gemini/config/skills/markdown-tools
bash ~/.gemini/config/skills/markdown-tools/scripts/install-markdown-converter.sh
```

Make sure `~/.local/bin` is in your `PATH`.

### Option 2: Install Finder Quick Action (macOS Services)

Enable right-click Markdown conversion directly inside macOS Finder:

```bash
bash ~/.gemini/config/skills/markdown-tools/scripts/install-finder-quick-action.sh
```

After running the script, right-click any `.md` file in Finder → **Quick Actions** → **Convert Markdown**.

---

## 🚀 CLI Usage Examples

### Render Markdown to PDF

```bash
# Render to PDF with Apple Light theme
forma convert document.md -f pdf -t apple-light

# Render to PDF with Terminal Dark theme
forma convert document.md -f pdf -t terminal-dark
```

### Convert to HTML or Word

```bash
# Convert to standalone HTML with VS Code Dark theme
forma convert document.md -f html -t vscode-dark

# Convert to Apple Pages
forma convert document.md -f pages -t amil-light
```

---

## 🤖 Installing as an Antigravity Agent Skill

To use this skill across multiple devices in Antigravity or Gemini AI Agent workflows:

1. Clone the repository into your skills directory:
   ```bash
   git clone https://github.com/studiohelioripple/markdown-tools.git ~/.gemini/config/skills/markdown-tools
   ```
2. The agent will automatically discover `markdown-tools` and `SKILL.md` when invoked.

---

## 📜 License

[MIT License](LICENSE) © studiohelioripple
