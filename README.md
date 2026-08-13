# hop — named bookmarks for directories and files

`hop` lets you reach places by **names you choose**, not by frecency.

Bookmark a **directory** and `hop` cds into it. Bookmark a **file** and `hop`
opens it in your editor. One name, one keystroke, the right action.

```bash
hop set work ~/w/work          # a directory
hop set todo ~/notes/todo.md   # a file

hop work    # → cd ~/w/work
hop todo    # → nvim ~/notes/todo.md
```

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/kimtaekkyun/hop/main/install.sh | bash
```

Installs `hop` into `~/.local/bin` and wires the shell wrapper into your rc file.
> `curl | bash` runs a remote script — review it first if you're cautious:
> `curl -fsSL https://raw.githubusercontent.com/kimtaekkyun/hop/main/install.sh | less`.

### git clone

```bash
git clone https://github.com/kimtaekkyun/hop.git
cd hop
./install.sh
```

Same result as the one-liner. The clone is no longer needed after install.
**Upgrade:** `git pull && ./install.sh`.

## Usage

```
hop NAME           cd there (directory) or open it in your editor (file)
hop get NAME       print NAME's resolved path   (scripts: cd "$(hop get NAME)")
hop set NAME [P]   add/overwrite NAME -> P      (P defaults to the current dir)
hop list           list all bookmarks
hop rm NAME        remove NAME
hop edit [what]    open the bookmarks file (or `config`) in your editor
hop config         show every setting: what it does, its value, how to set it
hop config K V     set setting K to V           (settings: editor)
hop init [bash|zsh]  print the shell wrapper for your rc
hop                list all (no args)
```

Tab-completion on bookmark names is included (`hop w<TAB>` → `work`).

`hop list` marks directories with a trailing `/`, and flags bookmarks whose
target has disappeared as `(missing)`.

## Settings

`hop config` is self-documenting — it tells you every setting, its current
value, where that value came from, and the command to change it:

```
$ hop config
editor = vi     (from built-in default)
    Command that opens file bookmarks. Flags are allowed.
    Must stay in the foreground until you close the file, so `code -w`, not `code`.
    set it:   hop config editor nvim        (values: nvim, vim, nano, code -w, subl -w)
    resolved from: $HOP_EDITOR, this file, $VISUAL, $EDITOR, vi

config file: ~/.config/hop/config   (not created yet)
edit it by hand: hop edit config
```

So there is one setting today, `editor`, and one command to change it:

```bash
hop config editor nvim        # set it
hop config editor             # print the effective value
hop config                    # the overview above
```

The value is a command line, so flags work: `hop config editor "code -w"`.

## Why? (vs zoxide / autojump)

zoxide and autojump are **frecency** tools — they learn from your `cd` history
and rank by frequency + recency. Great when you want "jump to wherever I keep
going that matches X".

hop is the other model: **named bookmarks**. You pin a stable name to a path,
and that name always goes there, deterministically. Useful when:

- you want a fixed short name for a long path (no rank drift),
- you want to **share** a set of project locations with a team (commit the bookmark file),
- you want it self-documenting (the names *mean* something),
- you keep going back to specific **files** — a config, a running notes file, a
  scratch TODO — which frecency `cd` tools don't address at all.

They're complements, not substitutes — many people use both.

## Requirements

- **Python 3.6+** — standard library only
- A bourne-ish shell: **bash** or **zsh** (Linux, macOS, Git Bash on Windows)
- On Git Bash, either `python3` or a working Python 3 `python` command

Python is just how `hop` is written — there's nothing to `pip install`, and it's
a single script in `~/.local/bin`, so it stays on your PATH in any virtualenv.

## How it works

An executable can't change its parent shell's directory, so `hop NAME` alone
only *prints* the path. `hop init bash` emits a tiny shell function that asks
`hop` what to do with a name and evaluates the answer — `cd -- <path>` for a
directory, `<editor> <path>` for a file. `eval "$(hop init bash)"` in your rc
loads it, the same pattern zoxide/fzf use.

## Customize

- Bookmarks: `$HOP_BOOKMARKS` (default `~/.local/share/hop/bookmarks`).
- Config: `$HOP_CONFIG` (default `~/.config/hop/config`).
- Both are plain text, one `key=value` per line, `#` comments, hand-editable.
- Shell: `hop init bash` or `hop init zsh`.

## Uninstall

```bash
./uninstall.sh                        # (from the clone) removes the binary + rc wiring
rm -rf ~/.local/share/hop ~/.config/hop   # then, if you want the data gone too
```

## License

MIT
