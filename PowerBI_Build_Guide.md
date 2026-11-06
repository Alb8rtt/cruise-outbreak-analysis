# Power BI Build Guide
## Cruise Ship Outbreak Analysis · CDC Vessel Sanitation Program

Two CSVs ship with this project. You need both.

| File | Shape | Use it for |
|---|---|---|
| `cruise_outbreaks.csv` | One row per investigated voyage, 425 rows, 38 columns | Everything except the headline comparison |
| `cruise_attack_rates_long.csv` | One row per group (Passengers / Crew) per voyage, 606 rows | The headline charts, because `group` is already a dimension |

The long file is restricted to the 303 voyages where CDC published **both** passenger and crew counts, so the comparison stays paired and neither side is summed over voyages the other side is missing.

---

## 1. Load

Home > **Get data** > **Text/CSV**. Load both files.

Before you click Load, check the preview. Then in the Data view fix these:

- `year` imports as a whole number and Power BI will try to **sum** it. Select the column > Column tools > **Summarization: Don't summarize**.
- `voyage_start` and `voyage_end` should be **Date**. If they came in as text, Column tools > Data type > Date.
- `pax_attack_rate`, `crew_attack_rate`, `overall_rate`, `attack_rate` should be **Decimal number**, formatted as **Percentage**.

---

## 2. The one measure that matters

Home > **New measure**:

```dax
Attack Rate =
DIVIDE(
    SUM ( 'cruise_attack_rates_long'[ill] ),
    SUM ( 'cruise_attack_rates_long'[onboard] )
)
```

Format it as Percentage, 2 decimal places.

**Know why this is not `AVERAGE(attack_rate)`.** Averaging per-voyage rates gives a 600-passenger expedition ship the same weight as a 6,000-passenger megaship. Dividing summed numerator by summed denominator weights every person equally. If an interviewer asks you one technical question about this report, it will be this one.

Two more worth adding:

```dax
Outbreaks = COUNTROWS ( 'cruise_outbreaks' )
```

(`DISTINCTCOUNT` of `ship` would give you 158, the number of distinct vessels, not the number of investigations.)

```dax
Pax to Crew Ratio =
VAR Pax =
    CALCULATE ( [Attack Rate], 'cruise_attack_rates_long'[group] = "Passengers" )
VAR Crew =
    CALCULATE ( [Attack Rate], 'cruise_attack_rates_long'[group] = "Crew" )
RETURN
    DIVIDE ( Pax, Crew )
```

Format the ratio as Decimal, 2 places. It should read 3.83 across the whole dataset.

---

## 3. Era column

Select the long table > **New column**:

```dax
Era =
SWITCH (
    TRUE (),
    'cruise_attack_rates_long'[year] <= 2000, "1993-2000",
    'cruise_attack_rates_long'[year] <= 2005, "2001-2005",
    'cruise_attack_rates_long'[year] <= 2010, "2006-2010",
    'cruise_attack_rates_long'[year] <= 2015, "2011-2015",
    'cruise_attack_rates_long'[year] <= 2020, "2016-2020",
    "2021-2026"
)
```

These sort correctly on their own because the text starts with the year.

---

## 4. The visuals

### Page 1 header: cards

Four **Card** visuals across the top.

| Card | Field | Should read |
|---|---|---|
| Passenger rate | `Attack Rate` filtered to group = Passengers | 6.34% |
| Crew rate | `Attack Rate` filtered to group = Crew | 1.66% |
| Ratio | `Pax to Crew Ratio` | 3.83 |
| Outbreaks | Count of rows on `cruise_outbreaks.csv` | 425 |

To filter a single card to one group, drop `group` into the visual's **Filters on this visual** well and tick the one you want.

### Chart 1 — Passengers vs crew

**Clustered column chart.**
- X-axis: `group`
- Y-axis: `Attack Rate`

Two bars, passengers roughly four times crew. This is the argument.

### Chart 2 — Rates by era

**Line chart.**
- X-axis: `Era`
- Y-axis: `Attack Rate`
- Legend: `group`

Both lines wander. The crew line drops from 2.16% to 1.27% by 2016–2020 and then rebounds to 1.71%; the passenger line moves from 5.90% to 5.43%. Neither movement is statistically significant across individual voyages (crew ρ = −0.097, p = 0.092; passenger ρ = +0.011, p = 0.850).

**Do not title this chart as a trend.** An earlier version of this project titled it *"Thirty years of improvement went to the crew"*, which was wrong: that reading came from a sample cut at 2020 that excluded the rebound. Title it *"Attack rate by era, passengers and crew"* and let the gap between the two lines be the point, because the gap is the finding and the slope is not.

### Chart 3 — Seasonality

**Column chart**, from `cruise_outbreaks.csv`.
- X-axis: `month_name`
- Y-axis: Count of `ship`

