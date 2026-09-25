# -*- coding: utf-8 -*-
"""DFG analiza brojki.xlsx -> assets/js/data.js

Reads the consolidated sheet "DFG 2018-2024" (institutions x years, MKD) plus
the yearly "detail" sheets that carry the open-call / direct split and the
highest / lowest individual grant.

Output schema (window.DFG):

    { meta: {source, rate, years, generated},
      levels: {
        national: {key, label, available, years, institutions[],
                   series: {total, open, direct, maxGrant, minGrant}
                                     -> {instId: [value|null x years]},
                   orgs:   {max, min}  -> {instId: [name|null x years]},
                   totals: {total: {all, noParties, noPartiesSport},
                            open: [...], direct: [...]},
                   context:{sectorIncome: [...], sectorShare: [...]},
                   availability: {measure: [years with data]}},
        local:     {... same shape, empty until the municipal data arrives ...}
      }}

Cell conventions taken over from the workbook:
    number        -> value
    0             -> 0.0
    "/"  ""  text -> None  (shown as a gap in the line chart)
"""
import datetime
import json
import os

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = (r"C:\Users\Boris\OneDrive - Macedonian Center for International "
       r"Cooperation\Desktop\DFG analiza brojki.xlsx")
OUT = os.path.join(HERE, "assets", "js", "data.js")

YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
RATE = 61.5            # MKD per EUR — the rate used throughout the workbook

MASTER_SHEET = "dfg 2018-2024"

# Yearly detail sheets: (normalised sheet title, year)
DETAIL_SHEETS = [
    ("dfg detali za 2018", 2018),
    ("2019 детали дфг", 2019),
    ("2020 detali", 2020),
    ("dfg 2021 detali", 2021),
    ("dfg 2022 detali", 2022),
]

# Short labels for the 17 rows of the master sheet, keyed by the "бр." column.
SHORT = {
    1: "Ген. секретаријат на Влада",
    2: "Односи меѓу заедниците",
    3: "Правда",
    4: "Економија и труд",
    5: "Животна средина",
    6: "Социјална политика",
    7: "Спорт (поранешна АМС)",
    8: "Здравство",
    9: "Одбрана",
    10: "Култура и туризам",
    11: "Земјоделство",
    12: "ИНОВА (поранешен ФИТР)",
    13: "Локална самоуправа",
    14: "Права на заедниците",
    15: "Дигитална трансформација",
    16: "Образование и наука",
    17: "Дирекција за спасување",
}

# Detail sheets identify some institutions by abbreviation (2018 sheet) and
# many by older/renamed variants, so matching goes through an exact-abbreviation
# table first and then through ordered keywords (first hit wins).
ABBREV = {
    "мо": 9, "ме": 4, "мзшв": 11, "мжпп": 5, "мз": 8, "мтсп": 6,
    "амс": 7, "мк": 10, "фитр": 12,
}

KEYWORDS = {
    1: ["генерален секретаријат"],
    2: ["односи меѓу заедниците"],
    3: ["правда"],
    4: ["економија"],
    5: ["животна средина"],
    6: ["социјална политика", "труд и социјална"],
    7: ["спорт"],
    8: ["здравство"],
    9: ["одбрана"],
    10: ["култура"],
    11: ["шумарство"],                       # "земјоделство" alone would also
    12: ["иновации", "инова", "фитр"],       # match the agricultural support
    13: ["локална самоуправа"],              # agency, which is not a row here
    14: ["правата на заедниците"],
    15: ["дигитална"],
    16: ["образование"],
    17: ["спасување"],
}

MEASURES = ["total", "open", "direct", "maxGrant", "minGrant"]


def num(v):
    """Cell -> float, or None for '/', blanks and text.

    Six decimals keeps the workbook's percentage fractions intact while
    dropping the float noise Excel leaves on the money columns.
    """
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 6)
    return None


