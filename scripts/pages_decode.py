#!/usr/bin/env python3
from __future__ import annotations
"""
pages_decode.py — Extract content + styles from an Apple Pages file
-------------------------------------------------------------------
Exports .pages → .docx via Apple Pages AppleScript, then parses the
resulting OOXML XML (entirely locally, no LLM, no pip packages) to produce:

  <name>_content.md   — document content as Markdown with inline style syntax
  <name>_style.yml    — all paragraph and character styles as human-readable YAML

Requires: Python 3.9+  ·  macOS  ·  Apple Pages (free, /Applications/Pages.app)

Usage:
  python3 pages_decode.py input.pages [-o output_dir] [--open]
"""

import sys, os, re, zipfile, tempfile, subprocess, argparse
from datetime import datetime
from xml.etree import ElementTree as ET

# ── OOXML namespace ───────────────────────────────────────────────────────────
WNS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def _w(name):               return f'{{{WNS}}}{name}'
def _wa(elem, attr, d=''):  return elem.get(f'{{{WNS}}}{attr}', d)

# ── Paragraph style ID / name → Markdown prefix ──────────────────────────────
# Pages uses its own style IDs on DOCX export — map every known variant.
PARA_PREFIX = {
    'Normal': '', 'Default': '', 'Body': '', 'Body Text': '',
    'Title':        '# ',
    'Heading':      '# ',   'Heading 1': '# ',  'Heading1': '# ',
    'Heading 2':    '## ',  'Heading2':  '## ',
    'Heading 3':    '### ', 'Heading3':  '### ',
    'Heading 4':    '#### ','Heading4':  '#### ',
    'Heading 5':    '#####','Heading5':  '#####',
    'Heading 6':    '######','Heading6': '######',
    'Quote':        '> ', 'Block Quote': '> ', 'BlockQuote': '> ', 'Quotation': '> ',
    'Bullet List':  '- ', 'BulletList':  '- ', 'ListBullet':  '- ', 'List Bullet':  '- ',
    'Numbered List':'1. ','NumberedList':'1. ','ListNumber':  '1. ','List Number':  '1. ',
}
CODE_STYLES = {'Code', 'Code Block', 'CodeBlock', 'Preformatted', 'Source Code', 'Verbatim'}

# ── Minimal YAML serializer / deserializer (stdlib only) ─────────────────────

def _yaml_key(k: str) -> str:
    k = str(k)
    if any(c in k for c in ':#{}[]|>&!@,') or (k and k[0].isdigit()):
        return f'"{k}"'
    return k

def _yaml_val(v) -> str:
    if isinstance(v, bool):         return 'true' if v else 'false'
    if v is None:                   return 'null'
    if isinstance(v, (int, float)): return str(v)
    s = str(v)
    if any(c in s for c in ':#{}[]|>&!') or s.lower() in ('true','false','null','yes','no'):
        return f'"{s}"'
    return s

def dict_to_yaml(data: dict, indent: int = 0) -> str:
    """Recursively serialize a nested dict to YAML text (no lists)."""
    lines = []
    pad = '  ' * indent
    for k, v in data.items():
        key = _yaml_key(k)
        if isinstance(v, dict):
            if v:
                lines.append(f'{pad}{key}:')
                lines.append(dict_to_yaml(v, indent + 1))
            else:
                lines.append(f'{pad}{key}: {{}}')
        else:
            lines.append(f'{pad}{key}: {_yaml_val(v)}')
    return '\n'.join(lines)

def yaml_to_dict(text: str) -> dict:
    """Parse our limited YAML subset (nested dicts, scalar values, no lists)."""
    root: dict = {}
    stack: list = [(-1, root)]
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(stripped)
        if ':' not in stripped:
            continue
        ci  = stripped.index(':')
        key = stripped[:ci].strip().strip('"\'')
        val = stripped[ci + 1:].strip()
        while len(stack) > 1 and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if not val:
            nd: dict = {}
            parent[key] = nd
            stack.append((indent, nd))
        else:
            parent[key] = _scalar(val)
    return root

def _scalar(s: str):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'): return s[1:-1]
    if s.startswith("'") and s.endswith("'"): return s[1:-1]
    if s.lower() == 'true':  return True
    if s.lower() == 'false': return False
    if s.lower() == 'null':  return None
    try:    return int(s)
    except: pass
    try:    return float(s)
    except: pass
    return s

# ── AppleScript: .pages → .docx ──────────────────────────────────────────────

