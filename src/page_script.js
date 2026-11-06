const NS = "http://www.w3.org/2000/svg";
const tt = document.getElementById("tt");
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = (n) => n.toLocaleString();

function el(tag, attrs, parent) {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}
function clear(svg) { while (svg.firstChild) svg.removeChild(svg.firstChild); }
function showTT(html, ev) {
  tt.innerHTML = html;
  tt.style.opacity = 1;
  const r = tt.getBoundingClientRect();
  let x = ev.clientX + 14, y = ev.clientY - r.height - 12;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y < 8) y = ev.clientY + 18;
  tt.style.left = x + "px"; tt.style.top = y + "px";
}
const hideTT = () => { tt.style.opacity = 0; };
function roundedBar(bx, by, bw, bh, fill, svg) {
  const r = Math.min(4, bw / 2, bh);
  el("path", {
    d: `M${bx},${by + bh} L${bx},${by + r} Q${bx},${by} ${bx + r},${by} ` +
       `L${bx + bw - r},${by} Q${bx + bw},${by} ${bx + bw},${by + r} L${bx + bw},${by + bh} Z`,
    fill
  }, svg);
}

/* ---------------------------------------------------------------- stat row */
(function statRow() {
  const h = DATA.finding1, d = DATA.dataset;
  const cells = [
    { v: h.pax_rate + "%", c: "o", l: "of passengers fell ill<br>" + fmt(h.pax_ill) + " of " + fmt(h.pax_total) },
    { v: h.crew_rate + "%", c: "b", l: "of crew fell ill<br>" + fmt(h.crew_ill) + " of " + fmt(h.crew_total) },
    { v: h.ratio + "×", c: "", l: "the passenger rate, as a<br>multiple of the crew rate" },
    { v: Math.round(100 * h.n_higher / h.n) + "%", c: "", l: "of outbreaks had a higher passenger<br>rate (" + h.n_higher + " of " + h.n + ")" },
    { v: fmt(d.analysis_set), c: "", l: "investigations analysed<br>across " + d.ships + " vessels" },
  ];
  document.getElementById("stats").innerHTML = cells.map(c =>
    `<div class="stat"><div class="v ${c.c}">${c.v}</div><div class="l">${c.l}</div></div>`).join("");
  document.getElementById("statnote").textContent =
    `${d.transcribed} investigations were transcribed from CDC records; ${d.dropped_no_date} carry ` +
    `month-only sailing dates and cannot be placed on a timeline, leaving ${d.analysis_set}. ` +
    `Rates come from the ${d.paired} records carrying both passenger and crew counts, spanning ` +
    `${d.paired_year_min} to ${d.paired_year_max}.`;
})();

/* --------------------------------------------------- 1. subgroup dumbbells */
function drawSub() {
  const svg = document.getElementById("c-sub"); clear(svg);
  const W = 760, H = 430, L = 196, R = 58, T = 26, B = 40;
  const rows = DATA.subgroups;
  const maxX = 8;
  const x = v => L + (W - L - R) * (v / maxX);
  const rowH = (H - T - B) / rows.length;
  const LABELS = { ship_size_band: "Passengers aboard", era: "Era", season: "Season" };

  for (let v = 0; v <= maxX; v += 2) {
    el("line", { x1: x(v), x2: x(v), y1: T - 6, y2: H - B, class: "grid-line" }, svg);
    el("text", { x: x(v), y: H - B + 18, class: "tick", "text-anchor": "middle" }, svg)
      .textContent = v + "%";
  }
  el("text", { x: L, y: T - 14, class: "alab" }, svg).textContent = "Pooled attack rate";

  let lastBy = null;
  rows.forEach((r, i) => {
    const cy = T + rowH * i + rowH / 2;
    if (r.by !== lastBy) {
      el("text", { x: 6, y: cy - 1, class: "dlab", fill: css("--ink-3") }, svg)
        .textContent = LABELS[r.by] || r.by;
      lastBy = r.by;
      if (i) el("line", { x1: 6, x2: W - R, y1: T + rowH * i - 2, y2: T + rowH * i - 2,
        stroke: css("--grid"), "stroke-width": 1 }, svg);
    }
    const name = r.group.replace(/^\d\.\s*/, "").replace(" (norovirus season)", "");
    el("text", { x: L - 12, y: cy + 4, class: "tick", "text-anchor": "end" }, svg).textContent = name;

    el("line", { x1: x(r.crew), x2: x(r.pax), y1: cy, y2: cy,
      stroke: css("--axis"), "stroke-width": 2, "stroke-linecap": "round" }, svg);
    el("circle", { cx: x(r.crew), cy, r: 6, fill: css("--s1"),
      stroke: css("--surface-1"), "stroke-width": 2 }, svg);
    el("circle", { cx: x(r.pax), cy, r: 6, fill: css("--s2"),
      stroke: css("--surface-1"), "stroke-width": 2 }, svg);
    el("text", { x: W - R + 8, y: cy + 4, class: "dlab", fill: css("--ink-2") }, svg)
      .textContent = r.ratio + "×";

    const hit = el("rect", { x: 0, y: T + rowH * i, width: W, height: rowH, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", e => showTT(
      `<b>${name}</b><div class="r"><i>Passengers</i><span>${r.pax}%</span></div>` +
      `<div class="r"><i>Crew</i><span>${r.crew}%</span></div>` +
      `<div class="r"><i>Ratio</i><span>${r.ratio}×</span></div>` +
      `<div class="r"><i>Outbreaks</i><span>${r.n}</span></div>`, e));
    hit.addEventListener("mouseleave", hideTT);
  });
  el("text", { x: W - R + 8, y: T - 14, class: "alab" }, svg).textContent = "Ratio";
}

