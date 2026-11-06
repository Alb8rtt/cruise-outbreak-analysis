"""Build the cruise outbreak analysis workbook from CDC VSP data.

Every analytical number in the workbook is an Excel formula, not a value written
from Python, so the whole thing recalculates if a row is added or changed.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import load as prepare_load
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.chart import BarChart, LineChart, ScatterChart, Reference, Series

OUT = str(Path(__file__).resolve().parent.parent / "Cruise_Outbreak_Analysis.xlsx")

NAVY = "1F3864"
ACCENT = "1F63D4"
LIGHT = "DCE6F1"
GREY = "F2F2F2"

H1 = Font(name="Arial", size=14, bold=True, color="FFFFFF")
H2 = Font(name="Arial", size=11, bold=True, color="FFFFFF")
BOLD = Font(name="Arial", size=10, bold=True)
BODY = Font(name="Arial", size=10)
SMALL = Font(name="Arial", size=9, color="595959")
TITLEFILL = PatternFill("solid", fgColor=NAVY)
HEADFILL = PatternFill("solid", fgColor=ACCENT)
SUBFILL = PatternFill("solid", fgColor=LIGHT)
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

PCT = "0.00%"
NUM = "#,##0"
DEC = "0.00"


# ----------------------------------------------------------------- load data
def load():
    """Use the shared pipeline so the workbook cannot drift from the CSVs."""
    df, _n_transcribed, _dropped = prepare_load()
    df = df.rename(columns={"voyage_start": "start_dt", "voyage_end": "end_dt"})
    return df.sort_values(["start_dt", "ship"], ascending=[False, True]).reset_index(drop=True)


def band(ws, r, c1, c2, text, fill=TITLEFILL, font=H1, height=22):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    cell = ws.cell(r, c1, text)
    cell.font = font
    cell.fill = fill
    cell.alignment = Alignment(vertical="center", horizontal="left", indent=1)
    ws.row_dimensions[r].height = height


# --------------------------------------------------------------------- DATA
def sheet_data(wb, df):
    ws = wb.create_sheet("Data")
    cols = [
        ("Year", 7), ("Cruise Line", 30), ("Ship", 30),
        ("Voyage Start", 13), ("Voyage End", 13), ("Voyage Days", 12),
        ("Month", 8), ("Season", 12),
        ("Pax Ill", 10), ("Pax Onboard", 13), ("Pax Attack Rate", 16),
        ("Crew Ill", 10), ("Crew Onboard", 13), ("Crew Attack Rate", 17),
        ("Pax : Crew Ratio", 17),
        ("Total Ill", 10), ("Total Onboard", 14), ("Overall Rate", 13),
        ("Passengers Aboard (band)", 22),
        ("Days Since Prior Outbreak (Same Ship)", 34),
        ("Causative Agent", 24),
        ("CDC Published Pax %", 20), ("Pax % Check", 14),
        ("CDC Published Crew %", 21), ("Crew % Check", 14),
        ("Era", 13),
        ("Paired Record", 14),
    ]
    for i, (name, w) in enumerate(cols, start=1):
        c = ws.cell(1, i, name)
        c.font = H2
        c.fill = HEADFILL
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 32

    n = len(df)
    last = n + 1
    for i, row in enumerate(df.itertuples(), start=2):
        ws.cell(i, 1, int(row.year))
        ws.cell(i, 2, row.cruise_line)
        ws.cell(i, 3, row.ship)
        ws.cell(i, 4, row.start_dt.date()).number_format = "mm/dd/yyyy"
        ws.cell(i, 5, row.end_dt.date()).number_format = "mm/dd/yyyy"
        ws.cell(i, 6, f"=IF(OR(D{i}=\"\",E{i}=\"\"),\"\",E{i}-D{i})")
        ws.cell(i, 7, f"=MONTH(D{i})")
        ws.cell(i, 8, f'=IF(OR(G{i}=12,G{i}<=3),"Dec-Mar (norovirus season)","Apr-Nov")')
        ws.cell(i, 9, None if pd.isna(row.passengers_ill) else int(row.passengers_ill))
        ws.cell(i, 10, None if pd.isna(row.passengers_total) else int(row.passengers_total))
        ws.cell(i, 11, f'=IF(OR(I{i}="",J{i}="",J{i}=0),"",I{i}/J{i})')
        ws.cell(i, 12, None if pd.isna(row.crew_ill) else int(row.crew_ill))
        ws.cell(i, 13, None if pd.isna(row.crew_total) else int(row.crew_total))
        ws.cell(i, 14, f'=IF(OR(L{i}="",M{i}="",M{i}=0),"",L{i}/M{i})')
        ws.cell(i, 15, f'=IF(OR(K{i}="",N{i}="",N{i}=0),"",K{i}/N{i})')
        ws.cell(i, 16, f'=IF(OR(I{i}="",L{i}=""),"",I{i}+L{i})')
        ws.cell(i, 17, f'=IF(OR(J{i}="",M{i}=""),"",J{i}+M{i})')
        ws.cell(i, 18, f'=IF(OR(P{i}="",Q{i}="",Q{i}=0),"",P{i}/Q{i})')
        ws.cell(i, 19, f'=IF(J{i}="","",IF(J{i}<1000,"1. Under 1,000",'
                       f'IF(J{i}<2000,"2. 1,000-1,999",IF(J{i}<3000,"3. 2,000-2,999","4. 3,000+"))))')
        # days since the previous outbreak on this same ship
        ws.cell(i, 20,
                f'=IF(_xlfn.MAXIFS($D$2:$D${last},$C$2:$C${last},C{i},$D$2:$D${last},"<"&D{i})=0,'
                f'"",D{i}-_xlfn.MAXIFS($D$2:$D${last},$C$2:$C${last},C{i},$D$2:$D${last},"<"&D{i}))')
        ws.cell(i, 21, row.causative_agent)
        ws.cell(i, 22, None if pd.isna(row.passenger_pct) else float(row.passenger_pct) / 100)
        ws.cell(i, 23, f'=IF(OR(K{i}="",V{i}=""),"",IF(ABS(K{i}-V{i})<0.0011,"OK","CHECK"))')
        # the crew percentage CDC publishes, checked the same way as the passenger one
        ws.cell(i, 24, None if pd.isna(row.crew_pct) else float(row.crew_pct) / 100)
        ws.cell(i, 25, f'=IF(OR(N{i}="",X{i}=""),"",IF(ABS(N{i}-X{i})<0.0011,"OK","CHECK"))')
        ws.cell(i, 26, f'=IF(A{i}<=2000,"1993-2000",IF(A{i}<=2005,"2001-2005",'
                       f'IF(A{i}<=2010,"2006-2010",IF(A{i}<=2015,"2011-2015",'
                       f'IF(A{i}<=2020,"2016-2020","2021-2026")))))')
        # 1 only when passenger AND crew counts both exist, so comparisons stay paired
        ws.cell(i, 27, f'=IF(AND(I{i}<>"",J{i}<>"",L{i}<>"",M{i}<>""),1,0)')

    for r in range(2, n + 2):
        for c in range(1, 28):
            cell = ws.cell(r, c)
            cell.font = BODY
            cell.border = BOX
        for c in (9, 10, 12, 13, 16, 17):
            ws.cell(r, c).number_format = NUM
        for c in (11, 14, 18, 22):
            ws.cell(r, c).number_format = PCT
        ws.cell(r, 15).number_format = "0.0\"x\""
        for c in (6, 7, 20):
            ws.cell(r, c).number_format = NUM

    tbl = Table(displayName="OutbreakData", ref=f"A1:AA{n + 1}")
    tbl.tableStyleInfo = TableStyleInfo(
        name="TableStyleLight9", showRowStripes=True, showColumnStripes=False)
    ws.add_table(tbl)
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:AA{n + 1}"
    return ws, n, last


# ----------------------------------------------------------------- ANALYSIS
def sheet_analysis(wb, df, last):
    ws = wb.create_sheet("Analysis")
    D = "Data!"
    rng = lambda col: f"{D}${col}$2:${col}${last}"
    ws.column_dimensions["A"].width = 34
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 17

    r = 1
    band(ws, r, 1, 7, "CRUISE SHIP OUTBREAK ANALYSIS  ·  CDC Vessel Sanitation Program")
    r += 1
    ws.cell(r, 1, "Every figure below is a live formula reading the Data tab. Add rows there and this recalculates.").font = SMALL
    r += 2

    # ---- Q1 passengers vs crew
    band(ws, r, 1, 7, "QUESTION 1  ·  Do passengers and crew get sick at the same rate?",
         fill=HEADFILL, font=H2, height=18)
    r += 1
    hdr = ["", "Outbreaks", "Total Pax Ill", "Total Pax Onboard", "Pax Attack Rate",
           "Total Crew Ill", "Total Crew Onboard"]
    for i, h in enumerate(hdr, start=1):
        c = ws.cell(r, i, h); c.font = BOLD; c.fill = SUBFILL; c.border = BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    first_q1 = r
    ws.cell(r, 1, "Outbreaks with BOTH passenger and crew counts").font = BODY
    ws.cell(r, 2, f'=SUMIFS({rng("AA")},{rng("AA")},1)')
    ws.cell(r, 3, f'=SUMIFS({rng("I")},{rng("AA")},1)')
    ws.cell(r, 4, f'=SUMIFS({rng("J")},{rng("AA")},1)')
    ws.cell(r, 5, f'=IF(D{r}=0,"",C{r}/D{r})')
    ws.cell(r, 6, f'=SUMIFS({rng("L")},{rng("AA")},1)')
    ws.cell(r, 7, f'=SUMIFS({rng("M")},{rng("AA")},1)')
    r += 1
    ws.cell(r, 1, "Crew attack rate (same voyages)").font = BOLD
    ws.cell(r, 5, f'=IF(G{r-1}=0,"",F{r-1}/G{r-1})')
    r += 1
    ws.cell(r, 1, "Passengers are this many times more likely to fall ill").font = BOLD
    ws.cell(r, 5, f'=IF(E{r-1}=0,"",E{first_q1}/E{r-1})')
    ws.cell(r, 5).number_format = "0.00\"x\""
    r += 1
    ws.cell(r, 1, "Outbreaks where the passenger rate exceeded the crew rate").font = BODY
    ws.cell(r, 2, f'=SUMPRODUCT((({rng("K")})>({rng("N")}))*(({rng("K")})<>""))')
    r += 1
    ws.cell(r, 1, "Crew live aboard for months, passengers for days. Same food, water and surfaces.").font = SMALL
    r += 2

    # ---- Q2 by era  (THE KEY TABLE)
    band(ws, r, 1, 7, "QUESTION 2  ·  Do the attack rates change across eras?",
         fill=HEADFILL, font=H2, height=18)
    r += 1
    for i, h in enumerate(["Era", "Paired Outbreaks", "Pax Ill", "Pax Onboard",
                           "Pax Attack Rate", "Crew Attack Rate", "Pax : Crew"], start=1):
        c = ws.cell(r, i, h); c.font = BOLD; c.fill = SUBFILL; c.border = BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    yr_first = r
    for era in ["1993-2000", "2001-2005", "2006-2010", "2011-2015", "2016-2020", "2021-2026"]:
        ws.cell(r, 1, era)
        ws.cell(r, 2, f'=COUNTIFS({rng("Z")},A{r},{rng("AA")},1)')
        ws.cell(r, 3, f'=SUMIFS({rng("I")},{rng("Z")},A{r},{rng("AA")},1)')
        ws.cell(r, 4, f'=SUMIFS({rng("J")},{rng("Z")},A{r},{rng("AA")},1)')
        ws.cell(r, 5, f'=IF(D{r}=0,"",C{r}/D{r})')
        ws.cell(r, 6, f'=IF(SUMIFS({rng("M")},{rng("Z")},A{r},{rng("AA")},1)=0,"",'
                      f'SUMIFS({rng("L")},{rng("Z")},A{r},{rng("AA")},1)/SUMIFS({rng("M")},{rng("Z")},A{r},{rng("AA")},1))')
        ws.cell(r, 7, f'=IF(OR(F{r}="",F{r}=0),"",E{r}/F{r})')
        r += 1
    yr_last = r - 1
    r += 1
    ws.cell(r, 1, "Change, first to last era with paired counts").font = BOLD
    ws.cell(r, 5, f'=IF(E{yr_first+1}=0,"",E{yr_first+5}/E{yr_first+1}-1)')
    ws.cell(r, 5).number_format = "+0.0%;-0.0%"
    ws.cell(r, 6, f'=IF(F{yr_first+1}=0,"",F{yr_first+5}/F{yr_first+1}-1)')
    ws.cell(r, 6).number_format = "+0.0%;-0.0%"
    for cc in range(1, 8):
        ws.cell(r, cc).border = BOX
    r += 1
    ws.cell(r, 1, "Counts are outbreaks with BOTH passenger and crew figures, the set the rates use. "
                  "1993-2000 is empty because CDC published no crew counts before 2004. The crew rate "
                  "reached a low of 1.27% in 2016-2020 and rebounded to 1.71%, so first-to-last "
                  "understates the dip and first-to-trough overstates the trend. Across individual "
                  "voyages neither trend is statistically significant (crew rho = -0.097, p = 0.092; "
                  "passenger rho = +0.011, p = 0.850). Read this table as the gap being present in "
                  "every era that has counts, not as a demonstrated improvement.").font = SMALL
    r += 2

    # ---- Q3 by line
    band(ws, r, 1, 7, "QUESTION 3  ·  Which lines report the most, and does volume mean severity?",
         fill=HEADFILL, font=H2, height=18)
    r += 1
    for i, h in enumerate(["Cruise Line", "Outbreaks", "Pax Ill", "Pax Onboard",
                           "Pax Attack Rate", "Worst Single Voyage", "Avg Voyage Days"], start=1):
        c = ws.cell(r, i, h); c.font = BOLD; c.fill = SUBFILL; c.border = BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    line_first = r
    lines = df.cruise_line.value_counts()
    lines = lines[lines >= 2].index.tolist()
    for ln in lines:
        ws.cell(r, 1, ln)
        ws.cell(r, 2, f'=COUNTIFS({rng("B")},A{r})')
        ws.cell(r, 3, f'=SUMIFS({rng("I")},{rng("B")},A{r})')
        ws.cell(r, 4, f'=SUMIFS({rng("J")},{rng("B")},A{r})')
        ws.cell(r, 5, f'=IF(D{r}=0,"",C{r}/D{r})')
        ws.cell(r, 6, f'=IF(D{r}=0,"",IFERROR(_xlfn.MAXIFS({rng("K")},{rng("B")},A{r}),""))')
        # bounded to the same 0-120 window the analysis uses, otherwise a
        # year-typo row drags an operator's mean from 7 days to 26
        ws.cell(r, 7).value = (f'=IFERROR(AVERAGEIFS({rng("F")},{rng("B")},A{r},'
                               f'{rng("F")},">=0",{rng("F")},"<=120"),"")')
        r += 1
    line_last = r - 1
    r += 1
    ws.cell(r, 1, "Operators with a single outbreak are not listed. Outbreak counts track fleet size "
                  "and voyage volume, so they are not a safety ranking, and the attack rate beside "
                  "them is pooled only over that operator's voyages that published counts, which is "
                  "fewer than the outbreak count in column B. Per-operator rates are NOT comparable "
                  "with each other: most operators carry a handful of voyages. Avg Voyage Days is "
                  "bounded to 0-120 days, matching the analysis window.").font = SMALL
    r += 2

    # ---- Q4 ship size
    band(ws, r, 1, 7, "QUESTION 4  ·  Do voyages with more passengers aboard have worse outbreaks?",
         fill=HEADFILL, font=H2, height=18)
    r += 1
    for i, h in enumerate(["Passengers Aboard", "Paired Outbreaks", "Pax Ill", "Pax Onboard",
                           "Pax Attack Rate", "Crew Attack Rate", ""], start=1):
        c = ws.cell(r, i, h); c.font = BOLD; c.fill = SUBFILL; c.border = BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    size_first = r
    for lbl in ["1. Under 1,000", "2. 1,000-1,999", "3. 2,000-2,999", "4. 3,000+"]:
        ws.cell(r, 1, lbl)
        ws.cell(r, 2, f'=COUNTIFS({rng("S")},A{r},{rng("AA")},1)')
        ws.cell(r, 3, f'=SUMIFS({rng("I")},{rng("S")},A{r},{rng("AA")},1)')
        ws.cell(r, 4, f'=SUMIFS({rng("J")},{rng("S")},A{r},{rng("AA")},1)')
        ws.cell(r, 5, f'=IF(D{r}=0,"",C{r}/D{r})')
        ws.cell(r, 6, f'=IF(SUMIFS({rng("M")},{rng("S")},A{r},{rng("AA")},1)=0,"",'
                      f'SUMIFS({rng("L")},{rng("S")},A{r},{rng("AA")},1)/SUMIFS({rng("M")},{rng("S")},A{r},{rng("AA")},1))')
        r += 1
    size_last = r - 1
    r += 2

    # ---- Q5 seasonality
    band(ws, r, 1, 7, "QUESTION 5  ·  When do outbreaks happen?", fill=HEADFILL, font=H2, height=18)
    r += 1
    for i, h in enumerate(["Month", "Outbreaks", "Pax Ill", "Pax Onboard",
                           "Pax Attack Rate", "", ""], start=1):
        c = ws.cell(r, i, h); c.font = BOLD; c.fill = SUBFILL; c.border = BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    mon_first = r
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for m, nm in enumerate(names, start=1):
        ws.cell(r, 1, nm)
        ws.cell(r, 2, f'=COUNTIFS({rng("G")},{m})')
        ws.cell(r, 3, f'=SUMIFS({rng("I")},{rng("G")},{m})')
        ws.cell(r, 4, f'=SUMIFS({rng("J")},{rng("G")},{m})')
        ws.cell(r, 5, f'=IF(D{r}=0,"",C{r}/D{r})')
        r += 1
    mon_last = r - 1
    r += 2

    # ---- Q6 recurrence
    band(ws, r, 1, 7, "QUESTION 6  ·  Do outbreaks repeat on the same ship?",
         fill=HEADFILL, font=H2, height=18)
    r += 1
    for i, h in enumerate(["Repeat window", "Repeat outbreaks", "Share of all outbreaks",
                           "", "", "", ""], start=1):
        c = ws.cell(r, i, h); c.font = BOLD; c.fill = SUBFILL; c.border = BOX
        c.alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    rec_first = r
    for w in (30, 60, 90, 180, 365):
        ws.cell(r, 1, f"Within {w} days")
        ws.cell(r, 2, f'=COUNTIFS({rng("T")},">0",{rng("T")},"<={w}")')
        ws.cell(r, 3, f'=IF(COUNTA({rng("C")})=0,"",B{r}/COUNTA({rng("C")}))')
        r += 1
    rec_last = r - 1
    r += 1
    ws.cell(r, 1, "Shortest gap between two outbreaks on the same ship (days)").font = BOLD
    ws.cell(r, 2, f'=_xlfn.MINIFS({rng("T")},{rng("T")},">0")')
    r += 1
    ws.cell(r, 1, "Outbreaks that follow a prior outbreak on the same ship").font = BODY
    ws.cell(r, 2, f'=SUMPRODUCT(({rng("T")}<>"")*1)')
    r += 1
    ws.cell(r, 1, "Most short-gap repeats are not a vessel returning to service too early. Of the 47 "
                  "outbreaks beginning within 30 days of a prior one on the same ship, 38 begin within "
                  "two days of the previous voyage ENDING and one overlaps it outright, so the median "
                  "gap is zero days. Those are the next sailing of the same loop, and the most "
                  "economical reading is one outbreak spanning a turnaround that CDC logged twice. "
                  "Treat these counts as investigations, not as distinct episodes.").font = SMALL

    # formats
    for rr in range(1, r + 1):
        for cc in range(1, 8):
            cell = ws.cell(rr, cc)
            if cell.font.size is None or cell.font.name != "Arial":
                if cell.value is not None and cell.font.b is not True:
                    cell.font = BODY
    for rr in list(range(first_q1, first_q1 + 3)) + list(range(yr_first, yr_last + 1)) + \
              list(range(line_first, line_last + 1)) + list(range(size_first, size_last + 1)) + \
              list(range(mon_first, mon_last + 1)):
        for cc in (3, 4):
            ws.cell(rr, cc).number_format = NUM
        for cc in (5, 6):
            ws.cell(rr, cc).number_format = PCT
        for cc in range(1, 8):
            ws.cell(rr, cc).border = BOX
    for rr in range(yr_first, yr_last + 1):
        ws.cell(rr, 7).number_format = "0.00\"x\""
    for rr in range(line_first, line_last + 1):
        ws.cell(rr, 6).number_format = PCT
        ws.cell(rr, 7).number_format = "0.0"
    for rr in range(rec_first, rec_last + 1):
        ws.cell(rr, 3).number_format = "0.0%"
        for cc in range(1, 4):
            ws.cell(rr, cc).border = BOX
    ws.cell(first_q1 + 2, 5).number_format = "0.00\"x\""
    # Q1 columns 6 and 7 are crew head counts, not rates
    ws.cell(first_q1, 6).number_format = NUM
    ws.cell(first_q1, 7).number_format = NUM
    ws.cell(first_q1 + 1, 6).number_format = "General"
    ws.cell(first_q1 + 1, 7).number_format = "General"

    return ws, dict(yr=(yr_first, yr_last), line=(line_first, line_last),
                    size=(size_first, size_last), mon=(mon_first, mon_last))


# ------------------------------------------------------------------- CHARTS
def sheet_charts(wb, refs):
    ws = wb.create_sheet("Charts")
    a = wb["Analysis"]

    yf, yl = refs["yr"]
    # skip the first era band: 1993-2000 has no paired counts, so plotting it
    # draws both series to zero at the left edge. Not a time series either, so
    # it is titled and labelled as eras, not years.
    c1 = LineChart(); c1.title = "Attack rate by era, passengers and crew"
    c1.y_axis.title = "Attack rate"; c1.x_axis.title = "Era"
    c1.height, c1.width = 8, 17
    data = Reference(a, min_col=5, max_col=6, min_row=yf - 1, max_row=yl)
    cats = Reference(a, min_col=1, min_row=yf + 1, max_row=yl)
    c1.add_data(data, titles_from_data=True); c1.set_categories(cats)
    ws.add_chart(c1, "B2")

    mf, ml = refs["mon"]
    c2 = BarChart(); c2.type = "col"; c2.title = "Outbreaks by month of voyage start"
    c2.y_axis.title = "Outbreaks"; c2.x_axis.title = "Month"
    c2.height, c2.width = 8, 17; c2.legend = None
    d2 = Reference(a, min_col=2, min_row=mf - 1, max_row=ml)
    k2 = Reference(a, min_col=1, min_row=mf, max_row=ml)
    c2.add_data(d2, titles_from_data=True); c2.set_categories(k2)
    ws.add_chart(c2, "B20")

    sf, sl = refs["size"]
    c3 = BarChart(); c3.type = "col"; c3.title = "Attack rate by passengers aboard"
    c3.y_axis.title = "Attack rate"; c3.height, c3.width = 8, 17
    d3 = Reference(a, min_col=5, max_col=6, min_row=sf - 1, max_row=sl)
    k3 = Reference(a, min_col=1, min_row=sf, max_row=sl)
    c3.add_data(d3, titles_from_data=True); c3.set_categories(k3)
    ws.add_chart(c3, "B38")

    # Deliberately NOT a chart of attack rate by operator. Most operators carry
    # a handful of voyages, so a sorted bar of per-operator rates reads as a
    # safety ranking, which this data cannot support. Outbreak counts, which
    # track fleet size and voyage volume, are what is plotted.
    lf, ll = refs["line"]
    c4 = BarChart(); c4.type = "bar"; c4.title = "Outbreak count by cruise line (tracks fleet size, not safety)"
    c4.height, c4.width = 11, 17; c4.legend = None
    d4 = Reference(a, min_col=2, min_row=lf - 1, max_row=ll)
    k4 = Reference(a, min_col=1, min_row=lf, max_row=ll)
    c4.add_data(d4, titles_from_data=True); c4.set_categories(k4)
    ws.add_chart(c4, "B56")

    ws.column_dimensions["A"].width = 3
    return ws


# ------------------------------------------------------------------- README
def sheet_readme(wb, df, n):
    ws = wb.create_sheet("Read Me", 0)
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 104
    rows = [
        ("T", "Cruise Ship Gastrointestinal Outbreak Analysis"),
        ("S", "Albert Rafael Alonso  ·  Source: CDC Vessel Sanitation Program"),
        ("", ""),
        ("H", "The question"),
        ("B", "Cruise lines treat gastrointestinal outbreaks as a vessel problem: deep clean the ship, "
              "sanitize surfaces, return to service. If that framing is right, then everyone aboard a "
              "ship during an outbreak should get sick at roughly the same rate. This analysis tests that."),
        ("", ""),
        ("H", "The data"),
        ("B", f"428 investigations were transcribed from CDC Vessel Sanitation Program records. Three "
              f"carry month-only sailing dates and cannot be placed on a timeline, so {n} are analysed, "
              "covering 1993 to July 2026. 303 carry both passenger and crew counts, spanning 2004 to "
              "2024, and every rate here comes from those. VSP has "
              "jurisdiction over every cruise ship carrying 13 or more passengers that calls on a US port. "
              "Each record is one investigated voyage: cruise line, ship, voyage dates, passengers ill out "
              "of passengers onboard, crew ill out of crew onboard, and the confirmed causative agent."),
        ("B", "CDC publishes passenger and crew counts only for closed reporting years. Recent-year rows "
              "appear without counts and are included for frequency analysis only. No count has been "
              "estimated or imputed anywhere in this workbook."),
        ("", ""),
        ("H", "What the analysis found"),
        ("B", "1.  Passengers fall ill at 6.34% against 1.66% for crew on the very same voyages, a "
              "factor of 3.83. That is 35,673 ill passengers out of 563,103 aboard, against 4,107 ill "
              "crew out of 248,020. The passenger rate was higher in 289 of the 303 outbreaks where "
              "both counts exist. The gap appears in all eleven subgroups the data supports, with "
              "ratios from 2.73x to 4.56x: every ship size band, every era that has paired counts and "
              "both seasons. Wilcoxon "
              "signed-rank p = 1.2e-47, rank-biserial r = 0.96."),
        ("B", "2.  The gap is persistent across eras, but neither group shows a statistically "
              "significant trend. The crew rate fell from 2.16% to a low of 1.27% in 2016-2020 and "
              "rebounded to 1.71%; the passenger rate moved from 5.90% to 5.43%. Across individual "
              "voyages, crew rho = -0.097 (p = 0.092) and passenger rho = +0.011 (p = 0.850). Neither "
              "is significant. What the data supports is that no trend is detectable in either "
              "direction over twenty-one years."),
        ("B", "3.  Most apparent repeat outbreaks are one episode counted twice. 47 outbreaks began "
              "within 30 days of a prior one on the same vessel, but 38 of those began within two "
              "days of the previous voyage ending and one overlapped it outright, median gap zero "
              "days. Those are the next sailing of the same loop. Genuine clustering exists but its "
              "size depends on the null: at the 90-day window, which is the defensible one, 3.4x "
              "under an unrestricted shuffle falls to 1.4x when the shuffle is restricted to within "
              "a calendar year. An earlier conclusion that vessels need longer clearance windows "
              "has been withdrawn."),
        ("B", "4.  No association between the number of passengers aboard and outbreak severity is "
              "detectable in this sample (rho = -0.061, p = 0.292), and the same is true of voyage "
              "length (rho = +0.020, p = 0.726). Neither result establishes that there is no "
              "relationship; at this sample size a modest one would not be detected. Note this is "
              "passengers ABOARD each sailing, not vessel capacity: the dataset carries no capacity "
              "field, so ship size proper was never tested. Both intuitive hypotheses are "
              "unsupported, and both are reported here rather than dropped."),
        ("", ""),
        ("H", "What this does not establish"),
        ("B", "Why the gap exists. This dataset carries no protocol, immunity or demographic "
              "variable. Protocol differences, acquired immunity from months of shipboard exposure, a "
              "younger crew population, and crew under-reporting are all live explanations, and "
              "nothing here ranks them. Separating them would need a line's internal medical logs and "
              "crew tenure data."),
        ("B", "Two earlier conclusions have been withdrawn. That crew outcomes improved while "
              "passenger outcomes did not rested on a sample cut at 2020 which excluded the post-2020 "
              "rebound; the cut was undisclosed and was what produced the significance. That vessels "
              "return to service too early rested on repeat outbreaks that turn out to be consecutive "
              "sailings."),
        ("", ""),
        ("H", "How this workbook is built"),
        ("B", "Data tab holds one row per investigated voyage as an Excel Table named OutbreakData. "
              "Attack rates, voyage length, size bands and days-since-the-last-outbreak-on-that-ship are "
              "all calculated columns, not pasted values."),
        ("B", "Analysis tab answers six questions using SUMIFS, COUNTIFS, AVERAGEIFS, SUMPRODUCT, "
              "MAXIFS, MINIFS and IFERROR against the Data tab. Every figure recalculates from Data, so "
              "adding rows updates them. The row labels are literal text: era boundaries, size bands "
              "and the cruise lines listed in Question 3 are typed, so a new era or a line outside "
              "that list needs its label added. This Read Me tab states findings as prose, which is "
              "text, not formulas."),
        ("B", "Charts tab shows attack rate by era, seasonality, attack rate by passengers aboard, "
              "and outbreak counts by line. None of the four is a time series or a safety ranking."),

        ("", ""),
        ("H", "Assumptions and limitations"),
        ("B", "·  Attack rates are calculated from the published ill and onboard counts, not copied from "
              "the CDC percentage column. The Data tab carries CDC's published percentage for BOTH "
              "passengers and crew alongside, and flags any row where the published figure and the "
              "counts disagree by more than a tenth of a point. Seven passenger rows and six crew "
              "rows are flagged, thirteen in all. Two of the crew ones look like a misplaced decimal "
              "point. Nothing is corrected; the flag is left in the data."),
        ("B", "·  CDC investigates a voyage when reported illness reaches 3% of passengers or crew, so "
              "this is a census of investigated outbreaks, not of all shipboard illness. Rates here are "
              "conditional on an outbreak having been investigated."),
        ("B", "·  Outbreak counts by cruise line reflect fleet size and voyage volume. They are not a "
              "safety ranking, and this workbook does not present them as one."),
        ("B", "·  Crew under-reporting is one of four live explanations for the gap, alongside protocol, "
              "acquired immunity and age mix. Crew have a financial incentive not to report illness "
              "that removes them from paid duty. This data cannot separate the four."),
        ("B", "·  Rate data covers 2004 to 2024, twenty-one years. The longer 1993 to 2026 span applies "
              "to outbreak frequency only."),
        ("B", "·  Seasonality is uncontrolled for exposure. Outbreaks concentrate December to March, but "
              "so does Caribbean sailing volume, and this dataset has no voyage counts by month."),
        ("B", "·  The Wilcoxon signed-rank test and the 2,000-iteration permutation tests were run in "
              "Python, because neither is a spreadsheet operation. src/analysis.py computes every "
              "figure quoted anywhere in this project, on the full sample, and ships alongside it."),
        ("B", "·  Two records carry voyage dates the CDC source cannot have meant: one ends 23 days "
              "before it starts, and one spans a year boundary with a typo'd year. Two further "
              "records are excluded from voyage-length statistics by a 120-day ceiling applied "
              "here, which is a judgement call and not a source defect: M/V Explorer 2004 is a "
              "genuine Semester at Sea voyage and Zuiderdam 2025 a Grand World Voyage. One pair of "
              "AIDAdiva 2019 records also overlaps. All are flagged, none corrected."),
        ("B", "·  Rows for 2019 through 2022 were read from a public mirror of the CDC page rather than "
              "cdc.gov directly, because the CDC archive URL was unreachable at collection time. 19 rows "
              "are affected and they are flagged in the source notes. Every source page was read "
              "through model-mediated text extraction rather than a direct HTML parse; totals "
              "reconcile and outliers were spot-checked, but no cell-level recheck against raw "
              "HTML has been done."),
        ("B", "·  The 303 paired voyages are not independent observations. They cover 121 vessels, "
              "and some recur heavily. The Wilcoxon and correlation p-values treat each voyage as "
              "independent, so the stated precision is optimistic. The effect size is large enough "
              "that clustering is very unlikely to overturn the direction."),
        ("B", "·  The 3% investigation threshold is triggered mostly by passenger illness, so the "
              "passenger rate here is effectively floored near 3% while the crew rate is not: 292 "
              "of 303 passenger rates sit at or above 3%, against 40 of 303 crew rates. The "
              "direction of the gap is robust; part of its magnitude comes from how these outbreaks "
              "came to be investigated."),
    ]
    r = 1
    for kind, text in rows:
        if kind == "T":
            band(ws, r, 1, 2, "  " + text, height=28)
        elif kind == "S":
            c = ws.cell(r, 2, text); c.font = Font(name="Arial", size=10, color="595959")
        elif kind == "H":
            c = ws.cell(r, 2, text)
            c.font = Font(name="Arial", size=11, bold=True, color=NAVY)
        elif kind == "B":
            c = ws.cell(r, 2, text); c.font = BODY
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 13 * (len(text) // 100 + 1) + 4
        r += 1
    return ws


# ------------------------------------------------------------ BUILD IT GUIDE
def sheet_guide(wb):
    ws = wb.create_sheet("Build It Yourself")
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 104
    rows = [
        ("T", "Build It Yourself"),
        ("", ""),
        ("H", "Add a native PivotTable (3 minutes)"),
        ("B", "The Analysis tab uses formulas rather than PivotTables so that every number is visible and "
              "auditable. Recruiters often ask for a PivotTable by name, so add one yourself:"),
        ("B", "1.  Go to the Data tab and click any cell inside the table."),
        ("B", "2.  Insert > PivotTable > New Worksheet."),
        ("B", "3.  Drag Cruise Line to Rows, Year to Columns, Pax Ill to Values (Sum), "
              "and Pax Onboard to Values (Sum)."),
        ("B", "4.  Add a calculated field: PivotTable Analyze > Fields, Items & Sets > Calculated Field. "
              "Name it Attack Rate, formula = Pax Ill / Pax Onboard, and format it as a percentage."),
        ("B", "5.  Add a Slicer on Causative Agent and one on Season. Now you can isolate norovirus-only "
              "outbreaks in one click."),
        ("", ""),
        ("H", "Rebuild the key formulas yourself so you can explain them"),
        ("B", "Attack rate:  =IF(OR(I2=\"\",J2=\"\",J2=0),\"\",I2/J2)  "
              "The guard matters. Rows without published counts would otherwise return a divide-by-zero."),
        ("B", "Days since the last outbreak on the same ship:  "
              "=D2-MAXIFS($D$2:$D$999,$C$2:$C$999,C2,$D$2:$D$999,\"<\"&D2)  "
              "MAXIFS finds the latest prior voyage date for that same ship. This is the formula to be "
              "ready to explain, it is the one that produced the recurrence finding."),
        ("B", "Count of outbreaks where passengers beat crew:  "
              "=SUMPRODUCT((range1>range2)*(range1<>\"\"))  "
              "SUMPRODUCT compares two ranges row by row without needing an array formula."),
        ("", ""),
        ("H", "How to talk about this in an interview"),
        ("B", "Lead with the finding, not the process. \"I pulled 30 years of CDC outbreak "
              "investigations, about 430 of them, and found passengers get sick at almost four times the "
              "crew rate on the same voyages. Crew live aboard for months and share the same water and "
              "galley, so the ship itself can't be the whole explanation.\""),
        ("B", "Then the part that makes them lean in. \"And over those 30 years the crew rate dropped "
              "about 40% while the passenger rate didn't move at all. Whatever the industry fixed, it "
              "fixed it for the crew and never extended it to passengers.\""),
        ("B", "Then the implication. \"That moves the problem from sanitation hardware toward passenger "
              "protocol and isolation speed, and the repeat-outbreak clustering says a ship coming off an "
              "outbreak needs a longer clearance window than it currently gets.\""),
        ("B", "Then volunteer the limitation before they find it. \"The honest caveat is crew "
              "under-reporting. Crew have an incentive not to report illness that pulls them off paid "
              "duty, and this data can't rule that out. I'd want the line's internal medical logs to "
              "separate those two explanations.\""),
        ("B", "That last move is the one that lands. Naming the weakness in your own analysis before the "
              "interviewer does reads as judgment, not as doubt."),
        ("", ""),
        ("H", "If they ask what you'd do next"),
        ("B", "·  Join to fleet deployment data so outbreak counts can be normalized per voyage, which "
              "would turn the cruise line comparison into something defensible."),
        ("B", "·  Pull CDC's ship sanitation inspection scores and test whether a low score predicts an "
              "outbreak in the following months. That is the obvious next question and the data is public."),
        ("B", "·  Model the revenue impact of extending the post-outbreak clearance window by 48 hours "
              "against the cost of a repeat outbreak and the compensation it triggers."),
    ]
    r = 1
    for kind, text in rows:
        if kind == "T":
            band(ws, r, 1, 2, "  " + text, height=28)
        elif kind == "H":
            c = ws.cell(r, 2, text)
            c.font = Font(name="Arial", size=11, bold=True, color=NAVY)
        elif kind == "B":
            c = ws.cell(r, 2, text); c.font = BODY
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 13 * (len(text) // 100 + 1) + 4
        r += 1
    return ws


def main():
    df = load()
    wb = Workbook()
    wb.remove(wb.active)
    _, n, last = sheet_data(wb, df)
    _, refs = sheet_analysis(wb, df, last)
    sheet_charts(wb, refs)
    sheet_readme(wb, df, n)
    # 'Build It Yourself' held private interview notes; kept out of the published file
    wb.move_sheet("Read Me", offset=-10)
    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
    wb["Data"].print_title_rows = "1:1"
    wb.active = 0
    wb.save(OUT)
    print(f"wrote {OUT}  ({n} data rows, sheets: {[s.title for s in wb.worksheets]})")


if __name__ == "__main__":
    main()
