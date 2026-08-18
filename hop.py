#!/usr/bin/env python3
"""hop — named bookmarks for directories and files.

  hop NAME           go to NAME: cd if it points at a directory, open it in
                     your editor if it points at a file
  hop jump NAME      explicit form of `hop NAME` (also works for reserved names)
  hop add NAME [P]   add/update NAME -> P   (P defaults to the current dir)
  hop list           list all bookmarks (`ls` is a shortcut)
  hop remove NAME    remove NAME (`rm` is a shortcut)
  hop path NAME      print NAME's path   (scripts: cd "$(hop path NAME)")
  hop edit [bookmarks|config]
                     open the selected file in your editor (bookmarks by default)
  hop config         show every setting: what it does, its value, how to set it
  hop config K V     set setting K to V   (settings: editor)
  hop init bash|zsh  print shell wrapper for rc — eval "$(hop init bash)"
  hop                list all (no arguments)

Bookmarks: $HOP_BOOKMARKS (default ~/.local/share/hop/bookmarks)
Config:    $HOP_CONFIG    (default ~/.config/hop/config)
Both are plain `key=value` text, '#' = comments, hand-editable.

Editor lookup order: $HOP_EDITOR, config `editor`, $VISUAL, $EDITOR, vi.

No executable can change its parent shell's directory, so `hop NAME` alone only
prints a path. Put `eval "$(hop init bash)"` (or zsh) in your rc so `hop NAME`
cds / opens directly — same pattern as zoxide/fzf.
"""
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

DB = Path(os.environ.get("HOP_BOOKMARKS") or os.path.expanduser("~/.local/share/hop/bookmarks"))
CONFIG = Path(os.environ.get("HOP_CONFIG") or os.path.expanduser("~/.config/hop/config"))

DB_HEADER = (
    "# hop bookmarks — one `name=path` per line, '#' lines are comments.\n"
    "# A path may be a directory (hop cds) or a file (hop opens your editor).\n"
)

CONFIG_HEADER = (
    "# hop config — one `key=value` per line, '#' lines are comments.\n"
    "# editor: command opening file bookmarks; flags allowed, e.g. `code -w`\n"
)

# Every setting hop understands, with the text `hop config` prints to explain it.
CONFIG_KEYS = {
    "editor": {
        "what": "Command that opens file bookmarks. Flags are allowed.",
        "hint": "Must stay in the foreground until you close the file, so"
                " `code -w`, not `code`.",
        "examples": ("nvim", "vim", "nano", "code -w", "subl -w"),
        "order": "$HOP_EDITOR, this file, $VISUAL, $EDITOR, vi",
    },
}


def _read_pairs(path):
    pairs = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            pairs[key.strip()] = value.strip()
    return pairs


def _write_pairs(path, header, pairs):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write(header)
        for key, value in pairs.items():
            fh.write(f"{key}={value}\n")


def load():
    return _read_pairs(DB)


def save(marks):
    _write_pairs(DB, DB_HEADER, marks)


def load_config():
    return _read_pairs(CONFIG)


def save_config(cfg):
    _write_pairs(CONFIG, CONFIG_HEADER, cfg)


def die(msg, code=1):
    print(f"hop: {msg}", file=sys.stderr)
    raise SystemExit(code)


def resolve(p):
    return os.path.abspath(os.path.expanduser(p))


def editor_source():
    """(command, where it came from) for opening file bookmarks."""
    value = os.environ.get("HOP_EDITOR")
    if value:
        return value, "$HOP_EDITOR"
    value = load_config().get("editor")
    if value:
        return value, str(CONFIG)
    for var in ("VISUAL", "EDITOR"):
        value = os.environ.get(var)
        if value:
            return value, f"${var}"
    return "vi", "built-in default"


def editor():
    """The command used to open file bookmarks. May carry flags (`code -w`)."""
    return editor_source()[0]