def txt(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return None


def inst_key(name):
    n = name.strip().lower()
    if n in ABBREV:
        return ABBREV[n]
    for i in range(1, 18):
        for kw in KEYWORDS[i]:
            if kw in n:
                return i
    return None


def put(store, key, year, value):
    store.setdefault(key, [None] * len(YEARS))[YEARS.index(year)] = value


# --------------------------------------------------------------------------
# master sheet
# --------------------------------------------------------------------------
def read_master(ws, unmapped):
    year_col = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=2, column=c).value
        if num(v) is not None and float(v) == int(v) and int(v) in YEARS:
            year_col[int(v)] = c
    assert sorted(year_col) == YEARS, sorted(year_col)

    institutions = []
    r = 3
    while True:
        a = ws.cell(row=r, column=1).value
        if not isinstance(a, int) or isinstance(a, bool):
            break
        name = txt(ws.cell(row=r, column=2).value)
        if not name:
            break
        no = a
        institutions.append({
            "id": "i%d" % no,
            "no": no,
            "name": name,
            "short": SHORT.get(no, name),
        })
        r += 1
    if len(institutions) != 17:
        print("  ! expected 17 institutions, found %d" % len(institutions))

    def row_vals(rr):
        return [num(ws.cell(row=rr, column=year_col[y]).value) for y in YEARS]

    # institution "бр." n sits in row n+2 of the master sheet
    total = {}
    for inst in institutions:
        total[inst["id"]] = row_vals(2 + inst["no"])

    # labelled summary rows (first occurrence wins -> the real table, not the
    # little helper chart further down the sheet)
    lab = {}
    for rr in range(20, 60):
        b = ws.cell(row=rr, column=2).value
        if isinstance(b, str):
            k = b.strip().lower()
            if k and k not in lab:
                lab[k] = rr

    def need(key):
        assert key in lab, "label not found: %r" % key
        return row_vals(lab[key])

    totals = {
        "all": need("вкупно"),
        "noParties": need("без политички партии"),
        "noPartiesSport": need("без политички партии и спорт"),
    }
    income = need("вкупни приходи на го - црм")
    share = need("процент на државно финансирање во вкупни приходи на го")

    # sanity check: the workbook total really is the sum of its rows
    for i, y in enumerate(YEARS):
        s = round(sum(v[i] or 0 for v in total.values()), 2)
        if abs(s - (totals["all"][i] or 0)) > 1:
            print("  ! %d: rows sum %.2f != ВКУПНО %.2f" % (y, s, totals["all"][i]))

    return institutions, total, totals, income, share


# --------------------------------------------------------------------------
# yearly detail sheets
# --------------------------------------------------------------------------
def read_detail(ws, year, series, orgs, unmapped):
    hdr = hdr_name = None
    for r in range(1, 6):
        for c in range(1, ws.max_column + 1):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, str) and v.strip().lower() in ("оду", "институција"):
                hdr, hdr_name = r, c
                break
        if hdr:
            break
    assert hdr, ws.title

    cols = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=hdr, column=c).value
        if v is None:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool) \
                and float(v) == int(v) and int(v) in YEARS:
            cols.setdefault("total", c)
            continue
        if not isinstance(v, str):
            continue
        h = v.strip().lower()
        if h in ("вкупно", "вупно") or h.startswith("вкупно за"):
            cols.setdefault("total", c)
        elif "без јавен" in h:
            cols.setdefault("direct", c)
        elif "јавен повик" in h or "јавен оглас" in h:
            cols.setdefault("open", c)
        elif "највисок" in h:
            cols.setdefault("maxOrg", c)
            cols["maxVal"] = c + 1
        elif "најнизок" in h:
            cols.setdefault("minOrg", c)
            cols["minVal"] = c + 1

    found = 0
    for r in range(hdr + 1, ws.max_row + 1):
        a = ws.cell(row=r, column=1).value
        if not isinstance(a, int) or isinstance(a, bool):
            continue
        name = txt(ws.cell(row=r, column=hdr_name).value)
        if not name:
            continue
        key = inst_key(name)
        if key is None:
            unmapped.add(name)
            continue
        iid = "i%d" % key
        found += 1
        # NOTE: the detail sheets carry their own "ВКУПНО" column, but the
        # headline series comes from the master sheet — only the channel
        # split and the grants are taken from here.
        if "open" in cols:
            put(series["open"], iid, year,
                num(ws.cell(row=r, column=cols["open"]).value))
        if "direct" in cols:
            put(series["direct"], iid, year,
                num(ws.cell(row=r, column=cols["direct"]).value))
        for m, vcol, ocol in (("max", "maxVal", "maxOrg"), ("min", "minVal", "minOrg")):
            if vcol in cols:
                val = num(ws.cell(row=r, column=cols[vcol]).value)
                org = txt(ws.cell(row=r, column=cols[ocol]).value) \
                    if val is not None else None
                put(orgs[m], iid, year, org)
                put(series[m + "Grant"], iid, year, val)
    print("  %-20s %2d institutions, columns %s" % (ws.title.strip(), found,
                                                    sorted(cols)))


