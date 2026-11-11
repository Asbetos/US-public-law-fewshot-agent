import { readFile } from "node:fs/promises";
import path from "node:path";
import { buildPayload, RESULTS } from "./lib/payload";

/**
 * Serves the dashboard as plain server-rendered HTML.
 *
 * Deliberately not a React page: the charts are vanilla SVG in
 * eval/dashboard_assets/, shared verbatim with the offline single-file build
 * produced by eval/dashboard.py. Assembling the HTML here means the page has no
 * hydration step to fail and no client bundle to load - a refresh simply
 * re-reads results/ from disk and re-renders.
 */
export const dynamic = "force-dynamic";
export const revalidate = 0;

const ASSETS = path.resolve(process.cwd(), "..", "eval", "dashboard_assets");

const LIVE_BAR = `
<div class="live-bar">
  <button class="ghost" onclick="location.reload()">Refresh</button>
  <label class="live-auto">
    <input type="checkbox" id="live-auto"> Auto-refresh (30s)
  </label>
  <span class="live-stamp" id="live-stamp"></span>
</div>`;

const LIVE_JS = `
(function () {
  var KEY = "fewshot-auto-refresh";
  var box = document.getElementById("live-auto");
  box.checked = localStorage.getItem(KEY) === "1";
  box.addEventListener("change", function () {
    localStorage.setItem(KEY, box.checked ? "1" : "0");
    if (box.checked) arm();
  });
  function arm() { setTimeout(function () { if (box.checked) location.reload(); }, 30000); }
  if (box.checked) arm();
})();`;

export async function GET() {
  let payload;
  try {
    payload = await buildPayload();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return new Response(
      `<!doctype html><meta charset="utf-8">
       <body style="font:14px/1.6 system-ui;max-width:44rem;margin:12vh auto;padding:0 1.5rem">
       <h1 style="font-size:19px">No results to show yet</h1>
       <p>${msg}</p>
       <p>Expected artefacts in <code>${RESULTS}</code>. Generate them with:</p>
       <pre style="background:#f2f1ec;padding:12px;border-radius:8px">cd ${path.resolve(process.cwd(), "..")}
python eval/score.py &amp;&amp; python eval/collect_infra.py</pre>
       <p><a href="/">retry</a></p></body>`,
      { status: 503, headers: { "content-type": "text/html; charset=utf-8" } },
    );
  }

  const [body, css, js] = await Promise.all([
    readFile(path.join(ASSETS, "body.html"), "utf8"),
    readFile(path.join(ASSETS, "dashboard.css"), "utf8"),
    readFile(path.join(ASSETS, "dashboard.js"), "utf8"),
  ]);

  const stamp = payload.generated_at
    ? `results written ${new Date(payload.generated_at).toLocaleString()}`
    : "";
  const json = JSON.stringify(payload).replace(/<\//g, "<\\/");

  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Few-shot labelling dashboard</title>
<style>
${css}
</style>
</head>
<body data-palette="#2a78d6,#eb6834">
${LIVE_BAR}
${body}
<div id="tip"></div>
<script id="payload" type="application/json">${json}</script>
<script>
${js}
renderDashboard(JSON.parse(document.getElementById("payload").textContent));
document.getElementById("live-stamp").textContent = ${JSON.stringify(stamp)};
${LIVE_JS}
</script>
</body>
</html>`;

  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store, max-age=0",
    },
  });
}
