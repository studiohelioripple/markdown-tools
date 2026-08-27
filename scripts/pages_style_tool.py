#!/usr/bin/env python3
import os
import sys
import re
import zipfile
import tempfile
import argparse
import subprocess
import xml.etree.ElementTree as ET

namespaces = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
}

def run_applescript(script_content):
    try:
        res = subprocess.run(
            ['osascript', '-e', script_content],
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"AppleScript Error: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

def check_pages_status():
    check_script = '''
    tell application "System Events"
        if not (exists process "Pages") and not (exists process "Pages Creator Studio") then
            return "not running"
        end if
    end tell
    tell application "Pages"
        if (count of documents) is 0 then
            return "no document"
        end if
        return "ok"
    end tell
    '''
    status = run_applescript(check_script)
    if "not running" in status:
        print("Error: Pages is not running.", file=sys.stderr)
        sys.exit(1)
    elif "no document" in status:
        print("Error: No document is open in Pages.", file=sys.stderr)
        sys.exit(1)

def export_doc_to_temp():
    fd, temp_docx_path = tempfile.mkstemp(suffix='.docx')
    os.close(fd)
    
    export_script = f'''
    tell application "Pages"
        export front document to POSIX file "{temp_docx_path}" as Microsoft Word
    end tell
    '''
    run_applescript(export_script)
    return temp_docx_path

def get_character_styles_map(styles_root):
    style_id_to_name = {}
    for style_tag in styles_root.findall('.//w:style', namespaces):
        style_type = style_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type')
        if style_type == 'character':
            style_id = style_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}styleId')
            name_tag = style_tag.find('w:name', namespaces)
            if name_tag is not None:
                name_val = name_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                style_id_to_name[style_id] = name_val
    return style_id_to_name

def list_styles(temp_docx_path):
    with zipfile.ZipFile(temp_docx_path, 'r') as docx:
        styles_xml = docx.read('word/styles.xml')
        styles_root = ET.fromstring(styles_xml)
        
        char_styles = []
        para_styles = []
        
        for style_tag in styles_root.findall('.//w:style', namespaces):
            style_type = style_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type')
            name_tag = style_tag.find('w:name', namespaces)
            if name_tag is not None:
                name_val = name_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                if style_type == 'character':
                    char_styles.append(name_val)
                elif style_type == 'paragraph':
                    para_styles.append(name_val)
        
        print("CHARACTER STYLES:")
        for s in sorted(char_styles):
            print(f"  - {s}")
        print("\nPARAGRAPH STYLES:")
        for s in sorted(para_styles):
            print(f"  - {s}")

def extract_words(temp_docx_path, target_style_filter=None):
    with zipfile.ZipFile(temp_docx_path, 'r') as docx:
        styles_xml = docx.read('word/styles.xml')
        styles_root = ET.fromstring(styles_xml)
        style_id_to_name = get_character_styles_map(styles_root)
        
        doc_xml = docx.read('word/document.xml')
        doc_root = ET.fromstring(doc_xml)
        
        word_styles = []
        for run_tag in doc_root.findall('.//w:r', namespaces):
            rPr = run_tag.find('w:rPr', namespaces)
            if rPr is not None:
                rStyle = rPr.find('w:rStyle', namespaces)
                if rStyle is not None:
                    style_id = rStyle.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                    style_name = style_id_to_name.get(style_id, style_id)
                    
                    if style_name == 'Default Paragraph Font':
                        continue
                    
                    if target_style_filter and style_name.lower() != target_style_filter.lower():
                        continue
                    
                    texts = run_tag.findall('w:t', namespaces)
                    text_content = "".join([t.text for t in texts if t.text])
                    words = re.findall(r"\b[\w'-]+\b", text_content)
                    for word in words:
                        word_styles.append((word, style_name))
        
        if target_style_filter:
            print(f"Words with style '{target_style_filter}':")
        else:
            print("Word\tStyle")
        for word, style in word_styles:
            if target_style_filter:
                print(f"  - {word}")
            else:
                print(f"{word}\t{style}")

