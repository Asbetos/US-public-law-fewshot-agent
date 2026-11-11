"use strict";
/* Renderer for the Q1 two-coder study dashboard (eval/compare_dashboard.py
   inlines this with the shared dashboard.css and the payload). Marks follow the
   dataviz skill: thin bars with a rounded data-end, 2px surface gaps, hairline
   grid, text in text tokens, a legend for two or more series, hover tooltips,
   and a table view for every chart. Each model's own sections render as soon as
   its run exists; the sections comparing the two models appear once both have run. */
function renderComparison(D) {
  "use strict";
  const C = D.comparison || {};
  const COLOR = { claude: "var(--series-1)", qwen: "var(--series-2)", flat: "var(--series-3)",
                  coders: "var(--neutral-fill)" };
  const NAME = { claude: "Claude Opus 5.5", qwen: "Qwen3.6-27B", coders: "human coders" };
  const SHORT = { claude: "Claude", qwen: "Qwen" };
  const ARMS = ["claude", "qwen"];
  const SEQ = ["var(--seq-100)", "var(--seq-400)", "var(--seq-700)"];
  const bad = v => v == null || Number.isNaN(v);
  const pct = v => (bad(v) ? "—" : (100 * v).toFixed(1) + "%");
  const pct0 = v => (bad(v) ? "—" : Math.round(100 * v) + "%");
  const f3 = v => (bad(v) ? "—" : Number(v).toFixed(3));
  const f2 = v => (bad(v) ? "—" : Number(v).toFixed(2));
  const n0 = v => (v == null ? "—" : Number(v).toLocaleString("en-US"));
  const ci = d => (d && d.lo != null ? ` [${f3(d.lo)}, ${f3(d.hi)}]` : "");
  const ciPct = d => (d && d.lo != null ? ` [${pct(d.lo)}, ${pct(d.hi)}]` : "");
  const range = (d, fmt) => (d && d.lo != null ? `${fmt(d.lo)} to ${fmt(d.hi)}` : "—");
  const pts = v => (bad(v) ? "—" : `${v < 0 ? "−" : "+"}${Math.abs(100 * v).toFixed(0)} points`);
  const pval = p => (bad(p) ? "—" : p < 0.001 ? "below 0.001" : Number(p).toFixed(3));
  const prob = v => (bad(v) ? "—" : Number(v) >= 0.01 ? Number(v).toFixed(2) : Number(v).toPrecision(2));
  const mins = m => (bad(m) ? "—" : m >= 90 ? `${(m / 60).toFixed(1)} h` : `${Math.round(m)} min`);
  const decimal = v => (bad(v) ? "—" : Number(v) >= 0.01 ? Number(v).toFixed(2) : Number(Number(v).toPrecision(1)).toFixed(10).replace(/0+$/, ""));
  const decisive = pv => (pv.n_middle < 10 ? `all but ${pv.n_middle} of its ${n0(pv.n)}` : `${pct(pv.share_decisive)} of its`);
  const SVGNS = "http://www.w3.org/2000/svg";
  const $ = id => document.getElementById(id);

  function el(tag, attrs, parent) {
    const n = document.createElementNS(SVGNS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function h(tag, cls, text, parent) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  }
  function note(host, text) { const p = h("p", "desc", text, host); p.style.marginTop = "10px"; return p; }

  /* ---- tooltip ---- */
  const tip = $("tip");
  function showTip(ev, title, rows) {
    tip.textContent = "";
    h("div", "t-title", title, tip);
    for (const r of rows) {
      const row = h("div", "t-row", null, tip);
      const key = h("span", "t-key", null, row);
      key.style.background = r.color || "transparent";
      h("span", "t-val", r.value, row);
      h("span", "t-name", r.name, row);
    }
    tip.style.opacity = "1";
    moveTip(ev);
  }
  function moveTip(ev) {
    const pad = 14, w = tip.offsetWidth, hh = tip.offsetHeight;
    let x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + w > window.innerWidth - 8) x = ev.clientX - w - pad;
    if (y + hh > window.innerHeight - 8) y = ev.clientY - hh - pad;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  function hideTip() { tip.style.opacity = "0"; }
  function bindMark(node, title, rows) {
    node.setAttribute("tabindex", "0");
    node.addEventListener("mouseenter", ev => showTip(ev, title, rows));
    node.addEventListener("mousemove", moveTip);
    node.addEventListener("mouseleave", hideTip);
    node.addEventListener("focus", () => {
      const b = node.getBoundingClientRect();
      showTip({ clientX: b.left + b.width / 2, clientY: b.top }, title, rows);
    });
    node.addEventListener("blur", hideTip);
  }

  /* ---- legend, table view ---- */
  function legend(host, items) {
    const lg = h("div", "legend", null, host);
    for (const it of items) {
      const item = h("div", "item", null, lg);
      const key = h("span", "key-rect", null, item);
      key.style.background = it.color;
      h("span", null, it.name, item);
    }
  }
  function tableView(host, cols, rows) {
    const wrap = h("div", "tv-wrap", null, host);
    const t = h("table", "tv", null, wrap);
    const tr = h("tr", null, null, h("thead", null, null, t));
    cols.forEach(c => h("th", null, c, tr));
    const tb = h("tbody", null, null, t);
    rows.forEach(r => { const x = h("tr", null, null, tb); r.forEach(v => h("td", null, v, x)); });
    return wrap;
  }
  function withTable(host, cols, rows) {
    /* a "Table" toggle beside the chart: the WCAG twin of every plot */
    const bar = h("div", "legend", null, host);
    bar.style.justifyContent = "flex-end";
    const btn = h("button", "ghost", "Table", bar);
    const tbl = tableView(host, cols, rows);
    tbl.classList.add("hidden");
    btn.addEventListener("click", () => {
      const hidden = tbl.classList.toggle("hidden");
      btn.textContent = hidden ? "Table" : "Chart";
      host.querySelectorAll("svg, .confusion-grid").forEach(s => s.classList.toggle("hidden", !hidden));
    });
  }

  /* ---- grouped columns: cats x series, values in [0, max] ---- */
  function groupedColumns(host, cats, series, opts) {
    opts = opts || {};
    const W = Math.max(host.clientWidth || 440, 320), H = opts.height || 220;
    const m = { t: 18, r: 10, b: 44, l: 44 };
    const pw = W - m.l - m.r, ph = H - m.t - m.b;
    const max = opts.max != null ? opts.max : Math.max(0.0001, ...series.flatMap(s => s.values.filter(v => v != null)));
    const fmt = opts.format || pct;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, role: "img" }, host);
    const ticks = opts.ticks || [0, 0.25, 0.5, 0.75, 1].map(t => t * max);
    for (const t of ticks) {
      const y = m.t + ph - (t / max) * ph;
      el("line", { x1: m.l, x2: W - m.r, y1: y, y2: y, class: "grid-line" }, svg);
      const tx = el("text", { x: m.l - 6, y: y + 4, "text-anchor": "end", class: "axis-text" }, svg);
      tx.textContent = (opts.tickFormat || fmt)(t);
    }
    const slot = pw / cats.length, k = series.length;
    const g = opts.labelValues && k > 1 ? 16 : 2;            // room for side-by-side value labels
    const bw = Math.min(24, (slot * 0.7 - g * (k - 1)) / k);
    cats.forEach((cat, i) => {
      const x0 = m.l + slot * i + (slot - (bw * k + g * (k - 1))) / 2;
      series.forEach((s, j) => {
        const v = s.values[i];
        if (v == null) return;
        const color = (s.colors && s.colors[i]) || s.color;   // per-category colour (identity bars)
        const x = x0 + j * (bw + g), y = m.t + ph - (v / max) * ph, hgt = Math.max(0, (v / max) * ph);
        const r = Math.min(4, hgt);
        const d = `M${x},${m.t + ph} v${-(hgt - r)} q0,-${r} ${r},-${r} h${bw - 2 * r} q${r},0 ${r},${r} v${hgt - r} z`;
        el("path", { d, fill: color, class: "mark" }, svg);
        if (opts.labelValues) {
          const vt = el("text", { x: x + bw / 2, y: y - 5, "text-anchor": "middle", class: "val-text" }, svg);
          vt.textContent = fmt(v);
        }
        const hit = el("rect", { x: x - 1, y: Math.min(y, m.t + ph - 24), width: bw + 2,
                                 height: Math.max(24, hgt), class: "hit" }, svg);
        bindMark(hit, cat + (opts.sub && opts.sub[i] ? ` (${opts.sub[i]})` : ""),
                 [{ color, value: fmt(v), name: s.name + (s.notes && s.notes[i] ? " · " + s.notes[i] : "") }]);
      });
      const ct = el("text", { x: m.l + slot * i + slot / 2, y: H - m.b + 16, "text-anchor": "middle", class: "cat-text" }, svg);
      ct.textContent = cat;
      if (opts.sub && opts.sub[i]) {
        const st = el("text", { x: m.l + slot * i + slot / 2, y: H - m.b + 31, "text-anchor": "middle", class: "axis-text" }, svg);
        st.textContent = opts.sub[i];
      }
    });
    el("line", { x1: m.l, x2: W - m.r, y1: m.t + ph, y2: m.t + ph, class: "grid-line" }, svg);
    if (opts.legendItems) legend(host, opts.legendItems);
    else if (series.length > 1) legend(host, series.map(s => ({ color: s.color, name: s.name })));
    if (opts.table) withTable(host, opts.table.cols, opts.table.rows);
    else withTable(host, [opts.catLabel || "category", ...series.map(s => s.name)],
      cats.map((c, i) => [c + (opts.sub && opts.sub[i] ? ` (${opts.sub[i]})` : ""), ...series.map(s => fmt(s.values[i]))]));
  }

  /* ---- horizontal bars: one row per category, one bar per series ---- */
  function hbars(host, cats, series, opts) {
    opts = opts || {};
    const W = Math.max(host.clientWidth || 440, 300), k = series.length;
    const barH = 12, gap = 2, rowH = k * (barH + gap) + 12;
    const m = { l: opts.labelWidth || 104, r: 58, t: 4 };
    const H = cats.length * rowH + m.t + 2;
    const pw = W - m.l - m.r;
    const max = opts.max != null ? opts.max : Math.max(1e-9, ...series.flatMap(s => s.values.filter(v => v != null)));
    const fmt = opts.format || pct;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, role: "img" }, host);
    cats.forEach((cat, i) => {
      const y0 = m.t + i * rowH;
      const lt = el("text", { x: m.l - 10, y: y0 + (k * (barH + gap)) / 2 + 3, "text-anchor": "end", class: "cat-text" }, svg);
      lt.textContent = cat;
      series.forEach((s, j) => {
        const v = s.values[i];
        if (v == null) return;
        const y = y0 + j * (barH + gap), w = v > 0 ? Math.max(2, (v / max) * pw) : 0;
        if (w > 0) {
          const r = Math.min(4, w / 2, barH / 2);
          const d = `M${m.l},${y} h${w - r} q${r},0 ${r},${r} v${barH - 2 * r} q0,${r} -${r},${r} h${-(w - r)} z`;
          el("path", { d, fill: s.color, class: "mark" }, svg);
        }
        const vt = el("text", { x: m.l + w + 6, y: y + barH - 2, class: "val-text" }, svg);
        vt.textContent = fmt(v);
        const hit = el("rect", { x: m.l, y: y - 1, width: Math.max(w, 30), height: barH + 2, class: "hit" }, svg);
        bindMark(hit, cat, [{ color: s.color, value: fmt(v), name: s.name + (s.notes && s.notes[i] ? " · " + s.notes[i] : "") }]);
      });
    });
    el("line", { x1: m.l, x2: m.l, y1: 0, y2: H, class: "grid-line" }, svg);
    if (series.length > 1) legend(host, series.map(s => ({ color: s.color, name: s.name })));
    if (opts.table) withTable(host, opts.table.cols, opts.table.rows);
    else withTable(host, [opts.catLabel || "category", ...series.map(s => s.name)],
      cats.map((c, i) => [c, ...series.map(s => fmt(s.values[i]))]));
  }

  /* ---- horizontal stacked bars (part-to-whole, ordinal bands) ---- */
  function stackedRows(host, rows, bands, colors) {
    const W = Math.max(host.clientWidth || 440, 320), rowH = 34, H = rows.length * rowH + 10;
    const m = { l: 120, r: 10 };
    const pw = W - m.l - m.r;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, role: "img" }, host);
    rows.forEach((r, i) => {
      const y = 6 + i * rowH;
      const lt = el("text", { x: m.l - 10, y: y + 15, "text-anchor": "end", class: "cat-text" }, svg);
      lt.textContent = r.label;
      let x = m.l;
      r.values.forEach((v, j) => {
        const w = Math.max(0, v * pw - 2);
        if (w <= 0) { x += v * pw; return; }
        const seg = el("rect", { x, y, width: w, height: 22, rx: 2, fill: colors[j], class: "mark" }, svg);
        bindMark(seg, `${r.label} (n=${r.n})`, [{ color: colors[j], value: pct(v), name: bands[j] }]);
        if (w > 44) {
          const t = el("text", { x: x + w / 2, y: y + 15, "text-anchor": "middle", class: "val-text" }, svg);
          t.textContent = pct(v);
          t.style.fill = j === 2 ? "#fff" : "var(--text-primary)";
        }
        x += v * pw;
      });
    });
    legend(host, bands.map((b, j) => ({ color: colors[j], name: b })));
    withTable(host, ["Claude label", "n", ...bands], rows.map(r => [r.label, r.n, ...r.values.map(pct)]));
  }

  /* ---- dumbbell: coders' kappa (gray) -> model kappa (color) ---- */
  function dumbbell(host, items) {
    const W = Math.max(host.clientWidth || 440, 320), rowH = 46, H = items.length * rowH + 36;
    const m = { l: 110, r: 150 };
    const pw = W - m.l - m.r;
    const sx = v => m.l + v * pw;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, role: "img" }, host);
    for (const t of [0, 0.25, 0.5, 0.75, 1]) {
      el("line", { x1: sx(t), x2: sx(t), y1: 6, y2: H - 26, class: "grid-line" }, svg);
      const tx = el("text", { x: sx(t), y: H - 10, "text-anchor": "middle", class: "axis-text" }, svg);
      tx.textContent = f2(t);
    }
    items.forEach((it, i) => {
      const y = 22 + i * rowH;
      const lt = el("text", { x: m.l - 12, y: y + 4, "text-anchor": "end", class: "cat-text" }, svg);
      lt.textContent = it.name;
      if (it.human == null || it.model == null) {
        const nt = el("text", { x: m.l, y: y + 4, class: "axis-text" }, svg);
        nt.textContent = "not yet run";
        return;
      }
      el("line", { x1: sx(it.human), x2: sx(it.model), y1: y, y2: y, stroke: "var(--hairline)", "stroke-width": 2 }, svg);
      const a = el("circle", { cx: sx(it.human), cy: y, r: 6, fill: COLOR.coders, stroke: "var(--surface-1)", "stroke-width": 2, class: "mark" }, svg);
      const b = el("circle", { cx: sx(it.model), cy: y, r: 6, fill: it.color, stroke: "var(--surface-1)", "stroke-width": 2, class: "mark" }, svg);
      bindMark(a, it.name, [{ color: COLOR.coders, value: f3(it.human), name: "coders' kappa with each other" }]);
      bindMark(b, it.name, [{ color: it.color, value: f3(it.model), name: "model's kappa with a coder" }]);
      const dt = el("text", { x: W - m.r + 12, y: y + 4, class: "val-text" }, svg);
      dt.textContent = `Δ ${f3(it.delta)}${ci(it.delta_ci)}`;
    });
    legend(host, [{ color: COLOR.coders, name: "coders with each other" }, ...items.filter(it => it.model != null).map(it => ({ color: it.color, name: it.name }))]);
    withTable(host, ["coder", "coders' kappa", "model kappa", "difference", "95% interval"],
      items.map(it => [it.name, f3(it.human), f3(it.model), f3(it.delta), range(it.delta_ci, f3)]));
  }

  /* ---- 2x2 counts with totals; every cell names what it counts ---- */
  function matrixGrid(host, spec) {
    const { rows, cols, cells } = spec;
    const N = cells[0][0].n + cells[0][1].n + cells[1][0].n + cells[1][1].n;
    const maxv = Math.max(1, ...cells.flat().map(c => c.n));
    const grid = h("div", "confusion-grid matrix", null, host);
    h("div", "mh", "", grid);
    cols.forEach(c => h("div", "mh", c, grid));
    h("div", "mh", "total", grid);
    rows.forEach((rl, r) => {
      h("div", "ml", rl, grid);
      cells[r].forEach((cell, c) => {
        const t = Math.sqrt(cell.n / maxv);
        const box = h("div", "mc" + (t > 0.55 ? " on-dark" : ""), null, grid);
        box.style.background = `color-mix(in oklab, var(--seq-550) ${Math.round(8 + 72 * t)}%, var(--surface-2))`;
        h("div", "mv", n0(cell.n), box);
        h("div", "mcap", cell.cap, box);
        h("div", "msh", `${pct(N ? cell.n / N : 0)} of all`, box);
        bindMark(box, `${rl} · ${cols[c]}`, [{ color: "var(--seq-550)", value: n0(cell.n), name: cell.cap },
                                              { value: pct(N ? cell.n / N : 0), name: "of the sections in this table" }]);
      });
      h("div", "mt", n0(cells[r][0].n + cells[r][1].n), grid);
    });
    h("div", "ml", "total", grid);
    [0, 1].forEach(c => h("div", "mt", n0(cells[0][c].n + cells[1][c].n), grid));
    h("div", "mt", n0(N), grid);
    withTable(host, ["", ...cols, "total"], [
      ...rows.map((rl, r) => [rl, ...cells[r].map(c => `${n0(c.n)} (${c.cap})`), n0(cells[r][0].n + cells[r][1].n)]),
      ["total", n0(cells[0][0].n + cells[1][0].n), n0(cells[0][1].n + cells[1][1].n), n0(N)]]);
  }

  function kv(host, pairs) { for (const [k, v] of pairs) { if (v == null || v === "") continue; h("dt", null, k, host); h("dd", null, String(v), host); } }

  /* ================================ state ================================ */
  const mm = C.model_vs_model || {}, cov = C.coverage || {}, vc = C.vs_coders || {}, VF = C.vs_final || {};
  const S = C.sample || {};
  const both = mm.n || 0;
  const hasFinal = S.final_yes != null;
  const ran = ARMS.filter(a => VF[a]);                       // models scored against the final label
  const main = ran.includes("qwen") ? "qwen" : ran[0];       // the model the explainer walks through
  const counts = v => { const t = (v && v.table) || {}; return { c11: +t["1,1"] || 0, c10: +t["1,0"] || 0, c01: +t["0,1"] || 0, c00: +t["0,0"] || 0 }; };
  if (!both) document.querySelectorAll(".both-only").forEach(n => n.classList.add("hidden"));

  /* ================================ header ================================ */
  $("page-subtitle").textContent =
    `${n0(S.n)} double-coded sections drawn at random from the Q1 panel (${S.volumes} volumes, ${n0(S.laws)} laws). ` +
    (hasFinal ? `The reference is the final reconciled label: ${n0(S.final_yes)} Yes (${pct(S.final_yes_rate)}), ${n0(S.final_no)} No. ` : "") +
    `Each model labels every section with the same SME few-shot kit and gives a 0–1 confidence and a written reason. Generated ${D.generated || ""}.`;
  for (const arm of ["qwen", "claude"]) {
    const c = cov[arm] || {};
    const p = h("span", "pill", null, $("status"));
    const sw = h("span", "swatch", null, p);
    sw.style.background = COLOR[arm];
    h("span", null, c.parsed ? `${NAME[arm]}: ${n0(c.parsed)} of ${n0(c.sample_rows)} sections answered` : `${NAME[arm]}: not yet run`, p);
  }
  if (!both) h("span", "pill muted", "Sections comparing the two models appear once both have run", $("status"));

  /* ================================ hero ================================ */
  if (both) {
    $("hero-lab").textContent = "Agreement between the two model coders";
    $("hero-val").textContent = pct(mm.agreement);
    $("hero-ci").textContent = `95% interval${ciPct(mm.ci && mm.ci.agreement)} · ${n0(both)} sections with both labels`;
    $("hero-note").textContent = `Kappa ${f2(mm.kappa)}${ci(mm.ci && mm.ci.kappa)}. ${NAME.claude} says Yes on ${pct(mm.yes_rate_claude)} of sections, ` +
      `${NAME.qwen} on ${pct(mm.yes_rate_qwen)}` + (hasFinal ? `, the final reconciled label on ${pct(S.final_yes_rate)}` : "") +
      ". Read the Yes rates beside every agreement figure: a coder who says Yes more often is not necessarily a better one.";
  } else if (main) {
    const v = VF[main], k = counts(v), c = v.ci || {};
    $("hero-lab").textContent = `Final-Yes sections ${SHORT[main]} also called Yes`;
    $("hero-val").textContent = pct(v.hit_rate);
    $("hero-ci").textContent = `${n0(k.c11)} of ${n0(v.n_final_yes)} · 95% interval ${range(c.hit_rate, pct0)}`;
    $("hero-note").textContent = `It also called Yes on ${n0(k.c10)} of ${n0(v.n_final_no)} final-No sections (${pct(v.false_alarm_rate)}), ` +
      `so ${pct0(v.precision)} of its ${n0(v.n_model_yes)} Yes calls are right. It matches the final label on ${pct(v.agreement)} of sections ` +
      `overall, mostly the many easy No sections; kappa, which discounts the agreement expected by chance, is ${f2(v.kappa)} (0 = chance, 1 = perfect).`;
  } else {
    $("hero-lab").textContent = "Waiting for the model runs";
  }

  /* ================================ findings (Qwen) ================================ */
  {
    const q = "qwen", v = VF[q], F = [];
    if (v) {
      const lc = C.qwen_layout_check;
      if (lc && lc.n && lc.chat && lc.flat) {
        const cnt = (s, rate, den) => Math.round(s[rate] * s[den]);
        const ch = lc.chat, fl = lc.flat, cg = lc.changes, rf = lc.reasons_first;
        const up = cg.final_yes_no_to_yes + cg.final_no_no_to_yes, down = cg.final_yes_yes_to_no + cg.final_no_yes_to_no;
        const changed = down === 0
          ? `All ${up} answers that changed went from No to Yes (${cg.final_yes_no_to_yes} on final-Yes sections, ${cg.final_no_no_to_yes} on final-No sections).`
          : `${up} answers went from No to Yes and ${down} from Yes to No.`;
        F.push(["The prompt layout changes Qwen's answers a lot",
          `On ${n0(lc.n)} sections labelled both ways, the one-block layout (the way Claude receives the prompt) caught ` +
          `${cnt(fl, "hit_rate", "n_final_yes")} of ${fl.n_final_yes} final-Yes sections instead of ${cnt(ch, "hit_rate", "n_final_yes")}, ` +
          `with ${cnt(fl, "false_alarm_rate", "n_final_no")} false alarms instead of ${cnt(ch, "false_alarm_rate", "n_final_no")}. ${changed} ` +
          `In the chat layout Qwen wrote a reasoning paragraph before every answer (${rf.chat} of ${rf.n}); in the one-block layout it did so on ${rf.flat}. ` +
          "Part of any Claude–Qwen difference may therefore come from the layout, not the model.", "#layout"]);
      }
      const tr = (C.triggers || {})[q];
      if (tr && tr.missed && tr["false alarm"]) {
        F.push(["Qwen often sees participation language and reasons it away",
          `In ${tr.missed.quote_names_mechanism} of its ${tr.missed.n} misses, the passage Qwen quotes names a participation mechanism ` +
          "(consultation, comment, a hearing, cooperation, rulemaking), yet it answered No. In a read-through of a sample of misses, its reasons " +
          "stretch the definition's exclusions: consultation tied to a grant programme treated as an “application for benefits or grants”, " +
          "outside involvement called “implementation” or “a study”, hearings called adjudication.", "#errors"]);
        F.push(["Many false alarms follow the written definition word for word",
          `${tr["false alarm"].quote_names_mechanism} of its ${tr["false alarm"].n} false alarms quote one of those words, such as a public ` +
          "comment period or rulemaking, which the definition lists as a Yes. Some may be coder misses or an unwritten coding rule; an expert " +
          "look at them would sharpen every model's score.", "#errors"]);
      }
      const lv = (C.length_view || {})[q], rh = (C.retry_history || {})[q];
      if (lv && lv.bands && lv.bands.length === 4) {
        const q4 = lv.bands[3], dis = lv.bands.reduce((a, b) => a + b.disagreements, 0);
        let t = `The longest quarter of sections (${q4.chars}) holds ${q4.final_yes} of the ${n0(S.final_yes)} final-Yes sections and ` +
          `${q4.disagreements} of Qwen's ${dis} disagreements with the final label.`;
        if (rh && rh.first_try_failures) t += ` ${rh.first_try_failures} sections ran out of reply room on the first try; retries rescued ` +
          `${rh.rescued}, and ${rh.unanswered} remain unanswered, ${rh.unanswered_final_yes} of them final Yes.`;
        F.push(["Long sections are where it goes wrong", t, "#wrong"]);
      }
      const cf = (C.confidence || {})[q], pv = C.p_yes_view;
      if (cf && cf.triage && cf.triage.length) {
        const tri = cf.triage[0], top = v.n - tri.reviewed, topErr = tri.disagreements - tri.disagreements_caught;
        let t = `Qwen states 1.0 on ${pct0(cf.share_at_1)} of its answers. Only ${pct(top ? topErr / top : null)} of those disagree with the ` +
          `final label, against ${pct(tri.reviewed ? tri.disagreements_caught / tri.reviewed : null)} of the rest: a person checking the ` +
          `${pct0(tri.share_reviewed)} of sections below 1.0 would see ${tri.disagreements_caught} of the ${tri.disagreements} disagreements.`;
        if (pv && pv.n) t += ` Its token probability P(Yes) is below 0.01 or above 0.99 on ${decisive(pv)} answers, so it cannot rank borderline sections.`;
        F.push(["Stated confidence is coarse but useful; P(Yes) is not", t, "#confidence"]);
      }
      const r = vc[q];
      if (r) F.push(["Against one coder's first answer, Qwen is on par with a second coder",
        `In one coder's seat, Qwen agrees with the other coder about as well as the two coders agreed with each other before reconciling ` +
        `(kappa ${f2(r.kappa_vs_reference_coder)} against ${f2(r.kappa_coder_vs_coder)}; difference ${f2(r.delta_kappa)}, 95% interval ` +
        `${range(r.delta_kappa_ci, f2)}). The coders' first answers often differ, which is why the reconciled final label is the reference.`, "#secondary"]);
    }
    if (!F.length) $("findings-block").classList.add("hidden");
    F.forEach(([title, text, href], i) => {
      const card = h("div", "finding", null, $("findings"));
      const hd = h("h3", null, null, card);
      h("span", "num", String(i + 1), hd);
      h("span", null, title, hd);
      h("p", null, text, card);
      const a = h("a", null, "See the numbers", card);
      a.href = href;
    });
  }

  /* ================================ key measures ================================ */
  {
    const kp = $("kpis");
    const tile = (lab, val, sub, color) => {
      const t = h("div", "tile", null, kp);
      const l = h("div", "lab", null, t);
      if (color) { const sw = h("span", "swatch", null, l); sw.style.background = color; }
      h("span", null, lab, l);
      h("div", "val", val, t);
      if (sub) h("div", "sub", sub, t);
    };
    if (both) {
      tile("Agreement between the two coders", pct(mm.agreement), "interval" + ciPct(mm.ci && mm.ci.agreement));
      tile("Kappa between the two coders", f2(mm.kappa), "interval" + ci(mm.ci && mm.ci.kappa));
    }
    for (const arm of ran) {
      const v = VF[arm], c = v.ci || {}, k = counts(v), cv = cov[arm] || {};
      tile("Sections answered", n0(cv.parsed), `of ${n0(cv.sample_rows)} · ${n0(cv.sample_rows - cv.parsed)} without an answer`, COLOR[arm]);
      tile("Final-Yes sections caught", pct(v.hit_rate), `${n0(k.c11)} of ${n0(v.n_final_yes)} · interval ${range(c.hit_rate, pct0)}`, COLOR[arm]);
      tile("False alarms on final-No", pct(v.false_alarm_rate), `${n0(k.c10)} of ${n0(v.n_final_no)} · interval ${range(c.false_alarm_rate, pct)}`, COLOR[arm]);
      tile("Yes calls that are right", pct(v.precision), `${n0(k.c11)} of ${n0(v.n_model_yes)} · interval ${range(c.precision, pct0)}`, COLOR[arm]);
      tile("How often it says Yes", pct(v["yes_rate_" + arm]), `final label ${pct(v.yes_rate_final)} on the same sections`, COLOR[arm]);
      tile("Agreement with the final label", pct(v.agreement), `interval ${range(c.agreement, pct)}`, COLOR[arm]);
      tile("Kappa with the final label", f2(v.kappa), `interval ${range(c.kappa, f2)} · 0 = chance, 1 = perfect`, COLOR[arm]);
      const r = vc[arm];
      if (r) tile("Kappa with a coder's first answer", f2(r.kappa_vs_reference_coder), `the coders with each other: ${f2(r.kappa_coder_vs_coder)}`, COLOR[arm]);
    }
  }

  /* ================================ how to read ================================ */
  if (main) {
    const v = VF[main], k = counts(v), who = SHORT[main];
    const FY = k.c11 + k.c01, FN = k.c10 + k.c00, MY = k.c11 + k.c10, N = FY + FN;
    $("howto-title").textContent = `Every answered section lands in one of four boxes (${who})`;
    $("howto-desc").textContent = `${who}'s label is compared with the final label on each of the ${n0(N)} sections it answered. ` +
      `Columns: what the coders' final sheet says. Rows: what ${who} said.`;
    matrixGrid($("howto-matrix"), {
      rows: [`${who} says Yes`, `${who} says No`], cols: ["Final label Yes", "Final label No"],
      cells: [[{ n: k.c11, cap: "caught" }, { n: k.c10, cap: "false alarm" }],
              [{ n: k.c01, cap: "missed" }, { n: k.c00, cap: "correct No" }]] });
    const po = (k.c11 + k.c00) / N, pm = MY / N, pf = FY / N, pe = pm * pf + (1 - pm) * (1 - pf), kap = (po - pe) / (1 - pe);
    const defs = $("howto-defs");
    const def = (term, rule, calc, meaning) => {
      const d = h("div", "def", null, defs);
      const top = h("div", null, null, d);
      h("span", "term", term, top);
      h("span", "rule", ` = ${rule}`, top);
      h("div", "calc", calc, d);
      h("div", "mean", meaning, d);
    };
    def("Catch rate (hit rate)", "caught ÷ all final-Yes sections", `${n0(k.c11)} ÷ ${n0(FY)} = ${pct(k.c11 / FY)}`,
      `Of the sections the coders' final sheet marks Yes, the share ${who} also called Yes. The other ${n0(k.c01)} are misses.`);
    def("False-alarm rate", "false alarms ÷ all final-No sections", `${n0(k.c10)} ÷ ${n0(FN)} = ${pct(k.c10 / FN)}`,
      `Of the sections marked No, the share ${who} wrongly called Yes. It looks small only because No sections are so many.`);
    def("Yes calls that are right (precision)", `caught ÷ all of ${who}'s Yes calls`, `${n0(k.c11)} ÷ ${n0(MY)} = ${pct(k.c11 / MY)}`,
      `When ${who} says Yes, how often the final label agrees.`);
    def("How often it says Yes (Yes rate)", `${who}'s Yes calls ÷ all sections`,
      `${n0(MY)} ÷ ${n0(N)} = ${pct(pm)}; the final label: ${n0(FY)} ÷ ${n0(N)} = ${pct(pf)}`,
      "Shows whether a model says Yes too often or too rarely, whatever it gets right.");
    def("Agreement", "(caught + correct No) ÷ all sections", `(${n0(k.c11)} + ${n0(k.c00)}) ÷ ${n0(N)} = ${pct(po)}`,
      "The share of sections where the two labels match. Almost any coder scores high here, because most sections are easy No's.");
    def("Kappa", "agreement beyond chance",
      `chance agreement ${pct(pe)}; (${pct(po)} − ${pct(pe)}) ÷ (100% − ${pct(pe)}) = ${f2(kap)}`,
      `If ${who} had scattered its ${n0(MY)} Yes calls at random, it would still match the final label on ${pct(pe)} of sections, ` +
      "because nearly everything is No. Kappa is the share of the remaining distance to perfect that it covers: 0 = no better than chance, 1 = perfect.");
    def("AC1", "another chance-corrected agreement score", `${f2(v.ac1)} here`,
      "Like kappa, but it assumes less agreement by chance when one answer dominates, so it stays high whenever both say No on most sections. " +
      "Shown because other project reports use it; read the catch rate and kappa first.");
    def("95% interval", "the range given after a number", `catch rate ${pct(v.hit_rate)}: interval ${range((v.ci || {}).hit_rate, pct)}`,
      "Where the number would likely land with a different random draw of laws. The laws are re-drawn 2,000 times, keeping each law's " +
      "sections together because sections of one law tend to be coded alike, and the middle 95% of the results is reported.");
  } else $("howto").classList.add("hidden");

  /* ================================ against the final label ================================ */
  if (hasFinal) {
    $("final-desc").textContent =
      `The reference is the label in the final coding workbook, after the human coders reconciled: Yes when every coder's final answer ` +
      `is Yes (${n0(S.final_yes)} sections, ${pct(S.final_yes_rate)}). ${S.final_disputed} sections whose coders were still split in the ` +
      `final workbook count as Yes, as the team decided, and are flagged; ${S.final_single} sections have one coder's answer only. ` +
      (both ? "Both coders are scored on the same sections." : "Sections a model did not answer are left out of its numbers.");
  }
  if (ran.length) {
    groupedColumns($("final-rates"), ["catch rate", "false alarms", "Yes calls right"],
      ran.map(arm => ({ name: NAME[arm], color: COLOR[arm],
        values: [VF[arm].hit_rate, VF[arm].false_alarm_rate, VF[arm].precision],
        notes: [`n=${VF[arm].n_final_yes} final Yes`, `n=${VF[arm].n_final_no} final No`, `n=${VF[arm].n_model_yes} Yes calls`] })),
      { max: 1, catLabel: "measure", labelValues: ran.length === 1, sub: ["final Yes caught", "final No called Yes", "of its Yes calls"],
        legendItems: ran.map(a => ({ color: COLOR[a], name: NAME[a] })) });
    tableView($("final-table"), ["coder", "sections", "agreement", "kappa", "AC1", "says Yes"],
      ran.map(arm => { const v = VF[arm], c = v.ci || {}; return [NAME[arm], n0(v.n), pct(v.agreement) + ciPct(c.agreement),
        f2(v.kappa) + ` [${range(c.kappa, f2)}]`, f2(v.ac1) + ` [${range(c.ac1, f2)}]`, `${pct(v["yes_rate_" + arm])} (final ${pct(v.yes_rate_final)})`]; }));
    note($("final-table"), ran.map(arm => { const k = counts(VF[arm]);
      return `${NAME[arm]}: caught ${n0(k.c11)}, missed ${n0(k.c01)}, false alarms ${n0(k.c10)}, correct No ${n0(k.c00)}; ` +
        `of the ${VF[arm].n_disputed} disputed sections it answered, it called ${VF[arm].disputed_model_yes} Yes.`; }).join(" "));
  } else h("p", "desc", hasFinal ? "Waiting for the model runs." : "Final labels not attached yet (eval/final_labels.py).", $("final-rates"));

  /* ================================ where it goes wrong ================================ */
  {
    const LV = C.length_view || {}, arms = ran.filter(a => LV[a] && LV[a].bands);
    if (arms.length) {
      const bands = LV[arms[0]].bands;
      const names = ["shortest", "second", "third", "longest"];
      const subs = bands.map(b => b.chars.replace(" chars", "").replace("up to ", "≤ ").replace("over ", "> "));
      const rows = [];
      for (const arm of arms) for (const b of LV[arm].bands) rows.push([b.band, b.chars, NAME[arm], n0(b.n), n0(b.final_yes), n0(b.caught),
        n0(b.missed), n0(b.false_alarms), n0(b.no_answer), pct(b.share_disagree)]);
      groupedColumns($("length"), names.map(n => `${n} quarter`), arms.map(arm => ({ name: NAME[arm], color: COLOR[arm],
        values: LV[arm].bands.map(b => b.share_disagree),
        notes: LV[arm].bands.map(b => `${b.disagreements} of ${b.answered} answered: ${b.missed} missed, ${b.false_alarms} false alarms`) })),
        { labelValues: arms.length === 1, sub: subs.map(s => s + " chars"), catLabel: "length",
          max: Math.max(0.05, ...arms.flatMap(a => LV[a].bands.map(b => b.share_disagree || 0))) * 1.2,
          legendItems: arms.length > 1 ? arms.map(a => ({ color: COLOR[a], name: NAME[a] })) : null,
          table: { cols: ["quarter", "length", "coder", "sections", "final Yes", "caught", "missed", "false alarms", "no answer", "differ"], rows } });
    } else h("p", "desc", "Waiting for the model runs.", $("length"));

    const host = $("retries");
    let any = false;
    for (const arm of ran) {
      const rh = (C.retry_history || {})[arm];
      if (!rh || rh.first_try_failures == null) continue;
      any = true;
      if (ran.length > 1) h("div", "subhead", NAME[arm], host);
      const lim = rh.reply_limit_by_attempt || {};
      const trunc = Object.keys(rh.first_try_failure_kinds || {}).every(s => s.startsWith("truncated"));
      const rows = [["first try", `${n0(rh.first_try_failures)} of ${n0((cov[arm] || {}).sample_rows)} sections ` +
        (trunc ? "ran out of reply room" : "failed") + (lim["1"] ? ` (limit ${n0(lim["1"])} tokens)` : "") +
        `; ${rh.first_try_failures_final_yes} of them are final Yes`]];
      for (const [a, n] of Object.entries(rh.rescued_by_attempt || {}))
        rows.push([`attempt ${a}`, `rescued ${n}` + (lim[a] ? ` (limit ${n0(lim[a])} tokens${lim[a] === lim["1"] ? ", unchanged" : ""})` : "")]);
      rows.push(["still unanswered", `${rh.unanswered}, of which ${rh.unanswered_final_yes} final Yes` +
        (rh.unanswered_chars_median ? `; median length ${n0(Math.round(rh.unanswered_chars_median))} characters` : "")]);
      const rs = (C.rescued_answers || {})[arm];
      if (rs) rows.push(["rescued answers", `matched the final label on ${pct(rs.match)}: ${rs.caught} caught, ${rs.missed} missed, ` +
        `${rs.false_alarms} false alarms, ${rs.correct_no} correct No`]);
      kv(h("dl", "kv", null, host), rows);
    }
    if (!any) h("p", "desc", "No failures recorded.", host);
  }

  /* ================================ prompt layout ================================ */
  {
    const lc = C.qwen_layout_check;
    if (lc && lc.n) {
      $("layout-desc").textContent = "The main run gave Qwen the twelve worked examples as a conversation: each example section as a " +
        "user turn and its answer as Qwen's own turn. Claude receives the same instructions, definition and examples as one block of " +
        `text with the section at the end. To see whether the layout alone matters, a random ${n0(lc.rows)} of the sections were labelled ` +
        "again by Qwen in the one-block layout.";
      const ch = lc.chat, fl = lc.flat, d = lc.difference || {}, dc = lc.difference_ci || {};
      $("layout-rates-desc").textContent = `${n0(lc.n)} sections answered in both layouts, ${ch.n_final_yes} of them final Yes. ` +
        `Kappa with the final label: chat ${f2(ch.kappa)}, one-block ${f2(fl.kappa)}.`;
      groupedColumns($("layout-rates"), ["catch rate", "false alarms", "Yes calls right"], [
        { name: "chat layout (main run)", color: COLOR.qwen, values: [ch.hit_rate, ch.false_alarm_rate, ch.precision],
          notes: [`${Math.round(ch.hit_rate * ch.n_final_yes)} of ${ch.n_final_yes}`, `${Math.round(ch.false_alarm_rate * ch.n_final_no)} of ${ch.n_final_no}`, `of ${ch.n_model_yes} Yes calls`] },
        { name: "one-block layout", color: COLOR.flat, values: [fl.hit_rate, fl.false_alarm_rate, fl.precision],
          notes: [`${Math.round(fl.hit_rate * fl.n_final_yes)} of ${fl.n_final_yes}`, `${Math.round(fl.false_alarm_rate * fl.n_final_no)} of ${fl.n_final_no}`, `of ${fl.n_model_yes} Yes calls`] }],
        { max: 1, labelValues: true, catLabel: "measure", sub: ["final Yes caught", "final No called Yes", "of each layout's Yes calls"] });
      note($("layout-rates"), `One-block minus chat: catch rate ${pts(d.hit_rate)} (95% interval ${pts(dc.hit_rate && dc.hit_rate.lo)} to ` +
        `${pts(dc.hit_rate && dc.hit_rate.hi)}), false alarms ${pts(d.false_alarm_rate)} (${pts(dc.false_alarm_rate && dc.false_alarm_rate.lo)} to ` +
        `${pts(dc.false_alarm_rate && dc.false_alarm_rate.hi)}). An exact test on the changed answers gives p = ${pval(lc.p_exact.final_yes)} on ` +
        `final-Yes sections and p = ${pval(lc.p_exact.final_no)} on final-No sections. With only ${ch.n_final_yes} final-Yes sections, the size of the gain is uncertain.`);
      const t = lc.table || {};
      matrixGrid($("layout-matrix"), { rows: ["chat: Yes", "chat: No"], cols: ["one-block: Yes", "one-block: No"],
        cells: [[{ n: +t["1,1"] || 0, cap: "Yes both times" }, { n: +t["1,0"] || 0, cap: "Yes → No" }],
                [{ n: +t["0,1"] || 0, cap: "No → Yes" }, { n: +t["0,0"] || 0, cap: "No both times" }]] });
      const rf = lc.reasons_first, cg = lc.changes;
      note($("layout-matrix"), `Of the No → Yes changes, ${cg.final_yes_no_to_yes} are final-Yes sections and ${cg.final_no_no_to_yes} final-No. ` +
        `Reasoning written before the answer: chat layout ${rf.chat} of ${rf.n} replies, one-block layout ${rf.flat} of ${rf.n}. ` +
        `${lc.reparsed} one-block replies came without the code fence around the answer; their answers were read from the saved reply.`);
    } else $("layout").classList.add("hidden");
  }

  /* ================================ confidence ================================ */
  const CF = C.confidence || {};
  {
    const BINS = C.conf_bin_labels || [];
    const arms = ARMS.filter(a => CF[a] && CF[a].n_with_confidence);
    if (arms.length && BINS.length) {
      const relOf = (arm, b) => CF[arm].match_final_by_bin && CF[arm].match_final_by_bin[b];
      hbars($("conf-hist"), BINS, arms.map(arm => ({ name: NAME[arm], color: COLOR[arm],
        values: BINS.map(b => (CF[arm].histogram || {})[b] ?? null) })), { format: n0, catLabel: "stated confidence" });
      note($("conf-hist"), arms.map(arm => `${NAME[arm]}: ${n0(CF[arm].n_missing)} answers gave no usable confidence; ` +
        `mean ${f3(CF[arm].mean)} when the label matches the final label, ${f3(CF[arm].mean_when_not_matching_final)} when it does not.`).join(" "));
      const rows = [];
      for (const arm of arms) for (const b of BINS) { const r = relOf(arm, b); if (r) rows.push([b, NAME[arm], n0(r.n), pct(r.share_matching_final),
        n0(r.disagreements), `${r.yes_calls_right} of ${r.yes_calls}`, `${r.no_calls_final_yes} of ${r.no_calls}`]); }
      hbars($("conf-rel"), BINS, arms.map(arm => ({ name: NAME[arm], color: COLOR[arm],
        values: BINS.map(b => relOf(arm, b) ? relOf(arm, b).share_matching_final : null),
        notes: BINS.map(b => relOf(arm, b) ? `${relOf(arm, b).disagreements} of ${relOf(arm, b).n} differ` : "") })),
        { max: 1, catLabel: "stated confidence",
          table: { cols: ["stated confidence", "coder", "answers", "match final", "differ", "Yes calls right", "No calls that are final Yes"], rows } });

      const arm = arms.includes("qwen") ? "qwen" : arms[0], tri = CF[arm].triage || [];
      const trows = [];
      for (const a of arms) for (const t of CF[a].triage || []) trows.push([NAME[a], `below ${t.below.toFixed(2)}`,
        `${n0(t.reviewed)} (${pct(t.share_reviewed)})`, `${t.disagreements_caught} of ${t.disagreements}`,
        `${t.misses_caught} of ${t.misses}`, `${t.false_alarms_caught} of ${t.false_alarms}`]);
      if (tri.length) {
        groupedColumns($("triage"), tri.map(t => `below ${t.below.toFixed(2)}`), [
          { name: "sections a person reads", color: COLOR.coders, values: tri.map(t => t.share_reviewed) },
          { name: "disagreements they see", color: COLOR[arm], values: tri.map(t => t.disagreements ? t.disagreements_caught / t.disagreements : null) }],
          { max: 1, labelValues: true, catLabel: "check answers stated",
            table: { cols: ["coder", "check answers stated", "sections read", "disagreements seen", "misses seen", "false alarms seen"], rows: trows } });
        const t0 = tri[0];
        note($("triage"), `${NAME[arm]}: checking everything stated below ${t0.below.toFixed(2)} means reading ${n0(t0.reviewed)} sections ` +
          `(${pct0(t0.share_reviewed)}) and seeing ${t0.disagreements_caught} of the ${t0.disagreements} disagreements: ` +
          `${t0.misses_caught} of ${t0.misses} misses and ${t0.false_alarms_caught} of ${t0.false_alarms} false alarms.`);
      }
    } else {
      for (const id of ["conf-hist", "conf-rel", "triage"]) h("p", "desc", "Waiting for the model runs.", $(id));
    }

    const pv = C.p_yes_view;
    if (pv && pv.n) {
      const cut = pv.cutoffs || {}, rm = pv.rate_matched_to_final || {};
      const label = b => b.replace("below ", "< ").replace(" and above", " and up").replace(/-/g, "–");
      $("pyes-desc").textContent = `Number of Qwen's answers by P(Yes). P(Yes) is below 0.01 or above 0.99 on ${decisive(pv)} answers: by the ` +
        "time Qwen writes the label it has already argued its way to an answer in text, so the probability is all but settled.";
      hbars($("pyes"), pv.bands.map(b => label(b.band)), [{ name: "answers", color: COLOR.qwen, values: pv.bands.map(b => b.n),
        notes: pv.bands.map(b => `${b.final_yes} of them final Yes`) }],
        { format: n0, labelWidth: 96, table: { cols: ["P(Yes)", "answers", "final Yes among them"], rows: pv.bands.map(b => [label(b.band), n0(b.n), n0(b.final_yes)]) } });
      if (cut["0.5"] && cut["0.01"]) note($("pyes"), (cut["0.01"].n_model_yes === cut["0.5"].n_model_yes
          ? `Lowering the cut-off for Yes from 0.5 to 0.01 changes nothing: ${cut["0.5"].n_model_yes} Yes calls either way. `
          : `Lowering the cut-off for Yes from 0.5 to 0.01 gives ${cut["0.01"].n_model_yes} Yes calls instead of ${cut["0.5"].n_model_yes}. `) +
        `Cutting where Qwen says Yes as often as the final label does (P(Yes) ≥ ${decimal(rm.threshold)}) gives catch rate ${pct(rm.hit_rate)}, ` +
        `false alarms ${pct(rm.false_alarm_rate)} and kappa ${f2(rm.kappa)}, against ${f2((VF.qwen || {}).kappa)} at 0.5: no better.`);
    } else $("pyes").closest(".card").classList.add("hidden");

    if (both) {
      hbars($("conf-agree"), BINS, ARMS.filter(a => CF[a] && CF[a].agreement_by_bin).map(arm => ({ name: NAME[arm], color: COLOR[arm],
        values: BINS.map(b => CF[arm].agreement_by_bin[b] ? CF[arm].agreement_by_bin[b].agreement_with_other_model : null),
        notes: BINS.map(b => CF[arm].agreement_by_bin[b] ? `n=${CF[arm].agreement_by_bin[b].n}` : "") })),
        { max: 1, catLabel: "stated confidence" });
      const g = C.graded_view || {};
      const rows = [["claude_yes", "Claude: Yes"], ["claude_no", "Claude: No"]].filter(r => g[r[0]]).map(r => ({
        label: r[1], n: g[r[0]].n,
        values: [g[r[0]]["share_p_yes_below_0.1"], g[r[0]]["share_p_yes_0.1_to_0.9"], g[r[0]]["share_p_yes_above_0.9"]] }));
      if (rows.length) stackedRows($("graded"), rows, ["Qwen P(Yes) < 0.1", "0.1 – 0.9", "> 0.9"], SEQ);
    }
  }

  /* ================================ the two models against each other ================================ */
  if (both) {
    const t = mm.table || {};
    matrixGrid($("confusion"), { rows: ["Claude: Yes", "Claude: No"], cols: ["Qwen: Yes", "Qwen: No"],
      cells: [[{ n: +t["1,1"] || 0, cap: "both Yes" }, { n: +t["1,0"] || 0, cap: "only Claude Yes" }],
              [{ n: +t["0,1"] || 0, cap: "only Qwen Yes" }, { n: +t["0,0"] || 0, cap: "both No" }]] });
    const rm = C.model_vs_model_rate_matched;
    const vals = [mm.yes_rate_claude, mm.yes_rate_qwen, rm ? mm.yes_rate_claude : null, hasFinal ? S.final_yes_rate : null];
    groupedColumns($("yesrates"), ["Claude", "Qwen", "Qwen", "final label"],
      [{ name: "share of sections labelled Yes", values: vals, colors: [COLOR.claude, COLOR.qwen, COLOR.qwen, COLOR.coders] }],
      { max: Math.max(0.1, ...vals.filter(v => v != null)) * 1.15, height: 210, labelValues: true, catLabel: "coder",
        sub: ["", "", "rate-matched", "reconciled"],
        legendItems: [{ color: COLOR.claude, name: NAME.claude }, { color: COLOR.qwen, name: NAME.qwen }, { color: COLOR.coders, name: "final reconciled label" }] });
    if (rm) note($("yesrates"), `Rate-matched: Qwen counted as Yes when P(Yes) ≥ ${Number(rm.threshold).toPrecision(3)}, which gives Claude's Yes rate. Agreement then ${pct(rm.agreement)}, kappa ${f2(rm.kappa)}.`);

    const sl = C.slices || {}, lq = sl.by_length_quartile || {}, cats = Object.keys(lq);
    if (cats.length) groupedColumns($("slice-length"), cats, [
      { name: NAME.claude, color: COLOR.claude, values: cats.map(k => lq[k].yes_rate_claude) },
      { name: NAME.qwen, color: COLOR.qwen, values: cats.map(k => lq[k].yes_rate_qwen) },
      { name: "final reconciled label", color: COLOR.coders, values: cats.map(k => lq[k].final_yes_rate) }],
      { catLabel: "length quarter", sub: cats.map(k => `n=${lq[k].n}`) });
    const rows = [];
    for (const [grp, lab] of [["by_length_quartile", "length"], ["by_n_coders", "coders"], ["by_volume", "volume"]])
      for (const [k, v] of Object.entries(sl[grp] || {})) rows.push([`${lab}: ${k}`, n0(v.n), pct(v.agreement),
        pct(v.yes_rate_claude), pct(v.yes_rate_qwen), pct(v.final_yes_rate), pct(v.claude_matches_final), pct(v.qwen_matches_final)]);
    if (rows.length) tableView($("slice-table"), ["slice", "n", "coders agree", "Claude Yes", "Qwen Yes", "final Yes", "Claude = final", "Qwen = final"], rows);
  }

  /* ================================ explorers ================================ */
  function explorer(ids, all, opts) {
    const filt = $(ids.filters), list = $(ids.list), more = $(ids.more);
    const selects = opts.selects.map(([options, initial]) => {
      const sel = h("select", null, null, filt);
      for (const [v, t] of options) { const o = h("option", null, t, sel); o.value = v; }
      if (initial) sel.value = initial;
      return sel;
    });
    const q = h("input", null, null, filt);
    q.placeholder = "search the reasons or the quotes";
    const count = h("label", null, "", filt);
    let shown = 0, cur = [];
    function render() {
      list.textContent = ""; shown = 0;
      const s = q.value.trim().toLowerCase();
      cur = all.filter(r => opts.matches(r, selects.map(x => x.value)) &&
        (!s || opts.text(r).toLowerCase().includes(s)));
      count.textContent = `${n0(cur.length)} of ${n0(opts.total(selects.map(x => x.value)))} ${opts.noun}`;
      showMore();
    }
    function showMore() {
      const next = cur.slice(shown, shown + 20);
      next.forEach(r => opts.card(r, list, selects.map(x => x.value))); shown += next.length;
      more.classList.toggle("hidden", shown >= cur.length);
      if (!cur.length) h("p", "desc", all.length ? "Nothing matches these filters." : "Nothing recorded yet.", list);
    }
    selects.forEach(s => s.addEventListener("change", render));
    q.addEventListener("input", render);
    more.addEventListener("click", showMore);
    render();
  }
  function quote(host, who, color, reason, span) {
    const blk = h("div", "quote", null, host);
    blk.style.borderLeft = `3px solid ${color}`;
    h("div", "lbl", `${who}: reason`, blk);
    h("div", null, reason || "(no reason recorded)", blk);
    if (span) { h("div", "lbl", `${who}: quoted passage`, blk).style.marginTop = "6px"; h("div", null, `“${span}”`, blk).style.color = "var(--text-secondary)"; }
  }
  const firsts = r => String(r["first answers"] || "—").replace(/\|/g, " / ");

  {
    const all = D.final_errors || [];
    const armsIn = ARMS.filter(a => all.some(r => ["missed", "false alarm", "no answer"].includes(r[`${SHORT[a]} outcome`])));
    if (!armsIn.length) h("p", "desc", "Nothing recorded yet.", $("fe-list"));
    else {
      const LV = C.length_view || {}, b = (LV[armsIn[0]] || {}).bounds_chars;
      const lenOpts = [["all", "Any length"]];
      if (b) lenOpts.push(["0", `Shortest quarter (≤ ${n0(Math.round(b[0]))} chars)`], ["1", "Second quarter"], ["2", "Third quarter"],
                          ["3", `Longest quarter (> ${n0(Math.round(b[2]))} chars)`]);
      const band = c => (!b ? null : c <= b[0] ? "0" : c <= b[1] ? "1" : c <= b[2] ? "2" : "3");
      const kinds = ["missed", "false alarm", "no answer"];
      explorer({ filters: "fe-filters", list: "fe-list", more: "fe-more" }, all, {
        noun: "sections",
        selects: [[armsIn.map(a => [a, NAME[a]]), armsIn.includes("qwen") ? "qwen" : armsIn[0]],
                  [[["any", "Any difference or no answer"], ["missed", "Missed: final Yes, model No"],
                    ["false alarm", "False alarm: final No, model Yes"], ["no answer", "No answer"]], "any"],
                  [lenOpts, "all"]],
        total: ([arm]) => all.filter(r => kinds.includes(r[`${SHORT[arm]} outcome`])).length,
        matches: (r, [arm, kind, len]) => {
          const o = r[`${SHORT[arm]} outcome`];
          return kinds.includes(o) && (kind === "any" || o === kind) && (len === "all" || band(r.chars) === len);
        },
        text: r => `${r["Claude reasoning"]} ${r["Qwen reasoning"]} ${r["Claude quoted span"]} ${r["Qwen quoted span"]}`,
        card: (r, list, [arm]) => {
          const who = SHORT[arm], o = r[`${who} outcome`];
          const c = h("div", "err", null, list);
          const top = h("div", "top", null, c);
          h("span", "pill" + (o === "missed" ? " fn" : o === "false alarm" ? " fp" : ""), o, top);
          h("span", "pill", `final label: ${r["final label"] || "—"}${r["final label status"] === "disputed" ? " (disputed)" : ""}`, top);
          for (const a of armsIn) h("span", "pill", `${SHORT[a]}: ${r[SHORT[a]] || "—"}`, top);
          h("span", "meta", `vol ${r.Volume} · ${r.law} · ${n0(r.chars)} chars · coders' first answers ${firsts(r)} · ` +
            `${who} confidence ${f2(r[`${who} confidence`])}` + (arm === "qwen" ? ` · P(Yes) ${prob(r["Qwen P(Yes)"])}` : ""), top);
          for (const a of armsIn) {
            const W = SHORT[a];
            if (r[`${W} reasoning`] || r[`${W} quoted span`]) quote(c, W, COLOR[a], r[`${W} reasoning`], r[`${W} quoted span`]);
          }
        } });
    }
  }

  if (both) {
    const all = D.disagreements || [];
    explorer({ filters: "dis-filters", list: "dis-list", more: "dis-more" }, all, {
      noun: "disagreements",
      selects: [[[["all", "All disagreements"], ["claude_yes", "Claude Yes, Qwen No"], ["qwen_yes", "Qwen Yes, Claude No"]], "all"],
                [[["all", "Any final label"], ["final_yes", "Final label Yes"], ["final_no", "Final label No"], ["disputed", "Disputed in the final sheet"]], "all"]],
      total: () => all.length,
      matches: (r, [who, fin]) => !((who === "claude_yes" && r.Claude !== "Yes") || (who === "qwen_yes" && r.Qwen !== "Yes") ||
        (fin === "final_yes" && r["final label"] !== "Yes") || (fin === "final_no" && r["final label"] !== "No") ||
        (fin === "disputed" && r["final label status"] !== "disputed")),
      text: r => `${r["Claude reasoning"]} ${r["Qwen reasoning"]} ${r["Claude quoted span"]} ${r["Qwen quoted span"]}`,
      card: (r, list) => {
        const c = h("div", "err", null, list);
        const top = h("div", "top", null, c);
        const fin = r["final label"] || "—";
        const right = who => (fin === "Yes" || fin === "No") ? (r[who] === fin ? " ✓" : " ✗") : "";
        h("span", "pill", `Claude: ${r.Claude}${right("Claude")}`, top);
        h("span", "pill", `Qwen: ${r.Qwen}${right("Qwen")}`, top);
        h("span", "pill", `final label: ${fin}${r["final label status"] === "disputed" ? " (disputed)" : ""}`, top);
        h("span", "meta", `vol ${r.Volume} · ${r.law} · ${n0(r.chars)} chars · coders' first answers ${firsts(r)} · ` +
          `Claude confidence ${f2(r["Claude confidence"])} · Qwen confidence ${f2(r["Qwen confidence"])} · Qwen P(Yes) ${prob(r["Qwen P(Yes)"])}`, top);
        quote(c, "Claude", COLOR.claude, r["Claude reasoning"], r["Claude quoted span"]);
        quote(c, "Qwen", COLOR.qwen, r["Qwen reasoning"], r["Qwen quoted span"]);
      } });
  }

  /* ================================ first answers (secondary) ================================ */
  dumbbell($("replacement"), ARMS.map(arm => {
    const v = vc[arm];
    return { name: NAME[arm], color: COLOR[arm], human: v ? v.kappa_coder_vs_coder : null, model: v ? v.kappa_vs_reference_coder : null,
             delta: v ? v.delta_kappa : null, delta_ci: v ? v.delta_kappa_ci : null };
  }));
  {
    const arms = ARMS.filter(a => vc[a]);
    groupedColumns($("hitfa"), ["caught", "false alarms", "caught"],
      arms.map(arm => ({ name: NAME[arm], color: COLOR[arm],
        values: [vc[arm].hit_rate_unanimous_yes, vc[arm].false_alarm_rate_unanimous_no, vc[arm].hit_rate_any_coder_yes],
        notes: [`n=${vc[arm].n_unanimous_yes}`, `n=${vc[arm].n_unanimous_no}`, `n=${vc[arm].n_any_yes}`] })),
      { max: 1, catLabel: "measure", labelValues: arms.length === 1, sub: ["all first answers Yes", "all first answers No", "any first answer Yes"],
        legendItems: arms.map(a => ({ color: COLOR[a], name: NAME[a] })) });
  }

  /* ================================ how this was run ================================ */
  {
    const runs = D.runs || {};
    const passes = rs => rs.map((r, i) => `${i === 0 ? "first pass" : "retry " + i} ${mins(r.minutes)} (${n0(r.ok)} answered` +
      (r.errors ? `, ${n0(r.errors)} still failing` : "") + ")").join("; ");
    const mainRuns = runs["qwen_raw.jsonl"] || [], flatRuns = runs["qwen_flat300.jsonl"] || [];
    const total = rs => rs.reduce((a, r) => a + r.minutes, 0);
    const first = mainRuns[0];
    const Q = D.qwen_meta || {}, q = cov.qwen || {};
    if (q.parsed) kv($("facts-qwen"), [
      ["model", Q.model || "cyankiwi/Qwen3.6-27B-AWQ-INT4 (4-bit)"],
      ["serving", Q.serving || "vLLM on one NVIDIA L4 GPU, prefix caching on"],
      ["sampling", "temperature 0, seed 0, thinking mode off"],
      ["prompt layout", "chat turns: instruction and definition as the system message, the 12 worked examples as user/assistant pairs, then the section; answer in a fenced json block"],
      ["sections answered", `${n0(q.parsed)} of ${n0(q.sample_rows)} (${n0(q.sample_rows - q.parsed)} with no answer)`],
      ["labelling passes", mainRuns.length ? passes(mainRuns) : null],
      ["labelling time", mainRuns.length ? `${mins(total(mainRuns))} in all; first pass about ${Math.round((first.ok + first.errors) / (first.minutes / 60))} sections per hour` : null],
      ["one-block layout check", flatRuns.length ? `${passes(flatRuns)}; ${mins(total(flatRuns))} in all` +
        ((C.qwen_layout_check || {}).reparsed ? `. Most of these "failures" were answers without the code fence: ` +
          `${C.qwen_layout_check.reparsed} were read afterwards from the saved replies` : "") : null],
      ["P(Yes) recorded", q.p_yes_present != null ? `${n0(q.p_yes_present)} answers (${n0(q.p_yes_censored || 0)} bounded because "No" fell outside the top-5 alternatives)` : null],
      ["median seconds per request", q.median_seconds_per_row != null ? `${Number(q.median_seconds_per_row).toFixed(0)} (8 requests in flight)` : null],
      ["prefix cache hit rate", Q.prefix_cache_hit_rate_pct != null ? `${Q.prefix_cache_hit_rate_pct}% (last logged)` : null]]);
    else h("p", "desc", "Not run yet.", $("facts-qwen").parentNode);
    const M = D.claude_manifest || {}, c = cov.claude || {};
    if (c.parsed || M.model) kv($("facts-claude"), [["model", M.model], ["effort", M.effort], ["route", M.auth],
      ["prompt layout", "one block: instruction, definition and the 12 examples as the system prompt, the section as the user turn; answer keys enforced by a JSON schema"],
      ["system prompt", M.system_prompt_chars ? `${n0(M.system_prompt_chars)} chars, sha256 ${M.system_prompt_sha256_16}` : null],
      ["Claude Code CLI / SDK", M.claude_code_cli ? `${M.claude_code_cli} / claude-agent-sdk ${M.claude_agent_sdk}` : null],
      ["sections answered", c.parsed != null ? `${n0(c.parsed)} (${c.errors || 0} errors)` : null],
      ["API-equivalent cost", c.api_equivalent_cost_usd != null ? `$${Number(c.api_equivalent_cost_usd).toFixed(2)}` : null],
      ["median seconds per section", c.median_seconds_per_row != null ? Number(c.median_seconds_per_row).toFixed(1) : null],
      ["mean output / thinking tokens", c.mean_output_tokens != null ? `${Math.round(c.mean_output_tokens)} / ${Math.round(c.mean_thinking_tokens || 0)}` : null],
      ["mean cached prefix tokens", c.mean_cache_read_tokens != null ? n0(Math.round(c.mean_cache_read_tokens)) : null],
      ["started", M.started_utc]]);
    else h("p", "desc", "Not run yet. Claude will label the same sections with the same kit, given as one block of text.", $("facts-claude").parentNode);
    const r = C.claude_repeat;
    if (r && r.n) note($("repeat"), `Repeat run: ${r.n} sections labelled twice; label agreement ${pct(r.label_agreement)}, kappa ${f2(r.kappa)}, ` +
      `${r.n_label_changes} label changes; mean confidence difference ${f3(r.confidence_abs_diff_mean)}.`);
  }

  /* ================================ caveats ================================ */
  {
    const rh = (C.retry_history || {}).qwen;
    for (const t of [
      "A descriptive comparison, not a pre-registered test: the Q1 plan's gates are separate and need a frozen manifest.",
      "The reference is the final reconciled label (every coder's final answer Yes). Sections still split in the final workbook count as Yes, as the team decided, and are flagged. The coders' first answers appear only in the secondary section.",
      "Some disagreements may be errors in the reference itself: several of Qwen's false alarms read like a Yes under the written definition. The catch and false-alarm rates measure agreement with the coders' final sheet, not accuracy against an absolute truth.",
      "Claude receives the kit as one block with its answer keys enforced by a schema; Qwen received it as chat turns. The layout check shows the layout alone moves Qwen's answers, so part of any Claude–Qwen difference may be the layout.",
      rh && rh.unanswered ? `Sections a model never answered are left out of its numbers, not counted as No (Qwen: ${rh.unanswered}, ${rh.unanswered_final_yes} of them final Yes).` : null,
      "Stated confidence is the model's own claim, not a measured probability. Qwen's P(Yes) is a real model probability, but in this setup it is close to 0 or 1.",
      "Yes is rare (about 5% of sections), so agreement is high for almost any coder: read the catch rate, the false alarms and kappa together.",
      "The “quotes a participation word” counts come from a crude keyword flag (consult, comment, hearing, cooperate, coordinate, concur, rulemaking); it marks passages, it does not judge them.",
      `Intervals are 95% law-clustered bootstraps stratified by volume (${n0(C.n_boot)} draws).`]) if (t) h("li", null, t, $("caveats"));
  }

  $("footer").textContent = "Built by eval/compare_dashboard.py from results/q1_panel3k/comparison.json, the per-section CSVs and the run logs.";

  /* theme toggle */
  const root = document.documentElement;
  try { const saved = localStorage.getItem("viz-theme"); if (saved) root.setAttribute("data-theme", saved); } catch (e) { /* storage blocked */ }
  $("theme").addEventListener("click", () => {
    const dark = root.getAttribute("data-theme") === "dark" || (!root.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
    root.setAttribute("data-theme", dark ? "light" : "dark");
    try { localStorage.setItem("viz-theme", dark ? "light" : "dark"); } catch (e) { /* storage blocked */ }
  });
}
