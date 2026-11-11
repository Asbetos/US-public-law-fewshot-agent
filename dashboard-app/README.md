# Local dashboard viewer

A tiny Next.js app that serves the results dashboard **live from `../results/`**,
so you refresh a browser tab instead of regenerating and downloading an HTML file.

```bash
cd dashboard-app
npm install      # once
npm run dev      # http://localhost:3000
```

In VS Code over SSH, port 3000 is forwarded automatically — just open the URL.

| Route | Serves |
|---|---|
| `/` | the dashboard, rendered server-side per request |
| `/api/data` | the same payload as JSON, for scripting |

Refresh re-reads `results/*.json` from disk. There is a **Refresh** button and an
optional 30-second auto-refresh (remembered in `localStorage`) in the top bar —
useful while a labelling run is still filling results in.

Point it somewhere else with `RESULTS_DIR=/path/to/results npm run dev`.

## Why there are no React chart components

The charts are vanilla SVG in [`../eval/dashboard_assets/`](../eval/dashboard_assets)
— `body.html`, `dashboard.css`, `dashboard.js` — and that directory is the **single
source of truth**, shared verbatim with the offline single-file build that
`eval/dashboard.py` produces. This app reads those three files and inlines them,
exactly as the Python generator does; `renderDashboard(payload)` is the same
function in both. Reimplementing the charts in React would fork rendering code
whose colour choices and mark geometry are validated, so it is deliberately not
done. **Edit the assets, never a copy.**

That also means the page has no hydration step and no client bundle: it is plain
server-rendered HTML, which is why it survives a flaky dev server.

## Deploying to Vercel

`npm run build && npm start` works, but a real Vercel deployment will **not** see
this cluster's filesystem. To host it, either commit a snapshot of `results/*.json`
into the app and read it from the bundle, or serve those artefacts from object
storage and fetch them in `app/lib/payload.ts`. Running it locally, as above, is
the intended use.
