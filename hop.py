#!/usr/bin/env python3
"""hop — named bookmarks for directories and files.

  hop NAME           go to NAME: cd if it points at a directory, open it in
                     your editor if it points at a file
  hop get NAME       print NAME's resolved path   (scripts: cd "$(hop get NAME)")
  hop set NAME [P]   add/overwrite NAME -> P   (P defaults to the current dir)
  hop list           list all bookmarks
  hop rm NAME        remove NAME
  hop edit [what]    open the bookmarks file (or `config`) in your editor
  hop config [K [V]] show config, or set key K to V  (e.g. hop config editor nvim)
  hop init [bash|zsh]  print shell wrapper for rc — eval "$(hop init bash)"
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

CONFIG_KEYS = ("editor",)


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


def editor():
    """The command used to open file bookmarks. May carry flags (`code -w`)."""
    return (
        os.environ.get("HOP_EDITOR")
        or load_config().get("editor")
        or os.environ.get("VISUAL")
        or os.environ.get("EDITOR")
        or "vi"
    )


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


def cmd_get(name):
    print(lookup(name))


def cmd_dispatch(name):
    """Emit the shell command the wrapper should eval for `hop NAME`."""
    path = lookup(name)
    if os.path.isdir(path):
        print(f"cd -- {shlex.quote(shell_path(path))}")
    elif os.path.isfile(path):
        print(f"{editor()} {shlex.quote(shell_path(path))}")
    else:
        die(f"'{name}' points at a missing path: {path}")


def cmd_set(name, path="."):
    marks = load()
    path = resolve(path)
    marks[name] = path
    save(marks)
    if os.path.isdir(path):
        kind = "dir, cd"
    elif os.path.isfile(path):
        kind = f"file, opens in {editor()}"
    else:
        kind = "missing — nothing there yet"
    print(f"hop: {name} -> {path}  ({kind})")


def cmd_list():
    marks = load()
    if not marks:
        print(f"hop: no bookmarks. add: hop set <name> [path]   (db: {DB})")
        return
    width = max(len(n) for n in marks)
    for name, path in marks.items():
        if os.path.isdir(path):
            shown = path.rstrip("/") + "/"
        elif os.path.isfile(path):
            shown = path
        else:
            shown = f"{path}  (missing)"
        print(f"{name:<{width}}  {shown}")


def cmd_rm(name):
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
    cfg = load_config()
    if key is None:
        print(f"# {CONFIG}")
        for k, v in cfg.items():
            print(f"{k}={v}")
        if "editor" not in cfg:
            print(f"# editor is unset — using {editor()} (from $HOP_EDITOR/$VISUAL/$EDITOR)")
        return
    if key not in CONFIG_KEYS:
        die(f"unknown config key '{key}'. known keys: {', '.join(CONFIG_KEYS)}")
    if value is None:
        print(cfg.get(key, ""))
        return
    cfg[key] = value
    save_config(cfg)
    print(f"hop: {key}={value}   ({CONFIG})")


_FUNC = '''hop() {
  case "${1:-}" in
    get|set|rm|del|list|edit|config|init|help|-h|--help|_dispatch) command hop "$@" ;;
    "") command hop ;;
    *)
      local __hop_cmd
      __hop_cmd=$(command hop _dispatch "$1") || return
      eval "$__hop_cmd"
      ;;
  esac
}'''

_BASH_COMP = '''_hop_completions() {
  local f="${HOP_BOOKMARKS:-$HOME/.local/share/hop/bookmarks}"
  COMPREPLY=($(compgen -W "$(awk -F= \'!/^[[:space:]]*(#|$)/{print $1}\' "$f" 2>/dev/null)" -- "${COMP_WORDS[COMP_CWORD]}"))
}
complete -F _hop_completions hop'''

_ZSH_COMP = '''_hop() {
  local f="${HOP_BOOKMARKS:-$HOME/.local/share/hop/bookmarks}"
  compadd -- $(awk -F= \'!/^[[:space:]]*(#|$)/{print $1}\' "$f" 2>/dev/null)
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
        cmd_list()
    elif a[0] in ("-h", "--help", "help"):
        print(__doc__)
    elif a[0] == "get":
        cmd_get(a[1]) if len(a) > 1 else die("usage: hop get NAME")
    elif a[0] == "_dispatch":
        cmd_dispatch(a[1]) if len(a) > 1 else die("usage: hop _dispatch NAME")
    elif a[0] == "set":
        if len(a) < 2:
            die("usage: hop set NAME [PATH]")
        cmd_set(a[1], a[2] if len(a) > 2 else ".")
    elif a[0] in ("rm", "del"):
        cmd_rm(a[1]) if len(a) > 1 else die("usage: hop rm NAME")
    elif a[0] == "edit":
        cmd_edit(a[1] if len(a) > 1 else "bookmarks")
    elif a[0] == "config":
        cmd_config(a[1] if len(a) > 1 else None, a[2] if len(a) > 2 else None)
    elif a[0] == "init":
        cmd_init(a[1] if len(a) > 1 else "bash")
    else:
        cmd_get(a[0])  # bare name -> get


if __name__ == "__main__":
    main()