/* ------------------------------------------------------------- 2. era line */
function drawEra() {
  const svg = document.getElementById("c-era"); clear(svg);
  const W = 760, H = 360, L = 52, R = 112, T = 20, B = 52;
  const d = DATA.eras, n = d.length, maxY = 8;
  const x = i => L + (W - L - R) * (n === 1 ? .5 : i / (n - 1));
  const y = v => T + (H - T - B) * (1 - v / maxY);

  for (let v = 0; v <= maxY; v += 2) {
    el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid-line" }, svg);
    el("text", { x: L - 10, y: y(v) + 4, class: "tick", "text-anchor": "end" }, svg)
      .textContent = v + "%";
  }
  el("line", { x1: L, x2: W - R, y1: y(0), y2: y(0), class: "axis-line" }, svg);
  d.forEach((p, i) => {
    el("text", { x: x(i), y: H - B + 18, class: "tick", "text-anchor": "middle" }, svg)
      .textContent = p.era;
    el("text", { x: x(i), y: H - B + 33, class: "tick", "text-anchor": "middle",
      fill: css("--ink-3") }, svg).textContent = "n=" + p.n;
  });

  [{ k: "pax", name: "Passengers", color: css("--s2") },
   { k: "crew", name: "Crew", color: css("--s1") }].forEach(s => {
    const pts = d.map((p, i) => [x(i), y(p[s.k])]);
    el("path", { d: "M" + pts.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join("L"),
      fill: "none", stroke: s.color, "stroke-width": 2,
      "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    pts.forEach(p => el("circle", { cx: p[0], cy: p[1], r: 6.5,
      fill: css("--surface-1"), stroke: s.color, "stroke-width": 2 }, svg));
    const last = pts[pts.length - 1];
    el("text", { x: last[0] + 14, y: last[1] + 4, class: "dlab", fill: s.color }, svg)
      .textContent = s.name;
    el("text", { x: last[0] + 14, y: last[1] + 20, class: "tick", fill: css("--ink-3") }, svg)
      .textContent = d[d.length - 1][s.k] + "%";
  });

  d.forEach((p, i) => {
    const w = (W - L - R) / n;
    const r = el("rect", { x: x(i) - w / 2, y: T, width: w, height: H - T - B,
      fill: "transparent" }, svg);
    r.addEventListener("mousemove", e => showTT(
      `<b>${p.era}</b><div class="r"><i>Years with counts</i><span>${p.years}</span></div>` +
      `<div class="r"><i>Passengers</i><span>${p.pax}%</span></div>` +
      `<div class="r"><i>Crew</i><span>${p.crew}%</span></div>` +
      `<div class="r"><i>Ratio</i><span>${p.ratio}×</span></div>` +
      `<div class="r"><i>Outbreaks</i><span>${p.n}</span></div>`, e));
    r.addEventListener("mouseleave", hideTT);
  });
}