def apply_style(temp_docx_path, target_word, target_style_name):
    # Parse styles.xml to find the style properties
    with zipfile.ZipFile(temp_docx_path, 'r') as docx:
        styles_xml = docx.read('word/styles.xml')
        styles_root = ET.fromstring(styles_xml)
        
        target_style_tag = None
        for style_tag in styles_root.findall('.//w:style', namespaces):
            style_type = style_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type')
            if style_type == 'character':
                name_tag = style_tag.find('w:name', namespaces)
                if name_tag is not None:
                    name_val = name_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                    if name_val.lower() == target_style_name.lower():
                        target_style_tag = style_tag
                        break
        
        if target_style_tag is None:
            print(f"Error: Character style '{target_style_name}' not found in the document.", file=sys.stderr)
            sys.exit(1)
            
        rPr = target_style_tag.find('w:rPr', namespaces)
        if rPr is None:
            print(f"Error: Style '{target_style_name}' contains no formatting properties.", file=sys.stderr)
            sys.exit(1)
            
        # Parse formatting properties
        font_family = "Helvetica"
        bold = False
        italic = False
        font_size = None
        applescript_color = None
        
        # 1. Font Family
        rFonts = rPr.find('w:rFonts', namespaces)
        if rFonts is not None:
            font_family = rFonts.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii', 'Helvetica')
            
        # 2. Bold / Italic
        b_tag = rPr.find('w:b', namespaces)
        if b_tag is not None:
            val = b_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
            bold = (val != '0')
        i_tag = rPr.find('w:i', namespaces)
        if i_tag is not None:
            val = i_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
            italic = (val != '0')
            
        # 3. Size (half-points in docx)
        sz = rPr.find('w:sz', namespaces)
        if sz is not None:
            sz_val = sz.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
            font_size = float(sz_val) / 2.0
            
        # 4. Color
        color_tag = rPr.find('w:color', namespaces)
        if color_tag is not None:
            hex_color = color_tag.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
            if hex_color and len(hex_color) == 6:
                r = int(hex_color[0:2], 16) * 257
                g = int(hex_color[2:4], 16) * 257
                b = int(hex_color[4:6], 16) * 257
                applescript_color = f"{{{r}, {g}, {b}}}"
                
        # Resolve PostScript font name variant
        font_name = font_family
        if bold or italic:
            # simple mapping heuristic
            suffix = ""
            if bold:
                suffix += "Bold"
            if italic:
                suffix += "Italic"
            font_name = f"{font_family}-{suffix}"

        # 5. Build AppleScript
        applescript_statements = []
        applescript_statements.append(f'set font of word i of body text to "{font_name}"')
        if font_size:
            applescript_statements.append(f'set size of word i of body text to {font_size}')
        if applescript_color:
            applescript_statements.append(f'set color of word i of body text to {applescript_color}')
            
        actions = "\n                ".join(applescript_statements)
        
        apply_as = f'''
        tell application "Pages"
            tell front document
                set wordList to words of body text
                set changedCount to 0
                repeat with i from 1 to count of wordList
                    set w to item i of wordList
                    if w is "{target_word}" then
                        {actions}
                        set changedCount to changedCount + 1
                    end if
                end repeat
                return changedCount
            end tell
        end tell
        '''
        
        count = run_applescript(apply_as)
        print(f"Successfully simulated style '{target_style_name}' on {count} occurrences of word '{target_word}'.")

def get_word_font_family(target_word):
    get_font_as = f'''
    tell application "Pages"
        tell front document
            set wordList to words of body text
            repeat with i from 1 to count of wordList
                if item i of wordList is "{target_word}" then
                    return font of word i of body text
                end if
            end repeat
            return "default"
        end tell
    end tell
    '''
    font_name = run_applescript(get_font_as)
    if font_name == "default" or not font_name:
        return "Helvetica"
    # Extract family name by stripping suffix like -Bold or -Regular
    if '-' in font_name:
        family = font_name.split('-')[0]
    else:
        family = font_name
    # Strip any ending words
    for suffix in [" Regular", " Bold", " Italic", " Bold Italic"]:
        if family.endswith(suffix):
            family = family[:-len(suffix)]
    return family

