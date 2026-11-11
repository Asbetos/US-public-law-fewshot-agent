"use strict";
/* Shared dashboard renderer.
   Used by BOTH eval/dashboard.py (inlined into a single offline HTML file)
   and dashboard-app/ (the local Next.js viewer). Edit here only - never in
   a copy - so the two can never drift apart. */
function renderDashboard(D) {
  "use strict";
  const ORDER = ["q6", "q1"];
  const QS = Object.keys(D.questions).filter(q => !D.questions[q].error)
    .sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b));
  const QLABEL = { q1: "Q1 participation", q6: "Q6 construction" };
  const SERIES = { q1: "var(--series-2)", q6: "var(--series-1)" };
  const pct = v => (v == null ? "—" : (100 * v).toFixed(1) + "%");
  const f3  = v => (v == null ? "—" : v.toFixed(3));
  const n0  = v => (v == null ? "—" : v.toLocaleString("en-US"));
  const SVGNS = "http://www.w3.org/2000/svg";

  function el(tag, attrs, parent) {
    const n = document.createElementNS(SVGNS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function txt(node, s) { node.textContent = s; return node; }

  /* ---- tooltip: values lead, labels follow; keyboard focus mirrors hover ---- */
  const tip = document.getElementById("tip");
  function showTip(ev, title, rows) {
    tip.textContent = "";
    const t = document.createElement("div");
    t.className = "t-title"; t.textContent = title; tip.appendChild(t);
    rows.forEach(r => {
      const row = document.createElement("div"); row.className = "t-row";
      if (r.color) { const k = document.createElement("span"); k.className = "t-key";
        k.style.background = r.color; row.appendChild(k); }
      const v = document.createElement("span"); v.className = "t-val"; v.textContent = r.value;
      const n = document.createElement("span"); n.className = "t-name"; n.textContent = r.name;
      row.appendChild(v); row.appendChild(n); tip.appendChild(row);
    });
    tip.style.opacity = "1";
    moveTip(ev);
  }
  function moveTip(ev) {
    const r = tip.getBoundingClientRect();
    let x = (ev.clientX || 0) + 14, y = (ev.clientY || 0) + 14;
    if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
    if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 14;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  function hideTip() { tip.style.opacity = "0"; }
  addEventListener("scroll", hideTip, true);

  function bindMark(node, group, title, rows) {
    const on = ev => {
      showTip(ev, title, rows);
      group.forEach(m => m.classList.toggle("dim", m !== node.__mark));
    };
    node.addEventListener("pointerenter", on);
    node.addEventListener("pointermove", moveTip);
    node.addEventListener("pointerleave", () => { hideTip(); group.forEach(m => m.classList.remove("dim")); });
    node.setAttribute("tabindex", "0");
    node.addEventListener("focus", ev => {
      const b = node.getBoundingClientRect();
      on({ clientX: b.left + b.width / 2, clientY: b.top });
    });
    node.addEventListener("blur", () => { hideTip(); group.forEach(m => m.classList.remove("dim")); });
  }

  function legend(host, items, shape) {
    /* the legend key mirrors the mark: rect for bars and cells, dot for dumbbells */
    host.textContent = "";
    items.forEach(it => {
      const d = document.createElement("span"); d.className = "item";
      const k = document.createElement("span"); k.className = "key-rect";
      if (shape === "dot") { k.style.borderRadius = "50%"; k.style.width = "10px";
                             k.style.height = "10px"; }
      k.style.background = it.color; d.appendChild(k);
      const s = document.createElement("span"); s.textContent = it.name; d.appendChild(s);
      host.appendChild(d);
    });
  }

  function tableView(host, cols, rows) {
    host.textContent = "";
    const t = document.createElement("table"); t.className = "tv";
    const th = document.createElement("tr");
    cols.forEach(c => { const e = document.createElement("th"); e.textContent = c; th.appendChild(e); });
    t.appendChild(th);
    rows.forEach(r => {
      const tr = document.createElement("tr");
      r.forEach(c => { const e = document.createElement("td"); e.textContent = c; tr.appendChild(e); });
      t.appendChild(tr);
    });
    host.appendChild(t);
  }
  document.querySelectorAll("[data-tv]").forEach(b => {
    b.addEventListener("click", () => {
      const host = document.getElementById(b.dataset.tv);
      const chart = host.previousElementSibling;
      const show = host.classList.contains("hidden");
      host.classList.toggle("hidden", !show);
      chart.classList.toggle("hidden", show);
      b.textContent = show ? "Chart view" : "Table view";
    });
  });

  /* ---------- grouped horizontal bars, optional CI whiskers ---------- */
  function groupedBars(host, cats, series, opts) {
    opts = opts || {};
    const W = host.clientWidth || 520, padL = opts.padL || 132, padR = 54,
          rowH = opts.rowH || 30, groupPad = 16, barH = Math.min(18, (rowH - 6) / series.length);
    /* Height must be derived from the same advance the draw loop uses, or the
       last group renders below the x-axis band and the card grows a scrollbar.
       groupH is barH per series plus the 2px surface gap between them. */
    const groupH = barH * series.length + 2 * (series.length - 1);
    const H = 22 + cats.length * (groupH + groupPad) + 18;
    const plotW = W - padL - padR;
    const max = opts.max != null ? opts.max : 1;
    const min = opts.min != null ? opts.min : 0;
    const x = v => padL + plotW * ((v - min) / (max - min));
    host.textContent = "";
    const svg = el("svg", { width: W, height: H, role: "img" }, host);
    const marks = [];

    const axisY = H - 18;
    [0, .25, .5, .75, 1].forEach(f => {
      const v = min + (max - min) * f, gx = x(v);
      el("line", { x1: gx, x2: gx, y1: 16, y2: axisY, class: "grid-line" }, svg);
      txt(el("text", { x: gx, y: axisY + 13, class: "axis-text", "text-anchor": "middle" }, svg),
          (opts.fmtAxis || (d => d.toFixed(2)))(v));
    });

    let y = 22;
    cats.forEach((cat, ci) => {
      const gh = groupH;
      txt(el("text", { x: padL - 10, y: y + gh / 2 + 4, class: "cat-text", "text-anchor": "end" }, svg), cat);
      series.forEach((s, si) => {
        const v = s.values[ci];
        const by = y + si * (barH + 2);           /* 2px surface gap between adjacent bars */
        if (v == null) { return; }
        const w = Math.max(1, x(v) - x(min));
        const r = el("rect", { x: x(min), y: by, width: w, height: barH,
                               fill: s.color, class: "mark", rx: 4 }, svg);
        /* square at the baseline: cover the left rounding */
        el("rect", { x: x(min), y: by, width: Math.min(4, w), height: barH, fill: s.color, class: "mark" }, svg);
        marks.push(r);
        const ci95 = s.ci && s.ci[ci];
        if (ci95) {
          const x1 = x(ci95.lo), x2 = x(ci95.hi), cy = by + barH / 2;
          el("line", { x1, x2, y1: cy, y2: cy, stroke: "var(--text-muted)", "stroke-width": 1.5 }, svg);
          [x1, x2].forEach(xx => el("line", { x1: xx, x2: xx, y1: cy - 4, y2: cy + 4,
                                              stroke: "var(--text-muted)", "stroke-width": 1.5 }, svg));
        }
        const lx = (ci95 ? x(ci95.hi) : x(v)) + 7;
        txt(el("text", { x: lx, y: by + barH / 2 + 4, class: "val-text" }, svg),
            (opts.fmtVal || f3)(v));
        const hit = el("rect", { x: padL, y: by - 3, width: plotW, height: barH + 6, class: "hit" }, svg);
        hit.__mark = r;
        bindMark(hit, marks, cat, [{ color: s.color, name: s.name,
          value: (opts.fmtVal || f3)(v) + (ci95 ? "  [" + f3(ci95.lo) + "–" + f3(ci95.hi) + "]" : "") }]);
      });
      y += gh + groupPad;
    });
    return svg;
  }

  /* ---------- confusion matrix: sequential one-hue ramp ---------- */
  function confusion(host, m, color) {
    const cells = [
      { r: 0, c: 0, k: "tp", lab: "True positive",  sub: "SME Yes · model Yes" },
      { r: 0, c: 1, k: "fn", lab: "False negative", sub: "SME Yes · model No" },
      { r: 1, c: 0, k: "fp", lab: "False positive", sub: "SME No · model Yes" },
      { r: 1, c: 1, k: "tn", lab: "True negative",  sub: "SME No · model No" }
    ];
    const W = host.clientWidth || 420, padL = 96, padT = 30, cw = (W - padL - 12) / 2, ch = 74;
    const H = padT + ch * 2 + 26;
    const total = m.tp + m.fp + m.fn + m.tn;
    const ramp = ["var(--seq-100)", "var(--seq-250)", "var(--seq-400)", "var(--seq-550)", "var(--seq-700)"];
    const step = v => { const f = total ? v / total : 0;
      return f < .01 ? ramp[0] : f < .05 ? ramp[1] : f < .2 ? ramp[2] : f < .6 ? ramp[3] : ramp[4]; };
    host.textContent = "";
    const svg = el("svg", { width: W, height: H, role: "img" }, host);
    txt(el("text", { x: padL + cw / 2, y: 14, class: "axis-text", "text-anchor": "middle" }, svg), "model: Yes");
    txt(el("text", { x: padL + cw + cw / 2, y: 14, class: "axis-text", "text-anchor": "middle" }, svg), "model: No");
    ["SME: Yes", "SME: No"].forEach((s, i) =>
      txt(el("text", { x: padL - 10, y: padT + ch * i + ch / 2 + 4, class: "cat-text", "text-anchor": "end" }, svg), s));
    const marks = [];
    cells.forEach(c => {
      const v = m[c.k], fill = step(v);
      const gx = padL + c.c * cw + 1, gy = padT + c.r * ch + 1;   /* 2px surface gap */
      const rect = el("rect", { x: gx, y: gy, width: cw - 2, height: ch - 2, fill, rx: 5, class: "mark" }, svg);
      marks.push(rect);
      const dark = fill === ramp[3] || fill === ramp[4];
      const ink = dark ? "#ffffff" : "var(--text-primary)";
      const t1 = el("text", { x: gx + (cw - 2) / 2, y: gy + ch / 2 - 1, "text-anchor": "middle",
                              fill: ink, "font-size": 20, "font-weight": 620 }, svg);
      txt(t1, n0(v));
      const t2 = el("text", { x: gx + (cw - 2) / 2, y: gy + ch / 2 + 17, "text-anchor": "middle",
                              fill: ink, "font-size": 11, opacity: .82 }, svg);
      txt(t2, total ? (100 * v / total).toFixed(1) + "%" : "—");
      const hit = el("rect", { x: gx, y: gy, width: cw - 2, height: ch - 2, class: "hit" }, svg);
      hit.__mark = rect;
      bindMark(hit, marks, c.lab, [
        { color, name: c.sub, value: n0(v) },
        { name: "of all rows", value: total ? (100 * v / total).toFixed(1) + "%" : "—" }
      ]);
    });
    return svg;
  }

  /* ---------- stacked bar: part-to-whole of a fixed budget ---------- */
  function stackedBar(host, segments, total, opts) {
    opts = opts || {};
    const W = host.clientWidth || 480, H = 96, padX = 2, barY = 24, barH = 34;
    const plotW = W - padX * 2;
    const x = v => plotW * (v / total);
    host.textContent = "";
    const svg = el("svg", { width: W, height: H, role: "img" }, host);
    const marks = [];
    let cursor = padX;
    segments.forEach((sg, i) => {
      const w = Math.max(0, x(sg.value) - (i ? 2 : 0));   /* 2px surface gap between fills */
      const r = el("rect", { x: cursor, y: barY, width: Math.max(w, 1), height: barH,
                             fill: sg.color, rx: 4, class: "mark" }, svg);
      marks.push(r);
      /* only label inside when the text genuinely fits with padding */
      const label = sg.value.toFixed(2);
      if (w > 46) {
        const t = el("text", { x: cursor + w / 2, y: barY + barH / 2 + 5, "text-anchor": "middle",
                               fill: sg.ink || "#ffffff", "font-size": 12.5, "font-weight": 600 }, svg);
        txt(t, label);
      }
      const hit = el("rect", { x: cursor, y: barY - 6, width: Math.max(w, 1), height: barH + 12,
                               class: "hit" }, svg);
      hit.__mark = r;
      bindMark(hit, marks, sg.name, [
        { color: sg.color, name: "GiB", value: sg.value.toFixed(2) },
        { name: "of " + total.toFixed(2) + " GiB", value: (100 * sg.value / total).toFixed(1) + "%" }
      ]);
      cursor += x(sg.value);
    });
    txt(el("text", { x: padX, y: 14, class: "axis-text" }, svg), "0");
    txt(el("text", { x: W - padX, y: 14, class: "axis-text", "text-anchor": "end" }, svg),
        total.toFixed(2) + " GiB total");
    return svg;
  }

  /* ---------- dumbbell: before -> after per item, one hue at two steps ------- */
  function dumbbell(host, cats, before, after, opts) {
    opts = opts || {};
    const W = host.clientWidth || 480, padL = opts.padL || 118, padR = 52, rowH = 38;
    const H = cats.length * rowH + 34, plotW = W - padL - padR;
    const x = v => padL + plotW * v;
    host.textContent = "";
    const svg = el("svg", { width: W, height: H, role: "img" }, host);
    [0, .25, .5, .75, 1].forEach(f => {
      el("line", { x1: x(f), x2: x(f), y1: 12, y2: H - 18, class: "grid-line" }, svg);
      txt(el("text", { x: x(f), y: H - 4, class: "axis-text", "text-anchor": "middle" }, svg),
          f.toFixed(2));
    });
    const marks = [];
    cats.forEach((cat, i) => {
      const y = 18 + i * rowH, b = before.values[i], a = after.values[i];
      if (b == null || a == null) return;
      txt(el("text", { x: padL - 10, y: y + 4, class: "cat-text", "text-anchor": "end" }, svg), cat);
      el("line", { x1: x(b), x2: x(a), y1: y, y2: y, stroke: "var(--hairline)",
                   "stroke-width": 2, "stroke-linecap": "round" }, svg);
      /* 2px surface ring keeps the dots legible where they nearly overlap */
      const dot = (v, fill) => {
        el("circle", { cx: x(v), cy: y, r: 7, fill: "var(--surface-1)" }, svg);
        return el("circle", { cx: x(v), cy: y, r: 5, fill, class: "mark" }, svg);
      };
      marks.push(dot(b, before.color), dot(a, after.color));
      /* label outside the pair on each side, so the two never collide */
      const lo = Math.min(b, a), hi = Math.max(b, a);
      txt(el("text", { x: x(lo) - 12, y: y + 4, class: "val-text", "text-anchor": "end" }, svg),
          f3(lo === b ? b : a));
      txt(el("text", { x: x(hi) + 12, y: y + 4, class: "val-text" }, svg), f3(hi === a ? a : b));
      const hit = el("rect", { x: padL, y: y - rowH / 2, width: plotW, height: rowH, class: "hit" }, svg);
      hit.__mark = marks[marks.length - 1];
      bindMark(hit, marks, cat, [
        { color: after.color, name: after.name, value: f3(a) },
        { color: before.color, name: before.name, value: f3(b) },
        { name: "change", value: (a - b >= 0 ? "+" : "") + (a - b).toFixed(3) }
      ]);
    });
    return svg;
  }

  /* ---------------- render ---------------- */
  /* Charts that live in a multi-column grid are drawn only after every card
     is in the DOM, so each one measures its final settled width. */
  const deferred = [];
  /* page chrome - derived from the payload so the static file and the app agree */
  const MODEL = (D.run && D.run.model_short) || "the model";
  const ts = D.test_set || {};
  document.getElementById("page-title").textContent =
    "Few-shot labelling of U.S. Statutes sections \u2014 " + MODEL;
  document.getElementById("page-subtitle").textContent =
    MODEL + " labelling " + n0(ts.rows) + " held-out sections from volumes "
    + (ts.volumes || []).join(", ") + ", scored against the subject-matter experts' own "
    + "labels. " + QS.length + " question" + (QS.length === 1 ? "" : "s")
    + ", 12 worked examples per prompt, temperature 0.";
  document.title = "Few-shot labelling \u2014 " + MODEL;

  /* hero — exactly one per view */
  const heroQ = QS.includes("q6") ? "q6" : QS[0];
  const hm = D.questions[heroQ].primary_strict;
  document.getElementById("hero-lab").textContent = QLABEL[heroQ] + " — F1 on the Yes class";
  document.getElementById("hero-val").textContent = f3(hm.f1_yes);
  const hci = hm.ci.f1_yes || {};
  document.getElementById("hero-ci").textContent =
    "95% CI " + f3(hci.lo) + " – " + f3(hci.hi) + "   ·   " + n0(hm.n) + " sections scored";
  document.getElementById("hero-note").textContent =
    "Precision " + f3(hm.precision_yes) + " · recall " + f3(hm.recall_yes) + " · MCC " + f3(hm.mcc) +
    " · Cohen's κ " + f3(hm.cohen_kappa) + ". The model found " + n0(hm.tp) + " of the " +
    n0(hm.tp + hm.fn) + " sections the experts marked Yes, at the cost of " + n0(hm.fp) +
    " false positives.";

  /* KPI row */
  const kpis = document.getElementById("kpis");
  QS.forEach(q => {
    const m = D.questions[q].primary_strict, c = D.questions[q].coverage;
    [["F1 (Yes)", f3(m.f1_yes), "P " + f3(m.precision_yes) + " · R " + f3(m.recall_yes)],
     ["MCC", f3(m.mcc), "κ " + f3(m.cohen_kappa)],
     ["Balanced accuracy", pct(m.balanced_accuracy), "specificity " + f3(m.specificity)],
     ["Answered", pct(c.parse_rate), n0(c.parsed) + " of " + n0(c.parsed + c.unparsed) + " parsed"]
    ].forEach(([lab, val, sub]) => {
      const d = document.createElement("div"); d.className = "tile";
      const l = document.createElement("div"); l.className = "lab";
      const sw = document.createElement("span"); sw.className = "swatch";
      sw.style.background = SERIES[q]; l.appendChild(sw);
      l.appendChild(document.createTextNode(QLABEL[q].split(" ")[0] + " " + lab));
      const v = document.createElement("div"); v.className = "val"; v.textContent = val;
      const s = document.createElement("div"); s.className = "sub"; s.textContent = sub;
      d.appendChild(l); d.appendChild(v); d.appendChild(s); kpis.appendChild(d);
    });
  });

  /* classification rates - operator-defined denominators, arithmetic shown */
  const RATES = [
    ["True positive",  "rate_true_positive",  "tp", "actual_positives"],
    ["False positive", "rate_false_positive", "fp", "actual_positives"],
    ["True negative",  "rate_true_negative",  "tn", "actual_negatives"],
    ["False negative", "rate_false_negative", "fn", "actual_negatives"]
  ];
  const rateHost = document.getElementById("rate-tiles");
  QS.forEach(q => {
    const m = D.questions[q].primary_strict;
    RATES.forEach(([lab, key, num, den]) => {
      const d = document.createElement("div"); d.className = "tile";
      const l = document.createElement("div"); l.className = "lab";
      const sw = document.createElement("span"); sw.className = "swatch";
      sw.style.background = SERIES[q]; l.appendChild(sw);
      l.appendChild(document.createTextNode(QLABEL[q].split(" ")[0] + " " + lab));
      const v = document.createElement("div"); v.className = "val";
      v.textContent = m[key] == null ? "—" : (100 * m[key]).toFixed(1) + "%";
      const su = document.createElement("div"); su.className = "sub";
      su.textContent = n0(m[num]) + " / " + n0(m[den]) + "  ("
                     + (den === "actual_positives" ? "actual Yes" : "actual No") + ")";
      d.appendChild(l); d.appendChild(v); d.appendChild(su); rateHost.appendChild(d);
    });
  });

  /* confusion matrices */
  const confHost = document.getElementById("confusions");
  QS.forEach(q => {
    const m = D.questions[q].primary_strict;
    const card = document.createElement("div"); card.className = "card";
    const head = document.createElement("div"); head.className = "card-head";
    const h = document.createElement("h3"); h.textContent = QLABEL[q];
    const btn = document.createElement("button");
    btn.className = "ghost tablebtn"; btn.textContent = "Table view";
    head.appendChild(h); head.appendChild(btn); card.appendChild(head);
    const p = document.createElement("p"); p.className = "desc";
    p.textContent = "Cell shade is share of all " + n0(m.n) + " scored sections. Experts marked "
      + n0(m.tp + m.fn) + " Yes (" + pct(m.actual_positive_rate) + "); the model marked "
      + n0(m.tp + m.fp) + " (" + pct(m.predicted_positive_rate) + ").";
    card.appendChild(p);
    const chart = document.createElement("div"); card.appendChild(chart);
    const tv = document.createElement("div"); tv.className = "hidden"; card.appendChild(tv);
    confHost.appendChild(card);
    deferred.push(() => confusion(chart, m, SERIES[q]));
    tableView(tv, ["", "Model Yes", "Model No", "Total"], [
      ["SME Yes", n0(m.tp), n0(m.fn), n0(m.tp + m.fn)],
      ["SME No",  n0(m.fp), n0(m.tn), n0(m.fp + m.tn)],
      ["Total",   n0(m.tp + m.fp), n0(m.fn + m.tn), n0(m.n)]
    ]);
    btn.addEventListener("click", () => {
      const show = tv.classList.contains("hidden");
      tv.classList.toggle("hidden", !show); chart.classList.toggle("hidden", show);
      btn.textContent = show ? "Chart view" : "Table view";
    });
  });

  /* metrics + CI */
  const METRICS = [["Precision (Yes)", "precision_yes"], ["Recall (Yes)", "recall_yes"],
                   ["F1 (Yes)", "f1_yes"], ["MCC", "mcc"], ["Balanced accuracy", "balanced_accuracy"]];
  const mSeries = QS.map(q => ({
    name: QLABEL[q], color: SERIES[q],
    values: METRICS.map(([, k]) => D.questions[q].primary_strict[k]),
    ci: METRICS.map(([, k]) => D.questions[q].primary_strict.ci[k] || null)
  }));
  legend(document.getElementById("leg-metrics"), mSeries);
  groupedBars(document.getElementById("ch-metrics"), METRICS.map(m => m[0]), mSeries, { rowH: 34 });
  tableView(document.getElementById("tv-metrics"),
    ["Metric"].concat(QS.map(q => QLABEL[q])),
    METRICS.map(([lab, k]) => [lab].concat(QS.map(q => {
      const m = D.questions[q].primary_strict, c = m.ci[k];
      return f3(m[k]) + (c ? " [" + f3(c.lo) + "–" + f3(c.hi) + "]" : "");
    }))));

  /* baseline comparison */
  const BASE = [["Accuracy", "accuracy"], ["F1 (Yes)", "f1_yes"], ["MCC", "mcc"]];
  const bCats = [], bModel = [], bNo = [];
  QS.forEach(q => BASE.forEach(([lab, k]) => {
    bCats.push(QLABEL[q].split(" ")[0] + " " + lab);
    bModel.push(D.questions[q].deployed_failures_as_no[k]);
    bNo.push(D.questions[q].baselines.always_no[k]);
  }));
  const bSeries = [
    { name: MODEL, color: "var(--series-1)", values: bModel },
    { name: "Always-No baseline", color: "var(--series-2)", values: bNo }
  ];
  legend(document.getElementById("leg-base"), bSeries);
  groupedBars(document.getElementById("ch-base"), bCats, bSeries, { rowH: 30, padL: 148 });
  tableView(document.getElementById("tv-base"), ["Measure", "Model", "Always-No"],
    bCats.map((c, i) => [c, f3(bModel[i]), f3(bNo[i])]));

  /* slices */
  const sliceHost = document.getElementById("slices");
  const SLICES = [["Volume", "By statute volume"], ["EntryType", "By entry type"],
                  ["length_bucket", "By section length"]];
  SLICES.forEach(([key, title]) => {
    const vals = [];
    QS.forEach(q => (D.questions[q].slices || []).forEach(s => {
      if (s.slice === key && !vals.includes(s.value)) vals.push(s.value);
    }));
    if (!vals.length) return;
    const series = QS.map(q => ({
      name: QLABEL[q], color: SERIES[q],
      values: vals.map(v => {
        const s = (D.questions[q].slices || []).find(z => z.slice === key && z.value === v);
        return s ? s.f1_yes : null;
      })
    }));
    const card = document.createElement("div"); card.className = "card";
    const head = document.createElement("div"); head.className = "card-head";
    const h = document.createElement("h3"); h.textContent = title;
    const btn = document.createElement("button"); btn.className = "ghost tablebtn"; btn.textContent = "Table view";
    head.appendChild(h); head.appendChild(btn); card.appendChild(head);
    const p = document.createElement("p"); p.className = "desc"; p.textContent = "F1 on the Yes class within each group.";
    card.appendChild(p);
    const lg = document.createElement("div"); lg.className = "legend"; card.appendChild(lg);
    const chart = document.createElement("div"); card.appendChild(chart);
    const tv = document.createElement("div"); tv.className = "hidden"; card.appendChild(tv);
    sliceHost.appendChild(card);
    legend(lg, series);
    deferred.push(() => groupedBars(chart, vals, series, { rowH: 30, padL: 108 }));
    tableView(tv, [title].concat(QS.map(q => QLABEL[q])),
      vals.map((v, i) => [v].concat(series.map(s => f3(s.values[i])))));
    btn.addEventListener("click", () => {
      const show = tv.classList.contains("hidden");
      tv.classList.toggle("hidden", !show); chart.classList.toggle("hidden", show);
      btn.textContent = show ? "Chart view" : "Table view";
    });
  });

  /* thinking-mode A/B */
  const AB = D.thinking_ab && D.thinking_ab[Object.keys(D.thinking_ab || {})[0]];
  if (AB && AB.arms && AB.arms.thinking_on) {
    document.getElementById("ab-block").classList.remove("hidden");
    const off = AB.arms.thinking_off, on = AB.arms.thinking_on;
    const AB_M = [["F1 (Yes)", "f1_yes"], ["MCC", "mcc"],
                  ["Recall (Yes)", "recall_yes"], ["Precision (Yes)", "precision_yes"]];
    const before = { name: "Thinking off (the run)", color: "var(--seq-250)",
                     values: AB_M.map(([, k]) => off[k]) };
    const after  = { name: "Thinking on", color: "var(--seq-550)",
                     values: AB_M.map(([, k]) => on[k]) };
    document.getElementById("ab-title").textContent =
      QLABEL[AB.question] + " — " + n0(AB.rows) + " identical rows";
    document.getElementById("ab-desc").textContent =
      "Same sections, same prompt, same seed; the only change is whether the model's native "
      + "reasoning mode is on. The thinking-off side is read out of the main run, not re-labelled.";
    legend(document.getElementById("leg-ab"), [before, after], "dot");
    dumbbell(document.getElementById("ch-ab"), AB_M.map(m => m[0]), before, after);
    tableView(document.getElementById("tv-ab"),
      ["Metric", "Thinking off", "Thinking on", "Change"],
      AB_M.map(([lab, k]) => [lab, f3(off[k]), f3(on[k]),
        (on[k] - off[k] >= 0 ? "+" : "") + (on[k] - off[k]).toFixed(3)]));

    const mult = D.thinking_ab[AB.question].delta.token_multiplier;
    const dF1 = on.f1_yes - off.f1_yes;
    [["Output tokens", (mult ? mult.toFixed(1) + "\u00d7" : "\u2014"),
      n0(Math.round(off.mean_completion_tokens || 0)) + " \u2192 "
      + n0(Math.round(on.mean_completion_tokens || 0)) + " per answer"],
     ["Change in F1 (Yes)", (dF1 >= 0 ? "+" : "") + dF1.toFixed(3),
      "on " + n0(AB.rows) + " rows"]
    ].forEach(([lab, val, sub]) => {
      const d = document.createElement("div"); d.className = "tile";
      const l = document.createElement("div"); l.className = "lab"; l.textContent = lab;
      const v = document.createElement("div"); v.className = "val"; v.textContent = val;
      const su = document.createElement("div"); su.className = "sub"; su.textContent = sub;
      d.appendChild(l); d.appendChild(v); d.appendChild(su);
      document.getElementById("ab-tiles").appendChild(d);
    });
    document.getElementById("ab-caveat").textContent =
      "Read this as directional, not decisive: " + n0(AB.rows) + " rows carry only "
      + n0(off.tp + off.fn) + " positives, so a difference of a few sections moves F1 visibly. "
      + "It answers whether reasoning mode is worth a full re-run, not by exactly how much.";
  }

  /* reliability tiles */
  const rel = document.getElementById("reliability");
  QS.forEach(q => {
    const s = D.questions[q].spans, c = D.questions[q].coverage, t = D.questions[q].throughput;
    [["Quote is verbatim", pct(s.span_verbatim_rate), n0(s.predicted_yes) + " Yes answers checked"],
     ["Quote overlaps SME's", f3(s.sme_span_iou_median), "median token IoU · n=" + n0(s.sme_span_compared)],
     ["Hit max_tokens", n0(c.truncated_at_max_tokens), "answers cut off mid-reply"],
     ["Mean answer length", n0(Math.round(t.mean_completion_tokens || 0)), "completion tokens"]
    ].forEach(([lab, val, sub]) => {
      const d = document.createElement("div"); d.className = "tile";
      const l = document.createElement("div"); l.className = "lab";
      const sw = document.createElement("span"); sw.className = "swatch"; sw.style.background = SERIES[q];
      l.appendChild(sw); l.appendChild(document.createTextNode(QLABEL[q].split(" ")[0] + " " + lab));
      const v = document.createElement("div"); v.className = "val"; v.textContent = val;
      const su = document.createElement("div"); su.className = "sub"; su.textContent = sub;
      d.appendChild(l); d.appendChild(v); d.appendChild(su); rel.appendChild(d);
    });
  });

  /* infrastructure */
  const INF = D.infra;
  if (INF && INF.memory_gib) {
    const M = INF.memory_gib, K = INF.kv, MO = INF.model, SV = INF.serving, OB = INF.observed;
    const pq = INF.per_question || {};
    const q = pq[heroQ] || pq[Object.keys(pq)[0]] || {};

    const tiles = [
      ["Model on disk", (MO.disk_gib || 0).toFixed(1) + " GiB", MO.quantisation + " · 27B params"],
      ["Weights in VRAM", (M.weights_and_runtime || 0).toFixed(2) + " GiB",
       (100 * M.weights_and_runtime / M.total).toFixed(0) + "% of the card"],
      ["KV cache", (M.kv_cache || 0).toFixed(2) + " GiB",
       n0(K.kv_cache_tokens) + " tokens · " + n0(K.kv_bytes_per_token) + " B/token"],
      ["Free VRAM", (M.unused || 0).toFixed(2) + " GiB", "of " + (M.total || 0).toFixed(2) + " GiB"],
      ["Median time per section", (q.median_seconds_per_row || 0).toFixed(1) + " s",
       "p95 " + (q.p95_seconds_per_row || 0).toFixed(0) + " s"],
      ["Sections per hour", q.rows_per_hour ? n0(Math.round(q.rows_per_hour)) : "—",
       "at " + (OB.mean_concurrent_reqs || "—") + " concurrent requests"],
      ["Prompt tokens per section", n0(Math.round(q.mean_prompt_tokens || 0)),
       (OB.prefix_cache_hit_rate_pct || 0) + "% served from prefix cache"],
      ["Generated per section", n0(Math.round(q.mean_completion_tokens || 0)) + " tok",
       (OB.mean_generation_tok_s || 0) + " tok/s aggregate"]
    ];
    const host = document.getElementById("infra-tiles");
    tiles.forEach(([lab, val, sub]) => {
      const d = document.createElement("div"); d.className = "tile";
      const l = document.createElement("div"); l.className = "lab"; l.textContent = lab;
      const v = document.createElement("div"); v.className = "val"; v.textContent = val;
      const su = document.createElement("div"); su.className = "sub"; su.textContent = sub;
      d.appendChild(l); d.appendChild(v); d.appendChild(su); host.appendChild(d);
    });

    const segs = [
      { name: "Model weights + runtime", value: M.weights_and_runtime, color: "var(--series-1)" },
      { name: "KV cache", value: M.kv_cache, color: "var(--series-2)" },
      { name: "CUDA graphs", value: M.cuda_graphs, color: "var(--series-3)" },
      { name: "Unused", value: M.unused, color: "var(--neutral-fill)", ink: "var(--text-primary)" }
    ].filter(sg => sg.value != null && sg.value > 0);
    document.getElementById("mem-desc").textContent =
      "The weights leave " + (M.kv_cache || 0).toFixed(2) + " GiB for the KV cache — "
      + n0(K.kv_cache_tokens) + " tokens, or only " + K.kv_blocks + " blocks of "
      + n0(K.attention_block_tokens) + ". That block size is forced by this model's hybrid "
      + "linear-attention layers, and it is what caps concurrency at "
      + (OB.mean_concurrent_reqs || "—") + " requests.";
    document.getElementById("mem-note").textContent =
      "What that buys: " + K.kv_blocks + " blocks total. The shared few-shot prefix is ~"
      + Math.ceil((q.mean_prompt_tokens || 0) / K.attention_block_tokens) + " of them, and with "
      + "prefix caching every request reuses those same blocks instead of copying them — which "
      + "is the difference between " + (OB.max_concurrent_reqs || "—")
      + " requests in flight and two.";
    legend(document.getElementById("leg-mem"), segs);
    deferred.push(() => stackedBar(document.getElementById("ch-mem"), segs, M.total));
    tableView(document.getElementById("tv-mem"), ["Allocation", "GiB", "Share"],
      segs.map(sg => [sg.name, sg.value.toFixed(2), (100 * sg.value / M.total).toFixed(1) + "%"]));

    const bl = q.latency_by_tokens || [];
    document.getElementById("lat-desc").textContent =
      "Median seconds against the section's true token length, across " + n0(q.rows)
      + " sections. Bars are the median; the whisker is the 25th-75th percentile spread. "
      + "Section counts are on each label — most of the corpus sits in the small buckets.";
    deferred.push(() => groupedBars(document.getElementById("ch-lat"),
      bl.map(b => b.bucket + " tok · n=" + n0(b.rows)),
      [{ name: "Median seconds", color: "var(--series-1)",
         values: bl.map(b => b.median_seconds),
         ci: bl.map(b => ({ lo: b.p25_seconds, hi: b.p75_seconds })) }],
      { rowH: 30, padL: 150,
        max: Math.max(1, ...bl.map(b => b.p75_seconds)) * 1.08,
        fmtVal: v => v.toFixed(1) + "s", fmtAxis: v => Math.round(v) + "s" }));
    if (bl.length) {
      const lo = bl[0], hi = bl[bl.length - 1];
      const inFactor = hi.median_tokens / Math.max(1, lo.median_tokens);
      const tFactor = hi.median_seconds / Math.max(0.1, lo.median_seconds);
      document.getElementById("lat-note").textContent =
        "Input grows " + inFactor.toFixed(0) + "x across these buckets (" + n0(lo.median_tokens)
        + " → " + n0(hi.median_tokens) + " tokens) but time only " + tFactor.toFixed(1)
        + "x, because output stays near-constant (" + Math.round(lo.median_completion_tokens)
        + " → " + Math.round(hi.median_completion_tokens) + " tokens generated). The cost of a "
        + "label is dominated by writing the answer, not by reading the section.";
    }
    tableView(document.getElementById("tv-lat"),
      ["Section tokens", "Sections", "Median tokens", "Median s", "p25 s", "p75 s", "Generated tok"],
      bl.map(b => [b.bucket, n0(b.rows), n0(b.median_tokens), b.median_seconds.toFixed(1),
                   b.p25_seconds.toFixed(1), b.p75_seconds.toFixed(1),
                   Math.round(b.median_completion_tokens)]));

    tableView(document.getElementById("tv-cfg"), ["Setting", "Value"], [
      ["GPU", INF.gpu.name + " · " + (INF.gpu.total_gib || 0).toFixed(2) + " GiB · driver " + INF.gpu.driver],
      ["Model", MO.repo],
      ["Architecture", MO.architecture + " · " + MO.layers + " layers, "
                       + MO.full_attention_layers + " full-attention"],
      ["KV geometry", MO.kv_heads + " kv-heads x " + MO.head_dim + " head-dim, vocab " + n0(MO.vocab_size)],
      ["vLLM / torch", SV.vllm + " / " + SV.torch],
      ["max_model_len", n0(SV.max_model_len)],
      ["max_num_seqs", SV.max_num_seqs],
      ["gpu_memory_utilization", SV.gpu_memory_utilization],
      ["kv_cache_dtype", SV.kv_cache_dtype + "  (halves KV vs bf16)"],
      ["enable_prefix_caching", String(SV.enable_prefix_caching) + "  (off by default for this model)"],
      ["Attention block size", n0(K.attention_block_tokens) + " tokens (forced by mamba page size)"],
      ["Weights load time", (SV.weights_load_seconds || 0) + " s"],
      ["Peak generation", (OB.peak_generation_tok_s || 0) + " tok/s"],
      ["Max concurrent requests", OB.max_concurrent_reqs]
    ]);
  } else {
    document.getElementById("infra-block").classList.add("hidden");
  }

  /* disagreement explorer */
  const ALL = [];
  QS.forEach(q => (D.questions[q].errors || []).forEach(e => ALL.push(Object.assign({ q }, e))));
  const vols = [...new Set(ALL.map(e => e.volume))].sort((a, b) => a - b);
  const fv = document.getElementById("f-v");
  vols.forEach(v => { const o = document.createElement("option"); o.value = v; o.textContent = "Volume " + v; fv.appendChild(o); });

  let shown = 12;
  function matches(e) {
    const q = document.getElementById("f-q").value, k = document.getElementById("f-k").value,
          v = document.getElementById("f-v").value, t = document.getElementById("f-t").value.toLowerCase();
    if (q !== "all" && e.q !== q) return false;
    if (k !== "all" && e.kind !== k) return false;
    if (v !== "all" && String(e.volume) !== v) return false;
    if (t && !((e.text + " " + e.justification + " " + e.section + " " + e.law).toLowerCase().includes(t))) return false;
    return true;
  }
  function renderErrs() {
    const host = document.getElementById("errs");
    host.textContent = "";
    const list = ALL.filter(matches);
    document.getElementById("f-count").textContent = n0(list.length) + " disagreements";
    list.slice(0, shown).forEach(e => {
      const d = document.createElement("div"); d.className = "err";
      const top = document.createElement("div"); top.className = "top";
      const pill = document.createElement("span");
      pill.className = "pill " + (e.kind === "false_positive" ? "fp" : "fn");
      pill.textContent = e.kind === "false_positive" ? "✕ false positive" : "○ false negative";
      const sw = document.createElement("span"); sw.className = "swatch"; sw.style.background = SERIES[e.q];
      const qn = document.createElement("span"); qn.textContent = QLABEL[e.q];
      const meta = document.createElement("span"); meta.className = "meta";
      meta.textContent = "Vol " + e.volume + " · " + e.law + " · " + e.section + " · " + n0(e.chars) + " chars";
      top.appendChild(pill); top.appendChild(sw); top.appendChild(qn); top.appendChild(meta);
      d.appendChild(top);

      const addQuote = (label, body) => {
        if (!body) return;
        const l = document.createElement("div"); l.className = "lbl"; l.textContent = label;
        const q = document.createElement("div"); q.className = "quote"; q.textContent = body;
        d.appendChild(l); d.appendChild(q);
      };
      addQuote("Section text", e.text);
      addQuote(e.kind === "false_positive" ? "Model's cited span (spurious)" : "Model's cited span", e.model_span);
      addQuote("Expert's supporting span", e.gold_span);
      addQuote("Model's justification", e.justification);
      host.appendChild(d);
    });
    document.getElementById("more").style.display = list.length > shown ? "" : "none";
  }
  ["f-q", "f-k", "f-v", "f-t"].forEach(id =>
    document.getElementById(id).addEventListener("input", () => { shown = 12; renderErrs(); }));
  document.getElementById("more").addEventListener("click", () => { shown += 24; renderErrs(); });
  renderErrs();

  deferred.forEach(fn => fn());

  /* metadata */
  const meta = document.getElementById("meta");
  (D.run.display || []).forEach(([k, v]) => {
    const dt = document.createElement("dt"); dt.textContent = k;
    const dd = document.createElement("dd"); dd.textContent = v;
    meta.appendChild(dt); meta.appendChild(dd);
  });

  /* theme toggle */
  document.getElementById("theme").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme");
    const dark = cur ? cur === "dark"
                     : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
  });

  /* re-render charts on resize so SVG widths track the cards */
  let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => location.reload(), 250); });
}
if (typeof module !== 'undefined') { module.exports = { renderDashboard }; }