def availability(series):
    out = {}
    for m, rows in series.items():
        yrs = [y for i, y in enumerate(YEARS)
               if any(v[i] is not None for v in rows.values())]
        out[m] = yrs
    return out


def extract():
    wb = openpyxl.load_workbook(SRC, data_only=True)
    sheets = {ws.title.strip().lower(): ws for ws in wb.worksheets}
    unmapped = set()

    print("master sheet:")
    ws = sheets[MASTER_SHEET]
    institutions, total, totals, income, share = read_master(ws, unmapped)
    print("  %d institutions x %d years" % (len(institutions), len(YEARS)))

    series = {m: {} for m in MEASURES}
    series["total"] = total
    orgs = {"max": {}, "min": {}}

    for title, year in DETAIL_SHEETS:
        assert title in sheets, title
        read_detail(sheets[title], year, series, orgs, unmapped)

    # every master institution gets a full-length array for every measure,
    # even when it never appears in a detail sheet (e.g. the 2025-only rows)
    for m in MEASURES:
        for inst in institutions:
            series[m].setdefault(inst["id"], [None] * len(YEARS))
    for m in orgs:
        for inst in institutions:
            orgs[m].setdefault(inst["id"], [None] * len(YEARS))

    def year_sum(rows, i):
        vals = [v[i] for v in rows.values() if v[i] is not None]
        return round(sum(vals), 6) if vals else None

    # channel totals are summed from the detail rows (one of the sheets stores
    # its total row shifted one column to the right, so reading it is fragile);
    # a year no detail sheet covers stays None -> a gap, not a zero
    totals["open"] = [year_sum(series["open"], i) for i in range(len(YEARS))]
    totals["direct"] = [year_sum(series["direct"], i) for i in range(len(YEARS))]
    for i, y in enumerate(YEARS):
        if totals["open"][i] is None:
            continue
        both = (totals["open"][i] or 0) + (totals["direct"][i] or 0)
        print("  %d: open %s + direct %s = %s" % (
            y, format(totals["open"][i], ",.0f"),
            format(totals["direct"][i] or 0, ",.0f"), format(both, ",.0f")))

    if unmapped:
        print("  unmapped institution names (skipped):")
        for n in sorted(unmapped):
            print("    -", n)

    national = {
        "key": "national",
        "label": "Национално ниво",
        "available": True,
        "years": YEARS,
        "institutions": institutions,
        "series": series,
        "orgs": orgs,
        "totals": totals,
        "context": {"sectorIncome": income, "sectorShare": share},
        "availability": availability(series),
    }
    local = {
        "key": "local",
        "label": "Локално ниво",
        "available": False,
        "years": YEARS,
        "institutions": [],
        "series": {m: {} for m in MEASURES},
        "orgs": {"max": {}, "min": {}},
        "totals": {"all": [], "noParties": [], "noPartiesSport": [],
                   "open": [], "direct": []},
        "context": {"sectorIncome": [], "sectorShare": []},
        "availability": {m: [] for m in MEASURES},
    }

    payload = {
        "meta": {
            "source": os.path.basename(SRC),
            "rate": RATE,
            "years": YEARS,
            "generated": datetime.date.today().isoformat(),
        },
        "levels": {"national": national, "local": local},
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// Generated by extract_data.py from %s. Do not edit by hand.\n"
                % os.path.basename(SRC))
        f.write("window.DFG = ")
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write(";\n")
    print("wrote", OUT)


if __name__ == "__main__":
    extract()