/* ------------------------------------------------- 3. consecutive sailings */
function drawConsec() {
  const svg = document.getElementById("c-consec"); clear(svg);
  const W = 760, H = 180, L = 16, R = 16, T = 46, B = 44;
  const f = DATA.finding3;
  // three categories, not two: consecutive sailings, records that overlap the
  // prior investigation outright, and genuinely separate episodes.
  const total = f.repeats_30d;
  const consec = f.consecutive_sailings;
  const overlap = f.overlapping_30d || 0;
  const rest = total - consec - overlap;
  const barW = W - L - R, barH = H - T - B;
  const w1 = barW * consec / total;
  const w2 = barW * overlap / total;

  roundedBar(L, T, w1, barH, css("--s2"), svg);
  if (overlap) roundedBar(L + w1 + 2, T, Math.max(w2 - 2, 3), barH, css("--s3"), svg);
  roundedBar(L + w1 + w2 + 2, T, barW - w1 - w2 - 2, barH, css("--s1"), svg);

  el("text", { x: L + 12, y: T + barH / 2 + 5, class: "dlab", fill: "#ffffff" }, svg)
    .textContent = consec + " begin within 2 days of the previous voyage ending";
  el("text", { x: L + w1 + w2 + 12, y: T + barH / 2 + 5, class: "dlab", fill: "#ffffff" }, svg)
    .textContent = rest + " do not";
  el("text", { x: L, y: T - 16, class: "alab" }, svg)
    .textContent = `All ${total} outbreaks beginning within 30 days of a prior outbreak on the same ship`;
  el("text", { x: L, y: H - 12, class: "tick", fill: css("--ink-3") }, svg)
    .textContent = `Median gap: ${f.median_days_after_prior_end} days`
      + (overlap ? `. The thin band is ${overlap} record that overlaps the prior investigation outright.` : "");
}

/* ---------------------------------------------------------- 4. clustering */
function drawClus() {
  const svg = document.getElementById("c-clus"); clear(svg);
  const W = 760, H = 300, L = 46, R = 16, T = 26, B = 46;
  const d = DATA.clustering, maxY = 80, gw = (W - L - R) / d.length;
  const y = v => T + (H - T - B) * (1 - v / maxY);

  for (let v = 0; v <= maxY; v += 20) {
    el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid-line" }, svg);
    el("text", { x: L - 10, y: y(v) + 4, class: "tick", "text-anchor": "end" }, svg).textContent = v;
  }
  el("line", { x1: L, x2: W - R, y1: y(0), y2: y(0), class: "axis-line" }, svg);
  el("text", { x: L, y: T - 8, class: "alab" }, svg)
    .textContent = "Repeat outbreaks on the same vessel";

  d.forEach((p, i) => {
    const exp = p["within year"];
    const pairs = [{ v: p.observed, c: css("--s2") }, { v: exp.expected, c: css("--s1") }];
    const bw = (gw - 28) / 2;
    pairs.forEach((b, j) => {
      const bx = L + gw * i + 14 + j * (bw + 2);
      const by = y(b.v);
      roundedBar(bx, by, bw, y(0) - by, b.c, svg);
      el("text", { x: bx + bw / 2, y: by - 7, class: "tick", "text-anchor": "middle",
        fill: css("--ink-2") }, svg).textContent = b.v;
    });
    el("text", { x: L + gw * i + gw / 2, y: H - B + 20, class: "tick", "text-anchor": "middle" }, svg)
      .textContent = p.window + " days";
    const hit = el("rect", { x: L + gw * i, y: T, width: gw, height: H - T - B,
      fill: "transparent" }, svg);
    hit.addEventListener("mousemove", e => showTT(
      `<b>Within ${p.window} days</b><div class="r"><i>Observed</i><span>${p.observed}</span></div>` +
      `<div class="r"><i>Unrestricted</i><span>${p.unrestricted.expected} (${p.unrestricted.times}×)</span></div>` +
      `<div class="r"><i>3-year block</i><span>${p["within 3-year block"].expected} (${p["within 3-year block"].times}×)</span></div>` +
      `<div class="r"><i>Within year</i><span>${exp.expected} (${exp.times}×)</span></div>`, e));
    hit.addEventListener("mouseleave", hideTT);
  });

  document.getElementById("clus-table").innerHTML =
    `<table><thead><tr><th>Window</th><th>Observed</th><th>Unrestricted shuffle</th>
     <th>Within 3-year block</th><th>Within calendar year</th></tr></thead><tbody>` +
    d.map(p => `<tr><td>${p.window} days</td><td>${p.observed}</td>` +
      ["unrestricted", "within 3-year block", "within year"].map(k =>
        `<td>${p[k].expected} ± ${p[k].sd} (${p[k].times}×)</td>`).join("") +
      `</tr>`).join("") + `</tbody></table>`;
}

