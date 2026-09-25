# ДФГ — Државно финансирање на граѓанското општество

An interactive, **fully static** dashboard for the state funding of civil
society organisations in North Macedonia, built from
`DFG analiza brojki.xlsx` (14 worksheets), covering **2018–2025**.

**One page, one chart, two levels** — switched with the
*Национално ниво / Локално ниво* toggle above the filter card:

- **Национално ниво** (default) — 17 institutions as lines plus a **Вкупно**
  total line, shown or hidden with the *Линија → Вкупно* checkbox.
- **Локално ниво** — placeholder for the municipality × year table. The data
  does not exist yet, so it shows a "coming soon" empty state (pills replaced
  by a note, context overlay disabled) instead of a broken chart.

Everything is in Macedonian (Cyrillic).

## Filters

Filters sit on two lines above the chart:

| Control | Options | Notes |
|---|---|---|
| **Единица** | МКД · € · % | € uses **61,50 МКД/€** (the workbook's own rate); % is each value ÷ that year's total × 100, so the total line always reads 100 % |
| **Контекст** | Нема · Приходи на ГО · Удел во приходите | dashed overlay on a right-hand axis, from the master sheet |
| **Години** | from/to selects, 2018–2025 | |
| **Линија** | ☑ Вкупно | untick to drop the total line — the caption then reads "без вкупната линија" |
| **Институции** | 17 pills + Сите / Топ 5 / Ниедно | Топ 5 ranks by the sum over the selected year range |
| | Ресетирај · Сними PNG | PNG is exported at 2× with the heading baked in |

The **basis is fixed to „Без политички партии и спорт“** — there is no
basis selector any more, so every total on the page (the Вкупно line, the
headline sentence and the `%` denominator) is that figure, which is what
makes the dashboard suitable for the DFG. A footnote under the chart spells
it out: *„Во овие средства не влегуваат средствата од спорт.“*

Missing years always render as a **gap** in the line (never as zero), and
the caption above the chart restates the current unit and year range.

## Data rules

- The master sheet `DFG 2018-2024` is authoritative for `Вкупно`, the three
  bases and the context rows; its `ВКУПНО` row matches the per-institution
  sums exactly, and the computed "Без политички партии и спорт" share
  reproduces the workbook's own percentage row for all eight years.
- The per-year detail sheets are still parsed for the public-call / direct
  split and the grant extremes — kept in `data.js` for later use, but **not
  surfaced in the UI** (their totals differ slightly from the master sheet,
  and the master sheet wins).
- `"/"` and blank cells → `null` → a gap in the line. `0` → a real 0.
- Percentages are shares of the fixed basis's annual total, so the total
  line itself always reads 100 %.

## Design

- Main colour `#005783` (headings, total line) · accent
  `#4a927b` (action buttons, active selectors, level switch) · background
  `#e9e9e9` — the same family as the SELDI dashboard.
- Institutions use a 17-colour Tableau-10-style categorical palette; the
  always-on total line is the main blue, the "Удел во приходите" overlay is
  the accent green dashed.
- Number formatting follows Macedonian conventions: `.` thousands separator,
  `,` decimal separator.
- Branding is Cyrillic throughout — the top bar, the tab title and the PNG
  header read **ДФГ**, not `DFG` (only the source workbook keeps its
  original name).

## Tech stack

Plain HTML + CSS + JavaScript with [Chart.js 4](https://www.chartjs.org/).
**No build step, no npm, no server-side code.** `index.html` loads the three
scripts and the stylesheet from `assets/`; the single-file build inlines them.

## Use it on a WordPress site

```
python build_singlefile.py
```

writes two **self-contained** files (CSS + data + Chart.js + app code all
inlined, zero external requests — the script asserts this and fails the build
otherwise):

- **`dist/dfg-dashboard-wordpress.html`** — a *fragment* with no
  `<html>/<head>/<body>` and no doctype. In wp-admin, add a **Custom HTML**
  block, open this file, select all + paste, then **Update**.

  The dashboard cannot conflict with your theme: everything is scoped under
  `.dfg-root` with `--dfg-*` custom properties and `dash-*` class names
  (so a theme rule such as `.section` or `.card` cannot match), and the
  critical properties are additionally re-stated with `!important` inside
  `.dfg-root` so a theme's own `!important` button/heading rules cannot
  restyle it. Verified against a deliberately hostile mock theme (bare
  `button`/`h2`/`li` rules with `!important`, `box-sizing: content-box`,
  Georgia body font).

  Embedded differences from the standalone site: the heading starts at
  `<h2>` (WordPress owns the `<h1>`), there is no top bar, no page padding
  or background (the content sits flush in your block) and the browser tab
  title is never changed.

- **`dist/dfg-dashboard-standalone.html`** — a full HTML document. Upload it
  via FTP/file manager if you'd rather serve it from your own hosting.

Notes:

- Pasting scripts requires an administrator account on a single-site
  WordPress. If the dashboard is blank after saving (scripts were stripped),
  install the **WPCode** plugin and paste the same file into a snippet, or
  use the FTP file instead.
- After every dashboard change: run `python build_singlefile.py`, then re-paste
  (or re-upload) the file.

## Updating the data

Data lives in `assets/js/data.js`, generated by `extract_data.py`:

```
python extract_data.py
```

It re-reads the workbook (path at the top of the script) and rewrites
`data.js`. The extractor maps the 17 master-sheet rows to stable ids, sums the
per-year detail sheets for the channel split and grants (exported but not
shown yet) and records the per-level availability flag the UI needs.

When the municipality table arrives, fill in the `local` level in the
extractor with the same shape (`institutions`, `series`, `totals`,
`context`, `availability`) and set `available: true` — the UI needs no change.

## Layout

```
index.html            entry point (dev: loads assets/ directly)
assets/css/style.css  all styling, scoped under .dfg-root (--dfg-* vars)
assets/js/data.js     generated data (do not edit by hand)
assets/js/dashboard.js  filters, chart, empty states, PNG export
assets/vendor/        cached Chart.js for the single-file builds
extract_data.py       xlsx → data.js extractor
build_singlefile.py   builds the WordPress fragment + standalone single file
dist/                 build output — paste (WordPress) or upload (FTP)
```