def shell_path(p):
    """Path as the calling shell sees it — Git Bash needs a POSIX form."""
    if shutil.which("cygpath"):
        try:
            out = subprocess.run(
                ["cygpath", "-u", p], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.decode("utf-8", "replace").strip()
        except OSError:
            pass
    return p


def lookup(name):
    marks = load()
    if name not in marks:
        die(f"no bookmark '{name}'. try: hop list")
    return marks[name]


def cmd_path(name, bare=False):
    print(lookup(name))
    # The wrapper always calls `hop _dispatch`, so a bare `hop NAME` typed at a
    # terminal means the wrapper is missing from this shell — which just looks
    # broken ("why did it print a path?"). Say so. A captured path is the
    # documented scripting use, so stay quiet when stdout isn't a terminal.
    if bare and sys.stdout.isatty():
        sh = "zsh" if os.environ.get("SHELL", "").endswith("zsh") else "bash"
        rc = f"~/.{sh}rc"
        print(
            f"\nhop: printed the path instead of going there, because the shell"
            f" wrapper\n      isn't loaded in this shell."
            f"\n      fix: source {rc}      (or just open a new terminal)"
            f"\n      no wrapper in {rc}? add:  eval \"$(hop init {sh})\"",
            file=sys.stderr,
        )


def cmd_dispatch(name):
    """Emit the shell command the wrapper should eval for `hop NAME`."""
    path = lookup(name)
    if os.path.isdir(path):
        print(f"cd -- {shlex.quote(shell_path(path))}")
    elif os.path.isfile(path):
        print(f"{editor()} {shlex.quote(shell_path(path))}")
    else:
        die(f"'{name}' points at a missing path: {path}")


def cmd_add(name, path="."):
    marks = load()
    existed = name in marks
    path = resolve(path)
    marks[name] = path
    save(marks)
    action = "updated" if existed else "added"
    if os.path.isdir(path):
        print(f"hop: {action} {name} -> {path}  (dir, cd)")
        return
    if not os.path.isfile(path):
        print(f"hop: {action} {name} -> {path}  (missing — nothing there yet)")
        return
    ed, source = editor_source()
    print(f"hop: {action} {name} -> {path}  (file, opens in {ed})")
    # First file bookmark with no editor chosen: say how to change it, once.
    if source == "built-in default":
        print(f"hop: to open files with something else: hop config editor nvim")


def cmd_list():
    marks = load()
    if not marks:
        print(f"hop: no bookmarks. add: hop add <name> [path]   (db: {DB})")
        return
    width = max(len(n) for n in marks)
    for name, path in marks.items():
        if os.path.isdir(path):
            shown = path.rstrip("/") + "/  [dir]"
        elif os.path.isfile(path):
            shown = f"{path}  [file]"
        else:
            shown = f"{path}  [missing]"
        print(f"{name:<{width}}  {shown}")


def cmd_remove(name):
    marks = load()
    if name not in marks:
        die(f"no bookmark '{name}'")
    del marks[name]
    save(marks)
    print(f"hop: removed {name}")


def cmd_edit(what="bookmarks"):
    if what == "config":
        target, header = CONFIG, CONFIG_HEADER
    elif what == "bookmarks":
        target, header = DB, DB_HEADER
    else:
        die(f"unknown target '{what}'. try: hop edit [bookmarks|config]")
    if not target.exists():
        _write_pairs(target, header, {})
    os.system(f"{editor()} {shlex.quote(str(target))}")


def cmd_config(key=None, value=None):
    """Show every setting with its current value and how to change it, or set one."""
    if key is None:
        for name, spec in CONFIG_KEYS.items():
            current, source = editor_source()
            print(f"{name} = {current}     (from {source})")
            print(f"    {spec['what']}")
            print(f"    {spec['hint']}")
            print(f"    set it:   hop config {name} nvim        (values: "
                  f"{', '.join(spec['examples'])})")
            print(f"    resolved from: {spec['order']}")
        print(f"\nconfig file: {CONFIG}"
              + ("" if CONFIG.is_file() else "   (not created yet)")
              + "\nedit it by hand: hop edit config")
        return
    if key not in CONFIG_KEYS:
        die(f"unknown setting '{key}'. hop knows: {', '.join(CONFIG_KEYS)}"
            f"\n      run `hop config` to see what each one does")
    if value is None:
        print(editor_source()[0])  # effective value, not just what's in the file
        return
    save_config(dict(load_config(), **{key: value}))
    print(f"hop: {key} = {value}   ({CONFIG})")


_FUNC = '''hop() {
  case "${1:-}" in
    add|list|ls|remove|rm|path|edit|config|init|help|-h|--help|_dispatch)
      command hop "$@" ;;
    jump)
      if [ "$#" -ne 2 ]; then
        command hop "$@"
        return
      fi
      local __hop_cmd
      __hop_cmd=$(command hop _dispatch "$2") || return
      eval "$__hop_cmd"
      ;;
    "") command hop ;;
    *)
      if [ "$#" -ne 1 ]; then
        printf '%s\\n' 'hop: usage: hop NAME' >&2
        return 2
      fi
      local __hop_cmd
      __hop_cmd=$(command hop _dispatch "$1") || return
      eval "$__hop_cmd"
      ;;
  esac
}'''

_BASH_COMP = '''_hop_completions() {
  local f="${HOP_BOOKMARKS:-$HOME/.local/share/hop/bookmarks}"
  local word="${COMP_WORDS[COMP_CWORD]}"
  local names
  names="$(awk -F= \'!/^[[:space:]]*(#|$)/{print $1}\' "$f" 2>/dev/null)"
  if (( COMP_CWORD == 1 )); then
    COMPREPLY=($(compgen -W "add list ls remove rm path edit config init jump help $names" -- "$word"))
    return
  fi
  case "${COMP_WORDS[1]}" in
    remove|rm|path|jump)
      if (( COMP_CWORD == 2 )); then
        COMPREPLY=($(compgen -W "$names" -- "$word"))
      fi
      ;;
    edit)
      if (( COMP_CWORD == 2 )); then
        COMPREPLY=($(compgen -W "bookmarks config" -- "$word"))
      fi
      ;;
    config)
      if (( COMP_CWORD == 2 )); then
        COMPREPLY=($(compgen -W "editor" -- "$word"))
      fi
      ;;
    init)
      if (( COMP_CWORD == 2 )); then
        COMPREPLY=($(compgen -W "bash zsh" -- "$word"))
      fi
      ;;
    add)
      if (( COMP_CWORD == 3 )); then
        compopt -o filenames
        COMPREPLY=($(compgen -f -- "$word"))
      fi
      ;;
  esac
}
complete -F _hop_completions hop'''

_ZSH_COMP = '''_hop() {
  local f="${HOP_BOOKMARKS:-$HOME/.local/share/hop/bookmarks}"
  if (( CURRENT == 2 )); then
    compadd -- add list ls remove rm path edit config init jump help \
      $(awk -F= \'!/^[[:space:]]*(#|$)/{print $1}\' "$f" 2>/dev/null)
    return
  fi
  case "$words[2]" in
    remove|rm|path|jump)
      (( CURRENT == 3 )) &&
        compadd -- $(awk -F= \'!/^[[:space:]]*(#|$)/{print $1}\' "$f" 2>/dev/null)
      ;;
    edit)
      (( CURRENT == 3 )) && compadd -- bookmarks config
      ;;
    config)
      (( CURRENT == 3 )) && compadd -- editor
      ;;
    init)
      (( CURRENT == 3 )) && compadd -- bash zsh
      ;;
    add)
      (( CURRENT == 4 )) && _files
      ;;
  esac
}
# compinit may not have run yet (rc order varies) — register only if it has.
(( $+functions[compdef] )) && compdef _hop hop'''


def cmd_init(shell="bash"):
    if shell not in ("bash", "zsh"):
        die(f"unsupported shell '{shell}'. try: hop init bash|zsh")
    comp = _BASH_COMP if shell == "bash" else _ZSH_COMP
    sys.stdout.write(_FUNC + "\n" + comp + "\n")


def main():
    a = sys.argv[1:]
    if not a or a[0] == "list":
        if len(a) > 1:
            die("usage: hop list")
        cmd_list()
    elif a[0] == "ls":
        if len(a) > 1:
            die("usage: hop ls")
        cmd_list()
    elif a[0] in ("-h", "--help", "help"):
        if len(a) > 1:
            die("usage: hop --help")
        print(__doc__)
    elif a[0] == "path":
        if len(a) != 2:
            die("usage: hop path NAME")
        cmd_path(a[1])
    elif a[0] == "_dispatch":
        if len(a) != 2:
            die("usage: hop _dispatch NAME")
        cmd_dispatch(a[1])
    elif a[0] == "jump":
        if len(a) != 2:
            die("usage: hop jump NAME")
        cmd_dispatch(a[1])
    elif a[0] == "add":
        if len(a) not in (2, 3):
            die("usage: hop add NAME [PATH]")
        cmd_add(a[1], a[2] if len(a) == 3 else ".")
    elif a[0] in ("remove", "rm"):
        if len(a) != 2:
            die(f"usage: hop {a[0]} NAME")
        cmd_remove(a[1])
    elif a[0] == "edit":
        if len(a) > 2:
            die("usage: hop edit [bookmarks|config]")
        cmd_edit(a[1] if len(a) == 2 else "bookmarks")
    elif a[0] == "config":
        if len(a) > 3:
            die("usage: hop config [KEY [VALUE]]")
        cmd_config(a[1] if len(a) > 1 else None, a[2] if len(a) > 2 else None)
    elif a[0] == "init":
        if len(a) != 2:
            die("usage: hop init bash|zsh")
        cmd_init(a[1])
    else:
        if len(a) != 1:
            die("usage: hop NAME")
        cmd_path(a[0], bare=True)  # wrapper absent -> print + explain


if __name__ == "__main__":
    main()