/* ------------------------------------------------------------- 5. scatter */
function drawScatter() {
  const svg = document.getElementById("c-scatter"); clear(svg);
  const W = 760, H = 380, L = 52, R = 20, T = 20, B = 52;
  const pts = DATA.scatter, fit = DATA.scatter_fit;
  const maxX = 6600, maxY = 45;
  const x = v => L + (W - L - R) * (v / maxX);
  const y = v => T + (H - T - B) * (1 - Math.min(v, maxY) / maxY);

  for (let v = 0; v <= maxY; v += 15) {
    el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid-line" }, svg);
    el("text", { x: L - 10, y: y(v) + 4, class: "tick", "text-anchor": "end" }, svg)
      .textContent = v + "%";
  }
  for (let v = 0; v <= 6000; v += 2000) {
    el("text", { x: x(v), y: H - B + 20, class: "tick", "text-anchor": "middle" }, svg)
      .textContent = v.toLocaleString();
  }
  el("line", { x1: L, x2: W - R, y1: y(0), y2: y(0), class: "axis-line" }, svg);
  el("text", { x: L, y: T - 4, class: "alab" }, svg).textContent = "Passenger attack rate";
  el("text", { x: (L + W - R) / 2, y: H - 10, class: "alab", "text-anchor": "middle" }, svg)
    .textContent = "Passengers aboard";

  pts.forEach(p => {
    const c = el("circle", { cx: x(p.x), cy: y(p.y), r: 4.5, fill: css("--s1"),
      "fill-opacity": 0.42, stroke: css("--surface-1"), "stroke-width": 1 }, svg);
    c.addEventListener("mousemove", e => showTT(
      `<b>${p.s}</b><div class="r"><i>Year</i><span>${p.yr}</span></div>` +
      `<div class="r"><i>Passengers</i><span>${fmt(p.x)}</span></div>` +
      `<div class="r"><i>Attack rate</i><span>${p.y}%</span></div>`, e));
    c.addEventListener("mouseleave", hideTT);
  });

  const yB = fit.intercept + fit.slope * maxX;
  el("line", { x1: x(0), y1: y(fit.intercept), x2: x(maxX), y2: y(yB),
    stroke: css("--ink-2"), "stroke-width": 2, "stroke-dasharray": "7 5",
    "stroke-linecap": "round" }, svg);
  el("text", { x: W - R - 6, y: y(yB) - 26, class: "dlab", fill: css("--ink-2"),
    "text-anchor": "end" }, svg).textContent = "Least-squares fit";
  el("text", { x: W - R - 6, y: y(yB) - 11, class: "tick", fill: css("--ink-3"),
    "text-anchor": "end" }, svg).textContent = "not significant, p = 0.29";
}

/* --------------------------------------------------------------- 6. months */
let monthMode = "count";
function drawMonth() {
  const svg = document.getElementById("c-month"); clear(svg);
  const W = 760, H = 320, L = 46, R = 16, T = 30, B = 42;
  const d = DATA.months;
  const key = monthMode === "count" ? "n_all" : "pax";
  const maxV = Math.max(...d.map(p => p[key] || 0));
  const maxY = monthMode === "count" ? Math.ceil(maxV / 20) * 20 : Math.ceil(maxV);
  const bw = (W - L - R) / d.length;
  const y = v => T + (H - T - B) * (1 - v / maxY);

  el("rect", { x: L, y: T, width: bw * 3, height: H - T - B,
    fill: css("--s1"), opacity: 0.07 }, svg);
  el("rect", { x: L + bw * 11, y: T, width: bw, height: H - T - B,
    fill: css("--s1"), opacity: 0.07 }, svg);
  el("text", { x: L + 6, y: T + 14, class: "alab", fill: css("--ink-3") }, svg)
    .textContent = "Norovirus season";

  for (let i = 0; i <= 4; i++) {
    const v = maxY * i / 4;
    el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: "grid-line" }, svg);
    el("text", { x: L - 10, y: y(v) + 4, class: "tick", "text-anchor": "end" }, svg)
      .textContent = monthMode === "count" ? v : v.toFixed(0) + "%";
  }
  el("line", { x1: L, x2: W - R, y1: y(0), y2: y(0), class: "axis-line" }, svg);

  d.forEach((p, i) => {
    const v = p[key] || 0;
    const bx = L + bw * i + 2, bWid = bw - 4, by = y(v);
    roundedBar(bx, by, bWid, Math.max(0, y(0) - by), css("--s1"), svg);
    el("text", { x: bx + bWid / 2, y: H - B + 19, class: "tick", "text-anchor": "middle" }, svg)
      .textContent = p.month;
    const hit = el("rect", { x: L + bw * i, y: T, width: bw, height: H - T - B,
      fill: "transparent" }, svg);
    hit.addEventListener("mousemove", e => showTT(
      `<b>${p.month}</b><div class="r"><i>Outbreaks (all)</i><span>${p.n_all}</span></div>` +
      `<div class="r"><i>With counts</i><span>${p.n_paired}</span></div>` +
      (p.pax !== null ? `<div class="r"><i>Attack rate</i><span>${p.pax}%</span></div>` : ""), e));
    hit.addEventListener("mouseleave", hideTT);
  });
  el("text", { x: L, y: T - 10, class: "alab" }, svg).textContent =
    monthMode === "count"
      ? "Outbreaks investigated, all 425 records"
      : "Pooled passenger attack rate, 303 records with counts";
}