**The trap everyone hits:** month names sort alphabetically, so you get Apr, Aug, Dec, Feb. Fix it once: Data view > select `month_name` > Column tools > **Sort by column** > `month`. Now it sorts Jan through Dec everywhere in the report.

### Chart 4 — Ship size (the null finding)

**Scatter chart**, from `cruise_outbreaks.csv`.
- X-axis: `passengers_total` (set Summarization to **Don't summarize**)
- Y-axis: `pax_attack_rate` (Don't summarize)
- Values: `ship`

Then Format pane > **Analytics** > **Trend line** > On.

Title it honestly: *"Ship size does not explain outbreak severity."* Do not hide a null result. Most junior portfolios only show the hypotheses that worked, and showing one that didn't is what makes the rest believable.

Caption it with the real statistic: the least-squares line slopes gently down, but that slope is carried by a handful of very small expedition ships with extreme rates and it does not survive a rank test (Spearman rho = -0.061, p = 0.29).

### Chart 5 — Repeat outbreaks

**Column chart**, from `cruise_outbreaks.csv`.
- X-axis: `is_repeat_30d`
- Y-axis: Count of `ship`

Or the better version: X-axis `ship`, Y-axis count, filtered to ships with 2 or more, sorted descending. Shows which vessels keep reappearing.

The observed-versus-chance comparison came from a permutation test in Python, not from the report. Put the numbers in a **Text box**, don't fake them with a visual, and quote all three nulls rather than the flattering one:

| Window | Observed | Unrestricted shuffle | Within 3-year block | Within calendar year |
| --- | --- | --- | --- | --- |
| 30 days | 47 | 7.8 (6.0x) | 17.2 (2.7x) | 24.1 (2.0x) |
| 90 days | 70 | 20.6 (3.4x) | 40.8 (1.7x) | 51.5 (1.4x) |

The unrestricted shuffle lets a 1997 vessel take a 2020 date, which inflates the effect. The within-year figures are the fair comparison. Use the 90-day row: at 30 days the independence assumption the test needs is weakest, because most sub-30-day repeats are consecutive sailings of the same loop rather than separate episodes.

---

## 5. Slicers

One row across the top, above the charts:

- `causative_agent`
- `season`
- `cruise_line` (set it to **Dropdown** in the Format pane, there are too many for a list)

Select all three, then **Format > Edit interactions** to confirm they filter every visual.

---

## 6. Polish

- **Page size:** Format > Canvas settings > 16:9. Don't leave it on whatever you dragged to.
- **Title the page with the finding, not the topic.** "Passengers fall ill at 3.8 times the crew rate on the same ship" beats "Cruise Outbreak Dashboard." A recruiter reads the title and nothing else if the title says nothing.
- **Colors:** pick two and stop. One for passengers, one for crew, grey for everything else. Don't let Power BI assign its default rainbow.
- **Turn off** visual headers and the "filters affecting this visual" tooltip clutter: Format > General > Header icons.
- **A text box at the bottom** with the source line and the note that four explanations for the gap are live and this data ranks none of them.

---

## 7. Publishing

Power BI Desktop is free. Getting a **public** link is not automatic, and many
organizations disable the feature, so check before investing hours in the build.

1. **Publish** to a workspace.
2. In the browser, open the report > File > **Embed report** > **Publish to web (public)**.

If "Publish to web" is missing or greyed out, the tenant administrator has
disabled it. Fall back to one of:

- Export to **PDF** and commit that alongside the `.pbix`
- Commit a screenshot of the finished report into the repository
- Build it in **Tableau Public**, which is free and designed for public sharing

A `.pbix` file plus a screenshot in the repository is a perfectly normal way to
publish a Power BI portfolio piece. Most people cannot publish publicly.

**Publish to web makes a report visible to anyone with the link, and to search
engines.** That is fine for public CDC data. Never use it for anything
containing real organizational data.

## Source and honesty notes

Data: CDC Vessel Sanitation Program outbreak investigations, 1993 to 2026.
https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks.html

Keep these visible rather than buried:

1. **Four explanations for the gap are live and this data ranks none of them.** Protocol (crew face mandatory hand hygiene, food-handler training and immediate isolation), acquired immunity from months of shipboard exposure, a younger crew population, and crew under-reporting driven by the incentive not to lose paid duty. Separating them would need a line's internal medical logs and crew tenure data. Say "not established", not "probably under-reporting".
2. CDC investigates once reported illness reaches 3% of passengers or crew, so every rate is conditional on an outbreak being investigated. This is not a rate across all cruises.
3. Counts are published only for closed reporting years. 122 of 425 records carry no counts and are flagged by `has_counts`. Nothing was estimated.
4. Thirteen records carry a CDC percentage that disagrees with CDC's own counts, seven on the passenger figure and six on the crew figure. The `cdc_pax_pct_check` and `cdc_crew_pct_check` columns flag them. Leaving the flag in the data beats silently picking one number.
