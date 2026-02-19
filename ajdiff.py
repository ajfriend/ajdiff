# /// script
# requires-python = ">=3.12"
# dependencies = ["typer"]
# ///
"""ajdiff — Local Git PR Diff Viewer.

Generates a GitHub-PR-like diff view in the browser using diff2html.
"""

import json
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    help="Generate a GitHub-PR-like diff view in the browser.",
    no_args_is_help=False,
)
console = Console(stderr=True)

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/diff2html/bundles/css/diff2html.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release/build/styles/github.min.css" id="hljs-light">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release/build/styles/github-dark.min.css" id="hljs-dark" disabled>
<style>
:root {{
  --bg: #ffffff;
  --fg: #1f2328;
  --header-bg: #f6f8fa;
  --border: #d1d9e0;
  --btn-bg: #f3f4f6;
  --btn-hover: #e5e7eb;
  --summary-bg: #f6f8fa;
  --sidebar-bg: #f6f8fa;
  --sidebar-width: 280px;
  --header-height: auto;
  --active-file-bg: rgba(9,105,218,0.1);
  --active-file-border: #0969da;
}}
[data-theme="dark"] {{
  --bg: #0d1117;
  --fg: #e6edf3;
  --header-bg: #161b22;
  --border: #30363d;
  --btn-bg: #21262d;
  --btn-hover: #30363d;
  --summary-bg: #161b22;
  --sidebar-bg: #161b22;
  --active-file-bg: rgba(56,139,253,0.15);
  --active-file-border: #58a6ff;
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0;
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--fg);
}}

/* === Sticky header === */
.aj-header {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--header-bg);
  border-bottom: 1px solid var(--border);
}}
.aj-header-top {{
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}}
.aj-header h1 {{
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  white-space: nowrap;
}}
.aj-header .aj-meta {{
  font-size: 13px;
  opacity: 0.7;
}}
.aj-controls {{
  margin-left: auto;
  display: flex;
  gap: 6px;
  align-items: center;
}}
.aj-btn {{
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--btn-bg);
  color: var(--fg);
  cursor: pointer;
  white-space: nowrap;
}}
.aj-btn:hover {{ background: var(--btn-hover); }}
.aj-btn.active {{
  background: #0969da;
  color: white;
  border-color: #0969da;
}}
.aj-current-file {{
  padding: 4px 20px 8px;
  font-size: 13px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  color: var(--fg);
  opacity: 0.8;
  border-top: 1px solid var(--border);
  display: none;
}}
.aj-current-file.visible {{
  display: block;
}}
kbd {{
  display: inline-block;
  padding: 1px 5px;
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, monospace;
  border: 1px solid var(--border);
  border-radius: 3px;
  background: var(--btn-bg);
  vertical-align: middle;
}}
.aj-keys {{
  font-size: 11px;
  opacity: 0.5;
  white-space: nowrap;
}}

/* === Layout === */
.aj-layout {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
}}
.aj-body {{
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}}

/* === Sidebar === */
.aj-sidebar {{
  width: var(--sidebar-width);
  min-width: 0;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}}
.aj-sidebar.collapsed {{
  width: 0 !important;
}}
.aj-sidebar.collapsed .aj-sidebar-content,
.aj-sidebar.collapsed + .aj-resize-handle {{
  display: none;
}}
/* === Resize handle === */
.aj-resize-handle {{
  width: 4px;
  cursor: col-resize;
  background: transparent;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}}