def export_pages_to_docx(pages_path: str, docx_path: str) -> None:
    """Export a .pages bundle to DOCX via Apple Pages (AppleScript)."""
    # Pages AppleScript export format constant is 'Microsoft Word' (code Pwrd).
    script = f"""
    tell application "Pages"
        activate
        delay 1
        set doc to open POSIX file "{pages_path}"
        delay 1
        set outF to POSIX file "{docx_path}"
        export doc to outF as Microsoft Word
        close doc saving no
    end tell
    """
    import time
    time.sleep(2)
    r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    time.sleep(2)
    if r.returncode != 0:
        raise RuntimeError(f'Pages export failed:\n{r.stderr.strip()}')
    if not os.path.exists(docx_path):
        raise RuntimeError(f'Pages produced no output at {docx_path}')

# ── Parse word/styles.xml → structured style dict ────────────────────────────

def _clean_font(name: str) -> str:
    """Strip weight/style suffixes that Pages appends to PostScript font names."""
    for suffix in (' Regular', ' Bold', ' Italic', ' Light', ' Medium',
                   ' BoldItalic', ' Semibold', ' Heavy', ' Thin', ' Condensed',
                   ' ExtraLight', ' Black', ' UltraLight', ' Display'):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name

def _rpr_to_dict(rPr) -> dict:
    """Extract style properties from a <w:rPr> element.

    Pages exports OOXML where every boolean attribute has an explicit val=
    attribute: val="0" means disabled, val="1" or absent means enabled.
    A bare <w:b/> with no val is also treated as enabled (standard OOXML).
    """
    if rPr is None:
        return {}
    props: dict = {}

    fonts = rPr.find(_w('rFonts'))
    if fonts is not None:
        f = _wa(fonts, 'ascii') or _wa(fonts, 'hAnsi')
        if f: props['font'] = _clean_font(f)

    sz = rPr.find(_w('sz'))
    if sz is not None:
        v = _wa(sz, 'val')
        if v: props['size'] = int(v) // 2      # half-points → points

    # Pages emits explicit val="0" on ALL boolean attributes to disable them.
    # val="0" → disabled;  val absent, "1", or "true" → enabled.
    def _flag(tag_name) -> bool:
        el = rPr.find(_w(tag_name))
        if el is None: return False
        v = _wa(el, 'val', '')
        return v != '0'     # absent or any value other than "0" = enabled

    if _flag('b'):                       props['bold']          = True
    if _flag('i'):                       props['italic']        = True
    if _flag('strike') or _flag('dstrike'): props['strikethrough'] = True

    u = rPr.find(_w('u'))
    if u is not None:
        uv = _wa(u, 'val')
        if uv and uv not in ('none', ''):
            props['underline'] = uv

    hl = rPr.find(_w('highlight'))
    if hl is not None:
        hv = _wa(hl, 'val', '')
        if hv and hv != 'none': props['highlight'] = hv

    color = rPr.find(_w('color'))
    if color is not None:
        cv = _wa(color, 'val', '').upper()
        if cv and cv not in ('AUTO', '000000'):
            props['color'] = cv

    shd = rPr.find(_w('shd'))
    if shd is not None:
        sv = _wa(shd, 'val', '').lower()
        fill = _wa(shd, 'fill', '').upper()
        if fill and fill not in ('FFFFFF', 'AUTO', '') and sv not in ('nil', 'clear'):
            props['background'] = fill

    return {k: v for k, v in props.items() if v not in (False, None, '', 0)}

def _ppr_to_dict(pPr) -> dict:
    """Extract layout properties from a <w:pPr> element."""
    if pPr is None:
        return {}
    props: dict = {}
    sp = pPr.find(_w('spacing'))
    if sp is not None:
        b = _wa(sp, 'before'); a = _wa(sp, 'after'); ln = _wa(sp, 'line')
        if b:  props['space_before'] = int(b)  // 20      # twips → points
        if a:  props['space_after']  = int(a)  // 20
        if ln: props['line_height']  = round(int(ln) / 240, 2)
    ind = pPr.find(_w('ind'))
    if ind is not None:
        left = _wa(ind, 'left')
        if left and int(left) > 0:
            props['indent_left'] = round(int(left) / 720, 2)
    jc = pPr.find(_w('jc'))
    if jc is not None:
        props['align'] = _wa(jc, 'val')
    return props

def extract_style_dict(docx_path: str) -> dict:
    """Parse word/styles.xml → paragraph_styles + character_styles dict."""
    with zipfile.ZipFile(docx_path) as z:
        raw = z.read('word/styles.xml')
    root = ET.fromstring(raw)
    para: dict = {}
    char: dict = {}
    for style in root.findall(_w('style')):
        stype = _wa(style, 'type', '')
        ne    = style.find(_w('name'))
        name  = _wa(ne, 'val', '') if ne is not None else ''
        if not name or name == 'Default Paragraph Font':
            continue
        rPr   = style.find(_w('rPr'))
        props = _rpr_to_dict(rPr)
        if stype == 'paragraph':
            pPr = style.find(_w('pPr'))
            props.update(_ppr_to_dict(pPr))
            if props: para[name] = props
        elif stype == 'character':
            if props: char[name] = props
    return {'paragraph_styles': para, 'character_styles': char}

