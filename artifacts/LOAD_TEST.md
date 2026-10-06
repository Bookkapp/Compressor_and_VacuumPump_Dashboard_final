# Chart load QA — 2026-09-30

## Handler default and whole-app follow-up

The earlier Detail QA selected All manually; it did not verify the default 6h. The follow-up reproduced empty charts at default 6h on HT9046MX-017. Read-only service probes found 480 Compressor samples (latest 2026-09-19 13:37:54) and 60 Vacuum samples (latest 2026-09-16 18:20:04), but zero samples within the last 6h for both. The cached recent-range probes completed in 1ms. Empty data and a slow request are distinct here.

During follow-up, the local backend stopped listening on port 5001 while Vite remained on port 5173. The reason for the stop was not established. Started the local development backend again and verified `/api/health=ok`; no production restart/deployment was performed.

Handler now defaults to latest available bounded history and shows actual dates, sample count, loading/error/empty states. Its primary trends, Pearson matrix and scatter share one compact, source-specific history request. The relationships use the plotted timestamp timeline, preserving paired-only Pearson, minimum 3 pairs, null for constant/missing correlations and the existing scatter cap. Identical poll responses reuse rows/options instead of resetting charts; changes at the same timestamp still update.

Six actual browser tabs opened distinct machines concurrently with the new default:

| Compressor machine | Data load (ms) | Samples | Stage first render after scrolling (ms) |
|---|---:|---:|---:|
| HT9046MX-070 | 217 | 480 | 177 |
| HT9046MX-071 | 2183 | 480 | 161 |
| HT9046MX-072 | 2162 | 480 | 148 |
| HT9046MX-080 | 1283 | 2000 | 264 |
| HT9046MX-081 | 1969 | 480 | 206 |
| HT9046MX-082 | 606 | 480 | 166 |

Mean data load: 1,403ms; maximum: 2,183ms. Machine 080 opens its worst-status module (M6), so its sample count differs from the earlier Analytics scenario. These are local measured runs, not a production SLA or a paired before/after Handler benchmark.

Switching tabs 071/072/081 to Vacuum concurrently loaded 60 samples each in 141/129/177ms. Their operating overview canvases finished in 102/105/109ms. The remaining three tabs stayed on Compressor. Source-specific snapshots and plots remained separate.

Verified both sources at 6h: 0 samples, explicit empty message and last sensor reading date, no misleading loading/blank canvases; “Show latest history” restored populated graphs. Rapid M2→M8 selection left M8 selected with loaded data. Across subsequent polls/metadata refreshes, initialized Stage charts retained `data-option-updates=1` for unchanged data. Server logs recorded no extra Handler correlation/relationship requests and no history HTTP errors.

Cross-page check: four Handler tabs continued polling while Database and Analytics ran in the remaining two tabs. Database latest history loaded 250 Compressor rows with HP/LP/TempHi/TempLo/Valve/Busy/Status/SV columns; switching to Vacuum loaded 60 rows with temperature/current/vibration/estimated pressure/accel axes and no Compressor columns. Database 6h correctly showed empty. Analytics Vacuum 6h returned 0 samples in 41ms with a range explanation; available history returned 60 samples in 24ms with a populated canvas. No UI error in any of the six tabs. Initial Database/Analytics selections still remained empty and required explicit load.

Numerical/contract Node tests: 5 passed; Python suite: 51 passed; production frontend build passed. The viewport override did not change the observed browser width, so this follow-up does not claim mobile verification. Machine/source data was read-only; aggregate evidence is in `artifacts/load-handler-6-tabs.json`.

## Earlier Analytics paired run

Tested the running local app at http://127.0.0.1:5001 against its configured MySQL sources. Six browser tabs selected six different Compressor machines, four modules and four metrics per tab, with All available history (bounded to 2,000 samples/module).

The 7-day round returned zero samples on these older sources and is excluded from chart timing comparisons. The populated browser baseline used the per-module API; the final round used compact batched history. Browser foreground/background scheduling and other local activity can vary timings; these are measured runs, not a production SLA.

| Tab | Before API/data load (ms) | After API/data load (ms) | Samples, both rounds |
|---|---:|---:|---:|
| 1 | 5385 | 672 | 1920 ตัวอย่าง |
| 2 | 5795 | 4172 | 1920 ตัวอย่าง |
| 3 | 7391 | 1222 | 1920 ตัวอย่าง |
| 4 | 7399 | 4185 | 5616 ตัวอย่าง |
| 5 | 5366 | 2719 | 1920 ตัวอย่าง |
| 6 | 4290 | 1721 | 1920 ตัวอย่าง |

Mean data load: 5.94s → 2.45s (58.8% lower). Worst tab: 7.40s → 4.18s. No toast errors and no sample-count changes in the paired round.

Chart canvas first-finished timings after load: 53–320ms for rendered charts in the final round. Offscreen charts are deferred until near the viewport; these numbers exclude intentionally deferred charts. Initial data load and chart render are separate measurements.

Additional real UI checks: six Handler Detail tabs at All, populated Compressor stage graphs and HP2 summary, lazy charts drawn after scrolling. Service/source probe also covers six devices with 24 concurrent history/metrics/correlation/relationship calls; reports are stored next to this file. Service probes exclude HTTP/socket/browser overhead.

Changes: per-source state/connection locks; single-flight cache scopes; four independent history connections per source; compact validated signal projection; one request per machine in Analytics; one history request for Detail primary graphs; immutable timeline/options reuse; viewport chart creation; stale-tab 401 cannot remove a newer shared login token.

Gates: 51 Python tests passed; production frontend build passed (existing ECharts size warning); local API health returns ok. No production deployment or source-table writes.
