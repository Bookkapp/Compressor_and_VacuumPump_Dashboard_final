# Historical browsing — 2 October 2026

## User workflow

- Data → Historical Charts: machine → mapped module → signals → date/time → Load charts.
- Database uses the same machine/module/time controls. Records are paged at the source, newest first; CSV/JSON exports the current page. Dynamic metrics is a numeric projection of those same source readings, capped at 100 source readings/page to bound DOM work.
- Analytics chooses up to 6 machines first, then up to 12 of their modules and 4 signals. Compressor and Vacuum Pump signal families remain separate charts, even when both are selected.
- Entry starts with no machine, module or history request. Metadata discovery still loads the fleet. OFF Compressor modules remain selectable for history. Source availability means an existing mapped telemetry module; an empty interval is reported honestly.
- Time inputs and chart labels use Bangkok UTC+7, independent of browser timezone. Custom intervals are `[start, end)`, up to 31 days each. Quick ranges end at the selected end time. Latest-history charts read only the newest 1,200 source rows; use explicit dates for older periods.

## Data contract and performance

Authenticated read-only endpoints:

- `/api/devices/{device_id}/history-page`: required `module_id`, optional paired `start/end`, `limit` 1–1,000, nonnegative `offset`.
- `/api/devices/{device_id}/history-chart`: same identity/time scope, `limit` 2–2,000 (UI 1,200), optional family-specific `signals`.

Machine/module ownership is validated against PM metadata before source I/O. Source tables remain read-only. Compressor uses its wide row's selected M1–M8 columns and configured scale; Vacuum uses its own temperature/current/acceleration/vibration columns. Vacuum pressure remains an estimate from vibration, never a measured-pressure field. Status/SV and null readings are retained. Timestamps returned on rows carry an explicit UTC+7 offset.

Date constraints are in SQL **before** limiting/paging. Raw records are ordered by `(source time DESC, id DESC)`. Large chart ranges pick real first/last `(timestamp, PK)` rows from each time bucket across the entire selected interval. IDs need not follow event time. No synthetic timestamps/averages are inserted. A single repeated timestamp yields at most two real tie-endpoints.

**Sampling limits:** short peaks or missing runs between sampled endpoints can be omitted. This is a bounded exploration chart, not a claim to preserve every extremum. A visible note directs users to raw Database records; summary statistics explicitly describe displayed samples. Existing null points are not interpolated or connected. No ML score, alert threshold, Profile or historical report is recomputed.

Results/stats use bounded 15-second LRU caches. Cache scope includes source, source machine identity, start/end, page/size and chart mode; raw wide Compressor reads are shared across its modules. Fixed striped locks coalesce identical concurrent reads. Network I/O uses the existing per-source history pools, away from the cache state lock. The client runs at most 4 series requests at once, aborts queued/outdated selections and checks cancellation before rendering. No selection state is shared between tabs. Chart slots retain fixed height during loading/empty/data states, and ECharts uses the existing lazy canvas component.

## Removed feature

The owner requested removal of detector evidence graphs from Alerts, Assigned Work, Maintenance log tables and expanded Data Logs. Their buttons, dialog, chart helper, backend evidence route and dedicated harness/tests were removed. Work actions retain Delete at the left (Admin), Start/Record at the right; report context fields and immutable service snapshots remain. PM detector integration/storage and source-time fleet trends remain existing concerns, separate from this historical sensor browser. `DETECTOR_EVIDENCE_INTEGRATION.md` is an archived earlier checkpoint.

## Local verification

- 72 Python tests, 10 Node tests; production frontend build.
- Read-only real localhost sources, including MX777's 32,887 rows within 1–30 September: 1,198 actual chart points spanning the true endpoints. The 2 September 00:00–01:00 query returns 60 points outside the legacy newest-N window.
- First source read/mapping took approximately 587 ms directly; full first HTTP request took 945 ms. Short load sample: 28 authenticated reads with 12 workers, median 955 ms, p95 1,103 ms, no contract/identity errors; source pages do not overlap. This is HTTP/source QA, not a production throughput or browser-paint guarantee.
- Browser QA checks four simultaneous tabs, machine-dependent module choices, explicit dates, separate family graphs, pagination, cancellation/selection reset, fixed slots and removal of old evidence actions. Screenshots and short load report are in `artifacts/history-browser-qa/`.
- Final Thai static build on localhost:5001 loads 60 real readings for 2 September 00:00–01:00 and has no browser console errors. Short-range time-axis labels were given fewer ticks after visual review; the 390 px layout stays within the document width.
- Only the local Dashboard API was restarted; no production deployment or source data writes.

## Card layout follow-up — 2 October

Historical Charts, Database and Analytics now use the same outer insets, shared panel frame/padding and 17 px headings as Maintenance, Alerts and Logs. Database filters have a shared card heading and responsive machine/module, date/time and dataset/load rows. At 900 px the date controls stack so their values remain readable; mobile outer insets are 12 px. Chart slots retain their existing fixed dimensions.

Local layout verification compares computed reference/new card geometry, loads 60 real Compressor readings in Database and Historical Charts, and checks desktop, 900 px and 390 px views plus the rebuilt Thai localhost page. 72 Python tests and production frontend build pass; the existing ECharts chunk warning remains. Screenshots/measurements: `artifacts/history-layout-qa/`. Data contracts and project phase are unchanged.
