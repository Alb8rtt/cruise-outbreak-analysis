# Sources — CDC Vessel Sanitation Program (VSP) cruise ship GI outbreak records

Collected 2026-11-05 and 2026-11-06.

## URLs fetched

| URL | Covers | Written to |
|---|---|---|
| https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks.html | 2023, 2024, 2025 | `outbreaks_2023_2026.csv` |
| https://www.cdc.gov/nceh/vsp/surv/gilist.htm | 2026 (to 2026-07-15) | `outbreaks_2023_2026.csv` |
| https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html | 1993–2018 | `outbreaks_1993_2018.csv` |
| https://www.restoredcdc.org/www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks.html | 2019–2022 (section "Earlier outbreaks (2019-2022)") | `outbreaks_2019_2022.csv` |
| https://archive.cdc.gov/#/details?url=... | wrapper used only to resolve archive link targets; no data taken | — |

The 1993–2018 page was read in several passes (the page text is ~104,200 characters and a
single read covers only the first 100,000), including one pass at `offset=98000` to reach
the final 1994 and 1993 rows.

### Note on the 2019–2022 source
The live CDC page links the 2019–2022 data to
`https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html`
(via an `archive.cdc.gov/#/details?url=...` wrapper). That URL was **not reachable** from this
session: `archive.cdc.gov/www_cdc_gov/vessel-sanitation/...-2019-2022.html` was refused as
off-allowlist, and direct HTTPS to `archive.cdc.gov` was blocked by the egress proxy. The
2019–2022 rows were therefore taken from the **restoredcdc.org mirror** of
`earlier-outbreaks.html`, which carries the 2019–2022 section inline. Values should be
re-verified against the canonical CDC archive page if that becomes reachable.

## Row counts

| File | Rows | Year range |
|---|---|---|
| `outbreaks_1993_2018.csv` | 345 | 1993–2018 |
| `outbreaks_2019_2022.csv` | 19 | 2019–2022 |

Per-year counts for the 1993–2018 file were cross-checked against a separate count of the
page's own tables and match exactly:

2018=11, 2017=11, 2016=13, 2015=12, 2014=9, 2013=9, 2012=16, 2011=14, 2010=14, 2009=15,
2008=14, 2007=24, 2006=36, 2005=20, 2004=36, 2003=25, 2002=23, 2001=4, 2000=6, 1999=5,
1998=8, 1997=9, 1996=3, 1995=3, 1994=4, 1993=1.

2019–2022: 2022=4, 2021=1, 2020=4, 2019=10.

## Source table shape vs. CSV columns

The CDC page does **not** publish twelve separate columns. It publishes:
`Year` / `Cruise Line` / `Cruise Ship` / `Sailing Dates` / `Causative Agent` /
`Case Counts (Passengers)` / `Case Counts (Crew)`.

- `Sailing Dates` is one cell, e.g. `04/25/2013-05/10/2013` → split into
  `voyage_start` / `voyage_end`.
- `Case Counts (Passengers)` is one cell, e.g. `23 of 1,963 (6.275%)` → split into
  `passengers_ill` / `passengers_total` / `passenger_pct`. Crew likewise.

No value was computed, rounded or inferred. Dates were zero-padded to MM/DD/YYYY, thousands
separators were stripped from counts, and `%` signs were stripped from percentages. That is
the only normalization applied.

## Commonly missing fields

In `outbreaks_1993_2018.csv`, all six count/percentage fields are empty for **92–93 of 345
rows** — essentially every row from 1993 through 2003, plus two later rows. On the page these
cells read `Data not available` or `Not available`, which was rendered as empty per the
"leave it empty" rule rather than copied as text.

Blank counts by column: `passengers_ill` 92, `passengers_total` 93, `passenger_pct` 93,
`crew_ill` 92, `crew_total` 92, `crew_pct` 92, `voyage_start` 3, `voyage_end` 3.

`outbreaks_2019_2022.csv` has **no** empty fields.

## Rows not fully transcribable, and oddities carried through as published

**Dates that could not be expressed as MM/DD/YYYY (3 rows — both date fields left empty):**
the page publishes only a month and year for these.
- 2002, Carnival Cruise Line, Carnival Pride — Sailing Dates cell reads `March 2002`
- 2001, Clipper Cruise Line, Nantucket Clipper — `September 2001`
- 2001, Delta Queen Steamboat Company, Mississippi — `August 2001`

**Internally inconsistent values, transcribed as published (not corrected):**
- 2013, Celebrity Cruise Lines, Celebrity Millennium, 04/25/2013–05/10/2013 — published as
  `23 of 1,963 (6.275%)`. 23/1963 is about 1.17%, so either the count or the percentage is
  wrong at the source. Verified against the page twice; left as published.
- 2011, Princess Cruises, Sea Princess, 05/30/2011–06/09/2011 — published as
  `14 of 2,128 (6.77%)`. Same kind of mismatch. Verified; left as published.
- 2004, Clipper Cruise Line, Nantucket Clipper — Sailing Dates `9/3/2004-8/11/2004`; the end
  date precedes the start date as published. Counts for this row are `Not available`.
- 1999, Clipper Cruise Line, Nantucket Clipper — Sailing Dates `1/2/1998-1/9/1999`, spanning
  two years; listed by CDC under 1999. Left as published.
- 2006, Royal Caribbean Cruise Line, Freedom of the Seas, 12/03/2006–12/10/2006 —
  `passenger_pct` is blank in the source although ill/total are given.