def apply_preset_style(target_word, preset_name):
    family = get_word_font_family(target_word)
    
    applescript_statements = []
    preset = preset_name.lower()
    
    if preset == "strong":
        font_name = f"{family}-Bold"
        applescript_statements.append(f'set font of word i of body text to "{font_name}"')
    elif preset == "emphasis":
        font_name = f"{family}-Italic"
        applescript_statements.append(f'set font of word i of body text to "{font_name}"')
    elif preset == "code":
        font_name = "CourierNewPSMT"
        applescript_statements.append(f'set font of word i of body text to "{font_name}"')
        applescript_statements.append('set color of word i of body text to {45000, 10000, 10000}')
        applescript_statements.append('set size of word i of body text to 9.0')
    elif preset == "warning":
        font_name = f"{family}-Bold"
        applescript_statements.append(f'set font of word i of body text to "{font_name}"')
        applescript_statements.append('set color of word i of body text to {65535, 0, 0}')
    elif preset == "info":
        font_name = f"{family}-Italic"
        applescript_statements.append(f'set font of word i of body text to "{font_name}"')
        applescript_statements.append('set color of word i of body text to {0, 0, 50000}')
    elif preset == "subtle":
        font_name = f"{family}-Italic"
        applescript_statements.append(f'set font of word i of body text to "{font_name}"')
        applescript_statements.append('set color of word i of body text to {35000, 35000, 35000}')
    elif preset == "highlight":
        font_name = f"{family}-Bold"
        applescript_statements.append(f'set font of word i of body text to "{font_name}"')
        applescript_statements.append('set color of word i of body text to {65535, 30000, 0}')
    else:
        print(f"Error: Unknown preset style '{preset_name}'. Supported presets: Strong, Emphasis, Code, Warning, Info, Subtle, Highlight", file=sys.stderr)
        sys.exit(1)
        
    actions = "\n                ".join(applescript_statements)
    
    apply_as = f'''
    tell application "Pages"
        tell front document
            set wordList to words of body text
            set changedCount to 0
            repeat with i from 1 to count of wordList
                set w to item i of wordList
                if w is "{target_word}" then
                    {actions}
                    set changedCount to changedCount + 1
                end if
            end repeat
            return changedCount
        end tell
    end tell
    '''
    
    count = run_applescript(apply_as)
    print(f"Successfully simulated preset style '{preset_name}' on {count} occurrences of word '{target_word}'.")

def main():
    check_pages_status()
    
    parser = argparse.ArgumentParser(description="Apple Pages Style Automation Speed Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # list-styles
    subparsers.add_parser("list-styles", help="List all defined character and paragraph styles in the document")
    
    # extract
    subparsers.add_parser("extract", help="Extract all words mapped to their character styles")
    
    # find
    find_parser = subparsers.add_parser("find", help="Find all words styled with a specific character style")
    find_parser.add_argument("--style", required=True, help="Character style name to filter by")
    
    # apply
    apply_parser = subparsers.add_parser("apply", help="Apply visual formatting of an existing character style to specific words")
    apply_parser.add_argument("--word", required=True, help="Word to apply formatting to")
    apply_parser.add_argument("--style", required=True, help="Name of the existing character style to copy formatting from")
    
    # simulate-preset
    preset_parser = subparsers.add_parser("simulate-preset", help="Simulate a standard preset style on specific words")
    preset_parser.add_argument("--word", required=True, help="Word to apply preset style to")
    preset_parser.add_argument("--preset", required=True, choices=["Strong", "Emphasis", "Code", "Warning", "Info", "Subtle", "Highlight"], help="Preset style name")
    
    args = parser.parse_args()
    
    # Special case: simulate-preset doesn't require a temporary docx export
    if args.command == "simulate-preset":
        apply_preset_style(args.word, args.preset)
        return
        
    temp_docx_path = export_doc_to_temp()
    
    try:
        if args.command == "list-styles":
            list_styles(temp_docx_path)
        elif args.command == "extract":
            extract_words(temp_docx_path)
        elif args.command == "find":
            extract_words(temp_docx_path, target_style_filter=args.style)
        elif args.command == "apply":
            apply_style(temp_docx_path, args.word, args.style)
    finally:
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)

if __name__ == '__main__':
    main()

