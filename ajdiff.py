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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #ffffff;
  --fg: #1b1f24;
  --fg-muted: #545d68;
  --header-bg: rgba(255,255,255,0.82);
  --border: #d4d8de;
  --btn-bg: #f0f2f5;
  --btn-hover: #e4e7eb;
  --btn-active-bg: #0550ae;
  --summary-bg: #f0f2f5;
  --sidebar-bg: #f5f6f8;
  --sidebar-width: 280px;
  --header-height: auto;
  --active-file-bg: rgba(5,80,174,0.08);
  --active-file-border: #0550ae;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.06);
  --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
  --radius: 8px;
  --transition: 150ms ease;
}}
[data-theme="dark"] {{
  --bg: #0e1116;
  --fg: #d4dae2;
  --fg-muted: #7d8590;
  --header-bg: rgba(14,17,22,0.82);
  --border: #262c36;
  --btn-bg: #1c2028;
  --btn-hover: #272d38;
  --btn-active-bg: #4184e4;
  --summary-bg: #151921;
  --sidebar-bg: #12161d;
  --active-file-bg: rgba(65,132,228,0.12);
  --active-file-border: #4184e4;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.2);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.3);
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0;
  height: 100%;
  overflow: hidden;
  font-family: var(--sans);
  background: var(--bg);
  color: var(--fg);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

/* === Custom scrollbars === */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
  background: var(--border);
  border-radius: 4px;
}}
::-webkit-scrollbar-thumb:hover {{ background: var(--fg-muted); }}

/* === Sticky header === */
.aj-header {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--header-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
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
  font-size: 13px;
  font-weight: 600;
  font-family: var(--mono);
  letter-spacing: -0.01em;
  margin: 0;
  white-space: nowrap;
}}
.aj-header .aj-meta {{
  font-size: 12px;
  color: var(--fg-muted);
}}
.aj-controls {{
  margin-left: auto;
  display: flex;
  gap: 5px;
  align-items: center;
}}
.aj-btn {{
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  font-family: var(--sans);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--btn-bg);
  color: var(--fg);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--transition), border-color var(--transition), box-shadow var(--transition);
  box-shadow: var(--shadow-sm);
}}
.aj-btn:hover {{
  background: var(--btn-hover);
  box-shadow: var(--shadow-md);
}}
.aj-btn.active {{
  background: var(--btn-active-bg);
  color: white;
  border-color: var(--btn-active-bg);
  box-shadow: 0 0 0 1px var(--btn-active-bg);
}}
.aj-current-file {{
  padding: 5px 20px 7px;
  font-size: 12px;
  font-family: var(--mono);
  color: var(--fg-muted);
  border-top: 1px solid var(--border);
  display: none;
}}
.aj-current-file.visible {{
  display: block;
}}
kbd {{
  display: inline-block;
  padding: 2px 5px;
  font-size: 11px;
  font-family: var(--mono);
  line-height: 1;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--btn-bg);
  color: var(--fg-muted);
  vertical-align: middle;
  box-shadow: var(--shadow-sm);
}}
.aj-keys {{
  font-size: 11px;
  color: var(--fg-muted);
  white-space: nowrap;
  opacity: 0.7;
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
  transition: width var(--transition);
}}
.aj-sidebar.collapsed {{
  width: 0 !important;
  border-right: none;
}}
.aj-sidebar.no-transition {{
  transition: none;
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
  transition: background var(--transition);
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
  padding: 9px 14px;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--sans);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  transition: color var(--transition);
}}
.aj-section-header:hover {{
  color: var(--fg);
}}
.aj-section-toggle {{
  font-size: 9px;
  opacity: 0.6;
}}
.aj-section-body {{
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}}

/* File list */
.aj-file-item {{
  padding: 5px 14px;
  font-size: 12px;
  font-family: var(--mono);
  cursor: pointer;
  border-left: 2px solid transparent;
  word-break: break-all;
  line-height: 1.5;
  transition: background var(--transition), border-color var(--transition);
}}
.aj-file-item:hover {{
  background: var(--btn-hover);
}}
.aj-file-item.active {{
  background: var(--active-file-bg);
  border-left-color: var(--active-file-border);
}}
.aj-file-dir {{
  color: var(--fg-muted);
}}
.aj-file-name {{
  color: var(--fg);
}}

