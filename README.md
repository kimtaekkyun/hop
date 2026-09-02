# hop — named targets for directories, files, and commands

`hop` lets you reach places by **names you choose**, not by frecency.

Bookmark a **directory** and `hop` cds into it. Bookmark a **file** and `hop`
opens it in your editor. Save a **command** and `hop` runs it. One name, one
keystroke, the right action.

```bash
hop add work ~/w/work          # a directory
hop add todo ~/notes/todo.md   # a file
hop add rncdc 'ssh -p 56030 worker@taekkyunkim-rncdc.vbee.lge.com'  # a command

hop work    # → cd ~/w/work
hop todo    # → nvim ~/notes/todo.md
hop rncdc   # → ssh -p 56030 worker@taekkyunkim-rncdc.vbee.lge.com
```

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/kimtaekkyun/hop/main/install.sh | bash
```

Installs `hop` into `~/.local/bin` and wires the shell wrapper into your rc file.
After installing or upgrading, refresh an existing shell with
`eval "$(command hop init bash)"` (or start a new shell).
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
hop NAME           cd (directory), open (file), or run (command)
hop jump NAME      explicit form of `hop NAME` (also works for reserved names)
hop add NAME [T]   add/update NAME -> T         (T defaults to the current dir)
hop list           list all bookmarks           (shortcut: `hop ls`)
hop remove NAME    remove NAME                  (shortcut: `hop rm`)
hop path NAME      print NAME's path            (scripts: `cd "$(hop path NAME)"`)
hop edit [bookmarks|config]
                   open the selected file in your editor (bookmarks by default)
hop config         show every setting: what it does, its value, how to set it
hop config K V     set setting K to V           (settings: editor)
hop init bash|zsh  print the shell wrapper for your rc
hop                list all (no args)
```

Tab-completion on bookmark names is included (`hop w<TAB>` → `work`).

`hop list` marks entries as `[dir]`, `[file]`, `[cmd]`, or `[missing]`.

### Target classification

`hop add` keeps the short syntax and classifies the target automatically:

- an existing directory or file is a path target,
- a command whose first token resolves on `PATH` is a command target,
- a missing path-shaped value remains a path target.

So an existing `dothis.py` opens in the editor, while `python3 dothis.py`
runs as a command:

```bash
hop add dothis ./dothis.py
hop add dothis 'python3 dothis.py'
```

The target type is stored with the entry, so a missing path is not later
mistaken for a command. Existing `name=/path` bookmark files remain valid.
Command targets use an executable and its arguments; shell operators such as
`|` and `&&` are passed as arguments rather than interpreted by a shell.

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

hop is the other model: **named targets**. You pin a stable name to a path or
command, and that name always performs the same action, deterministically. Useful when:

- you want a fixed short name for a long path (no rank drift),
- you want to **share** a set of project locations with a team (commit the bookmark file),
- you want it self-documenting (the names *mean* something),
- you keep going back to specific **files** — a config, a running notes file, a
  scratch TODO — which frecency `cd` tools don't address at all,
- you want a short name for a repeated command such as an SSH connection.

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
directory, `<editor> <path>` for a file, or a safely quoted command for a
command target. `eval "$(hop init bash)"` in your rc loads it, the same pattern
zoxide/fzf use. `hop jump NAME` is the explicit form when a target name
conflicts with a command such as `list` or `config`.

## Customize

- Bookmarks: `$HOP_BOOKMARKS` (default `~/.local/share/hop/bookmarks`).
- Config: `$HOP_CONFIG` (default `~/.config/hop/config`).
- Both are plain text, one `key=value` per line, `#` comments, hand-editable.
Existing plain values are paths; new command targets use the `cmd:` prefix.
- Shell: `hop init bash` or `hop init zsh`.

## Uninstall

```bash
./uninstall.sh                        # (from the clone) removes the binary + rc wiring
rm -rf ~/.local/share/hop ~/.config/hop   # then, if you want the data gone too
```

## License

MIT
