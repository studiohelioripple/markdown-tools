#!/usr/bin/env bash
# Install Finder Quick Actions for Markdown conversion on macOS with 9 Themes Selection
# Including Terminal Dark (CLI Slate & Amber) based on sample-pallet

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Finder Quick Actions are only supported on macOS." >&2
  exit 1
fi

SERVICES_DIR="${HOME}/Library/Services"
mkdir -p "${SERVICES_DIR}"

create_workflow() {
    local WORKFLOW_NAME="$1"
    local WORKFLOW_DIR="${SERVICES_DIR}/${WORKFLOW_NAME}.workflow"
    local CONTENTS_DIR="${WORKFLOW_DIR}/Contents"
    
    mkdir -p "${CONTENTS_DIR}"
    
    cat > "${CONTENTS_DIR}/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSIconPath</key>
    <string>Automator</string>
    <key>NSServices</key>
    <array>
        <dict>
            <key>NSBackgroundColorName</key>
            <string>background</string>
            <key>NSBackgroundStrokeColorName</key>
            <string>line</string>
            <key>NSIconName</key>
            <string>Automator</string>
            <key>NSMenuItem</key>
            <dict>
                <key>default</key>
                <string>Convert Markdown</string>
            </dict>
            <key>NSMessage</key>
            <string>runWorkflowAsService</string>
            <key>NSRequiredContext</key>
            <dict>
                <key>NSApplicationIdentifier</key>
                <string>com.apple.finder</string>
            </dict>
            <key>NSSendFileTypes</key>
            <array>
                <string>public.item</string>
                <string>net.daringfireball.markdown</string>
                <string>public.text</string>
                <string>public.plain-text</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
PLIST

    cat > "${CONTENTS_DIR}/document.wflow" << 'WFLOW'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AMApplicationBuild</key>
    <string>523</string>
    <key>AMApplicationVersion</key>
    <string>2.10</string>
    <key>AMDocumentVersion</key>
    <string>2</string>
    <key>actions</key>
    <array>
        <dict>
            <key>action</key>
            <dict>
                <key>AMAccepts</key>
                <dict>
                    <key>Container</key>
                    <string>List</string>
                    <key>Optional</key>
                    <false/>
                    <key>Types</key>
                    <array>
                        <string>com.apple.cocoa.path</string>
                    </array>
                </dict>
                <key>AMActionVersion</key>
                <string>2.0.3</string>
                <key>AMApplication</key>
                <array>
                    <string>Automator</string>
                </array>
                <key>AMParameterProperties</key>
                <dict>
                    <key>COMMAND_STRING</key>
                    <dict/>
                    <key>CheckedForUserDefault</key>
                    <dict/>
                    <key>inputMethod</key>
                    <dict/>
                    <key>shell</key>
                    <dict/>
                    <key>source</key>
                    <dict/>
                </dict>
                <key>AMProvides</key>
                <dict>
                    <key>Container</key>
                    <string>List</string>
                    <key>Types</key>
                    <array>
                        <string>com.apple.cocoa.path</string>
                    </array>
                </dict>
                <key>ActionBundlePath</key>
                <string>/System/Library/Automator/Run Shell Script.action</string>
                <key>ActionName</key>
                <string>Run Shell Script</string>
                <key>ActionParameters</key>
                <dict>
                    <key>COMMAND_STRING</key>
                    <string>export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

SELECTION=$(osascript &lt;&lt; 'APPLESCRIPT'
set formatChoices to {"PDF (.pdf)", "HTML (.html)", "Apple Pages (.pages)", "Microsoft Word (.docx)"}
set userChoice to (choose from list formatChoices with title "Convert Markdown" with prompt "Step 1 of 2: Select output format:" default items {"PDF (.pdf)"} OK button name "Next" cancel button name "Cancel")
if userChoice is false then
    return "CANCELLED"
end if

set selectedFmt to item 1 of userChoice
set fmtCode to "pdf"
if selectedFmt contains "PDF" then set fmtCode to "pdf"
if selectedFmt contains "HTML" then set fmtCode to "html"
if selectedFmt contains "Pages" then set fmtCode to "pages"
if selectedFmt contains "Word" then set fmtCode to "docx"

set themeChoices to {¬
    "1. Amil Light (Default - Modern Slate)", ¬
    "2. Amil Dark (Midnight Slate &amp; Cyan)", ¬
    "3. Terminal Dark (CLI Slate &amp; Amber)", ¬
    "4. Apple Light (Cupertino SF Pro)", ¬
    "5. Apple Dark (Space Black &amp; Blue)", ¬
    "6. VS Code Dark (Markdown Preview &amp; Graphs)", ¬
    "7. GitHub Light (Primer Modern)", ¬
    "8. Nord Frost (Arctic Polar Dark)", ¬
    "9. Editorial Ivory (Classic Serif &amp; Crimson)"}

set themeChoice to (choose from list themeChoices with title "Convert Markdown" with prompt "Step 2 of 2: Select rendering theme:" default items {"1. Amil Light (Default - Modern Slate)"} OK button name "Convert" cancel button name "Cancel")
if themeChoice is false then
    return "CANCELLED"
end if

set selectedTheme to item 1 of themeChoice
set themeCode to "amil-light"
if selectedTheme contains "Amil Light" then set themeCode to "amil-light"
if selectedTheme contains "Amil Dark" then set themeCode to "amil-dark"
if selectedTheme contains "Terminal Dark" then set themeCode to "terminal-dark"
if selectedTheme contains "Apple Light" then set themeCode to "apple-light"
if selectedTheme contains "Apple Dark" then set themeCode to "apple-dark"
if selectedTheme contains "VS Code" then set themeCode to "vscode-dark"
if selectedTheme contains "GitHub" then set themeCode to "github-light"
if selectedTheme contains "Nord" then set themeCode to "nord-frost"
if selectedTheme contains "Editorial" then set themeCode to "editorial-serif"

return fmtCode &amp; "|" &amp; themeCode
APPLESCRIPT
)

if [ "$SELECTION" = "CANCELLED" ] || [ -z "$SELECTION" ]; then
    exit 0
fi

FORMAT=$(echo "$SELECTION" | cut -d'|' -f1)
THEME=$(echo "$SELECTION" | cut -d'|' -f2)

CONVERTER=""
if command -v forma &gt;/dev/null 2&gt;&amp;1; then
    CONVERTER="forma convert"
elif [ -f "$HOME/.gemini/config/skills/markdown-tools/scripts/markdown_convert.py" ]; then
    CONVERTER="python3 $HOME/.gemini/config/skills/markdown-tools/scripts/markdown_convert.py"
elif [ -f "$HOME/markdown-to-pages/markdown_convert.py" ]; then
    CONVERTER="python3 $HOME/markdown-to-pages/markdown_convert.py"
fi

if [ -z "$CONVERTER" ]; then
    osascript -e 'display alert "Error" message "Conversion engine not found. Please verify markdown-tools skill installation." as critical'
    exit 1
fi

SUCCESS_COUNT=0
FAIL_COUNT=0
LAST_OUT=""

for f in "$@"; do
    ext="$(echo "${f##*.}" | tr '[:upper:]' '[:lower:]')"
    if [ "$ext" != "md" ] &amp;&amp; [ "$ext" != "markdown" ]; then
        continue
    fi
    
    if $CONVERTER "$f" -f "$FORMAT" -t "$THEME"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        LAST_OUT="${f%.*}.${FORMAT}"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

if [ $SUCCESS_COUNT -gt 0 ]; then
    FORMAT_UPPER=$(echo "$FORMAT" | tr '[:lower:]' '[:upper:]')
    if [ $SUCCESS_COUNT -eq 1 ] &amp;&amp; [ -n "$LAST_OUT" ]; then
        osascript -e "display notification \"Converted to $FORMAT_UPPER ($THEME)\" with title \"Markdown Converted\" subtitle \"$(basename "$LAST_OUT")\" sound name \"Glass\""
    else
        osascript -e "display notification \"Converted $SUCCESS_COUNT files to $FORMAT_UPPER ($THEME)\" with title \"Markdown Conversion Complete\" sound name \"Glass\""
    fi
elif [ $FAIL_COUNT -gt 0 ]; then
    osascript -e 'display alert "Conversion Failed" message "Failed to convert Markdown file(s)." as warning'
fi
</string>
                    <key>CheckedForUserDefault</key>
                    <true/>
                    <key>inputMethod</key>
                    <integer>1</integer>
                    <key>shell</key>
                    <string>/bin/bash</string>
                    <key>source</key>
                    <string></string>
                </dict>
                <key>BundleIdentifier</key>
                <string>com.apple.RunShellScript</string>
                <key>CFBundleVersion</key>
                <string>2.0.3</string>
                <key>CanShowSelectedItemsWhenRun</key>
                <false/>
                <key>CanShowWhenRun</key>
                <true/>
                <key>Category</key>
                <array>
                    <string>AMCategoryUtilities</string>
                </array>
                <key>Class Name</key>
                <string>RunShellScriptAction</string>
                <key>InputUUID</key>
                <string>A1B2C3D4-E5F6-7890-ABCD-EF1234567890</string>
                <key>Keywords</key>
                <array>
                    <string>Shell</string>
                    <string>Script</string>
                    <string>Command</string>
                    <string>Run</string>
                    <string>Unix</string>
                </array>
                <key>OutputUUID</key>
                <string>B2C3D4E5-F6A7-8901-BCDE-F12345678901</string>
                <key>UUID</key>
                <string>C3D4E5F6-A7B8-9012-CDEF-123456789012</string>
                <key>UnlocalizedApplications</key>
                <array>
                    <string>Automator</string>
                </array>
                <key>arguments</key>
                <dict>
                    <key>0</key>
                    <dict>
                        <key>default value</key>
                        <integer>0</integer>
                        <key>name</key>
                        <string>inputMethod</string>
                        <key>required</key>
                        <string>0</string>
                        <key>type</key>
                        <string>0</string>
                        <key>uuid</key>
                        <string>0</string>
                    </dict>
                    <key>1</key>
                    <dict>
                        <key>default value</key>
                        <string>/bin/sh</string>
                        <key>name</key>
                        <string>shell</string>
                        <key>required</key>
                        <string>0</string>
                        <key>type</key>
                        <string>0</string>
                        <key>uuid</key>
                        <string>1</string>
                    </dict>
                    <key>2</key>
                    <dict>
                        <key>default value</key>
                        <string></string>
                        <key>name</key>
                        <string>source</string>
                        <key>required</key>
                        <string>0</string>
                        <key>type</key>
                        <string>0</string>
                        <key>uuid</key>
                        <string>2</string>
                    </dict>
                    <key>3</key>
                    <dict>
                        <key>default value</key>
                        <string></string>
                        <key>name</key>
                        <string>COMMAND_STRING</string>
                        <key>required</key>
                        <string>0</string>
                        <key>type</key>
                        <string>0</string>
                        <key>uuid</key>
                        <string>3</string>
                    </dict>
                </dict>
                <key>isViewVisible</key>
                <integer>1</integer>
                <key>location</key>
                <string>449.500000:305.000000</string>
                <key>nibPath</key>
                <string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/Base.lproj/main.nib</string>
            </dict>
            <key>isViewVisible</key>
            <integer>1</integer>
        </dict>
    </array>
    <key>connectors</key>
    <dict/>
    <key>workflowMetaData</key>
    <dict>
        <key>workflowTypeIdentifier</key>
        <string>com.apple.Automator.servicesMenu</string>
    </dict>
</dict>
</plist>
WFLOW
}

echo "Installing Finder Quick Actions..."
create_workflow "Convert Markdown"
create_workflow "Convert"

/System/Library/CoreServices/pbs -update 2>/dev/null || true

echo "✓ Quick Actions installed successfully with 9 design themes!"
