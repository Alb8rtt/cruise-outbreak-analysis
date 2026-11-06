"""Every statistic the published artifacts quote. Run this to reproduce them.

Nothing here is computed on a filtered subsample unless the filter is named in
the output, because an undisclosed filter is how a null result turns into a
significant one.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import load, paired_set, ERA_LABELS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(20261106)
N_PERM = 2000

df, n_transcribed, dropped = load()
p = paired_set(df)
out = {}

print("=" * 72)
print("DATASET")
print("=" * 72)
print(f"  transcribed records          {n_transcribed}")
print(f"  dropped, month-only dates    {len(dropped)}")
print(f"  analysis set                 {len(df)}")
print(f"  with both counts (paired)    {len(p)}   years {int(p.year.min())}-{int(p.year.max())}")
print(f"  without both counts          {len(df) - len(p)}")
print(f"  distinct ships               {df.ship.nunique()}")
out["dataset"] = {
    "transcribed": n_transcribed, "dropped_no_date": len(dropped),
    "analysis_set": len(df), "paired": len(p), "unpaired": len(df) - len(p),
    "ships": int(df.ship.nunique()), "lines": int(df.cruise_line.nunique()),
    "first_voyage": str(df.voyage_start.min().date()),
    "last_voyage": str(df.voyage_start.max().date()),
    "paired_year_min": int(p.year.min()), "paired_year_max": int(p.year.max()),
}

print()
print("=" * 72)
print("FINDING 1  passenger vs crew attack rate")
print("=" * 72)
P = p.passengers_ill.sum() / p.passengers_total.sum()
C = p.crew_ill.sum() / p.crew_total.sum()
higher = int((p.pax_attack_rate > p.crew_attack_rate).sum())
lower = int((p.pax_attack_rate < p.crew_attack_rate).sum())
w = stats.wilcoxon(p.pax_attack_rate, p.crew_attack_rate, alternative="greater")
n = len(p)
rb = 1 - (2 * (n * (n + 1) / 2 - w.statistic)) / (n * (n + 1) / 2)
med_diff = (p.pax_attack_rate - p.crew_attack_rate).median()
print(f"  passengers  {100*P:.2f}%   {int(p.passengers_ill.sum()):,} of {int(p.passengers_total.sum()):,}")
print(f"  crew        {100*C:.2f}%   {int(p.crew_ill.sum()):,} of {int(p.crew_total.sum()):,}")
print(f"  ratio       {P/C:.2f}x")
print(f"  passenger rate higher in {higher} of {n}  (lower in {lower})")
print(f"  Wilcoxon signed-rank p = {w.pvalue:.3g}")
print(f"  rank-biserial r = {abs(rb):.2f}   median per-voyage difference = {100*med_diff:.2f} pp")
out["finding1"] = {
    "pax_rate": round(100 * P, 2), "crew_rate": round(100 * C, 2), "ratio": round(P / C, 2),
    "pax_ill": int(p.passengers_ill.sum()), "pax_total": int(p.passengers_total.sum()),
    "crew_ill": int(p.crew_ill.sum()), "crew_total": int(p.crew_total.sum()),
    "n_higher": higher, "n_lower": lower, "n": n,
    "wilcoxon_p": float(w.pvalue), "rank_biserial": round(abs(rb), 2),
    "median_diff_pp": round(100 * med_diff, 2),
}

print("\n  does the gap hold inside subgroups?")
sub = []
for col in ["ship_size_band", "era", "season"]:
    for k, g in p.groupby(col, observed=True):
        if g.passengers_total.sum() and g.crew_total.sum():
            a = g.passengers_ill.sum() / g.passengers_total.sum()
            b = g.crew_ill.sum() / g.crew_total.sum()
            sub.append({"by": col, "group": str(k), "n": len(g),
                        "pax": round(100 * a, 2), "crew": round(100 * b, 2),
                        "ratio": round(a / b, 2)})
for r in sub:
    print(f"    {r['by']:<16}{r['group']:<28}n={r['n']:<5}pax {r['pax']:>5}%  crew {r['crew']:>5}%  {r['ratio']}x")
out["subgroups"] = sub
print(f"  gap present in all {len(sub)} subgroups: {all(r['ratio'] > 1 for r in sub)}")

print()
print("=" * 72)
print("FINDING 2  rates over time")
print("=" * 72)
eras = []
for e in ERA_LABELS:
    g = p[p.era == e]
    if not len(g) or not g.passengers_total.sum():
        continue
    a = g.passengers_ill.sum() / g.passengers_total.sum()
    b = g.crew_ill.sum() / g.crew_total.sum()
    eras.append({"era": e, "n": len(g), "years": f"{int(g.year.min())}-{int(g.year.max())}",
                 "pax": round(100 * a, 2), "crew": round(100 * b, 2),
                 "ratio": round(a / b, 2)})
print(f"  {'era':<12}{'actual years':<14}{'n':>5}{'pax':>8}{'crew':>8}{'ratio':>8}")
for r in eras:
    print(f"  {r['era']:<12}{r['years']:<14}{r['n']:>5}{r['pax']:>8}{r['crew']:>8}{r['ratio']:>7}x")
out["eras"] = eras

first, last = eras[0], eras[-1]
best = min(eras, key=lambda r: r["crew"])
print(f"\n  crew, first to last era : {first['crew']}% -> {last['crew']}%  "
      f"({100*(last['crew']/first['crew']-1):+.0f}%)")
print(f"  crew, first to trough   : {first['crew']}% -> {best['crew']}% ({best['era']})  "
      f"({100*(best['crew']/first['crew']-1):+.0f}%)")
print(f"  pax,  first to last era : {first['pax']}% -> {last['pax']}%  "
      f"({100*(last['pax']/first['pax']-1):+.0f}%)")

print("\n  rank trend across individual voyages, FULL paired sample:")
for lab, col in [("crew rate", "crew_attack_rate"), ("passenger rate", "pax_attack_rate")]:
    s = stats.spearmanr(p.year, p[col])
    print(f"    {lab:<16} rho = {s.statistic:+.3f}   p = {s.pvalue:.3f}   "
          f"{'significant' if s.pvalue < 0.05 else 'NOT significant'}")
cr = stats.spearmanr(p.year, p.crew_attack_rate)
px = stats.spearmanr(p.year, p.pax_attack_rate)
print("    (an earlier version of this analysis cut the sample at 2020, which")
print("     excluded the post-2020 rebound and made the crew trend look significant.")
print("     The full-sample figures above are the ones reported.)")
out["finding2"] = {
    "crew_first": first["crew"], "crew_last": last["crew"], "crew_trough": best["crew"],
    "crew_trough_era": best["era"],
    "crew_change_full_pct": round(100 * (last["crew"] / first["crew"] - 1)),
    "crew_change_to_trough_pct": round(100 * (best["crew"] / first["crew"] - 1)),
    "pax_first": first["pax"], "pax_last": last["pax"],
    "pax_change_full_pct": round(100 * (last["pax"] / first["pax"] - 1)),
    "crew_rho": round(float(cr.statistic), 3), "crew_p": round(float(cr.pvalue), 3),
    "pax_rho": round(float(px.statistic), 3), "pax_p": round(float(px.pvalue), 3),
}

print()
print("=" * 72)
print("FINDING 3  repeat outbreaks on the same vessel")
print("=" * 72)
rep = df[df.days_since_prior_outbreak.notna()].copy()
w30 = rep[rep.days_since_prior_outbreak.le(30)]
# A repeat is a "consecutive sailing" only if it starts 0-2 days AFTER the
# prior voyage ended. A negative gap means the two investigations overlap,
# which is a separate data-quality problem, so it is counted separately
# rather than folded in as if it were a next-sailing case.
consec = w30[w30.days_after_prior_voyage_end.between(0, 2)]
overlap = w30[w30.days_after_prior_voyage_end.lt(0)]
print(f"  outbreaks beginning within 30 days of a prior one on the same ship: {len(w30)}")
print(f"  of those, beginning 0-2 days AFTER the prior voyage ended:          {len(consec)}")
print(f"  of those, overlapping the prior investigation outright:             {len(overlap)}")
print(f"  median days between prior voyage end and next voyage start:         "
      f"{w30.days_after_prior_voyage_end.median():.0f}")
print("  -> most of these are the immediately following sailing of the same loop,")
print("     which is more consistent with one episode spanning a turnaround than")
print("     with a vessel released early from cleaning.")
out["finding3"] = {
    "repeats_30d": len(w30), "consecutive_sailings": len(consec),
    "overlapping_30d": len(overlap),
    "median_days_after_prior_end": float(w30.days_after_prior_voyage_end.median()),
    "non_consecutive_30d": len(w30) - len(consec) - len(overlap),
}


def count_repeats(ship_codes, day_nums, windows):
    """Repeats per window, vectorised.

    day_nums is already ascending, so sorting by ship (stable) groups each
    vessel's outbreaks with their dates still in order. Adjacent differences
    inside a group are then the gaps between consecutive outbreaks on that ship.
    """
    order = np.argsort(ship_codes, kind="stable")
    s = ship_codes[order]
    d = day_nums[order]
    same = s[1:] == s[:-1]
    gaps = d[1:] - d[:-1]
    ok = same & (gaps > 0)
    return {w: int((ok & (gaps <= w)).sum()) for w in windows}


d_sorted = df.sort_values("voyage_start")
ship_codes = pd.factorize(d_sorted.ship)[0]
day_nums = (d_sorted.voyage_start.values.astype("datetime64[D]")
            .astype(int))
# take the year from the sailing date, not the transcribed year column: one
# row (Nantucket Clipper, year=1999, sails 1998-01-02) disagrees, and the
# blocking key must match the dates being shuffled.
years = d_sorted.voyage_start.dt.year.values
WINDOWS = (30, 60, 90)
observed = count_repeats(ship_codes, day_nums, WINDOWS)

print("\n  permutation test, three different nulls")
print("  (unrestricted lets a 1997 ship take a 2020 date, which it never could)")

# "within 3-year block" uses floor(year/3), so the first block (1993-1994) and
# the last (2025-2026) span two years rather than three. The middle ten span
# three. The effect is inside Monte Carlo noise, but the label is approximate.
NULLS = [("unrestricted", None), ("within 3-year block", 3), ("within year", 1)]
sims = {name: {w: [] for w in WINDOWS} for name, _ in NULLS}
for name, blocks in NULLS:
    if blocks is None:
        groups = [np.arange(len(ship_codes))]
    else:
        key = years // blocks
        groups = [np.where(key == b)[0] for b in np.unique(key)]
    for _ in range(N_PERM):
        sh = ship_codes.copy()
        for idx in groups:
            sh[idx] = rng.permutation(ship_codes[idx])
        c = count_repeats(sh, day_nums, WINDOWS)
        for w in WINDOWS:
            sims[name][w].append(c[w])

clus = []
for w in WINDOWS:
    obs = observed[w]
    row = {"window": w, "observed": obs}
    for name, _ in NULLS:
        a = np.array(sims[name][w])
        pval = (a >= obs).mean()
        row[name] = {"expected": round(float(a.mean()), 1), "sd": round(float(a.std()), 1),
                     "p": f"<{1/N_PERM:.4f}" if pval == 0 else round(float(pval), 4),
                     "times": round(float(obs / a.mean()), 1)}
        pstr = "<" + format(1 / N_PERM, ".4f") if pval == 0 else format(pval, ".4f")
        print(f"    {w:>3}d  {name:<22} observed {obs:>3}   expected "
              f"{a.mean():>5.1f} ± {a.std():.1f}   {obs/a.mean():.1f}x   p {pstr}")
    clus.append(row)
out["clustering"] = clus
print("\n  NOTE: the test assumes outbreaks are independent events. Because most")
print("  sub-30-day repeats are consecutive sailings, that assumption is weak at")
print("  the 30-day window. The 90-day figures are the more defensible ones.")

print()
print("=" * 72)
print("FINDING 4  null results")
print("=" * 72)
s1 = stats.spearmanr(p.passengers_total, p.pax_attack_rate)
v = p[p.voyage_days_valid]
s2 = stats.spearmanr(v.voyage_days, v.pax_attack_rate)
print(f"  ship size vs attack rate    rho = {s1.statistic:+.3f}  p = {s1.pvalue:.3f}  n = {len(p)}")
print(f"  voyage length vs attack rate rho = {s2.statistic:+.3f}  p = {s2.pvalue:.3f}  n = {len(v)}")
print(f"  (voyage length excludes {len(p)-len(v)} rows whose source dates are unusable)")
out["finding4"] = {
    "size_rho": round(float(s1.statistic), 3), "size_p": round(float(s1.pvalue), 3),
    "len_rho": round(float(s2.statistic), 3), "len_p": round(float(s2.pvalue), 3),
    "len_n": len(v), "len_excluded": len(p) - len(v),
}

print()
print("=" * 72)
print("DATA QUALITY")
print("=" * 72)
chk = df[df.cdc_pax_pct_check == "CHECK"]
print(f"  rows where CDC's PASSENGER percentage disagrees with its own counts: {len(chk)}")
for r in chk.itertuples():
    print(f"    {r.year} {r.ship:<30} {int(r.passengers_ill)}/{int(r.passengers_total)} "
          f"= {100*r.pax_attack_rate:.2f}%  published {r.passenger_pct}%")
chk_crew = df[df.cdc_crew_pct_check == "CHECK"]
print(f"\n  rows where CDC's CREW percentage disagrees with its own counts: {len(chk_crew)}")
for r in chk_crew.itertuples():
    print(f"    {r.year} {r.ship:<30} {int(r.crew_ill)}/{int(r.crew_total)} "
          f"= {100*r.crew_attack_rate:.2f}%  published {r.crew_pct}%")
src_err = df[df.voyage_days_source_error]
print(f"\n  rows whose voyage dates the source cannot have meant: {len(src_err)}")
for r in src_err.itertuples():
    print(f"    {r.year} {r.ship:<30} {r.voyage_start.date()} -> {r.voyage_end.date()} "
          f"({int(r.voyage_days)} days)")
bad = df[~df.voyage_days_valid & df.voyage_days.notna()]
print(f"\n  rows outside the 0-120 day analysis window (incl. the two above): {len(bad)}")
for r in bad.itertuples():
    print(f"    {r.year} {r.ship:<30} {r.voyage_start.date()} -> {r.voyage_end.date()} "
          f"({int(r.voyage_days)} days)")
ov = df[df.days_after_prior_voyage_end.lt(0)]
print(f"\n  rows overlapping the prior outbreak on the same ship: {len(ov)}")
for r in ov.itertuples():
    print(f"    {r.year} {r.ship:<30} starts {int(-r.days_after_prior_voyage_end)} days "
          f"before the previous investigation ended")
out["quality"] = {
    "cdc_pax_pct_disagreements": len(chk),
    "cdc_crew_pct_disagreements": len(chk_crew),
    "cdc_pct_disagreements_total": len(chk) + len(chk_crew),
    "voyage_days_source_errors": len(src_err),
    "outside_voyage_day_window": len(bad),
    "overlapping_records": len(ov),
    "unpaired_1993_2003": int((df[~df.paired].year <= 2003).sum()),
    "unpaired_2004_on": int((df[~df.paired].year >= 2004).sum()),
    "paired_distinct_ships": int(df[df.paired].ship.nunique()),
    "operators_with_one_paired_record": int(
        (df[df.paired].cruise_line.value_counts() == 1).sum()),
}

# series the dashboard plots
names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
months = []
for m in range(1, 13):
    allm = df[df.month == m]
    pm = p[p.month == m]
    months.append({"month": names[m - 1], "n_all": int(len(allm)), "n_paired": int(len(pm)),
                   "pax": round(100 * pm.passengers_ill.sum() / pm.passengers_total.sum(), 2)
                   if len(pm) and pm.passengers_total.sum() else None})
out["months"] = months

sc = p[["passengers_total", "pax_attack_rate", "ship", "year"]].dropna()
out["scatter"] = [{"x": int(r.passengers_total), "y": round(100 * r.pax_attack_rate, 2),
                   "s": r.ship, "yr": int(r.year)} for r in sc.itertuples()]
slope, intercept = np.polyfit(sc.passengers_total, 100 * sc.pax_attack_rate, 1)
out["scatter_fit"] = {"slope": float(slope), "intercept": float(intercept)}

out["gap_by_era"] = [{"era": e["era"], "years": e["years"], "ratio": e["ratio"],
                      "pax": e["pax"], "crew": e["crew"], "n": e["n"]} for e in eras]

json.dump(out, open(ROOT / "analysis_results.json", "w"), indent=1, default=str)
print(f"\nwrote {ROOT / 'analysis_results.json'}")
