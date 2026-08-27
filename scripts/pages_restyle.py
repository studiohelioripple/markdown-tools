#!/usr/bin/env python3
"""
pages_restyle.py — Apply a style sheet to an Apple Pages or Markdown document
-----------------------------------------------------------------------------
Transfers paragraph and character styles from a style source to a target document.
No LLM calls. No third-party packages. Requires Python 3.9+, Apple Pages.

Style source can be:
  • A  _style.yml  file produced by pages_decode.py
  • Any  .pages  file (its styles are extracted automatically)

Content source can be:
  • A  .md  Markdown file
  • A  .pages  file (content is extracted as Markdown automatically)

Usage:
  python3 pages_restyle.py input.pages --style template_style.yml -o output.pages
  python3 pages_restyle.py input.pages --style template.pages      -o output.pages
  python3 pages_restyle.py notes.md    --style brand_style.yml     -o notes.pages
  python3 pages_restyle.py report.md   --style corporate.pages     -o report.pages --open
"""

import sys, os, tempfile, subprocess, argparse

# ── Resolve script directory so sibling scripts can be imported from anywhere ─
_HERE = os.path.dirname(os.path.abspath(__file__))
_MARKDOWN_TOOLS_SCRIPTS = os.path.normpath(os.path.join(_HERE, "..", "..", "markdown-tools", "scripts"))
sys.path.insert(0, _HERE)
if os.path.exists(_MARKDOWN_TOOLS_SCRIPTS):
    sys.path.insert(0, _MARKDOWN_TOOLS_SCRIPTS)

from pages_decode import (
    export_pages_to_docx,
    extract_markdown,
    extract_style_dict,
    yaml_to_dict,
)
import md_to_pages as mtp

# ── Load style from .yml or .pages ───────────────────────────────────────────

def load_style_dict(source: str) -> dict:
    """
    Return a style dict from a _style.yml file, .docx file, or .pages file.
    """
    ext = os.path.splitext(source)[1].lower()
    if ext in ('.yml', '.yaml'):
        with open(source, 'r', encoding='utf-8') as f:
            return yaml_to_dict(f.read())
    elif ext == '.docx':
        return extract_style_dict(os.path.abspath(source))
    elif ext == '.pages':
        with tempfile.TemporaryDirectory() as tmp:
            tmp_docx = os.path.join(tmp, 'style_src.docx')
            print(f'Exporting style source "{os.path.basename(source)}" → DOCX …', flush=True)
            export_pages_to_docx(os.path.abspath(source), tmp_docx)
            return extract_style_dict(tmp_docx)
    else:
        raise ValueError(f'Unsupported style source: {source!r}. Use .yml, .yaml, .docx, or .pages')

# ── Load content as Markdown string ──────────────────────────────────────────