.aj-resize-handle:hover,
.aj-resize-handle.dragging {{
  background: var(--active-file-border);
}}
.aj-resize-handle::after {{
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -3px;
  right: -3px;
}}
.aj-sidebar-content {{
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}}
.aj-sidebar-section {{
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}
.aj-sidebar-section.aj-files-section {{
  flex: 1;
  min-height: 0;
}}
.aj-sidebar-section.aj-commits-section {{
  border-top: 1px solid var(--border);
  max-height: 40%;
  flex-shrink: 0;
}}
.aj-sidebar-section.aj-commits-section.collapsed-section {{
  max-height: none;
  flex: 0 0 auto;
}}
.aj-sidebar-section.aj-commits-section.collapsed-section .aj-section-body {{
  display: none;
}}
.aj-section-header {{
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.6;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}}
.aj-section-header:hover {{
  opacity: 0.8;
}}
.aj-section-toggle {{
  font-size: 10px;
}}
.aj-section-body {{
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}}

/* File list */
.aj-file-item {{
  padding: 5px 12px;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  cursor: pointer;
  border-left: 3px solid transparent;
  word-break: break-all;
  line-height: 1.4;
}}
.aj-file-item:hover {{
  background: var(--btn-hover);
}}
.aj-file-item.active {{
  background: var(--active-file-bg);
  border-left-color: var(--active-file-border);
}}
.aj-file-dir {{
  opacity: 0.5;
}}
.aj-file-name {{
  opacity: 1;
}}

/* Commits list */
.aj-commit-item {{
  padding: 4px 12px;
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.aj-commit-hash {{
  opacity: 0.5;
}}

/* === Main content === */
.aj-main {{
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}}
#diff-container {{
  padding: 16px 20px 40px;
}}

/* Hide diff2html's built-in file list — we have our own sidebar */
.d2h-file-list-wrapper {{
  display: none !important;
}}
/* Disable diff2html's sticky line numbers — breaks in our scroll container */
.d2h-code-linenumber,
.d2h-code-side-linenumber {{
  position: static !important;
}}

/* Dark theme overrides for diff2html */
[data-theme="dark"] .d2h-wrapper {{
  --d2h-bg-color: #0d1117;
  --d2h-border-color: #30363d;
}}
[data-theme="dark"] .d2h-file-header {{
  background: #161b22 !important;
  border-color: #30363d !important;
}}
[data-theme="dark"] .d2h-file-header .d2h-file-name {{
  color: #e6edf3 !important;
}}
[data-theme="dark"] .d2h-code-linenumber,
[data-theme="dark"] .d2h-code-side-linenumber {{
  background: #161b22 !important;
  color: #8b949e !important;
  border-color: #30363d !important;
}}
[data-theme="dark"] .d2h-code-line,
[data-theme="dark"] .d2h-code-side-line {{
  background: #0d1117 !important;
  color: #e6edf3 !important;
}}
[data-theme="dark"] .d2h-del {{
  background-color: rgba(248,81,73,0.15) !important;
}}
[data-theme="dark"] .d2h-ins {{
  background-color: rgba(63,185,80,0.15) !important;
}}
[data-theme="dark"] .d2h-del .d2h-code-line-ctn,
[data-theme="dark"] .d2h-del .d2h-code-side-line {{
  background-color: rgba(248,81,73,0.15) !important;
}}
[data-theme="dark"] .d2h-ins .d2h-code-line-ctn,
[data-theme="dark"] .d2h-ins .d2h-code-side-line {{
  background-color: rgba(63,185,80,0.15) !important;
}}
[data-theme="dark"] .d2h-info {{
  background: #161b22 !important;
  color: #8b949e !important;
  border-color: #30363d !important;
}}
[data-theme="dark"] .d2h-file-diff .d2h-del.d2h-change {{
  background-color: rgba(248,81,73,0.15) !important;
}}
[data-theme="dark"] .d2h-file-diff .d2h-ins.d2h-change {{
  background-color: rgba(63,185,80,0.15) !important;
}}
</style>
</head>
<body>
<div class="aj-layout">
  <!-- Sticky header -->
  <div class="aj-header">
    <div class="aj-header-top">
      <h1>{title}</h1>
      <span class="aj-meta">{meta}</span>
      <div class="aj-controls">
        <span class="aj-keys"><kbd>j</kbd><kbd>k</kbd> nav</span>
        <button class="aj-btn" id="btn-sidebar" onclick="toggleSidebar()" title="Toggle sidebar (b)">Sidebar</button>
        <button class="aj-btn" id="btn-split" onclick="toggleView()">Split</button>
        <button class="aj-btn" id="btn-theme" onclick="toggleTheme()">Theme</button>
      </div>
    </div>
    <div class="aj-current-file" id="current-file"></div>
  </div>

  <!-- Body: sidebar + main -->
  <div class="aj-body">
    <div class="aj-sidebar" id="sidebar">
      <div class="aj-sidebar-content">
        <!-- File list -->
        <div class="aj-sidebar-section aj-files-section">
          <div class="aj-section-header">
            <span>Files</span>
          </div>
          <div class="aj-section-body" id="file-list"></div>
        </div>
        <!-- Commits -->
        <div class="aj-sidebar-section aj-commits-section" id="commits-section">
          <div class="aj-section-header" onclick="toggleCommits()">
            <span>Commits ({num_commits})</span>
            <span class="aj-section-toggle" id="commits-toggle">&#9660;</span>
          </div>
          <div class="aj-section-body" id="commits-list">{commits_html}</div>
        </div>
      </div>
    </div>
    <div class="aj-resize-handle" id="resize-handle"></div>
    <div class="aj-main" id="main-scroll">
      <div id="diff-container"></div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/diff2html/bundles/js/diff2html-ui.min.js"></script>
<script>
const diffString = {diff_json};
let currentView = 'side-by-side';
const mainScroll = document.getElementById('main-scroll');

function render(view) {{
  currentView = view;
  const targetEl = document.getElementById('diff-container');
  const config = {{
    drawFileList: false,
    fileContentToggle: true,
    matching: 'lines',
    outputFormat: view,
    highlight: true,
    renderNothingWhenEmpty: false,
  }};
  const ui = new Diff2HtmlUI(targetEl, diffString, config);
  ui.draw();
  ui.highlightCode();

  document.getElementById('btn-split').classList.toggle('active', view === 'side-by-side');

  buildFileList();
  updateCurrentFile();
}}

/* === File list sidebar === */
function buildFileList() {{
  const container = document.getElementById('file-list');
  container.innerHTML = '';
  const wrappers = document.querySelectorAll('.d2h-file-wrapper');
  wrappers.forEach((w, i) => {{
    const nameEl = w.querySelector('.d2h-file-name');
    const fullPath = nameEl ? nameEl.textContent.trim() : `File ${{i + 1}}`;
    const item = document.createElement('div');
    item.className = 'aj-file-item';
    item.dataset.index = i;

    // Split into dir + filename
    const lastSlash = fullPath.lastIndexOf('/');
    if (lastSlash >= 0) {{
      item.innerHTML = '<span class="aj-file-dir">' + fullPath.substring(0, lastSlash + 1) + '</span>'
        + '<span class="aj-file-name">' + fullPath.substring(lastSlash + 1) + '</span>';
    }} else {{
      item.innerHTML = '<span class="aj-file-name">' + fullPath + '</span>';
    }}

    item.addEventListener('click', () => {{
      wrappers[i].scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }});
    container.appendChild(item);
  }});
}}

/* === Current file tracking === */
function updateCurrentFile() {{
  const wrappers = document.querySelectorAll('.d2h-file-wrapper');
  const items = document.querySelectorAll('.aj-file-item');
  const currentFileEl = document.getElementById('current-file');
  if (!wrappers.length) return;

  let activeIdx = 0;
  for (let i = 0; i < wrappers.length; i++) {{
    const rect = wrappers[i].getBoundingClientRect();
    // The wrapper is "current" if its top is above middle of viewport
    if (rect.top <= 150) activeIdx = i;
  }}

  items.forEach((item, i) => {{
    item.classList.toggle('active', i === activeIdx);
  }});

  // Scroll active item into view in sidebar
  const activeItem = items[activeIdx];
  if (activeItem) {{
    activeItem.scrollIntoView({{ block: 'nearest' }});
  }}

  // Update header current file
  const nameEl = wrappers[activeIdx]?.querySelector('.d2h-file-name');
  if (nameEl) {{
    currentFileEl.textContent = nameEl.textContent.trim();
    currentFileEl.classList.add('visible');
  }}
}}

mainScroll.addEventListener('scroll', updateCurrentFile);

function setView(view) {{
  render(view);
  localStorage.setItem('ajdiff-view', view);
}}

function toggleView() {{
  setView(currentView === 'side-by-side' ? 'line-by-line' : 'side-by-side');
}}

/* === Sidebar toggle === */
function toggleSidebar() {{
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.toggle('collapsed');
  localStorage.setItem('ajdiff-sidebar', sidebar.classList.contains('collapsed') ? 'collapsed' : 'open');
}}

/* === Commits toggle === */
function toggleCommits() {{
  const section = document.getElementById('commits-section');
  const toggle = document.getElementById('commits-toggle');
  section.classList.toggle('collapsed-section');
  toggle.innerHTML = section.classList.contains('collapsed-section') ? '&#9654;' : '&#9660;';
}}

/* === Theme === */
function getPreferredTheme() {{
  const stored = localStorage.getItem('ajdiff-theme');
  if (stored) return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}}

function applyTheme(theme) {{
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('hljs-light').disabled = (theme === 'dark');
  document.getElementById('hljs-dark').disabled = (theme === 'light');
}}

function toggleTheme() {{
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  localStorage.setItem('ajdiff-theme', next);
  applyTheme(next);
  render(currentView);
}}

/* === Keyboard navigation === */
document.addEventListener('keydown', (e) => {{
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  const files = document.querySelectorAll('.d2h-file-wrapper');
  if (!files.length) return;

  if (e.key === 'j' || e.key === 'k') {{
    e.preventDefault();
    let current = -1;
    for (let i = 0; i < files.length; i++) {{
      if (files[i].getBoundingClientRect().top <= 150) current = i;
    }}
    let target;
    if (e.key === 'j') target = Math.min(current + 1, files.length - 1);
    else target = Math.max(current - 1, 0);
    files[target].scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}
  if (e.key === 'b') {{
    e.preventDefault();
    toggleSidebar();
  }}
}});

/* === Sidebar resize drag === */
(function() {{
  const handle = document.getElementById('resize-handle');
  const sidebar = document.getElementById('sidebar');
  let dragging = false;

  handle.addEventListener('mousedown', (e) => {{
    e.preventDefault();
    dragging = true;
    handle.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }});

  document.addEventListener('mousemove', (e) => {{
    if (!dragging) return;
    const newWidth = Math.max(120, Math.min(e.clientX, window.innerWidth - 200));
    sidebar.style.width = newWidth + 'px';
  }});

  document.addEventListener('mouseup', () => {{
    if (!dragging) return;
    dragging = false;
    handle.classList.remove('dragging');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    localStorage.setItem('ajdiff-sidebar-width', sidebar.style.width);
  }});
}})();

/* === Adjust layout for header height === */
function adjustHeaderOffset() {{
  const header = document.querySelector('.aj-header');
  const body = document.querySelector('.aj-body');
  if (header && body) {{
    body.style.paddingTop = header.offsetHeight + 'px';
  }}
}}

const resizeObserver = new ResizeObserver(adjustHeaderOffset);
resizeObserver.observe(document.querySelector('.aj-header'));

/* === Init === */
applyTheme(getPreferredTheme());

// Restore sidebar state
if (localStorage.getItem('ajdiff-sidebar') === 'collapsed') {{
  document.getElementById('sidebar').classList.add('collapsed');
}}
const savedWidth = localStorage.getItem('ajdiff-sidebar-width');
if (savedWidth) {{
  document.getElementById('sidebar').style.width = savedWidth;
}}

const savedView = localStorage.getItem('ajdiff-view') || 'side-by-side';
render(savedView);
adjustHeaderOffset();
</script>
</body>
</html>
"""


def git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )


def is_git_repo() -> bool:
    result = git("rev-parse", "--is-inside-work-tree")
    return result.returncode == 0


def get_merge_base(base: str, head: str) -> str | None:
    result = git("merge-base", base, head)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def parse_diff_stats(diff_text: str) -> tuple[int, int, int]:
    """Parse diff text to count files, additions, deletions."""
    files = 0
    additions = 0
    deletions = 0
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            files += 1
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return files, additions, deletions


@app.command()
def main(
    base: Annotated[
        str,
        typer.Argument(help="Base ref to diff against (default: master)."),
    ] = "master",
    head: Annotated[
        str,
        typer.Argument(help="Head ref (default: HEAD)."),
    ] = "HEAD",
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Save HTML to this path instead of a temp file."),
    ] = None,
    no_open: Annotated[
        bool,
        typer.Option("--no-open", help="Print the file path without opening the browser."),
    ] = False,
) -> None:
    """Generate a GitHub-PR-like diff view in the browser.

    \b
    Examples:
        ajdiff                     # diff current branch vs master
        ajdiff main                # diff current branch vs main
        ajdiff v4.0.0              # diff current branch vs a tag
        ajdiff feature-a feature-b # diff between two refs
    """
    if not is_git_repo():
        console.print("[bold red]Error:[/] not inside a git repository.")
        raise typer.Exit(1)

    # Get the diff
    with console.status("[bold]Running git diff..."):
        diff_result = git("diff", f"{base}...{head}")

    if diff_result.returncode != 0:
        stderr = diff_result.stderr.strip()
        console.print(f"[bold red]Error:[/] git diff failed: {stderr}")
        raise typer.Exit(1)

    diff_text = diff_result.stdout
    if not diff_text.strip():
        console.print("[yellow]No differences found.[/]")
        raise typer.Exit(0)

    # Stats
    num_files, additions, deletions = parse_diff_stats(diff_text)
    console.print(
        f"[bold]{num_files}[/] files changed, "
        f"[green]+{additions}[/] / [red]-{deletions}[/]"
    )

    # Commit log
    log_result = git("log", "--oneline", f"{base}..{head}")
    commits_text = log_result.stdout.strip() if log_result.returncode == 0 else ""
    num_commits = len(commits_text.splitlines()) if commits_text else 0

    # Branch names for title
    branch_result = git("rev-parse", "--abbrev-ref", "HEAD")
    current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else head

    title = f"{base} ... {current_branch}" if head == "HEAD" else f"{base} ... {head}"
    meta = f"{num_files} files changed, {num_commits} commits"

    commits_html = ""
    if commits_text:
        for line in commits_text.splitlines():
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            parts = escaped.split(" ", 1)
            hash_part = parts[0]
            msg_part = parts[1] if len(parts) > 1 else ""
            commits_html += (
                f'<div class="aj-commit-item">'
                f'<span class="aj-commit-hash">{hash_part}</span> {msg_part}'
                f'</div>'
            )

    html = HTML_TEMPLATE.format(
        title=title,
        meta=meta,
        num_commits=num_commits,
        commits_html=commits_html,
        diff_json=json.dumps(diff_text),
    )

    # Write output
    if output:
        out_path = output.resolve()
        out_path.write_text(html)
    else:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".html", prefix="ajdiff-", delete=False, mode="w"
        )
        tmp.write(html)
        tmp.close()
        out_path = Path(tmp.name)

    console.print(f"[dim]{out_path}[/]")

    if not no_open:
        webbrowser.open(f"file://{out_path}")


if __name__ == "__main__":
    app()
