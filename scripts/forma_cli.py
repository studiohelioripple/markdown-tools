#!/usr/bin/env python3
"""
forma_cli.py — Unified CLI interface for the Forma Document Protocol
----------------------------------------------------------------------
Forma decouples binary document formats (.pages, .docx) into an Intermediate
Representation pair: {<name>_content.md, <name>_style.yml}.

Commands:
  forma decode      Extract .pages or .docx → {_content.md, _style.yml}
  forma restyle     Apply _style.yml or template document to any document
  forma standardize Standardize a document into pure named styles (stylize)
  forma convert     Convert .md → .pdf, .html, .pages, or .docx with 8 native themes
"""

import sys, os, argparse
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import markdown_convert as mc
try:
    import pages_decode as pd
    import pages_restyle as pr
    import pages_standardize as ps
except ImportError:
    pass

FORMA_LOGO = r"""
  _____                          
 |  ___|o  _ __ _ __ ___   __ _  
 | |_  | |/ '__| '_ ` _ \ / _` | 
 |  _| | | |   | | | | | | (_| | 
 |_|   |_|_|   |_| |_| |_|\__,_| 
     The Dual-State Document Engine
"""

def cmd_decode(args):
    pd.decode_pages(args.input, args.output_dir)
    if args.open:
        base = os.path.splitext(os.path.basename(args.input))[0]
        out_dir = os.path.abspath(args.output_dir) if args.output_dir else os.path.dirname(os.path.abspath(args.input))
        os.system(f'open "{os.path.join(out_dir, f"{base}_content.md")}"')
        os.system(f'open "{os.path.join(out_dir, f"{base}_style.yml")}"')

def cmd_restyle(args):
    pr.restyle(args.input, args.style, args.output, open_result=args.open)

def cmd_standardize(args):
    ps.standardize_document(args.input, args.output, args.style, open_result=args.open)

def cmd_convert(args):
    prog_name = os.path.basename(sys.argv[0])
    target_fmt = args.format
    if not target_fmt:
        if prog_name == 'md-to-pdf': target_fmt = 'pdf'
        elif prog_name == 'md-to-html': target_fmt = 'html'
        elif prog_name == 'md-to-docx': target_fmt = 'docx'
        elif prog_name == 'md-to-pages': target_fmt = 'pages'
        else: target_fmt = 'pdf'

    force_rtl = True if args.rtl else (False if args.ltr else None)
    out_path = Path(args.output) if args.output else None
    dest = mc.convert_markdown(
        Path(args.input),
        output_format=target_fmt,
        output=out_path,
        theme=args.theme,
        custom_css=args.css,
        rtl=force_rtl
    )
    print(f"✓ Created {dest}")
    if args.open:
        os.system(f'open "{dest}"')

def main():
    prog_name = os.path.basename(sys.argv[0])
    alias_map = {
        'pages-to-md': 'decode', 'docx-to-md': 'decode',
        'md-to-pages': 'convert', 'md-to-docx': 'convert', 'md-to-pdf': 'convert', 'md-to-html': 'convert',
        'pages-restyle': 'restyle',
        'pages-standardize': 'standardize', 'docx-standardize': 'standardize', 'stylize': 'standardize'
    }
    if prog_name in alias_map and (len(sys.argv) < 2 or sys.argv[1] not in ('-h', '--help', '-v', '--version')):
        sys.argv.insert(1, alias_map[prog_name])

    parser = argparse.ArgumentParser(
        prog='forma',
        description='Forma Protocol — Separation of Content & Style for .pages, .docx, .pdf, .html, and .md',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Run "forma <command> --help" for command-specific options.'
    )
    parser.add_argument('-v', '--version', action='version', version='Forma Protocol v2.3 (9 Theme Engine)')

    subparsers = parser.add_subparsers(dest='command', help='Forma commands')

    # decode
    p_dec = subparsers.add_parser('decode', help='Extract document → {_content.md, _style.yml}', aliases=['pages-to-md', 'docx-to-md'])
    p_dec.add_argument('input', help='Path to .pages or .docx file')
    p_dec.add_argument('-o', '--output-dir', help='Output directory for IR pair')
    p_dec.add_argument('--open', action='store_true', help='Open IR files when done')

    # restyle
    p_res = subparsers.add_parser('restyle', help='Apply style sheet or template to document')
    p_res.add_argument('input', help='Content source (.md, .pages, .docx)')
    p_res.add_argument('--style', required=True, help='Style source (_style.yml, .pages, .docx)')
    p_res.add_argument('-o', '--output', required=True, help='Output document path (.pages or .docx)')
    p_res.add_argument('--open', action='store_true', help='Open output when done')

    # standardize / stylize
    p_std = subparsers.add_parser('standardize', help='Audit & standardize document into pure named styles', aliases=['stylize', 'pages-standardize', 'docx-standardize'])
    p_std.add_argument('input', help='Input document (.pages, .docx, .md)')
    p_std.add_argument('-o', '--output', help='Output document path (.pages or .docx)')
    p_std.add_argument('--style', help='Optional template style sheet')
    p_std.add_argument('--open', action='store_true', help='Open output when done')

    # convert
    p_cnv = subparsers.add_parser('convert', help='Convert Markdown → .pdf, .html, .pages, or .docx', aliases=['md-to-pages', 'md-to-docx', 'md-to-pdf', 'md-to-html'])
    p_cnv.add_argument('input', help='Markdown file (.md)')
    p_cnv.add_argument('-o', '--output', help='Output path (.pdf, .html, .pages, or .docx)')
    p_cnv.add_argument('-f', '--format', choices=['pdf', 'html', 'pages', 'docx'], help='Target format (default: pdf)')
    p_cnv.add_argument(
        '-t', '--theme',
        default='amil-light',
        help='Theme name: "amil-light", "amil-dark", "terminal-dark", "apple-light", "apple-dark", "vscode-dark", "github-light", "nord-frost", "editorial-serif" (or custom CSS file path)'
    )
    p_cnv.add_argument('--css', default='', help='Custom CSS overrides')
    p_cnv.add_argument('--rtl', action='store_true', default=None, help='Force Right-to-Left (RTL) mode')
    p_cnv.add_argument('--ltr', action='store_true', help='Force Left-to-Right (LTR) mode')
    p_cnv.add_argument('--open', action='store_true', help='Open output when done')

    args = parser.parse_args()

    if not args.command:
        print(FORMA_LOGO)
        parser.print_help()
        sys.exit(0)

    cmd_map = {
        'decode': cmd_decode, 'pages-to-md': cmd_decode, 'docx-to-md': cmd_decode,
        'restyle': cmd_restyle,
        'standardize': cmd_standardize, 'stylize': cmd_standardize, 'pages-standardize': cmd_standardize, 'docx-standardize': cmd_standardize,
        'convert': cmd_convert, 'md-to-pages': cmd_convert, 'md-to-docx': cmd_convert, 'md-to-pdf': cmd_convert, 'md-to-html': cmd_convert,
    }

    fn = cmd_map.get(args.command)
    if fn:
        try:
            fn(args)
        except Exception as e:
            print(f'Error: {e}', file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    main()