def load_content_md(source: str) -> str:
    """
    Return document content as Markdown text.
    .md files are read directly; .docx / .pages files are parsed.
    """
    ext = os.path.splitext(source)[1].lower()
    if ext == '.md':
        with open(source, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == '.docx':
        return extract_markdown(os.path.abspath(source))
    elif ext == '.pages':
        with tempfile.TemporaryDirectory() as tmp:
            tmp_docx = os.path.join(tmp, 'content_src.docx')
            print(f'Exporting content source "{os.path.basename(source)}" → DOCX …', flush=True)
            export_pages_to_docx(os.path.abspath(source), tmp_docx)
            return extract_markdown(tmp_docx)
    else:
        raise ValueError(f'Unsupported content source: {source!r}. Use .md, .docx, or .pages')

# ── Convert style dict → DocxBuilder-compatible theme ────────────────────────

def style_dict_to_theme(sd: dict) -> dict:
    """
    Map a _style.yml dict → the THEME_STYLES dict format used by DocxBuilder.

    THEME_STYLES stores font sizes as half-point strings ("52").
    _style.yml stores them as integer points (26).
    This function converts between the two.
    """
    para = sd.get('paragraph_styles', {})

    def lookup(*names) -> dict:
        for n in names:
            if n in para:
                return para[n]
        return {}

    def to_entry(props: dict) -> dict:
        pts = props.get('size', 12)
        return {
            'font':   props.get('font', 'Helvetica Neue'),
            'size':   str(int(pts) * 2),          # points → half-points string
            'bold':   props.get('bold', False),
            'italic': props.get('italic', False),
            'color':  str(props.get('color', '1D1D1F')).upper(),
        }

    body_props = lookup('Body', 'Normal', 'Body Text', 'Default')

    def le(*primary_names):
        p = lookup(*primary_names)
        return to_entry(p if p else body_props)

    return {
        'title': le('Title'),
        'h1':    le('Heading 1', 'Heading', 'Heading1'),
        'h2':    le('Heading 2', 'Heading2'),
        'h3':    le('Heading 3', 'Heading3'),
        'h4':    le('Heading 4', 'Heading4'),
        'h5':    le('Heading 5', 'Heading5'),
        'h6':    le('Heading 6', 'Heading6'),
        'body':  to_entry(body_props),
        'quote': le('Block Quote', 'Quote', 'Quotation'),
        'code':  le('Code', 'Code Block', 'CodeBlock', 'Preformatted', 'Source Code'),
        'list':  le('Bullet List', 'List Bullet', 'ListBullet', 'Numbered List'),
    }

def extract_custom_char_styles(sd: dict) -> dict:
    """Extract custom character style definitions for DocxBuilder."""
    char_dict = sd.get('character_styles', {})
    res = {}
    for name, props in char_dict.items():
        if name in ('Default Paragraph Font', 'Hyperlink', 'Link'):
            continue
        style_id = name.replace(' ', '')
        rpr_parts = []
        if props.get('font'):
            f = props['font']
            rpr_parts.append(f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}"/>')
        if props.get('size'):
            sz = int(props['size']) * 2
            rpr_parts.append(f'<w:sz w:val="{sz}"/>')
        if props.get('bold'):
            rpr_parts.append('<w:b/><w:bCs/>')
        if props.get('italic'):
            rpr_parts.append('<w:i/><w:iCs/>')
        if props.get('strikethrough'):
            rpr_parts.append('<w:strike/>')
        if props.get('underline'):
            u = props['underline'] if isinstance(props['underline'], str) else 'single'
            rpr_parts.append(f'<w:u w:val="{u}"/>')
        if props.get('highlight'):
            hl = props['highlight'] if isinstance(props['highlight'], str) else 'yellow'
            rpr_parts.append(f'<w:highlight w:val="{hl}"/>')
        if props.get('color'):
            hex_val = str(props['color']).lstrip('#').upper()
            rpr_parts.append(f'<w:color w:val="{hex_val}"/>')
        if props.get('background'):
            hex_val = str(props['background']).lstrip('#').upper()
            rpr_parts.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{hex_val}"/>')

        res[style_id] = {
            "name": name,
            "rPr": "".join(rpr_parts)
        }
    return res

# ── Apply style + convert ─────────────────────────────────────────────────────

def restyle(
    input_path:   str,
    style_source: str,
    output_path:  str,
    open_result:  bool = False,
) -> str:
    """
    Apply the styles from style_source to the content in input_path
    and produce a native .pages file at output_path.
    """
    abs_input  = os.path.abspath(input_path)
    abs_output = os.path.abspath(output_path)
    abs_style  = os.path.abspath(style_source)

    print(f'Loading style from  "{os.path.basename(abs_style)}" …', flush=True)
    sd    = load_style_dict(abs_style)
    theme = style_dict_to_theme(sd)
    custom_char_styles = extract_custom_char_styles(sd)

    print(f'Loading content from "{os.path.basename(abs_input)}" …', flush=True)
    md_content = load_content_md(abs_input)

    # Inject the custom theme into mtp.THEME_STYLES under a temporary key
    # so convert_md_to_pages can use it without modifying the source.
    _key = '__restyle_custom__'
    mtp.THEME_STYLES[_key] = theme
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_md = os.path.join(tmp, 'content.md')
            with open(tmp_md, 'w', encoding='utf-8') as f:
                f.write(md_content)
            mtp.convert_md_to_pages(
                tmp_md, abs_output,
                theme=_key,
                custom_char_styles=custom_char_styles,
                open_result=open_result,
            )
    finally:
        mtp.THEME_STYLES.pop(_key, None)

    print(f'✓  Output → {abs_output}')
    return abs_output

# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description=(
            'Apply paragraph & character styles from a .yml or .pages template\n'
            'to a .pages or .md document and produce a new .pages file.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  python3 pages_restyle.py report.pages --style brand.yml -o report_branded.pages\n'
            '  python3 pages_restyle.py notes.md     --style template.pages -o notes.pages\n'
        ),
    )
    p.add_argument('input',
                   help='Content source document (.pages or .md)')
    p.add_argument('--style', required=True,
                   help='Style source: a _style.yml file or a .pages template document')
    p.add_argument('-o', '--output', required=True,
                   help='Output .pages file path')
    p.add_argument('--open', action='store_true',
                   help='Open the result in Pages when done')
    args = p.parse_args()

    for f in (args.input, args.style):
        if not os.path.exists(f):
            print(f'Error: not found: {f}', file=sys.stderr)
            sys.exit(1)

    try:
        restyle(args.input, args.style, args.output, open_result=args.open)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
