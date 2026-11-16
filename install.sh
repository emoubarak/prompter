#!/usr/bin/env bash
# Link `prompter` into ~/.local/bin (or the directory given as $1).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dest="${1:-$HOME/.local/bin}"
mkdir -p "$dest"
ln -sfn "$here/prompter" "$dest/prompter"
echo "Linked $dest/prompter -> $here/prompter"
command -v prompter >/dev/null || echo "Add $dest to your PATH to run 'prompter' from anywhere."
