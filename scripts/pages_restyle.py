#!/usr/bin/env python3
"""
pages_restyle.py — Apply a style sheet to an Apple Pages or Markdown document
-----------------------------------------------------------------------------
Transfers paragraph and character styles from a style source to a target document.
"""

import sys, os, tempfile, subprocess, argparse
from pathlib import Path

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
import markdown_convert as mc

def load_style_dict(source: str) -> dict:
    ext = os.path.splitext(source)[1].lower()
    if ext in ('.yml', '.yaml'):
        with open(source, 'r', encoding='utf-8') as f:
            return yaml_to_dict(f.read())
    elif ext == '.docx':
        return extract_style_dict(os.path.abspath(source))
    elif ext == '.pages':
        with tempfile.TemporaryDirectory() as tmp:
            tmp_docx = os.path.join(tmp, 'style_src.docx')
            export_pages_to_docx(os.path.abspath(source), tmp_docx)
            return extract_style_dict(tmp_docx)
    else:
        raise ValueError(f'Unsupported style source: {source!r}. Use .yml, .yaml, .docx, or .pages')

def load_content_md(source: str) -> str:
    ext = os.path.splitext(source)[1].lower()
    if ext == '.md':
        with open(source, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == '.docx':
        return extract_markdown(os.path.abspath(source))
    elif ext == '.pages':
        with tempfile.TemporaryDirectory() as tmp:
            tmp_docx = os.path.join(tmp, 'content_src.docx')
            export_pages_to_docx(os.path.abspath(source), tmp_docx)
            return extract_markdown(tmp_docx)
    else:
        raise ValueError(f'Unsupported content source: {source!r}. Use .md, .docx, or .pages')

def restyle(
    input_path:   str,
    style_source: str,
    output_path:  str,
    open_result:  bool = False,
) -> str:
    abs_input  = os.path.abspath(input_path)
    abs_output = os.path.abspath(output_path)
    abs_style  = os.path.abspath(style_source)

    print(f'Loading style from  "{os.path.basename(abs_style)}" …', flush=True)
    sd = load_style_dict(abs_style)

    print(f'Loading content from "{os.path.basename(abs_input)}" …', flush=True)
    md_content = load_content_md(abs_input)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_md = os.path.join(tmp, 'content.md')
        with open(tmp_md, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        mc.convert_markdown(
            source=Path(tmp_md),
            output_format='pages',
            output=Path(abs_output),
        )
        if open_result:
            subprocess.run(['open', abs_output])

    print(f'✓  Output → {abs_output}')
    return abs_output

def main():
    p = argparse.ArgumentParser(
        description='Apply paragraph & character styles from a .yml or .pages template to a .pages or .md document.'
    )
    p.add_argument('input', help='Content source document (.pages or .md)')
    p.add_argument('--style', required=True, help='Style source: a _style.yml file or a .pages template document')
    p.add_argument('-o', '--output', required=True, help='Output .pages file path')
    p.add_argument('--open', action='store_true', help='Open the result in Pages when done')
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