/* Commits list */
.aj-commit-item {{
  padding: 4px 14px;
  font-size: 11px;
  font-family: var(--mono);
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.aj-commit-hash {{
  color: var(--fg-muted);
}}

/* === Main content === */
.aj-main {{
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}}
/* Hide diff content during sidebar resize to avoid expensive reflow */
.aj-main.resizing #diff-container {{
  display: none;
}}
#diff-container {{
  padding: 12px 16px 40px;
}}

/* === diff2html overrides === */

/* Hide diff2html's built-in file list — we have our own sidebar */
.d2h-file-list-wrapper {{
  display: none !important;
}}
/* Disable diff2html's sticky line numbers — breaks in our scroll container */
.d2h-code-linenumber,
.d2h-code-side-linenumber {{
  position: static !important;
}}

/* File wrapper cards */
.d2h-file-wrapper {{
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  overflow: hidden;
  margin-bottom: 12px !important;
  box-shadow: var(--shadow-sm);
}}
.d2h-file-header {{
  background: var(--sidebar-bg) !important;
  border-bottom: 1px solid var(--border) !important;
  padding: 8px 12px !important;
}}
.d2h-file-header .d2h-file-name-wrapper {{
  font-family: var(--mono) !important;
  font-size: 12px !important;
}}

/* Fix sub-pixel hairlines between diff rows */
.d2h-diff-table {{
  border-collapse: collapse !important;
  border-spacing: 0 !important;
  font-family: var(--mono) !important;
  font-size: 12px !important;
  line-height: 1.45 !important;
}}
.d2h-diff-tbody {{
  border: none !important;
}}
.d2h-diff-table tr {{
  border: none !important;
}}
.d2h-ins,
.d2h-del,
.d2h-cntx,
.d2h-info {{
  border: none !important;
}}
/* Kill the 1px cell padding that creates visible gaps */
.d2h-diff-table td {{
  border: none !important;
  padding: 0 !important;
}}
/* Restore just the line-number right separator */
.d2h-code-linenumber,
.d2h-code-side-linenumber {{
  border-right: 1px solid var(--border) !important;
  padding: 0 8px !important;
  font-size: 11px !important;
  color: var(--fg-muted) !important;
  background: var(--sidebar-bg) !important;
  min-width: 40px !important;
  text-align: right !important;
}}
/* Make code line divs fill cells fully */
.d2h-code-line,
.d2h-code-side-line {{
  padding: 0 12px !important;
}}
/* Fix empty placeholder cells showing wrong color */
.d2h-emptyplaceholder {{
  background: var(--bg) !important;
}}
/* Info/hunk header rows */
.d2h-info {{
  background: var(--sidebar-bg) !important;
  color: var(--fg-muted) !important;
}}

/* === Light theme diff colors === */
.d2h-del {{
  background-color: #ffebe9 !important;
}}
.d2h-ins {{
  background-color: #dafbe1 !important;
}}
.d2h-del .d2h-code-line-ctn,
.d2h-del .d2h-code-side-line {{
  background-color: #ffebe9 !important;
}}
.d2h-ins .d2h-code-line-ctn,
.d2h-ins .d2h-code-side-line {{
  background-color: #dafbe1 !important;
}}
/* Inline word-level highlights */
.d2h-del .d2h-code-line-ctn del,
.d2h-del .d2h-code-side-line del {{
  background-color: rgba(255,80,60,0.28) !important;
}}
.d2h-ins .d2h-code-line-ctn ins,
.d2h-ins .d2h-code-side-line ins {{
  background-color: rgba(30,170,70,0.25) !important;
}}
/* Light mode code text needs to be dark */
.d2h-code-line,
.d2h-code-side-line {{
  color: #1b1f24 !important;
}}

