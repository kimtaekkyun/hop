#!/usr/bin/env bash
# hop installer — named bookmarks for directories and files.
#
# Install methods (all produce the same result, no source tree needed after):
#   1) git clone … && ./install.sh        -> copies local hop.py
#   2) curl -fsSL <raw>/install.sh | bash -> downloads hop.py
set -euo pipefail

CMD=hop
# Repository used by the curl installer:
OWNER="kimtaekkyun"
REPO="hop"
BRANCH="main"
RAW="https://raw.githubusercontent.com/$OWNER/$REPO/$BRANCH"

BIN="$HOME/.local/bin"
mkdir -p "$BIN"

# 1) Find a working Python 3 executable. Git Bash commonly exposes it as `python`.
PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 6) else 1)' >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "hop needs Python 3.6+ (\`python3\` or \`python\`), which was not found." >&2
  case "$(uname -s)" in
    Darwin)       echo "  brew install python3    (or: xcode-select --install)" >&2 ;;
    Linux)        echo "  sudo apt install python3     # dnf/yum/pacman: equivalent" >&2 ;;
    MINGW*|MSYS*) echo "  winget install Python.Python.3   (or https://python.org)" >&2 ;;
    *)            echo "  install Python 3.6+ from https://python.org" >&2 ;;
  esac
  exit 1
fi

# 2) Obtain hop — local copy (git clone) preferred, else download (curl|sh).
# A piped script has no source directory; only use a local hop.py for a real file.
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
SRC_DIR=""
if [ -n "$SCRIPT_PATH" ] && [ -f "$SCRIPT_PATH" ]; then
  SRC_DIR="$(cd "$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd)"
fi

rm -f "$BIN/$CMD" "$BIN/$CMD.download"  # replace cleanly
SOURCE=""
INSTALL_KIND=""
if [ -n "$SRC_DIR" ] && [ -f "$SRC_DIR/$CMD.py" ]; then
  SOURCE="$SRC_DIR/$CMD.py"
  INSTALL_KIND="local"
elif command -v curl >/dev/null 2>&1; then
  SOURCE="$BIN/$CMD.download"
  INSTALL_KIND="remote"
  echo "downloading $CMD.py from $RAW ..."
  if ! curl -fsSL "$RAW/$CMD.py" -o "$SOURCE"; then
    rm -f "$SOURCE"
    echo "download failed. Check the GitHub URL or use: git clone" >&2
    exit 1
  fi
else
  echo "no local $CMD.py and no curl. git clone the repo and run ./install.sh." >&2
  exit 1
fi

# Match the installed script's shebang to the interpreter found above.
if ! sed "1s|.*|#!/usr/bin/env $PYTHON_BIN|" "$SOURCE" > "$BIN/$CMD"; then
  rm -f "$BIN/$CMD" "$BIN/$CMD.download"
  echo "failed to install $CMD" >&2
  exit 1
fi
rm -f "$BIN/$CMD.download"
chmod +x "$BIN/$CMD"
echo "installed ($INSTALL_KIND)   $BIN/$CMD"

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "note: $BIN is not on your PATH. Add:  export PATH=\"$BIN:\$PATH\"" >&2 ;;
esac

# 3) wire the shell wrapper into the rc, idempotently (bash or zsh).
if [ -n "${ZSH_VERSION:-}" ] || [[ "${SHELL:-}" == *zsh ]]; then
  RC="$HOME/.zshrc"; LINE='eval "$(hop init zsh)"'
else
  RC="$HOME/.bashrc"; LINE='eval "$(hop init bash)"'
fi
touch "$RC"
if grep -qxF "$LINE" "$RC"; then
  echo "already wired in $RC"
else
  { echo; echo "# hop (named bookmarks for dirs and files)"; echo "$LINE"; } >> "$RC"
  echo "added   $LINE   ->  $RC"
fi

echo
echo "done. Start a new shell (or: source $RC), then try:  hop list"
