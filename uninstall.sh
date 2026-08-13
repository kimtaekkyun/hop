#!/usr/bin/env bash
# hop uninstaller — removes the binary and the rc wiring.
# Bookmark data is YOURS and is left in place; its path is shown at the end.
set -uo pipefail

CMD=hop
rm -f "$HOME/.local/bin/$CMD" && echo "removed  $HOME/.local/bin/$CMD"

for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
  [ -f "$RC" ] || continue
  if grep -q 'hop init' "$RC"; then
    grep -v -e 'hop init' -e '# hop (named bookmarks for dirs and files)' "$RC" > "$RC.tmp" \
      && mv "$RC.tmp" "$RC"
    echo "cleaned  $RC"
  fi
done

DATA="$(dirname "${HOP_BOOKMARKS:-$HOME/.local/share/hop/bookmarks}")"
CFG="$(dirname "${HOP_CONFIG:-$HOME/.config/hop/config}")"
echo
echo "bookmark data left at: $DATA"
echo "config left at:        $CFG"
echo "remove them if you wish:  rm -rf \"$DATA\" \"$CFG\""