/* === Dark theme overrides for diff2html === */
[data-theme="dark"] .d2h-wrapper {{
  --d2h-bg-color: #0e1116;
  --d2h-border-color: #262c36;
}}
[data-theme="dark"] .d2h-file-wrapper {{
  border-color: var(--border) !important;
}}
[data-theme="dark"] .d2h-file-header {{
  background: var(--sidebar-bg) !important;
  border-color: var(--border) !important;
}}
[data-theme="dark"] .d2h-file-header .d2h-file-name {{
  color: var(--fg) !important;
}}
[data-theme="dark"] .d2h-code-linenumber,
[data-theme="dark"] .d2h-code-side-linenumber {{
  background: #151921 !important;
  color: #4a5163 !important;
  border-color: var(--border) !important;
}}
[data-theme="dark"] .d2h-code-line,
[data-theme="dark"] .d2h-code-side-line {{
  background: #0e1116 !important;
  color: #d4dae2 !important;
}}
[data-theme="dark"] .d2h-del {{
  background-color: rgba(248,81,73,0.12) !important;
}}
[data-theme="dark"] .d2h-ins {{
  background-color: rgba(63,185,80,0.12) !important;
}}
[data-theme="dark"] .d2h-del .d2h-code-line-ctn,
[data-theme="dark"] .d2h-del .d2h-code-side-line {{
  background-color: rgba(248,81,73,0.12) !important;
}}
[data-theme="dark"] .d2h-ins .d2h-code-line-ctn,
[data-theme="dark"] .d2h-ins .d2h-code-side-line {{
  background-color: rgba(63,185,80,0.12) !important;
}}
[data-theme="dark"] .d2h-del .d2h-code-line-ctn del,
[data-theme="dark"] .d2h-del .d2h-code-side-line del {{
  background-color: rgba(248,81,73,0.28) !important;
}}
[data-theme="dark"] .d2h-ins .d2h-code-line-ctn ins,
[data-theme="dark"] .d2h-ins .d2h-code-side-line ins {{
  background-color: rgba(63,185,80,0.25) !important;
}}
[data-theme="dark"] .d2h-info {{
  background: #151921 !important;
  color: #4a5163 !important;
  border-color: var(--border) !important;
}}
[data-theme="dark"] .d2h-file-diff .d2h-del.d2h-change {{
  background-color: rgba(248,81,73,0.12) !important;
}}
[data-theme="dark"] .d2h-file-diff .d2h-ins.d2h-change {{
  background-color: rgba(63,185,80,0.12) !important;
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
  const main = document.getElementById('main-scroll');
  let dragging = false;
  let rafPending = false;
  let pendingWidth = 0;
  let activeFileIdx = 0;
  let scrollOffsetInFile = 0;

  handle.addEventListener('mousedown', (e) => {{
    e.preventDefault();
    // Remember which file and scroll offset within it
    const wrappers = document.querySelectorAll('.d2h-file-wrapper');
    const mainTop = main.getBoundingClientRect().top;
    for (let i = 0; i < wrappers.length; i++) {{
      if (wrappers[i].getBoundingClientRect().top <= mainTop) activeFileIdx = i;
    }}
    scrollOffsetInFile = mainTop - wrappers[activeFileIdx].getBoundingClientRect().top;
    dragging = true;
    handle.classList.add('dragging');
    main.classList.add('resizing');
    sidebar.classList.add('no-transition');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }});

  document.addEventListener('mousemove', (e) => {{
    if (!dragging) return;
    pendingWidth = Math.max(120, Math.min(e.clientX, window.innerWidth - 200));
    if (!rafPending) {{
      rafPending = true;
      requestAnimationFrame(() => {{
        sidebar.style.width = pendingWidth + 'px';
        rafPending = false;
      }});
    }}
  }});

  document.addEventListener('mouseup', () => {{
    if (!dragging) return;
    dragging = false;
    handle.classList.remove('dragging');
    main.classList.remove('resizing');
    sidebar.classList.remove('no-transition');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    localStorage.setItem('ajdiff-sidebar-width', sidebar.style.width);
    // Restore scroll to the exact position within the file
    const wrappers = document.querySelectorAll('.d2h-file-wrapper');
    if (wrappers[activeFileIdx]) {{
      wrappers[activeFileIdx].scrollIntoView({{ block: 'start' }});
      main.scrollTop += scrollOffsetInFile;
    }}
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
