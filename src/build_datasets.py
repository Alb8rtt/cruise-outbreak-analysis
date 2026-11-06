"""Write the two analysis-ready CSVs that the dashboard and Power BI build use.

Both come from prepare.py, so names, size bands and derived fields match the
workbook and the dashboard exactly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import load, paired_set  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

WIDE_COLS = [
    "year", "cruise_line", "ship", "voyage_start", "voyage_end", "voyage_days",
    "voyage_days_valid", "voyage_days_source_error",
    "month", "month_name", "quarter", "season", "era",
    "passengers_ill", "passengers_total", "pax_attack_rate",
    "crew_ill", "crew_total", "crew_attack_rate", "pax_crew_ratio",
    "total_ill", "total_onboard", "overall_rate",
    "ship_size_band", "days_since_prior_outbreak", "days_after_prior_voyage_end",
    "is_consecutive_sailing", "overlaps_prior_outbreak", "is_repeat_30d",
    "causative_agent", "paired", "has_counts",
    # CDC publishes a percentage beside its own counts for some records. Both
    # the passenger and the crew percentage are checked against the counts and
    # both flags are exported, so a reader can find every disagreement the
    # README cites without rerunning the pipeline.
    "passenger_pct", "cdc_pax_pct_variance_pp", "cdc_pax_pct_check",
    "crew_pct", "cdc_crew_pct_variance_pp", "cdc_crew_pct_check",
]
LONG_KEEP = ["year", "cruise_line", "ship", "voyage_start", "voyage_days",
             "month_name", "season", "era", "ship_size_band", "causative_agent"]


def main():
    df, n_transcribed, dropped = load()

    wide = df[WIDE_COLS].copy()
    for c in ("voyage_start", "voyage_end"):
        if c in wide:
            wide[c] = wide[c].dt.strftime("%Y-%m-%d")
    wide.to_csv(ROOT / "cruise_outbreaks.csv", index=False)

    # tidy, paired voyages only, so neither group is summed over voyages the
    # other group is missing
    import pandas as pd
    p = paired_set(df)
    parts = []
    for grp, ill, tot in [("Passengers", "passengers_ill", "passengers_total"),
                          ("Crew", "crew_ill", "crew_total")]:
        part = p[LONG_KEEP + [ill, tot]].copy()
        part.columns = LONG_KEEP + ["ill", "onboard"]
        part["group"] = grp
        parts.append(part)
    long = pd.concat(parts, ignore_index=True)
    long["attack_rate"] = long.ill / long.onboard
    long["voyage_start"] = long.voyage_start.dt.strftime("%Y-%m-%d")
    long = long[LONG_KEEP + ["group", "ill", "onboard", "attack_rate"]]
    long.to_csv(ROOT / "cruise_attack_rates_long.csv", index=False)

    print(f"transcribed {n_transcribed}, dropped {len(dropped)} without a resolvable date")
    print(f"wrote cruise_outbreaks.csv        {len(wide)} rows x {len(wide.columns)} cols")
    print(f"wrote cruise_attack_rates_long.csv {len(long)} rows "
          f"({long.group.value_counts().to_dict()})")
    pp = p.passengers_ill.sum() / p.passengers_total.sum()
    cc = p.crew_ill.sum() / p.crew_total.sum()
    print(f"paired voyages {len(p)}: passengers {100*pp:.2f}%, crew {100*cc:.2f}%, "
          f"ratio {pp/cc:.2f}x")


if __name__ == "__main__":
    main()
