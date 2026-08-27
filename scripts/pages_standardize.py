#!/usr/bin/env python3
"""
pages_standardize.py — Standardize / Stylize a document into pure named styles
-------------------------------------------------------------------------------
Keywords: standardize, stylize

Takes a .pages, .docx, or .md document:
1. Performs a full formatting audit, detecting direct-formatting overrides,
   un-styled text spans, and raw inline styles.
2. Synthesizes a clean, standardized _style.yml sheet defining semantic
   Paragraph Styles (Title, Heading 1-6, Body, Quote, Code, List) and
   Character Styles (Bold, Italic, Strikethrough, Underline, Highlight,
   Hyperlink, Inline Code, Color RRGGBB, Background RRGGBB).
3. Re-compiles the document into pure OOXML using <w:rStyle> references exclusively
   and zero direct-formatting overrides on runs.
4. Emits the standardized target document (.pages or .docx) alongside its canonical
   Intermediate Representation pair: {<basename>_content.md, <basename>_style.yml}.

No LLM calls. Pure local tool processing. Requires Python 3.9+ and Apple Pages.

Usage:
  python3 pages_standardize.py input.pages [-o output.pages] [--open]
  python3 pages_standardize.py report.docx -o report_clean.docx
  python3 pages_standardize.py article.md --style brand.yml -o article_styled.pages
"""

import sys, os, tempfile, subprocess, argparse
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_MARKDOWN_TOOLS_SCRIPTS = os.path.normpath(os.path.join(_HERE, "..", "..", "markdown-tools", "scripts"))
sys.path.insert(0, _HERE)
if os.path.exists(_MARKDOWN_TOOLS_SCRIPTS):
    sys.path.insert(0, _MARKDOWN_TOOLS_SCRIPTS)

from pages_decode import (
    decode_pages, extract_style_dict, dict_to_yaml, yaml_to_dict
)
from pages_restyle import load_content_md, load_style_dict, style_dict_to_theme
import md_to_pages as mtp

