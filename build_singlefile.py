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

The fragment's JavaScript is shipped base64(UTF-8) and decoded in one line at
run time, because the WordPress content filters of the target site rewrite the
ampersand character inside <script> (observed live: 652 rewrites -> SyntaxError
-> the dashboard never mounts). The payload contains no ampersand and no angle
bracket, so there is nothing for such a filter to rewrite. The standalone
build keeps the plain, readable sources — it is served from a static host that
performs no such rewriting.
"""

from __future__ import annotations

import base64
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
    "dash-caption", "dash-foot", "dash-chart", "dash-chart2",
    "dash-empty", "dash-png",
    "dash-dlg", "dash-dlg-title", "dash-dlg-actions",
    "dash-table", "dash-tbl", "dash-tbl-dot", "dash-unit", "dash-src",
    "dash-sort", "dash-sort-ico",
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


def encoded_script_block(scripts: list[str]) -> str:
    """The fragment's single <script>: the very same code, base64(UTF-8).

    Host CMS content filters may rewrite characters inside inline scripts —
    civicamobilitas.mk turned every other ampersand into a numeric entity,
    which is a SyntaxError that stopped the dashboard from mounting at all.
    The payload below is pure base64 (A-Z a-z 0-9 + / =) and the one-line
    decoder around it holds no ampersand and no angle bracket, so such a
    filter has nothing left to rewrite and a JS minifier only ever sees a
    string literal. It decodes to exactly the sources the standalone build
    ships.
    """
    payload = base64.b64encode("\n".join(scripts).encode("utf-8")).decode("ascii")
    return (
        "<script>\n"
        "/* ==== dfg-dashboard: begin inlined scripts (generated) ==== */\n"
        "/* The JavaScript is base64(UTF-8) so that content filters which\n"
        "   rewrite characters inside scripts find nothing to rewrite; the\n"
        "   browser decodes and runs it immediately. */\n"
        f'eval(new TextDecoder().decode(Uint8Array.from(atob("{payload}"),'
        "function(c){return c.charCodeAt(0)})));\n"
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
    fragment_script = encoded_script_block(scripts)
    markup = body_html_of(index_html)

    # ---- WordPress fragment: style + markup + one inline script ------------
    fragment = (
        style + "\n\n" + markup + ("\n\n" if markup else "") + fragment_script + "\n"
    )

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

    # the fragment must survive a CMS that rewrites characters inline:
    # no ampersand anywhere in the payload, and it must decode back 1:1
    m = re.search(r"<script>(.*?)</script>", fragment, re.S)
    if not m:
        fail("fragment: no inlined <script> block")
    if "<" in m.group(1):
        fail("fragment: the inline script must not contain '<'")
    if "&" in m.group(1):
        fail("fragment: the inline script must not contain '&'")
    p = re.search(r'atob\("([A-Za-z0-9+/=]+)"\)', m.group(1))
    if not p:
        fail("fragment: the base64 payload was not found")
    if base64.b64decode(p.group(1)).decode("utf-8") != "\n".join(scripts):
        fail("fragment: the base64 payload does not round-trip")
    if "&" in style:
        fail("fragment: the <style> block must not contain '&'")

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
