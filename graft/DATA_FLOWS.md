# Data Flows

## Current historical read path — 2026-10-02

Machine selection → mapped module/source → custom [start,end) Bangkok dates → explicit history-page/history-chart request → ownership/field validation → source SQL identity + time filter before LIMIT → raw pages or bounded actual bucket endpoints → source-specific graphs/columns. Wide Compressor source reads can serve multiple modules; each request maps its own columns. Aborted selections never render older responses. Retired detector evidence graph actions/API in the older checkpoint are no longer the review path.


**Presentation supersession — 1 Oct:** Stored z + stored threshold + global persistence → panel-only contributor bands; stored dominant feature → global score explanation. This edge is display-only: no new scoring/notification gate or DB write. Original global-on-every-panel statement below is historical.

**1 Oct:** Operation source SELECT → qualified1m/strict Active → atomic analytics window/Episode/checkpoint/outbox → PM event receipt + `pm_detector_*` (+live/fresh Alert) → authenticated Dashboard evidence. `pm_detector_episodes.pm_alert_id` → Work.source_alert_id → frozen Service Log incident context. Manual work has reported interval without requiring detector Alert. Description/DONE does not become cause label, probability update or recovery. Global red band can be temperature-driven; panel/source context must be explained.

## Incident reports — 2026-10-01

```text
Admin manual work -> validated reported interval/timezone -> pm_work_orders (ADMIN_WORK_ORDER)
Critical ACK -> pm_work_orders (ALERT_LINKED, physical onset unknown)
Assigned tech/Admin service submission -> lock WO -> original incident_context_json + Service Log + DONE -> atomic commit
Service Logs -> Original incident report disclosure (frozen at submission)
```

`source_alert_id` remains a PM Alert ID, not Operation Episode UUID. No automatic training/cause/recovery label. Operation new 1m Episode archive is local rehearsal only; explicit live bridge/mapping/graph edge remains pending. Details: `docs/INCIDENT_REPORT_WORKFLOW.md`.

## Maintenance / logs / overview trend (2026-09-30)

```text
pm_alerts warning -> Acknowledge -> suppression only
pm_alerts critical -> Acknowledge -> pm_work_orders (alert_recorded_at copied)
pm_work_orders -> Maintenance / Assigned Work (oldest first)
Service Log -> pm_maintenance_logs.parts_json + other_cost_baht + cost_baht
pm_maintenance_logs -> Maintenance (total only) / Data > Logs (line items)
Admin delete -> pm_deletion_audit snapshot + hard delete (same DB transaction)
pm_diagnostic_snapshots.recorded_at -> 7-day daily-latest fleet counts -> Overview
```

Trend currently uses dashboard snapshot recording time, not source event time. A day without snapshots remains null. No source telemetry table is written by this flow.

## Local normal-port MX777 rehearsal (2026-09-23)

```text
scripts/mock777_month.py (synthetic fixture, isolated provenance)
  -> scripts/copy_mock777_to_local_source.py (append-only, localhost/777 guard)
  -> localhost ht9046mx_iot.ht9046mx_readings (normal source schema)
  -> OPERATION :8000 calibration + ACTIVE_FROZEN test profile + inference
  -> ht9046mx_iot.compressor_health_scores (MX777, M1–M8)
  -> Dashboard :5001 telemetry_sources.py + pm_* metadata
  -> /api/devices and /api/overview/health-trend
```

`scripts/run_mock777_local_stream.py` adds 12 accelerated five-minute points and checks API propagation/concurrent HTTP requests. This route is local test-only, not the production release/model contract. History API row limits currently prevent full 7-day/month telemetry graphs even though source rows exist.

## Live telemetry

```text
MySQL source tables (read-only)
  -> telemetry_sources.py mapping
  -> poller remembers latest identity/sample
  -> services.py updates pm_devices / pm_modules / pm_diagnostic_snapshots
  -> REST + WebSocket
  -> React Handler Detail / Analytics
```

History charts query source MySQL on demand and do not copy full telemetry history into `pm_sensor_readings`.

## Vacuum decision

```text
vibration mm/s
  -> inverse calibration -> Estimated Pressure kPa
  -> -90/-70/-60 rule
  -> module condition + issue_key
  -> alert policy
  -> Vacuum-specific UI
```

## Compressor ML

```text
External ML producer
  -> compressor_health_scores (read-only to dashboard)
  -> latest machine + module row cache
  -> pm_diagnostic_snapshots / alert policy
  -> ML Condition UI
```

No matching ML row leads to `Awaiting ML Score`; it does not lead to a generated score.

## Alert lifecycle

```text
diagnostic issue
  -> daily dedupe by device + module + issue
  -> pm_alerts
  -> UI Acknowledge
  -> acknowledged_at + suppressed_until (+7 days)
  -> same/lower issue suppressed; new issue or escalation allowed
```
