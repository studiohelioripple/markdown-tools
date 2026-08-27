#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/bin"

mkdir -p "${INSTALL_DIR}"
chmod +x "${SCRIPT_DIR}/markdown_convert.py" "${SCRIPT_DIR}/forma_cli.py"

ln -sfn "${SCRIPT_DIR}/markdown_convert.py" "${INSTALL_DIR}/md-convert"
ln -sfn "${SCRIPT_DIR}/forma_cli.py" "${INSTALL_DIR}/forma"

echo "✓ Installed md-convert and forma -> ${INSTALL_DIR}"
echo "Usage:"
echo "  forma convert document.md -f pdf -t apple-light"
echo "  md-convert document.md -f html -t amil-light"
