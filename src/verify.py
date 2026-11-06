"""Check the workbook's computed cells against an independent calculation.

Scope, stated honestly: this checks the DESCRIPTIVE figures the workbook
computes in Excel formulas, by recomputing each one here in pandas with
explicit bounds rather than reusing the pipeline's own banding. It does not
re-derive the inferential statistics (Wilcoxon, Spearman, the permutation
nulls); those live only in src/analysis.py, and a second implementation of
them is in the audit scripts rather than here.

It loads through prepare.load() so names and normalization match the workbook,
which means a check whose two sides both descend from load() can only catch a
write error, not a definition error. Those are marked [weak] below. The era,
size-band and recurrence checks are genuine independent recomputations.
"""
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import load as prepare_load

WB = Path(__file__).resolve().parent.parent / "Cruise_Outbreak_Analysis.xlsx"


def assert_recalculated(path):
    """openpyxl writes formulas without evaluating them.

    A workbook straight out of build_workbook.py therefore holds thousands of
    formulas and no cached results, and every check below would read None and
    report a false failure. Detect that and say so, instead of printing 46
    FAILs that look like the analysis is wrong.
    """
    formulas = load_workbook(path, data_only=False)
    cached = load_workbook(path, data_only=True)
    n_formula = n_cached = 0
    for name in formulas.sheetnames:
        fs, cs = formulas[name], cached[name]
        for row in fs.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    n_formula += 1
                    if cs.cell(cell.row, cell.column).value is not None:
                        n_cached += 1
    if n_formula and not n_cached:
        raise SystemExit(
            f"{path.name} holds {n_formula:,} formulas and no cached results, so "
            "there is nothing to check yet.\n\nopenpyxl writes formulas without "
            "evaluating them. Open the workbook in Excel or\nLibreOffice and save "
            "it, or run:\n\n    soffice --headless --convert-to xlsx --outdir . "
            f"{path.name}\n\nthen run this script again.")
    return n_formula, n_cached


n_formula, n_cached = assert_recalculated(WB)
wb = load_workbook(WB, data_only=True)
print(f"workbook: {n_formula:,} formulas, {n_cached:,} carry cached results\n")
a = wb["Analysis"]
d = wb["Data"]

df, n_transcribed, dropped_rows = prepare_load()
# guard the one failure mode an internal check cannot see: a silent row filter
# inside load(). These are the disclosed figures, asserted rather than trusted.
assert n_transcribed == 428, f"expected 428 transcribed records, got {n_transcribed}"
assert len(dropped_rows) == 3, f"expected 3 undateable records, got {len(dropped_rows)}"
assert len(df) == 425, f"expected 425 in the analysis set, got {len(df)}"
df = df.rename(columns={"voyage_start": "start_dt"})
full = df[df.paired]

fails = []


def chk(label, got, want, tol=1e-6):
    ok = (got is not None) and abs(float(got) - float(want)) <= tol
    print(f"  {'PASS' if ok else 'FAIL'}  {label:<52} workbook={got}  pandas={want}")
    if not ok:
        fails.append(label)


# locate the Q1 block
q1 = None
for r in range(1, 40):
    if a.cell(r, 1).value == "Outbreaks with BOTH passenger and crew counts":
        q1 = r
        break
print("=== Q1 passengers vs crew ===")
chk("outbreak count with counts [weak]", a.cell(q1, 2).value, len(full))
chk("total passengers ill", a.cell(q1, 3).value, full.passengers_ill.sum())
chk("total passengers onboard", a.cell(q1, 4).value, full.passengers_total.sum())
chk("pooled passenger attack rate", a.cell(q1, 5).value,
    full.passengers_ill.sum() / full.passengers_total.sum())
chk("total crew ill", a.cell(q1, 6).value, full.crew_ill.sum())
chk("total crew onboard", a.cell(q1, 7).value, full.crew_total.sum())
chk("pooled crew attack rate", a.cell(q1 + 1, 5).value,
    full.crew_ill.sum() / full.crew_total.sum())
ratio = (full.passengers_ill.sum() / full.passengers_total.sum()) / \
        (full.crew_ill.sum() / full.crew_total.sum())
chk("pax:crew ratio", a.cell(q1 + 2, 5).value, ratio)
higher = int(((full.passengers_ill / full.passengers_total) >
              (full.crew_ill / full.crew_total)).sum())
