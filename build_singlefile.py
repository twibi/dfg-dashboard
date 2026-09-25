#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the single-file distribution outputs for the DFG dashboard.

Outputs
-------
dist/dfg-dashboard-wordpress.html   WordPress Custom-HTML-block fragment
dist/dfg-dashboard-standalone.html  standalone HTML document (double-click to open)

Both files are fully self-contained: scoped CSS, the chart library and the
generated data are inlined as ordinary text. The fragment carries no
<html>/<head>/<body>, no doctype and no <script src>, so it can be pasted
straight into a WordPress Custom HTML block.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

HTML_FILE = ROOT / "index.html"
CSS_FILE = ROOT / "assets" / "css" / "style.css"
JS_FILES = [
    ROOT / "assets" / "vendor" / "chart.umd.min.js",
    ROOT / "assets" / "js" / "data.js",
    ROOT / "assets" / "js" / "dashboard.js",
]

FRAGMENT_OUT = DIST / "dfg-dashboard-wordpress.html"
STANDALONE_OUT = DIST / "dfg-dashboard-standalone.html"

STYLES_PLACEHOLDER = "<!--DFG_STYLES-->"

# every class the app actually renders must be covered by the scoped stylesheet
REQUIRED_CSS_CLASSES = (
    "dfg-root",
    "dash-topbar", "dash-topbar-inner", "dash-brand",
    "dash-page", "dash-section", "dash-head", "dash-sub", "dash-insight",
    "dash-levelbar",
    "dash-card", "dash-row", "dash-group", "dash-label",
    "dash-seg", "dash-seg-btn", "dash-select", "dash-years", "dash-sep",
    "dash-spacer", "dash-actions", "dash-btn",
    "dash-check", "dash-chk",
    "dash-pill-line", "dash-pills", "dash-pill", "dash-pill-actions",
    "dash-mini", "dash-dot", "dash-note",
    "dash-caption", "dash-foot", "dash-chart", "dash-empty",
)

FORBIDDEN_PATTERNS = (
    (re.compile(r"<script[^>]*\bsrc\s*=", re.I), "<script src>"),
    (re.compile(r"<link[^>]*\brel\s*=\s*[\"']?stylesheet", re.I), "external stylesheet"),
    (re.compile(r"<img[^>]*\bsrc\s*=\s*[\"']?(?!data:)[^\"'>]*", re.I), "external image"),
    (re.compile(r"<(?:iframe|object|embed)\b", re.I), "embedded frame"),
    (re.compile(r"@import", re.I), "@import"),
    (re.compile(r"url\(\s*[\"']?(?:https?:)?//", re.I), "remote url()"),
)


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing input file: {path}")
    return path.read_text(encoding="utf-8")


def style_block(css: str) -> str:
    return (
        "<style>\n"
        "/* ==== dfg-dashboard: begin scoped styles (generated) ==== */\n"
        f"{css.rstrip()}\n"
        "/* ==== dfg-dashboard: end scoped styles ==== */\n"
        "</style>"
    )


def script_block(scripts: list[str]) -> str:
    body = "\n".join(scripts)
    return (
        "<script>\n"
        "/* ==== dfg-dashboard: begin inlined scripts (generated) ==== */\n"
        f"{body}\n"
        "/* ==== dfg-dashboard: end inlined scripts ==== */\n"
        "</script>"
    )


def body_html_of(index_html: str) -> str:
    """The markup that lives between <body> and its scripts (usually empty)."""
    m = re.search(r"<body[^>]*>(.*)</body>", index_html, re.S | re.I)
    if not m:
        fail("index.html has no <body> element")
    inner = m.group(1)
    inner = re.sub(r"<script\b.*?</script>", "", inner, flags=re.S | re.I)
    inner = inner.replace(STYLES_PLACEHOLDER, "")
    return inner.strip()


def assert_scoped(css: str) -> None:
    if ".dfg-root" not in css:
        fail("style.css does not contain the .dfg-root scoping selector")
    for cls in REQUIRED_CSS_CLASSES:
        if f".{cls}" not in css:
            fail(f"style.css is missing required class .{cls}")


def assert_self_contained(content: str, name: str) -> None:
    for pat, what in FORBIDDEN_PATTERNS:
        if pat.search(content):
            fail(f"{name} contains an external reference: {what}")


def main() -> None:
    index_html = read(HTML_FILE)
    css = read(CSS_FILE)
    scripts = [read(p) for p in JS_FILES]

    if STYLES_PLACEHOLDER not in index_html:
        fail(f"index.html is missing the {STYLES_PLACEHOLDER} placeholder")

    assert_scoped(css)

    style = style_block(css)
    script = script_block(scripts)
    markup = body_html_of(index_html)

    # ---- WordPress fragment: style + markup + one inline script ------------
    fragment = style + "\n\n" + markup + ("\n\n" if markup else "") + script + "\n"

    # ---- Standalone document ----------------------------------------------
    head_m = re.search(r"<head>.*</head>", index_html, re.S | re.I)
    if not head_m:
        fail("index.html has no <head> element")
    head = head_m.group(0).replace(STYLES_PLACEHOLDER, style)
    # dev-time <link> is superseded by the inlined <style>
    head = re.sub(
        r'[ \t]*<link\b[^>]*href="assets/css/style\.css"[^>]*>\r?\n?',
        "", head,
    )
    if STYLES_PLACEHOLDER in head:
        fail(f"{STYLES_PLACEHOLDER} did not get replaced inside <head>")
    if STYLES_PLACEHOLDER in index_html[: head_m.start()] or STYLES_PLACEHOLDER in index_html[head_m.end():]:
        fail(f"{STYLES_PLACEHOLDER} must live inside <head>")

    standalone = index_html
    standalone = standalone[: head_m.start()] + head + standalone[head_m.end():]

    body_m = re.search(r"(<body[^>]*>).*?(</body>)", standalone, re.S | re.I)
    if not body_m:
        fail("standalone build: no <body> element")
    new_body = body_m.group(1) + "\n" + markup + ("\n" if markup else "") + script + "\n" + body_m.group(2)
    standalone = standalone[: body_m.start()] + new_body + standalone[body_m.end():]
    standalone = standalone.replace("\t", "    ")

    # ---- assertions --------------------------------------------------------
    assert_self_contained(fragment, "fragment")
    m = re.search(r"<style>(.*?)</style>", fragment, re.S)
    if not m:
        fail("fragment: no inlined <style> block")
    assert_scoped(m.group(1))
    if "<!doctype" in fragment.lower():
        fail("fragment: must not carry a doctype")
    if re.search(r"</?(?:html|head|body)\b", fragment, re.I):
        fail("fragment: must not contain <html>/<head>/<body> tags")

    assert_self_contained(standalone, "standalone")
    m = re.search(r"<style>(.*?)</style>", standalone, re.S)
    if not m:
        fail("standalone: no inlined <style> block")
    assert_scoped(m.group(1))

    # the standalone build, by contrast, must be a complete document
    for tag in ("<!doctype html>", "<html", "<head>", "<body"):
        if tag not in standalone.lower():
            fail(f"standalone: missing {tag}")

    DIST.mkdir(exist_ok=True)
    FRAGMENT_OUT.write_text(fragment, encoding="utf-8")
    STANDALONE_OUT.write_text(standalone, encoding="utf-8")

    print(f"OK  fragment    -> {FRAGMENT_OUT}  ({len(fragment):,} chars)")
    print(f"OK  standalone  -> {STANDALONE_OUT}  ({len(standalone):,} chars)")


if __name__ == "__main__":
    main()