# ── Build styleId → display-name map ─────────────────────────────────────────

def _build_style_map(styles_xml: bytes) -> dict:
    root = ET.fromstring(styles_xml)
    m = {}
    for s in root.findall(_w('style')):
        sid = _wa(s, 'styleId', '')
        ne  = s.find(_w('name'))
        if sid and ne is not None:
            m[sid] = _wa(ne, 'val', '')
    return m

# ── Parse a single run → Markdown fragment ────────────────────────────────────

def _run_to_md(run_elem, style_map: dict) -> str:
    """Convert one <w:r> to a Markdown/HTML-annotated string."""
    parts = []
    for ch in run_elem:
        if ch.tag == _w('t'):   parts.append(ch.text or '')
        elif ch.tag == _w('br'): parts.append('\n')
    text = ''.join(parts)
    if not text:
        return ''

    rPr = run_elem.find(_w('rPr'))
    if rPr is None:
        return text

    # Named character style reference (Pages uses 'Link' for hyperlinks)
    rs = rPr.find(_w('rStyle'))
    sv = _wa(rs, 'val') if rs is not None else ''
    if sv in ('Link', 'Hyperlink'):
        return f'[{text}](link)'

    # Pages exports character styles as direct formatting — detect each type.
    # IMPORTANT: Pages adds an empty <w:u/> alongside colored text; we must
    # NOT treat that as underline.  Check color first.

    color  = rPr.find(_w('color'))
    shd    = rPr.find(_w('shd'))
    b      = rPr.find(_w('b'))    is not None
    i_flag = rPr.find(_w('i'))    is not None
    strike = (rPr.find(_w('strike'))  is not None or
              rPr.find(_w('dstrike')) is not None)
    u_elem = rPr.find(_w('u'))
    hl_elem= rPr.find(_w('highlight'))

    if color is not None:
        cv = _wa(color, 'val', '').upper()
        if cv and cv not in ('AUTO', '000000'):
            return f'<span style="color: #{cv}">{text}</span>'

    if shd is not None:
        fill = _wa(shd, 'fill', '').upper()
        if fill and fill not in ('FFFFFF', 'AUTO', 'F2F2F7'):
            return f'<span style="background-color: #{fill}">{text}</span>'

    if b and i_flag: return f'***{text}***'
    if b:            return f'**{text}**'
    if i_flag:       return f'*{text}*'
    if strike:       return f'~~{text}~~'

    if u_elem is not None:
        uv = _wa(u_elem, 'val', '')
        if uv and uv not in ('none', ''):
            return f'<u>{text}</u>'

    if hl_elem is not None:
        hv = _wa(hl_elem, 'val', '')
        if hv: return f'<mark>{text}</mark>'

    return text

# ── Parse a single paragraph → Markdown line ─────────────────────────────────

def _para_to_md(para_elem, style_map: dict, code_state: list) -> str:
    pPr   = para_elem.find(_w('pPr'))
    pse   = pPr.find(_w('pStyle')) if pPr is not None else None
    sid   = _wa(pse, 'val', 'Normal') if pse is not None else 'Normal'
    dname = style_map.get(sid, sid)
    is_code = (dname in CODE_STYLES or sid in CODE_STYLES)

    # Gather content from all child elements
    parts = []
    for ch in para_elem:
        if ch.tag == _w('r'):
            parts.append(_run_to_md(ch, style_map))
        elif ch.tag == _w('hyperlink'):
            # Reconstruct link; run inside may have Link rStyle already handled
            inner = ''.join(_run_to_md(r, style_map) for r in ch.findall(_w('r')))
            parts.append(inner)
        elif ch.tag == _w('ins'):        # tracked insertion — treat as regular
            for r in ch.findall(_w('r')):
                parts.append(_run_to_md(r, style_map))
    content = ''.join(parts)

    if is_code:
        if not code_state[0]:
            code_state[0] = True
            return '```\n' + content
        return content

    # Close any open code block
    close = ''
    if code_state[0]:
        code_state[0] = False
        close = '```\n\n'

    if not content.strip():
        return close.rstrip('\n') if close else ''

    prefix = PARA_PREFIX.get(sid)
    if prefix is None:
        prefix = PARA_PREFIX.get(dname, '')

    return close + prefix + content

# ── Parse a table → GFM Markdown lines ───────────────────────────────────────