- 2004, Windjammer Barefoot Cruises, Legacy, 01/04/2004–01/10/2004 —
  `passengers_total` is blank in the source although ill count and percentage are given.
- 2006, Holland America Line, Veendam — Sailing Dates cell reads `4/22-5/9/2006`; the year
  appears once for the range, so recorded as 04/22/2006 and 05/09/2006.

**Annotations dropped from date fields (kept out so the date columns stay clean):**
- 1997, Royal Cruise Line, Royal Odyssey, 03/25/1997–04/04/1997 — cell also reads
  `(no sail recommendation)`
- 2006, Royal Caribbean Cruise Line, Freedom of the Seas, 12/03/2006–12/10/2006 — cell also
  reads `(no sail recommendation)`

**Cruise line names are inconsistent at the source** and were left as published, e.g.
`Celebrity Cruises` vs `Celebrity Cruise Lines`; `Carnival Cruise Line` vs
`Carnival Cruise Lines` vs `Carnival Cruises`; `Clipper Cruise Line` vs `Clipper Cruises`;
`SilverSea Cruise Line` vs `SilverSeas Cruise Line` vs `Silversea Cruises`;
`Cunard Line` vs `Cunard Cruise Line`; `P&O Cruises` vs `P & O Cruises`;
`Royal Caribbean` vs `Royal Caribbean Cruise Line` vs `Royal Caribbean International`.
Ship names likewise, in two patterns: a dropped prefix (`Maasdam` vs `ms Maasdam`, `Veendam`
vs `ms Veendam`) and a dropped brand (`Constellation` vs `Celebrity Constellation`, `Conquest`
vs `Carnival Conquest`, `Insignia` vs `Oceania Insignia`, and six more).

## Method caveat
Page text was read through WebFetch, whose extraction is model-mediated rather than a direct
HTML parse (direct HTTPS to `archive.cdc.gov` was blocked by the session's egress proxy).
Totals were reconciled against the page's own per-year row counts and several suspicious rows
were re-verified individually, but a cell-level re-check against the raw HTML is advisable
before using this for anything load-bearing.


## 2023–2026 (`outbreaks_2023_2026.csv`)

Collected 2026-11-05 from the two live CDC pages listed above, in a separate pass from the
archived years. 64 rows:

| Year | Rows | Counts published |
|---|---|---|
| 2023 | 14 | yes |
| 2024 | 18 | yes |
| 2025 | 23 | no |
| 2026 | 9 | no |

CDC publishes passenger and crew counts only for closed reporting years, so the 2025 and 2026
rows carry cruise line, ship, voyage dates and causative agent but no counts. Those cells were
left empty rather than estimated. The latest voyage start in the file is 2026-07-15; outbreaks
after that date had not been posted when this was collected.

## Method caveat — applies to every file here

All source pages were read through model-mediated text extraction (a fetch-and-summarise tool),
not a direct HTML parse, because the hosts are unreachable by direct HTTP from the collection
environment. Per-year row counts were cross-checked against a separate count of each page's own
tables and reconcile exactly, and outlier rows were individually re-verified against the page.
A cell-level recheck against raw HTML has **not** been done and is advisable before treating any
single row as authoritative.

## Normalisation applied downstream

`src/prepare.py` maps source spelling variants to one name each, because CDC spells several
operators and eleven vessels more than one way across years.

Cruise lines, 21 mappings covering 14 operators: Holland America, Celebrity, Royal Caribbean,
Norwegian, Carnival, Clipper, Cunard, Regent/Radisson Seven Seas, P&O, Silversea, Viking,
Fred Olsen, Regal and Seabourn. Several of these are spelled three ways in the source, which
is why there are more mappings than operators. One row also carries a CDC annotation inside
the operator name (`Imperial Majesty Cruises (investigation at request of cruise line outside
the U.S.)`), which is stripped back to the operator. One row lists the parent holding company
(`Prestige Cruise Holdings`) in place of the operating brand and is mapped to
`Oceania Cruises`, the same treatment already applied to the two Viking entities.

Vessels, 12 mappings: `ms Maasdam` → `Maasdam`, `ms Veendam` → `Veendam`, and ten where CDC
dropped the brand prefix in some years and kept it in others: `Constellation`, `Mercury`,
`Infinity`, `Millennium` and `Summit` → the `Celebrity` names; `Conquest`, `Celebration` and
`Holiday` → the `Carnival` names; `Insignia` → `Oceania Insignia`; and `MV Marina` →
`Oceania Marina`, which carries a vessel prefix and a dropped brand on the same row.

Without these mappings the dataset reports 168 vessels and 44 operators. That double-counts
ten vessels and four operators. The correct figures are **158 vessels and 40 operators**, and
they are what every artifact quotes.

### One unresolved name

`Coronia` (Cunard Line, 2001-03-11 to 2001-03-29) is very probably a transcription error for
`Caronia`, which appears separately for Cunard in 2002. Cunard operated *Caronia* from 1999 to
2004 and never operated a *Coronia*. The two are one edit apart, under the same operator, in
consecutive years. It is **left unmerged** because the CDC page could not be re-read to confirm
the spelling at source, and merging on an assumption would be the same class of error as
leaving a real duplicate in. If confirmed, the vessel count becomes 157. The repeat-outbreak
windows are unaffected either way: the gap between the two records is 378 days.

The raw CSVs in this folder are left exactly as transcribed; normalisation happens at load time.
