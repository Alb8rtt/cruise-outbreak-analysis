"""Load, normalize and derive the CDC VSP outbreak dataset.

Single source of truth. Every other script imports from here so the published
artifacts cannot drift apart.

Decisions made here, all of them disclosed in the README:
  * 428 records were transcribed. 3 carry month-only sailing dates in the CDC
    source and cannot be placed on a timeline, so the analysis set is 425.
  * Ship and cruise-line names are normalized, because the CDC source spells
    several of each more than one way across years.
  * Size bands are left-closed / right-open, so 2,000 passengers falls in the
    2,000-2,999 band rather than 1,000-1,999.
  * Nothing is imputed. Blank counts stay blank.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# CDC spells these differently across years. Same operator, same vessel.
LINE_FIXES = {
    "Holland America": "Holland America Line",
    "Celebrity Cruise Lines": "Celebrity Cruises",
    "Royal Caribbean Cruise Line": "Royal Caribbean International",
    "Royal Caribbean": "Royal Caribbean International",
    "Norwegian Cruise Lines": "Norwegian Cruise Line",
    "Carnival Cruises": "Carnival Cruise Line",
    "Carnival Cruise Lines": "Carnival Cruise Line",
    "Clipper Cruises": "Clipper Cruise Line",
    "Cunard Cruise Line": "Cunard Line",
    "Regent Seven Seas": "Regent Seven Seas Cruises",
    "Radisson Seven Seas Cruises": "Regent Seven Seas Cruises",
    "P & O Cruises": "P&O Cruises",
    "SilverSea Cruise Line": "Silversea Cruises",
    "SilverSeas Cruise Line": "Silversea Cruises",
    "Viking Cruises": "Viking Ocean Cruises",
    "Viking Ocean Cruises II Ltd.": "Viking Ocean Cruises",
    "Viking Expedition Operations": "Viking Ocean Cruises",
    "Fred Olsen Cruises": "Fred Olsen Cruise Lines",
    "Regal Cruises": "Regal Cruise Line",
    "Seabourn Cruise Lines": "Seabourn Cruise Line",
    # CDC appended an annotation to this operator's name on one row
    "Imperial Majesty Cruises (investigation at request of cruise line outside "
    "the U.S.)": "Imperial Majesty Cruises",
    # parent holding company, listed once in place of the operating brand.
    # Same treatment as the Viking entities above.
    "Prestige Cruise Holdings": "Oceania Cruises",
}

# CDC lists the same vessel with and without its brand prefix across years.
SHIP_FIXES = {
    "ms Maasdam": "Maasdam",
    "ms Veendam": "Veendam",
    "Constellation": "Celebrity Constellation",
    "Mercury": "Celebrity Mercury",
    "Infinity": "Celebrity Infinity",
    "Millennium": "Celebrity Millennium",
    "Summit": "Celebrity Summit",
    "Conquest": "Carnival Conquest",
    "Celebration": "Carnival Celebration",
    "Holiday": "Carnival Holiday",
    "Insignia": "Oceania Insignia",
    # dropped brand AND a vessel prefix on the same row
    "MV Marina": "Oceania Marina",
}

SIZE_BINS = [0, 1000, 2000, 3000, 10 ** 9]
SIZE_LABELS = ["1. Under 1,000", "2. 1,000-1,999", "3. 2,000-2,999", "4. 3,000+"]

ERA_BINS = [1992, 2000, 2005, 2010, 2015, 2020, 2027]
ERA_LABELS = ["1993-2000", "2001-2005", "2006-2010", "2011-2015", "2016-2020", "2021-2026"]


def load():
    """Return (analysis_set, n_transcribed, dropped_rows)."""
    frames = [pd.read_csv(f) for f in sorted(DATA.glob("outbreaks_*.csv"))]
    df = pd.concat(frames, ignore_index=True)
    n_transcribed = len(df)

    for c in ["passengers_ill", "passengers_total", "crew_ill", "crew_total",
              "passenger_pct", "crew_pct"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["cruise_line"] = df.cruise_line.str.strip().replace(LINE_FIXES)
    df["ship"] = df.ship.str.strip().replace(SHIP_FIXES)

    df["voyage_start"] = pd.to_datetime(df.voyage_start, format="%m/%d/%Y", errors="coerce")
    df["voyage_end"] = pd.to_datetime(df.voyage_end, format="%m/%d/%Y", errors="coerce")

    dropped = df[df.voyage_start.isna()].copy()
    df = df[df.voyage_start.notna()].sort_values("voyage_start").reset_index(drop=True)

    df["voyage_days"] = (df.voyage_end - df.voyage_start).dt.days
    # Four rows carry a voyage length the source cannot have meant: one ends
    # before it starts, one spans a year boundary with a typo'd year, and two
    # run for months. Flagged, never corrected. The 120-day ceiling is a
    # judgement call and it is stated in the README, because M/V Explorer 2004
    # (172 days) is a genuine Semester at Sea voyage, not a source error.
    # Two distinct things, kept apart on purpose.
    # (a) source defects: dates the CDC source cannot have meant.
    df["voyage_days_source_error"] = (
        df.voyage_days.notna() & ((df.voyage_days < 0) | (df.voyage_days > 365)))
    # (b) the analysis window. The 120-day ceiling is a judgement call, not a
    # source defect: M/V Explorer 2004 (172 days) is a genuine Semester at Sea
    # voyage and Zuiderdam 2025 (125 days) a genuine Grand World Voyage. Both
    # are excluded from voyage-length statistics by this threshold because they
    # are not comparable to a one-week cruise, not because the dates are wrong.
    df["voyage_days_valid"] = df.voyage_days.between(0, 120)

    df["month"] = df.voyage_start.dt.month
    df["month_name"] = df.voyage_start.dt.strftime("%b")
    df["quarter"] = "Q" + df.voyage_start.dt.quarter.astype(str)
    df["season"] = np.where(df.month.isin([12, 1, 2, 3]),
                            "Dec-Mar (norovirus season)", "Apr-Nov")
    df["era"] = pd.cut(df.year, ERA_BINS, labels=ERA_LABELS)

    df["pax_attack_rate"] = df.passengers_ill / df.passengers_total
    df["crew_attack_rate"] = df.crew_ill / df.crew_total
    # six voyages report zero ill crew, which makes the ratio infinite rather
    # than large. Leave those blank instead of shipping inf into the CSV; the
    # workbook's own formula guards the same way.
    df["pax_crew_ratio"] = (df.pax_attack_rate / df.crew_attack_rate).replace(
        [np.inf, -np.inf], np.nan)
    df["total_ill"] = df.passengers_ill + df.crew_ill
    df["total_onboard"] = df.passengers_total + df.crew_total
    df["overall_rate"] = df.total_ill / df.total_onboard

    # paired = both passenger and crew counts published; the comparison set
    df["paired"] = df[["passengers_ill", "passengers_total",
                       "crew_ill", "crew_total"]].notna().all(axis=1)
    df["has_counts"] = np.where(df.paired, "Counts published", "Counts not published")

    # left-closed, right-open: 2,000 passengers lands in the 2,000-2,999 band
    df["ship_size_band"] = pd.cut(df.passengers_total, SIZE_BINS,
                                  labels=SIZE_LABELS, right=False)

    prior_start = df.groupby("ship").voyage_start.shift(1)
    prior_end = df.groupby("ship").voyage_end.shift(1)
    df["days_since_prior_outbreak"] = (df.voyage_start - prior_start).dt.days
    # how long after the PREVIOUS voyage ended did this one begin?
    df["days_after_prior_voyage_end"] = (df.voyage_start - prior_end).dt.days
    # 0-2 days AFTER the prior voyage ended. A negative gap means the two
    # investigations overlap, which is a data-quality problem rather than a
    # next-sailing case, so it is deliberately not folded in here.
    df["is_consecutive_sailing"] = df.days_after_prior_voyage_end.between(0, 2)
    df["overlaps_prior_outbreak"] = df.days_after_prior_voyage_end.lt(0)
    df["is_repeat_30d"] = np.where(
        df.days_since_prior_outbreak.le(30), "Repeat within 30 days", "First or >30 days")

    # CDC publishes a percentage beside its own counts. Check both, not just one.
    df["cdc_pax_pct_variance_pp"] = (100 * df.pax_attack_rate - df.passenger_pct).round(2)
    df["cdc_crew_pct_variance_pp"] = (100 * df.crew_attack_rate - df.crew_pct).round(2)
    df["cdc_pax_pct_check"] = np.where(
        df.passenger_pct.isna() | df.pax_attack_rate.isna(), "",
        np.where(df.cdc_pax_pct_variance_pp.abs() > 0.11, "CHECK", "OK"))
    df["cdc_crew_pct_check"] = np.where(
        df.crew_pct.isna() | df.crew_attack_rate.isna(), "",
        np.where(df.cdc_crew_pct_variance_pp.abs() > 0.11, "CHECK", "OK"))
    # kept under the old names so the workbook's column mapping still resolves
    df["cdc_pct_variance_pp"] = df.cdc_pax_pct_variance_pp
    df["cdc_pct_check"] = df.cdc_pax_pct_check

    return df, n_transcribed, dropped


def paired_set(df):
    return df[df.paired].copy()


if __name__ == "__main__":
    df, n_t, dropped = load()
    print(f"transcribed       : {n_t}")
    print(f"dropped (no date) : {len(dropped)}")
    for r in dropped.itertuples():
        print(f"    {r.year}  {r.cruise_line} / {r.ship}")
    print(f"analysis set      : {len(df)}")
    print(f"paired (both counts): {int(df.paired.sum())}")
    print(f"no published counts : {int((~df.paired).sum())}")
    print(f"distinct ships      : {df.ship.nunique()}")
    print(f"distinct lines      : {df.cruise_line.nunique()}")
    print(f"date range          : {df.voyage_start.min().date()} to {df.voyage_start.max().date()}")
    p = paired_set(df)
    print(f"paired year range   : {int(p.year.min())} to {int(p.year.max())}")
    print(f"size bands          : {df.ship_size_band.value_counts().sort_index().to_dict()}")