def _table_to_md(tbl_elem, style_map: dict) -> list:
    rows = []
    for tr in tbl_elem.findall(_w('tr')):
        cells = []
        for tc in tr.findall(_w('tc')):
            cp = []
            for para in tc.findall(_w('p')):
                for ch in para:
                    if ch.tag == _w('r'):
                        cp.append(_run_to_md(ch, style_map))
                    elif ch.tag == _w('hyperlink'):
                        cp.extend(_run_to_md(r, style_map) for r in ch.findall(_w('r')))
            cells.append(''.join(cp).strip())
        rows.append(cells)
    if not rows:
        return []
    lines  = ['| ' + ' | '.join(rows[0]) + ' |']
    lines += ['| ' + ' | '.join(['---'] * len(rows[0])) + ' |']
    lines += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    lines += ['']
    return lines

# ── Full document.xml → Markdown ──────────────────────────────────────────────

def extract_markdown(docx_path: str) -> str:
    """Parse word/document.xml from a .docx and return markdown text."""
    with zipfile.ZipFile(docx_path) as z:
        doc_xml = z.read('word/document.xml')
        try:    styles_raw = z.read('word/styles.xml')
        except: styles_raw = b'<w:styles/>'
    style_map  = _build_style_map(styles_raw)
    root       = ET.fromstring(doc_xml)
    body       = root.find(_w('body'))
    if body is None:
        return ''

    lines: list = []
    code_state  = [False]   # mutable flag

    for elem in body:
        if elem.tag == _w('p'):
            lines.append(_para_to_md(elem, style_map, code_state))
        elif elem.tag == _w('tbl'):
            if code_state[0]:
                lines.append('```'); lines.append('')
                code_state[0] = False
            lines.extend(_table_to_md(elem, style_map))
        # sectPr and other structural elements are silently skipped

    if code_state[0]:
        lines.append('```')

    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# ── Top-level: decode a .pages file ──────────────────────────────────────────

def decode_pages(
    pages_path: str,
    output_dir: str | None = None,
) -> tuple[str, str]:
    """
    Export, parse and save content + styles from a .pages file.
    Returns (content_md_path, style_yml_path).
    """
    abs_in  = os.path.abspath(pages_path)
    base    = os.path.splitext(os.path.basename(abs_in))[0]
    out_dir = os.path.abspath(output_dir) if output_dir else os.path.dirname(abs_in)
    os.makedirs(out_dir, exist_ok=True)

    content_path = os.path.join(out_dir, f'{base}_content.md')
    style_path   = os.path.join(out_dir, f'{base}_style.yml')

    with tempfile.TemporaryDirectory() as tmp:
        if abs_in.lower().endswith('.docx'):
            tmp_docx = abs_in
        else:
            tmp_docx = os.path.join(tmp, 'export.docx')
            print(f'Exporting  {os.path.basename(abs_in)} → DOCX …', flush=True)
            export_pages_to_docx(abs_in, tmp_docx)

        print('Extracting styles  …', flush=True)
        sd = extract_style_dict(tmp_docx)
        style_dict = {
            'meta': {
                'source_file':   os.path.basename(abs_in),
                'extracted_at':  datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'apply_command': (
                    f'python3 pages_restyle.py <doc> '
                    f'--style {base}_style.yml -o <out>.pages'
                ),
            },
            'paragraph_styles': sd['paragraph_styles'],
            'character_styles': sd['character_styles'],
        }

        print('Extracting content …', flush=True)
        markdown = extract_markdown(tmp_docx)

    # ── Write outputs ──────────────────────────────────────────────────────────
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    with open(style_path, 'w', encoding='utf-8') as f:
        f.write(f'# Style sheet extracted from: {os.path.basename(abs_in)}\n')
        f.write(f'# Generated {stamp} by pages_decode.py\n')
        f.write(f'# Usage: python3 pages_restyle.py <doc> --style '
                f'{base}_style.yml -o <out>.pages\n\n')
        f.write(dict_to_yaml(style_dict))
        f.write('\n')

    with open(content_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
        f.write('\n')

    print(f'✓  Content → {content_path}')
    print(f'✓  Styles  → {style_path}')
    return content_path, style_path

# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description='Extract content + styles from an Apple Pages (.pages) file'
    )
    p.add_argument('input',  help='Path to .pages file')
    p.add_argument('-o', '--output-dir',
                   help='Directory for output files (default: same as input)')
    p.add_argument('--open', action='store_true',
                   help='Open the output files when done')
    args = p.parse_args()

    if not os.path.exists(args.input):
        print(f'Error: not found: {args.input}', file=sys.stderr)
        sys.exit(1)

    try:
        cp, sp = decode_pages(args.input, getattr(args, 'output_dir', None))
        if args.open:
            subprocess.run(['open', cp])
            subprocess.run(['open', sp])
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
