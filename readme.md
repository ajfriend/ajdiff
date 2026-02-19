# ajdiff

A local Git diff viewer that opens a GitHub-PR-like side-by-side diff in your browser.

## Usage

```bash
uv run ajdiff.py                     # diff current branch vs master
uv run ajdiff.py main                # diff current branch vs main
uv run ajdiff.py v4.0.0              # diff current branch vs a tag
uv run ajdiff.py feature-a feature-b # diff between two refs
```

## Features

- Side-by-side and unified diff views (toggle with the Split button)
- Collapsible file tree with path compression and file status badges (Added, Modified, Deleted, Renamed)
- Syntax highlighting via highlight.js
- Dark and light themes (respects system preference, toggle with Theme button)
- Keyboard navigation: `Ctrl-n` / `Ctrl-p` to jump between files, `b` to toggle sidebar
- Resizable sidebar
- Commit list with timestamps
- Right-click files to copy `subl` command or file path

## Options

| Flag        | Description                                        |
|-------------|----------------------------------------------------|
| `--output`  | Save HTML to a specific path instead of a tempfile |
| `--no-open` | Print the file path without opening the browser    |


## References

- [Running scripts with uv](https://docs.astral.sh/uv/guides/scripts/)
- [One-shot Python tools](https://simonwillison.net/2024/Dec/19/one-shot-python-tools/)