chk("outbreaks where pax rate > crew rate", a.cell(q1 + 3, 2).value, higher)

# era block
print("\n=== Q2 by era ===")
ERAS = {"1993-2000": (1993, 2000), "2001-2005": (2001, 2005), "2006-2010": (2006, 2010),
        "2011-2015": (2011, 2015), "2016-2020": (2016, 2020), "2021-2026": (2021, 2026)}
for rr in range(1, 60):
    lbl = a.cell(rr, 1).value
    if lbl in ERAS:
        lo, hi = ERAS[lbl]
        subf = full[(full.year >= lo) & (full.year <= hi)]
        # the workbook's era count is PAIRED outbreaks, matching the rates beside it
        chk(f"{lbl} paired outbreak count", a.cell(rr, 2).value, len(subf))
        chk(f"{lbl} pax ill", a.cell(rr, 3).value, subf.passengers_ill.sum())
        if subf.passengers_total.sum() > 0:
            chk(f"{lbl} pax attack rate", a.cell(rr, 5).value,
                subf.passengers_ill.sum() / subf.passengers_total.sum())
            chk(f"{lbl} crew attack rate", a.cell(rr, 6).value,
                subf.crew_ill.sum() / subf.crew_total.sum())

# size block
print("\n=== Q4 by ship size ===")
bands = {"1. Under 1,000": (0, 1000), "2. 1,000-1,999": (1000, 2000),
         "3. 2,000-2,999": (2000, 3000), "4. 3,000+": (3000, 10 ** 9)}
for rr in range(1, 120):
    lbl = a.cell(rr, 1).value
    if lbl in bands:
        lo, hi = bands[lbl]
        sub = full[(full.passengers_total >= lo) & (full.passengers_total < hi)]
        chk(f"{lbl} outbreaks", a.cell(rr, 2).value, len(sub))
        if len(sub):
            chk(f"{lbl} attack rate", a.cell(rr, 5).value,
                sub.passengers_ill.sum() / sub.passengers_total.sum())

# recurrence
print("\n=== Q6 recurrence ===")
d2 = df.sort_values("start_dt")
gaps = []
for _ship, g in d2.groupby("ship"):
    s = g.start_dt.sort_values().tolist()
    for x, y in zip(s, s[1:]):
        gaps.append((y - x).days)
for rr in range(1, 140):
    lbl = a.cell(rr, 1).value
    if isinstance(lbl, str) and lbl.startswith("Within "):
        w = int(lbl.split()[1])
        chk(f"repeats within {w} days", a.cell(rr, 2).value,
            sum(1 for g in gaps if 0 < g <= w))
    if lbl == "Shortest gap between two outbreaks on the same ship (days)":
        chk("shortest gap", a.cell(rr, 2).value, min(g for g in gaps if g > 0))

# data tab integrity
print("\n=== Data tab checks ===")
# these were previously printed without being checked, which read as verified
pax_flagged = sum(1 for r in range(2, d.max_row + 1) if d.cell(r, 23).value == "CHECK")
crew_flagged = sum(1 for r in range(2, d.max_row + 1) if d.cell(r, 25).value == "CHECK")
chk("rows flagged: CDC pax % vs counts", pax_flagged,
    int((df.cdc_pax_pct_check == "CHECK").sum()))
chk("rows flagged: CDC crew % vs counts", crew_flagged,
    int((df.cdc_crew_pct_check == "CHECK").sum()))
nrows = sum(1 for r in range(2, d.max_row + 1) if d.cell(r, 3).value)
chk("data tab row count [weak]", nrows, len(df))

# vessel and operator counts, read off the Data tab rather than from the frame
ships = {d.cell(r, 3).value for r in range(2, d.max_row + 1) if d.cell(r, 3).value}
lines = {d.cell(r, 2).value for r in range(2, d.max_row + 1) if d.cell(r, 2).value}
chk("distinct vessels on the Data tab", len(ships), df.ship.nunique())
chk("distinct operators on the Data tab", len(lines), df.cruise_line.nunique())

# the ratio column must never carry inf, which is what shipped before
import math
ratios = [d.cell(r, 15).value for r in range(2, d.max_row + 1)]
n_inf = sum(1 for v in ratios if isinstance(v, float) and math.isinf(v))
chk("infinite pax:crew ratios on the Data tab", n_inf, 0)

print("\n" + ("ALL CHECKS PASSED" if not fails else f"FAILURES: {fails}"))