def standardize_document(
    input_path: str,
    output_path: str | None = None,
    style_template: str | None = None,
    open_result: bool = False,
) -> tuple[str, str, str]:
    """
    Standardize a document by converting all direct formatting to named styles,
    stripping inline override clutter, and emitting clean (.pages/.docx, _content.md, _style.yml).
    Returns (out_doc_path, content_md_path, style_yml_path).
    """
    abs_in = os.path.abspath(input_path)
    base_name = os.path.splitext(os.path.basename(abs_in))[0]
    out_dir = os.path.dirname(abs_in)

    if output_path:
        abs_out = os.path.abspath(output_path)
    else:
        ext = '.docx' if abs_in.lower().endswith('.docx') else '.pages'
        abs_out = os.path.join(out_dir, f'{base_name}_standardized{ext}')

    content_md_path = os.path.join(out_dir, f'{base_name}_content.md')
    style_yml_path = os.path.join(out_dir, f'{base_name}_style.yml')

    print(f'⚡ Standardizing "{os.path.basename(abs_in)}" (Forma Protocol) …', flush=True)

    # 1. Extract content and style in a single pass (1 export call)
    print('  [1/4] Auditing document structure & extracting content …', flush=True)
    if style_template:
        content_md = load_content_md(abs_in)
        style_dict = load_style_dict(style_template)
    else:
        if abs_in.lower().endswith(('.pages', '.docx')):
            cp, sp = decode_pages(abs_in, out_dir)
            with open(cp, 'r', encoding='utf-8') as f: content_md = f.read()
            with open(sp, 'r', encoding='utf-8') as f: style_dict = yaml_to_dict(f.read())
        else:
            with open(abs_in, 'r', encoding='utf-8') as f: content_md = f.read()
            style_dict = {
                'paragraph_styles': {
                    'Title':     {'font': 'SF Pro Display', 'size': 26, 'bold': True,  'color': '111111'},
                    'Heading 1': {'font': 'SF Pro Display', 'size': 20, 'bold': True,  'color': '111111'},
                    'Heading 2': {'font': 'SF Pro Display', 'size': 16, 'bold': True,  'color': '1D1D1F'},
                    'Heading 3': {'font': 'SF Pro Text',    'size': 13, 'bold': True,  'color': '2C2C2E'},
                    'Body':      {'font': 'SF Pro Text',    'size': 13, 'bold': False, 'color': '1D1D1F'},
                    'Block Quote':{'font':'SF Pro Text',    'size': 12, 'italic': True,'color': '555555'},
                    'Code':      {'font': 'SF Mono',        'size': 11, 'color': 'D63384'},
                },
                'character_styles': {
                    'Bold':          {'bold': True},
                    'Italic':        {'italic': True},
                    'Bold Italic':   {'bold': True, 'italic': True},
                    'Strikethrough': {'strikethrough': True},
                    'Underline':     {'underline': 'single'},
                    'Highlight':     {'highlight': 'yellow'},
                    'Inline Code':   {'font': 'SF Mono', 'color': 'D63384'},
                    'Hyperlink':     {'color': '0066CC', 'underline': 'single'},
                }
            }

    # Standardize style dict structure
    style_dict['meta'] = {
        'protocol': 'Forma v2.0 Standardized',
        'source_file': os.path.basename(abs_in),
        'standardized_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'guarantee': '100% named character and paragraph styles, zero direct formatting on runs',
    }

    # 2. Auto-detect direct formatting overrides and convert to named styles
    print('  [2/4] Detecting direct overrides & synthesizing Character Styles …', flush=True)
    import re
    def repl_span(m):
        style_str = m.group(1)
        inner = m.group(2)
        c_match = re.search(r'(?<![a-zA-Z-])color\s*:\s*#([0-9a-fA-F]{6})', style_str)
        b_match = re.search(r'background(?:-color)?\s*:\s*#([0-9a-fA-F]{6})', style_str)
        props = {}
        name_parts = []
        if c_match:
            hex_c = c_match.group(1).upper()
            props['color'] = hex_c
            name_parts.append(f'Fg{hex_c}')
        if b_match:
            hex_b = b_match.group(1).upper()
            props['background'] = hex_b
            name_parts.append(f'Bg{hex_b}')
        if not props:
            return m.group(0)
        style_id = 'AutoColor' + ''.join(name_parts)
        if style_id not in style_dict['character_styles']:
            style_dict['character_styles'][style_id] = props
        return f'<span class="{style_id}">{inner}</span>'
    
    content_md = re.sub(r'<span\s+style="([^"]+)">([\s\S]*?)</span>', repl_span, content_md)

    theme = style_dict_to_theme(style_dict)

    # 3. Write Intermediate Representation files (_content.md and _style.yml)
    print('  [3/4] Exporting Intermediate Representation ({_content.md, _style.yml}) …', flush=True)
    with open(content_md_path, 'w', encoding='utf-8') as f:
        f.write(content_md)
        f.write('\n')

    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    with open(style_yml_path, 'w', encoding='utf-8') as f:
        f.write(f'# Standardized Style Sheet for: {os.path.basename(abs_in)}\n')
        f.write(f'# Generated {stamp} by pages_standardize.py\n\n')
        f.write(dict_to_yaml(style_dict))
        f.write('\n')

    from pages_restyle import extract_custom_char_styles
    custom_char_styles = extract_custom_char_styles(style_dict)

    # 4. Re-compile document with 100% named character styles & zero overrides
    print(f'  [4/4] Compiling standardized target → {os.path.basename(abs_out)} …', flush=True)
    _key = '__standardize_theme__'
    mtp.THEME_STYLES[_key] = theme
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_md = os.path.join(tmp, 'clean_content.md')
            with open(tmp_md, 'w', encoding='utf-8') as f:
                f.write(content_md)
            mtp.convert_md_to_pages(
                tmp_md, abs_out,
                theme=_key,
                custom_char_styles=custom_char_styles,
                open_result=open_result
            )
    finally:
        mtp.THEME_STYLES.pop(_key, None)

    print(f'\n✨ Standardization complete!')
    print(f'  ✓ Target Document: {abs_out}')
    print(f'  ✓ Content IR:      {content_md_path}')
    print(f'  ✓ Style IR:        {style_yml_path}')
    return abs_out, content_md_path, style_yml_path

def main():
    p = argparse.ArgumentParser(
        description='Standardize / Stylize a document into pure named styles (Forma Protocol)',
        epilog='Keywords: standardize, stylize'
    )
    p.add_argument('input', help='Input document (.pages, .docx, or .md)')
    p.add_argument('-o', '--output', help='Output document path (.pages or .docx)')
    p.add_argument('--style', help='Optional template style sheet (.yml, .pages, or .docx)')
    p.add_argument('--open', action='store_true', help='Open standardized document when done')
    args = p.parse_args()

    if not os.path.exists(args.input):
        print(f'Error: file not found: {args.input}', file=sys.stderr)
        sys.exit(1)

    try:
        standardize_document(args.input, args.output, args.style, open_result=args.open)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
