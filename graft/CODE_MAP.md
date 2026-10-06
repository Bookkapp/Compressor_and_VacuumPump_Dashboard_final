# Code Map

**Current historical browsing — 2 Oct:** `app/history_browser.py` owns validated machine/module/time queries, raw paging, bounded bucket sampling and shared source-row caches. `main.py` exposes authenticated history-page/history-chart endpoints. `frontend/src/HistoryPages.jsx` owns machine-first Historical Charts/Database/Analytics; `history-browser.mjs` holds family/date/concurrency helpers. Tests: `tests/test_history_browser.py`, `frontend/tests/history-browser.test.mjs`; read-only QA: `scripts/qa_history_browser.py`. Detector graph dialog/helper/API and their dedicated test/harness files in the archived entries below have been removed.


**Contributor attribution — 1 Oct:** `detector-chart.mjs::primaryContributors/panelRegions/panelHighlightSummary` use stored score vector and identical >= threshold; `DetectorEvidence.jsx` supplies responsive label policy/table. Tests in `frontend/tests/detector-chart.test.mjs` cover temperature-only isolation, multiple crossers, gaps, missing z, threshold equality, unchanged evidence and tooltip escaping.

**Detector evidence — 1 Oct:** `app/detector_evidence.py` resolves immutable work/log or Alert reference → PM derived tables; `app/main.py` authenticated route; `frontend/src/DetectorEvidence.jsx` review dialog + `detector-chart.mjs` pure chart shaping; main.jsx buttons/context and MarkArea registration. `db.py` nullable source-time migration, `services.py` source timestamp diagnostic/trend. Tests `test_detector_evidence.py`, chart Node tests and `scripts/qa_detector_database.py`; dev visual harness in `frontend/tests/evidence-qa.*` (not production entry). Backend bridge owned by sibling Operation `qualified_bridge.py`.

**Incident context edge (2026-10-01):** `app/maintenance_evidence.py` validates reported times and freezes Work Order context; `services.py` creates/updates Work Orders and transactionally snapshots linked Service Logs; `db.py::migrate_incident_evidence`/`schema.sql` add nullable fields; `frontend/src/main.jsx` manual form/Assigned Work/Log disclosure + `i18n.js`; regression `tests/test_maintenance_evidence.py`, local migration runner `scripts/qa_incident_context_migration.py`. New Operation Episode UUID is not `source_alert_id`. See `docs/INCIDENT_REPORT_WORKFLOW.md`.

| เรื่อง | Source / config | Backend truth | API | Frontend | Tests |
| --- | --- | --- | --- | --- | --- |
| Vacuum mapping | `.env.example`, `app/config.py` | `app/telemetry_sources.py::_vacuum_sample` | history/metrics ใน `app/main.py` | `Detail`, `vacuumSensorGaugeItems` | `test_telemetry_sources.py` |
| Vacuum formula/rules | supplied calibration | `app/diagnostics.py` | module status + alerts | `vacuumPressureState`, rule panel | `test_vacuum_rules.py` |
| Compressor M1–M8 | source wide columns | `app/telemetry_sources.py::_compressor_samples` | devices/history/metrics | Compressor source/module tabs | `test_telemetry_sources.py` |
| Compressor ML | `COMPRESSOR_HEALTH_*` | `_refresh_compressor_health_scores`, `register_external_sample` | devices payload | ML Condition / Awaiting ML Score | `test_telemetry_sources.py` |
| Alerts → Work Order | `APP_TIMEZONE`, `pm_alerts`, `pm_work_orders.source_alert_id` | `app/services.py::alert_should_insert`, `acknowledge_alert`; Critical only creates order | `PATCH /api/alerts/{id}/acknowledge` | `AlertsPage`, `WorkOrderList` | `test_alert_policy.py`, `test_maintenance_workflow.py` |
| Analytics | history + metric rows | `app/analytics.py`, service queries | `/history`, `/metrics`, `/api/v1/analytics/*` | `Compare` | `test_analytics.py` |
| Maintenance assigned work | `pm_work_orders` | `app/services.py::list_work_orders`, `update_work_order`, `delete_work_order` | `/api/work-orders`, Admin `DELETE /api/work-orders/{id}` | `Maintenance`, `WorkOrderList`, scoped `assigned-work-*` styles | `test_maintenance_workflow.py`, frontend build |
| Maintenance logs/costs/audit | `pm_maintenance_logs.parts_json`, `other_cost_baht`, `pm_deletion_audit` | `app/services.py::create_maintenance_log`, `update_maintenance_log`, `delete_maintenance_log`, `_maintenance_costs` | `GET/POST/PATCH/DELETE /api/maintenance-logs` (PATCH/DELETE Admin) | `Maintenance`, `LogTable`, `DataLogsPage`, `EditMaintenanceLogForm` | `test_maintenance_workflow.py`, frontend build |
| Service Log completion | `pm_work_orders`, `pm_maintenance_logs` | `app/services.py::create_maintenance_log` transaction | `POST /api/maintenance-logs`; PATCH rejects DONE | `Maintenance`, `WorkOrderList` | `test_maintenance_workflow.py` |
| Overview priority/status | `pm_modules`, `pm_diagnostic_snapshots` | `app/services.py::latest_module_rows` (24–48h score baseline), `get_summary`, `create_maintenance_log` status reset | `/api/devices`, `/api/summary` | `Overview`, `CompressorHealthMap`, `VacuumAttentionList`, `TopDeteriorating`; `styles.css` | `test_maintenance_workflow.py`, frontend build + local visual QA |
| Overview fleet trend | `pm_diagnostic_snapshots.recorded_at`, `condition_state` | `app/services.py::get_fleet_health_trend` (7-day latest/module/day + TTL/lock) | `/api/overview/health-trend?range=7d` | `FleetHealthTrend` in `frontend/src/main.jsx`; `styles.css` | `test_health_trend.py`, localhost MySQL query, frontend build |
| Overview work queue preview | `pm_work_orders` | `app/services.py::list_work_orders` | `/api/work-orders` | `OverviewWorkOrderList` → `Maintenance` view | browser preview + build |
| Multi-tab freshness | live source, source history | `app/telemetry_sources.py::MySQLTelemetryPoller`, `ReadOnlyTelemetrySources.history_for`; `app/websocket_manager.py` | `/ws`, history/metrics endpoints | `App` visibility-aware polling | `test_poller_batch.py`, `test_websocket_manager.py`, local mock |
| Advanced Threshold | `pm_modules.thresholds_json` | `app/diagnostics.py::compute_diagnostics`, `app/services.py::update_module` | `PATCH /api/modules/{id}` (Admin) | `Admin` module picker/toggle | `test_maintenance_workflow.py` |
| ENG/TH | browser localStorage | n/a | n/a | `frontend/src/i18n.js`, `AdminSettingsPanel`, `useT`, Thai font CSS | build + visual QA |
| WebSocket auth | app token | `app/main.py::websocket_endpoint` | `/ws` subprotocol `adi-v1` | `App` WebSocket client | local handshake |
| Metadata schema | `schema.sql` | `app/db.py` | n/a | n/a | migration verified in staging |
| Theme/layout | n/a | n/a | n/a | `frontend/src/styles.css` | build + visual QA |

## Important boundaries

- `app/telemetry_sources.py` may only SELECT source telemetry/ML outputs.
- All application writes stay in tables prefixed `pm_`.
- Formula and severity truth belongs in `app/diagnostics.py`; frontend copies bands only for explanation and must match tests/docs.
- `public/` is generated; edit `frontend/src/`, then rebuild.
