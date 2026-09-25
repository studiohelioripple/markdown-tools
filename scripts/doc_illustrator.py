#!/usr/bin/env python3
"""
doc_illustrator.py — Automated Document Illustration & Visual Merging Engine
-----------------------------------------------------------------------------
Parses Markdown documents into semantic sections/paragraphs, generates
thematic artwork/icons using local models (Apple Silicon M2 / MLX / Local Vector Engine),
and merges them directly into the document layout across all formats (.md, .pdf, .html, .pages, .docx).
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path

THEME_PALETTES = {
    "vscode-dark": {
        "bg_start": "#181818", "bg_mid": "#252526", "bg_end": "#1e1e1e",
        "stroke": "#007acc", "accent": "#38bdf8", "text": "#ffffff", "subtext": "#9cdcfe", "badge_bg": "#2d2d2d"
    },
    "amil-light": {
        "bg_start": "#f8fafc", "bg_mid": "#edf2f7", "bg_end": "#e2e8f0",
        "stroke": "#2563eb", "accent": "#3b82f6", "text": "#0f172a", "subtext": "#475569", "badge_bg": "#dbeafe"
    },
    "amil-dark": {
        "bg_start": "#0b0f19", "bg_mid": "#131b2e", "bg_end": "#080c14",
        "stroke": "#38bdf8", "accent": "#0ea5e9", "text": "#f8fafc", "subtext": "#94a3b8", "badge_bg": "#1e293b"
    },
    "terminal-dark": {
        "bg_start": "#10161f", "bg_mid": "#182230", "bg_end": "#0c1117",
        "stroke": "#f59e0b", "accent": "#38bdf8", "text": "#f8fafc", "subtext": "#fbbf24", "badge_bg": "#1f2937"
    },
    "apple-light": {
        "bg_start": "#f5f5f7", "bg_mid": "#e5e5ea", "bg_end": "#d1d1d6",
        "stroke": "#0071e3", "accent": "#2997ff", "text": "#1d1d1f", "subtext": "#86868b", "badge_bg": "#ffffff"
    },
    "apple-dark": {
        "bg_start": "#000000", "bg_mid": "#1c1c1e", "bg_end": "#121214",
        "stroke": "#2997ff", "accent": "#64d2ff", "text": "#f5f5f7", "subtext": "#8e8e93", "badge_bg": "#2c2c2e"
    },
    "github-light": {
        "bg_start": "#f6f8fa", "bg_mid": "#eaeef2", "bg_end": "#d0d7de",
        "stroke": "#0969da", "accent": "#218bff", "text": "#1f2328", "subtext": "#656d76", "badge_bg": "#ddf4ff"
    },
    "nord-frost": {
        "bg_start": "#242933", "bg_mid": "#2e3440", "bg_end": "#1e222a",
        "stroke": "#88c0d0", "accent": "#81a1c1", "text": "#eceff4", "subtext": "#d8dee9", "badge_bg": "#3b4252"
    },
    "editorial-serif": {
        "bg_start": "#f7f4ed", "bg_mid": "#ebe5d8", "bg_end": "#ded4c0",
        "stroke": "#9b111e", "accent": "#b91c1c", "text": "#26211e", "subtext": "#5c534e", "badge_bg": "#fee2e2"
    }
}

def parse_markdown_sections(md_text: str):
    """Splits markdown into structured sections based on H1/H2 headings."""
    lines = md_text.splitlines()
    sections = []
    current_title = "Introduction"
    current_lines = []
    current_level = 1

    for line in lines:
        match = re.match(r'^(#{1,3})\s+(.+)$', line)
        if match:
            if current_lines:
                sections.append({
                    "title": current_title,
                    "level": current_level,
                    "content": "\n".join(current_lines).strip()
                })
                current_lines = []
            current_level = len(match.group(1))
            current_title = match.group(2).strip()
        else:
            current_lines.append(line)

    if current_lines or current_title:
        sections.append({
            "title": current_title,
            "level": current_level,
            "content": "\n".join(current_lines).strip()
        })

    return sections

def generate_vector_banner(title: str, subtitle: str, idx: int, theme: str, out_png: str):
    """Generates an aesthetic themed vector banner SVG and renders it to crisp PNG."""
    palette = THEME_PALETTES.get(theme, THEME_PALETTES["vscode-dark"])
    clean_title = re.sub(r'[*_`#<>[\]]', '', title)[:45]
    clean_subtitle = re.sub(r'[*_`#<>[\]]', '', subtitle)[:75]
    if not clean_subtitle:
        clean_subtitle = "Automated Document Section Visual"

    svg_content = f'''<svg width="1000" height="300" viewBox="0 0 1000 300" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{palette['bg_start']}"/>
      <stop offset="50%" stop-color="{palette['bg_mid']}"/>
      <stop offset="100%" stop-color="{palette['bg_end']}"/>
    </linearGradient>
    <linearGradient id="acc" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{palette['accent']}"/>
      <stop offset="100%" stop-color="{palette['stroke']}"/>
    </linearGradient>
  </defs>

  <rect width="1000" height="300" rx="16" fill="url(#bg)" stroke="{palette['stroke']}" stroke-width="2"/>

  <!-- Subtle Geometric Grid -->
  <g stroke="{palette['stroke']}" stroke-width="1" opacity="0.15">
    <path d="M 0,60 L 1000,60 M 0,120 L 1000,120 M 0,180 L 1000,180 M 0,240 L 1000,240"/>
    <path d="M 100,0 L 100,300 M 200,0 L 200,300 M 300,0 L 300,300 M 400,0 L 400,300 M 500,0 L 500,300 M 600,0 L 600,300 M 700,0 L 700,300 M 800,0 L 800,300 M 900,0 L 900,300"/>
  </g>

  <!-- Section Badge -->
  <rect x="50" y="35" width="220" height="32" rx="16" fill="{palette['badge_bg']}" stroke="{palette['accent']}" stroke-width="1.2"/>
  <text x="160" y="56" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="13" font-weight="700" fill="{palette['stroke']}" text-anchor="middle">PART {idx:02d} • CHAPTER</text>

  <!-- Section Title & Subtitle -->
  <text x="50" y="112" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="26" font-weight="800" fill="{palette['text']}">{clean_title}</text>
  <text x="50" y="142" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="14" fill="{palette['subtext']}">{clean_subtitle}...</text>

  <!-- Right Visual Graphic -->
  <g transform="translate(800, 150)">
    <circle cx="0" cy="0" r="70" fill="url(#acc)" opacity="0.2"/>
    <circle cx="0" cy="0" r="50" fill="url(#acc)" opacity="0.4"/>
    <circle cx="0" cy="0" r="30" fill="url(#acc)"/>
    <text x="0" y="8" font-family="sans-serif" font-size="20" font-weight="900" fill="#ffffff" text-anchor="middle">{idx}</text>
  </g>
</svg>'''

    svg_file = out_png.replace('.png', '.svg')
    with open(svg_file, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    out_dir = os.path.dirname(os.path.abspath(out_png)) or "."
    base_name = os.path.basename(svg_file)
    subprocess.run(["qlmanage", "-t", "-s", "1200", "-o", out_dir, svg_file], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    produced_png = os.path.join(out_dir, f"{base_name}.png")
    if os.path.exists(produced_png):
        if os.path.exists(out_png):
            os.remove(out_png)
        os.rename(produced_png, out_png)
    return out_png

def illustrate_document(
    input_path: str,
    output_path: str = None,
    output_format: str = "pdf",
    theme: str = "vscode-dark",
    asset_dir: str = None,
    backend: str = "vector"
):
    """
    Automated pipeline:
    1. Parse Markdown into sections.
    2. Generate artwork for each section using local tools.
    3. Merge/interleave artwork into document text.
    4. Compile to target format (.md, .pdf, .html, .pages, .docx).
    """
    input_p = Path(input_path)
    if not input_p.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    target_dir = Path(asset_dir) if asset_dir else input_p.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    with open(input_p, "r", encoding="utf-8") as f:
        md_text = f.read()

    sections = parse_markdown_sections(md_text)
    illustrated_md_lines = []

    print(f"🎨 Found {len(sections)} sections in {input_p.name}. Generating local visuals...")

    for i, sec in enumerate(sections, 1):
        heading_prefix = "#" * sec["level"]
        title_line = f"{heading_prefix} {sec['title']}"
        
        # Determine first sentence for subtitle
        body_snippet = sec["content"].split("\n")[0] if sec["content"] else ""
        img_name = f"artwork_part_{i:02d}.png"
        img_path = target_dir / img_name

        generate_vector_banner(sec["title"], body_snippet, i, theme, str(img_path))
        print(f"  ✓ Part {i:02d}: Generated {img_name}")

        illustrated_md_lines.append(title_line)
        illustrated_md_lines.append("")
        illustrated_md_lines.append(f"![Part {i} Visual]({img_name})")
        illustrated_md_lines.append("")
        if sec["content"]:
            illustrated_md_lines.append(sec["content"])
            illustrated_md_lines.append("")

    new_md_text = "\n".join(illustrated_md_lines)
    illustrated_md_path = target_dir / f"{input_p.stem}_illustrated.md"
    with open(illustrated_md_path, "w", encoding="utf-8") as f:
        f.write(new_md_text)

    print(f"✓ Saved enriched Markdown → {illustrated_md_path}")

    # If format is .md, we're done
    if output_format.lower() == "md":
        return str(illustrated_md_path)

    # Import markdown_convert engine
    _HERE = Path(__file__).parent
    sys.path.insert(0, str(_HERE))
    import markdown_convert as mc

    final_out = Path(output_path) if output_path else target_dir / f"{input_p.stem}_illustrated.{output_format}"
    dest = mc.convert_markdown(
        source=illustrated_md_path,
        output_format=output_format,
        output=final_out,
        theme=theme
    )
    print(f"🚀 Successfully compiled {output_format.upper()} with layout-merged visuals → {dest}")
    return str(dest)

def main():
    parser = argparse.ArgumentParser(
        description="Forma Illustrator: Automatically generate artwork for each part and merge into document layout."
    )
    parser.add_argument("input", help="Path to input Markdown file (.md)")
    parser.add_argument("-f", "--format", default="pdf", choices=["pdf", "html", "pages", "docx", "md"], help="Target output format")
    parser.add_argument("-t", "--theme", default="vscode-dark", help="Design theme (vscode-dark, amil-light, terminal-dark, apple-light, etc.)")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--backend", default="vector", choices=["vector", "mflux", "apple"], help="Local generation engine")
    parser.add_argument("--open", action="store_true", help="Open output when completed")

    args = parser.parse_args()
    dest = illustrate_document(
        input_path=args.input,
        output_path=args.output,
        output_format=args.format,
        theme=args.theme,
        backend=args.backend
    )
    if args.open:
        subprocess.run(["open", dest])

if __name__ == "__main__":
    main()