/* ------------------------------------------------------------------ tables */
const TABLES = {
  sub: () => `<table><thead><tr><th>Subgroup</th><th>Outbreaks</th><th>Passenger rate</th>
    <th>Crew rate</th><th>Ratio</th></tr></thead><tbody>` +
    DATA.subgroups.map(r => `<tr><td>${r.group.replace(/^\d\.\s*/, "")}</td><td>${r.n}</td>
      <td>${r.pax}%</td><td>${r.crew}%</td><td>${r.ratio}×</td></tr>`).join("") + `</tbody></table>`,
  era: () => `<table><thead><tr><th>Era</th><th>Years with counts</th><th>Outbreaks</th>
    <th>Passenger rate</th><th>Crew rate</th><th>Ratio</th></tr></thead><tbody>` +
    DATA.eras.map(e => `<tr><td>${e.era}</td><td>${e.years}</td><td>${e.n}</td>
      <td>${e.pax}%</td><td>${e.crew}%</td><td>${e.ratio}×</td></tr>`).join("") + `</tbody></table>`,
  month: () => `<table><thead><tr><th>Month</th><th>Outbreaks (all)</th><th>With counts</th>
    <th>Passenger rate</th></tr></thead><tbody>` +
    DATA.months.map(m => `<tr><td>${m.month}</td><td>${m.n_all}</td><td>${m.n_paired}</td>
      <td>${m.pax === null ? "—" : m.pax + "%"}</td></tr>`).join("") + `</tbody></table>`,
  clus: () => `<table><thead><tr><th>Window</th><th>Observed</th><th>Unrestricted</th>
    <th>3-year block</th><th>Within year</th></tr></thead><tbody>` +
    DATA.clustering.map(c => `<tr><td>${c.window} days</td><td>${c.observed}</td>` +
      ["unrestricted", "within 3-year block", "within year"].map(k =>
        `<td>${c[k].expected} ± ${c[k].sd} (${c[k].times}×)</td>`).join("") +
      `</tr>`).join("") + `</tbody></table>`,
};
const TKEYS = ["sub", "era", "month", "clus"];
function setTable(which) {
  document.getElementById("tables").innerHTML = TABLES[which]();
  TKEYS.forEach(k => document.getElementById("t-" + k)
    .setAttribute("aria-pressed", String(k === which)));
}

/* -------------------------------------------------------------------- wire */
// byline counts come from the data, never typed into the page
(() => {
  const e = document.getElementById("n-ships");
  if (e) e.textContent = DATA.dataset.ships;
})();

function drawAll() { drawSub(); drawEra(); drawConsec(); drawClus(); drawScatter(); drawMonth(); }
drawAll();
setTable("sub");
TKEYS.forEach(k => document.getElementById("t-" + k)
  .addEventListener("click", () => setTable(k)));

function setMonth(mode) {
  monthMode = mode;
  document.getElementById("m-count").setAttribute("aria-pressed", String(mode === "count"));
  document.getElementById("m-rate").setAttribute("aria-pressed", String(mode === "rate"));
  drawMonth();
}
document.getElementById("m-count").addEventListener("click", () => setMonth("count"));
document.getElementById("m-rate").addEventListener("click", () => setMonth("rate"));

matchMedia("(prefers-color-scheme: dark)").addEventListener("change", drawAll);
addEventListener("scroll", hideTT, { passive: true });
