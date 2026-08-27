---
name: markdown-tools
description: >-
  Comprehensive suite for Markdown processing, multi-target conversion (PDF, HTML, Apple Pages, DOCX),
  custom themes, and layout-preserving translation. Features 9 curated themes (Amil Design Light/Dark,
  Terminal Dark / CLI Slate & Amber, Apple Design Light/Dark, VS Code Dark, GitHub Light, Nord Frost, Editorial Serif),
  native Mermaid diagram rendering (with dark/light contrast), KaTeX math formulas, callout banners, RTL/Persian support,
  and OOXML named paragraph style bindings for Apple Pages and Microsoft Word.
---

# Markdown Tools & Conversion Suite

Unified engine for Markdown processing, formatting, translation, and multi-format compilation on macOS using 100% local tools with **Amil Design**, **Apple Design**, **Terminal/CLI Slate**, and **VS Code Markdown Preview** aesthetics.

> [!IMPORTANT]
> **User Keyword Rule & Theme Prompting**:
> 1. When the user says **"render"** for a Markdown file, it explicitly means **creating a styled PDF from the Markdown file**.
> 2. Whenever the user requests rendering or converting a Markdown file without specifying a theme, **always offer or ask the user for their preferred theme** from the 9 available themes below (with `amil-light` or `terminal-dark` as top options).

---

## 1. The 9 Curated Design Themes

| Theme ID | Mode | Inspiration & Visual Style | Best Use Cases |
|---|---|---|---|
| `amil-light` *(default)* | Light | Soft light-gray canvas (`#eaedf2`), floating white card, royal blue accents (`#2563eb`), macOS window dot code blocks. | Technical docs, reports, modern documentation |
| `amil-dark` | Dark | Obsidian midnight slate (`#0b0f19`), elevated slate card (`#131b2e`), electric cyan/sky accents (`#38bdf8`), neon callouts. | High-tech specs, engineering docs, night reading |
| `terminal-dark` | Dark | CLI Slate & Amber palette (`#10161f` canvas, `#182230` card), electric cyan commands (`#38bdf8`), golden amber keywords (`#f59e0b`), terminal lime status dots. | Developer documentation, terminal guides, CLI logs, architecture specs |
| `apple-light` | Light | Apple HIG Cupertino canvas (`#f5f5f7`), pure white rounded card, SF Pro typography, Apple system blue (`#0071e3`). | Apple-style proposals, executive briefs, clean whitepapers |
| `apple-dark` | Dark | Apple Space Black (`#000000`), elevated dark card (`#1c1c1e`), vibrant Apple blue (`#2997ff`), iOS-style dark alerts. | Apple developer docs, media decks, dark presentations |
| `vscode-dark` | Dark | Authentic VS Code editor theme (`#181818`), `#007acc` blue, high-contrast code blocks, **glowing dark Mermaid graphs & diagrams**. | Code walkthroughs, system architectures, flowchart-heavy docs |
| `github-light` | Light | GitHub Primer canvas (`#f6f8fa`), crisp white card, GitHub blue (`#0969da`), authentic GFM alerts and table styling. | Open-source guides, README exports, GitHub-style docs |
| `nord-frost` | Dark | Arctic Polar Night (`#242933`), Snow Storm text, Frost ice blue (`#88c0d0`), and Aurora green/purple highlights. | Minimalist aesthetic docs, developer guides, calm dark mode |
| `editorial-serif` | Light | Warm ivory bookish paper (`#f7f4ed`), deep espresso ink (`#26211e`), New York serif typography, royal crimson accents (`#9b111e`). | Academic papers, essays, legal texts, literary publishing |

### Theme Aliases
All previous theme names automatically map to the canonical themes:
- `amil-design`, `amil`, `light`, `default` → `amil-light`
- `dark`, `midnight` → `amil-dark`
- `terminal`, `cli`, `cli-dark`, `slate-amber`, `pallet`, `palette` → `terminal-dark`
- `modern`, `apple`, `cupertino`, `apple-design` → `apple-light`
- `space-dark`, `apple-dark-mode` → `apple-dark`
- `vscode`, `markdown-dark`, `vs-dark` → `vscode-dark`
- `github`, `primer` → `github-light`
- `nord`, `arctic` → `nord-frost`
- `classic`, `academic`, `editorial`, `serif`, `new-york` → `editorial-serif`

---

## 2. Multi-Target Markdown Conversion & Named Styles

Converts Markdown documents into **PDF**, **HTML**, **Apple Pages (`.pages`)**, or **Word (`.docx`)**. 
On conversion to Pages or DOCX, an automated OOXML post-processor guarantees that all text runs are bound to native named styles (`Title`, `Heading 1–6`, `Body`, `Block Quote`, `Code`, `Bullet List`, `Numbered List`).

### Global CLI Commands & Shortcuts

Installed in `~/.local/bin`:

| Command | Shortcut Alias | Function |
|---|---|---|
| `forma convert` | `md-to-pages`, `md-to-pdf`, `md-to-html`, `md-to-docx` | Convert Markdown into `.pages`, `.pdf`, `.html`, or `.docx` |
| `md-convert` | `python3 .../markdown_convert.py` | Direct entrypoint to multi-target markdown conversion engine |

```bash
# Render to PDF using Terminal Dark theme (CLI Slate & Amber)
forma convert document.md -f pdf -t terminal-dark

# Convert Markdown to Apple Pages (.pages) with named styles applied
forma convert document.md -f pages -t apple-light

# Render to PDF using VS Code Dark theme (great for diagrams & graphs)
forma convert document.md -f pdf -t vscode-dark

# Convert to HTML with Amil Dark
forma convert document.md -f html -t amil-dark

# Render with RTL for Persian/Arabic documents
forma convert document_fa.md -f pdf -t terminal-dark --rtl
```

---

## 3. Finder Right-Click Quick Action (macOS Services)

Users can right-click any `.md` or `.markdown` file in Finder and select **Quick Actions → Convert Markdown**:
1. **Step 1**: Choose target format (`PDF`, `HTML`, `Apple Pages`, `Microsoft Word`).
2. **Step 2**: Choose from 9 design themes with `Amil Light` pre-selected.
3. System compiles the file and triggers a native macOS notification with audio feedback (`Glass`).

To reinstall or refresh the Quick Action:
```bash
bash ~/.gemini/config/skills/markdown-tools/scripts/install-finder-quick-action.sh
```

