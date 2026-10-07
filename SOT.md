> **Final private Server release — 6 Oct 2026:** On “Set up ระบบนี้ให้หน่อย”, read `HANDOFF_SERVER.md` first. Owner explicitly authorized real deploy secrets/config in this PRIVATE `_final` repository. This supersedes older secret-exclusion instructions for this release. Server .69 Dashboard / .73 Operation; no Server installation or Profile approval has occurred in packaging.

# Source of Truth

## Compressor signal policy — 2026-10-06

Current owner-approved Compressor policy: actual last-reading age <= 30 minutes is ONLINE, > 30 minutes is OFFLINE; unknown/invalid last-reading time is OFFLINE. The former Compressor NO_SIGNAL interval after 20 minutes is removed. Vacuum freshness thresholds and retained diagnostic conditions remain unchanged. Boundary coverage verifies 20 minutes, 20 minutes + 1 second, just under/exactly/just over 30 minutes.

Handler/source classification uses stored Compressor module membership for canonical HT9046MX identities, including shared Handlers. Summary and Handler list apply the same source classification; no telemetry timestamps or retained diagnostic evidence are rewritten.

## Actual Server .69 installation — 2026-10-06

Latest deployment state supersedes older local-only/no-installation status below: portable Dashboard is running behind nginx on .69, API and new metadata MySQL are loopback-only, with a per-user login task and rotating-log restart supervisor. Both sources have verified SELECT-only table access. Owner supplied `vacuum_pump_db_reader`; real Vacuum identity is `device_id`, configured explicitly. Current discovery: 21 Handlers/162 modules (160 Compressor/two Vacuum), both source errors null. Optional ML lookup is disabled and no score is fabricated. User-task restart/backup/API checks pass; boot-before-login, other-machine LAN and browser QA are unverified. Operation/Profile/source telemetry remained unchanged. 70 unittest / 82 pytest tests and production build pass. Full acceptance record and outstanding gates: [SERVER_ACCEPTANCE.md](deployment/SERVER_ACCEPTANCE.md).

Final deployed history-page/history-chart reads pass for both sources. The Vacuum fixture isolates/configurably tests both `devices_id` and `device_id`, rather than inheriting a different live `.env`; runtime formulas remain unchanged.

## Log page scrolling & viewport height fix — 2026-10-06

- **Log page scrolling & sticky detachment**: Resolved phantom vertical scroll and sidebar sliding on short-content pages (Data Logs `#logs`). Removed unzoomed `body` from `min-height: calc(100vh / var(--dashboard-scale))` in `frontend/src/styles.css`, restricting scaled min-height only to `#root` descendants (`.app-shell, .login-shell`). `body` maintains standard `100vh`. Added `window.scrollTo(0, 0)` on view navigation in `frontend/src/main.jsx`.
- Verified via headless Edge CDP: `htmlScrollHeight == htmlClientHeight` (707px in 707px viewport), zero phantom scroll, sidebar pinned at `(0, 0)` without clipping or desynchronization.

## Numbering reset & Vacuum Pump tooltip — 2026-10-06

- **Sequence & ID Numbering Reset**: Admin-only feature to reset high-running pm_alerts.id and pm_work_orders.id sequences back to 1. Work orders archive to pm_deletion_audit; pm_maintenance_logs work_order_id set to NULL to keep service logs intact; modules in UNDER_MAINTENANCE are restored to diagnostic state; ALTER TABLE AUTO_INCREMENT = 1 executed.
- **Vacuum Pump Diagnostic Tooltip**: VacuumAttentionList implements portal-based diagnostic tooltip using .compressor-module-diagnostic class, identical responsive bounds, theme compatibility, and status/awaiting ML score placeholders.
- 82 Python tests and production frontend build pass.

## Dashboard display 90% — 2026-10-06

Owner chose a 90% desktop display with the existing component arrangement instead of a scrollable sidebar. Root scaling, viewport-height compensation and portal coordinates are updated. Actual 1280 x 720/browser-100% check: Logout fully visible, navigation has no scrollbar, document has no horizontal overflow; tooltip remains in the viewport. 65 Python tests and final production build pass. Evidence: docs/DASHBOARD_90_PERCENT_20261006.md and artifacts/dashboard-90-percent-qa/overview.png.


## Offline status — 2026-10-06

Owner-requested Offline after more than 30 minutes without signal now projects into device/module status, summary and filters. Earlier transient loss is NO_SIGNAL. Compressor Overview cells are grey with solid borders and a matching Offline legend; caption counts all Compressor machines. 65 Python tests, final build and actual local web checks pass. Details and screenshots: docs/OFFLINE_STATUS_20261006.md. Local API restart only; source data and Profile/Active policies unchanged. Earlier connectivity descriptions below are historical.


## Historical page layout — 2026-10-02

Historical Charts/Database/Analytics card frames use the same shared panel styling as Maintenance/Alerts/Logs: 6 px corners, theme border/background, 22 px by 24 px panel padding, 17 px headings and aligned 28 px desktop/12 px mobile outer insets. Database selection controls are grouped in responsive rows. This presentation change preserves machine-first explicit loading, source-specific fields, cancellation and fixed chart slots. Local layout QA: `artifacts/history-layout-qa/`; 72 Python tests and frontend production build pass.

## Current historical browser — 2026-10-02

The owner removed detector evidence graph UI/API from Alerts, Maintenance and Logs. Their incident context/report snapshots still exist. Data now includes Historical Charts; Database and Analytics choose machine before mapped source/module, then custom Bangkok date/time and explicit loading. `/history-page` uses raw SQL pages; `/history-chart` covers custom intervals using bounded real timestamp/PK bucket endpoints, or a bounded newest-row query for Latest history. Source fields, nulls, OFF module histories and separate Compressor/Vacuum meanings are preserved. Statistics describe displayed samples; sampling can omit short peaks. See `docs/HISTORY_BROWSER.md`. Archived evidence UI notes below describe the earlier checkpoint, not current UI.

**Contributor update — 1 Oct:** Sensor-panel red now requires that panel's stored |z| >= threshold during global persistence. Score graph stays global; names/signed z/baseline are visible in tooltip/table, all crossers retained (not dominant-only). 69 Python/17 Node tests and build pass; actual archived MX080 narrow/Desktop/filter QA performed. No score/Profile/threshold/DB/Server changes. Startup/settling remains proposed, not fitted/active: sibling Operation `deployment/STARTUP_SETTLING_VALIDATION_PLAN.md`.

**Latest local integration — 1 Oct:** Added authenticated detector evidence API and review graphs from Alert/Work/Log; Operation PM outbox bridge owns derived minute/Episode/Alert identity. Report interval/snapshot, source units, independent Profile contexts and missing data retained; no new Health/cause %. Source-time Fleet Trend migration is additive; old timestamps not backfilled. QA69 Python/8 Node, temp build and Desktop/mobile/filter check pass; 10 parallel local fixture-auth reads return75 points/no writes. No Server/Git push/real Profile or actual Alert/work mutation. Owner identified first global red band: mainly temperature-driven possible normal transition, not pressure fault; contributor/settling review remains next. Details `docs/DETECTOR_EVIDENCE_INTEGRATION.md`.

สถานะ ณ 2026-10-01

## Owner-requested rollback — 2026-10-01

The custom static auto-refresh implementation added for the previous local-preview request was in this deployable repository and has been removed at the owner's request, including its helper/tests/guide and local watcher processes. Vite config/package scripts and document-cache behavior return to their pre-change state. Earlier incident date/time and frozen-report features remain. Ordinary local API startup replaces the custom reload launcher; no production Server, Profile/model/threshold or source telemetry is changed. Verification: `graft/CHANGE_CHECKLIST.md`.

## Incident evidence ล่าสุด (2026-10-01)

Dashboard เป็นจุดรายงานประจำวันสำหรับทั้ง Alert-linked และ Admin-created Work Orders. เพิ่ม `report_origin` และ nullable occurrence start/end/timezone/precision ที่ `pm_work_orders`; linked Service Log freeze Description/เวลาที่รายงานเป็น `incident_context_json` (`UNREVIEWED`, cause `UNKNOWN`). Unknown onset ไม่เท่ากับ created_at, DONE ไม่เท่ากับกราฟ recovery, และไม่มี Alert ไม่เท่ากับ detector false negative โดยอัตโนมัติ. Full QA 63/63 tests (2.01 s), frontend build ผ่านที่ temporary output, localhost metadata migration 2 ครั้งผ่าน ไม่แก้ source/Work/Log rows. Dashboard browser UAT, integrated evidence-graph link และ new 1m scorer→live Alert mapping ยังไม่ผ่าน ไม่มี Server action. รายละเอียด `docs/INCIDENT_REPORT_WORKFLOW.md`.

## Maintenance และ Fleet Trend ล่าสุด (2026-09-30)

- Warning Acknowledge บันทึก suppression 7 วันเท่านั้น; Critical Acknowledge สร้าง Work Order หนึ่งใบต่อ Alert. Assigned Work เรียง `created_at ASC, id ASC` และแสดงเวลา Alert (`pm_work_orders.alert_recorded_at`) หรือเวลาเปิดงาน manual.
- Service Log ใหม่เก็บ `parts_json` (name, quantity, unit_cost_baht, line_cost_baht), `other_cost_baht`, `cost_baht` รวม. Log เดิมที่ไม่มีรายการแยก แสดงเป็น legacy unitemized cost ไม่อ้างว่าเป็นค่าแรง.
- Admin แก้ไข Log ได้ และลบ Log/Work Order active ได้. การลบเก็บ snapshot, actor และเวลาใน `pm_deletion_audit` ใน transaction เดียว. ลบ Log แล้ว Work Order ที่ DONE ยังคง DONE; ลบ Work Order ระหว่าง IN_PROGRESS แล้ว module กลับไปตาม diagnostic ล่าสุด ไม่ถือว่า repair สำเร็จ.
- Fleet Trend อ่าน `pm_diagnostic_snapshots.recorded_at` เป็นวันตาม MySQL และใช้ snapshot ล่าสุดต่อ module ต่อวัน; ไม่มี snapshot ให้เป็น null. Local MySQL ณ 30 ก.ย. มี diagnostic coverage 65 modules ในวันที่ 24 และ 30 ก.ย.; 25–29 ก.ย. ไม่มี diagnostic จึงไม่มีเส้นเชื่อม. **เวลาใน trend คือเวลา snapshot ที่แอปบันทึก ไม่ใช่ source event time**; poll/replay ข้อมูลเก่าอาจดูใหม่เกินจริง. ต้องแก้ event-time provenance ก่อนใช้ตัดสินใจ Production.
- Schema migration ของ metadata `predictive_maintenance` บน localhost ผ่าน, query Trend และ Logs ตอบได้. ยังไม่ได้ deploy/ทดสอบบน Server หรือ staging. การทดสอบ automated 43/43 และ frontend build ผ่านในรอบนี้; browser visual QA ยังไม่ทำ.

## Normal-port localhost MX777 rehearsal (2026-09-23; newer than the isolated mock below)

- ตามคำสั่งเจ้าของโครงการ ใช้ MySQL localhost:3306 ชุดปกติ (`ht9046mx_iot`, `ht9046mx_analytics`, `predictive_maintenance`) และ API ปกติ OPERATION :8000 / Dashboard :5001 / OP web :5173. **ไม่ได้ต่อหรือ deploy Server 10.195.17.69/73**. ข้อยกเว้นเฉพาะการทดสอบนี้คือ append ข้อมูลสังเคราะห์ `machine_number=777` ลง source table ปกติ; ไม่แตะข้อมูลเครื่องอื่น. Mock schemas ก่อนหน้ายังคงเป็น fixture/provenance ไม่ใช่ database ที่ services ปกติใช้งาน.
- `ht9046mx_iot.ht9046mx_readings` มี 43,212 timestamps ของ 777 (30 วัน + 12 จุดห่างกัน 5 นาที); discovery API เห็น MX777. Calibration API รอบแรก fail closed เมื่อ history มี coverage ไม่สม่ำเสมอ; เติม history ใน fixture แล้วรันใหม่ได้ 8 candidates `READY_FOR_APPROVAL` ก่อน approve ผ่าน API ปกติเป็น 8 `ACTIVE_FROZEN` IDs 160–167, batch `6ed6230f-121b-434b-8500-db8301b35511`. ใช้ test-only contract/codebook/service-epoch versions ใน process local และ `MOCK777_TEST_APPROVER`; rollback เป็น `NO_ACTIVE_PROFILE_FAIL_CLOSED`. **ไม่ใช่ profile approval/release สำหรับ production**.
- Inference เริ่มต้น 200 windows/โมดูล แล้ว accelerated stream 12 ช่วง × 8 โมดูล = 96 คะแนนเพิ่ม; `compressor_health_scores` มี 212 results/โมดูล ภายใต้ alias `MX777`, ล่าสุด 22:08. Dashboard machine ID 400 แสดง M5/M6 score 15/`MAINTENANCE_REQUIRED`; API เห็นผลครบ 12/12 ช่วง. Alert 777 ที่คงอยู่ 3 รายการ (M5/M6 critical, M8 warning) ไม่มี duplicate จากแต่ละ stream step. ไม่ได้ยืนยันการ acknowledge/Work Order ในรอบนี้.
- Accelerated stream ใช้เวลา scoring สูงสุด 3.163s/step, median source-to-Dashboard API 10.293s/step; 40 concurrent Dashboard GET ด้วย 10 HTTP workers ไม่มี HTTP error, p95 2.695s. เป็น load sample สั้น **ไม่ใช่ 10 browser tabs หรือ 1-hour wall-clock soak**. Dashboard tests 41/41, OP tests 19/19 และ production builds ทั้งสองระบบผ่าน; build เตือน JS chunks ขนาดใหญ่.
- พบข้อจำกัด: history endpoint สูงสุด 2,000 timestamp (~35h ใน fixture), metrics สูงสุด 3,000 metric rows (~8h) แม้ source มี 30 วัน; จึงยังดูกราฟ 7 วัน/เดือนครบไม่ได้. Fleet Health Trend ใช้ `pm_diagnostic_snapshots.recorded_at` ซึ่ง poller อาจบันทึกเป็นเวลาปัจจุบันแม้ source sample เก่ากว่า ทำให้ freshness ใน trend ชวนเข้าใจผิด. OP runtime `inference.py` ใช้ `max(abs(relative_z))` และ fixed mapping เป็น Health Score แต่บันทึก `ARX-Ridge__seed_13` เป็น model_version; **ยังไม่ได้รัน ARX-Ridge artifact จริง**. แก้คำสั่งเปิด OP frontend :5173 จาก positional root ที่ตอบ 404 เป็น `vite --host 127.0.0.1 --port 5173`; browser แสดงหน้า Calibration และ MX777 `8/8 Active`, 43,212 rows จริง แต่การคลิกเข้าเครื่องหมดเวลาที่ browser client. Dashboard browser ยังอยู่หน้า login จึงยังไม่ยืนยันกราฟ/หลายแท็บผ่าน UI.
- รอบนี้ไม่พร้อม Production: ต้องแก้ model provenance/score semantics, event-time freshness, month-range downsampling/pagination, security key/TLS, verified versions/rollback, source timezone, sustained browser/multi-worker QA และ staging acceptance ก่อน deploy. โปรไฟล์สังเคราะห์ 777 ต้องไม่ถูกนำไปใช้กับเครื่องจริง.
- Test-data labeling gap: Dashboard แสดงป้าย `TEST DATA` เฉพาะ `model_version` ที่มี `MOCK_ONLY`; ผล 777 จาก normal-path runtime กลับใช้ชื่อ `ARX-Ridge__seed_13` จึงไม่มีป้ายทดสอบ แม้เป็นข้อมูลสังเคราะห์. OP Calibration UI ใช้ข้อความ `ACTIVE IN PRODUCTION` กับ test-only profile. ต้องเพิ่ม provenance/test flag ที่เชื่อถือได้ก่อนเปิดให้ผู้ใช้ทั่วไปเห็นข้อมูลชุดนี้.

## ระบบปัจจุบัน

- Backend: FastAPI (`app/`)
- Frontend: React + ECharts (`frontend/src/`), build output ที่ `public/`
- Metadata: MySQL ตาราง `pm_*`
- Telemetry: อ่านอย่างเดียวจาก MySQL `10.195.17.73`
- Deployment target: Web App Server `10.195.17.69` แต่ยังไม่ได้ deploy ในรอบนี้

## Data truth

| Source | Identity | Modules | ข้อมูลหลัก |
| --- | --- | --- | --- |
| Vacuum Pump | `devices_id` | `vacuum-pump` | temperature, current, accel x/y/z, vibration mm/s |
| Compressor | `machine_number` | `compressor-m1` ถึง `compressor-m8` | HP/LP stage values, temperatures, valve, busy, status, SV |
| Compressor ML | machine + module + recorded_at | M1–M8 | health_score, condition, model_version |

Vacuum Pump ไม่มี pressure sensor. `pressure_kpa` ใน application เป็นค่าประมาณจาก:

`Pressure(kPa) = (Vibration(mm/s) + 2.2098) / -0.0439`

## Alert policy

- Key: `device_id + module_id + issue_key`
- Same/lower severity: สูงสุดหนึ่ง record ต่อวันตาม `Asia/Bangkok`
- Acknowledge: ระงับ same/lower severity ของ issue เดิม 7 วัน
- Severity escalation และ issue ใหม่: แจ้งได้ทันที
- State ถูกเก็บใน MySQL ไม่พึ่ง localStorage ของ browser

## Compressor ML contract

Table default: `ht9046mx_iot.compressor_health_scores`; ปิดด้วย `COMPRESSOR_HEALTH_ENABLED=false` จนกว่าจะมี producer จริง. Required columns: `machine_number`, `module_id`, `recorded_at`, `health_score`, `condition`, `model_version`.

เมื่อไม่มี row ที่ตรงกัน UI ต้องแสดง `Awaiting ML Score`.

## Verification ล่าสุด

- Python compile: ผ่าน
- Frontend production build: ผ่าน
- Automated tests: เพิ่ม coverage สำหรับ vacuum rules, mapping, ML contract และ alert policy
- Local MySQL integration: ผ่านบนเครื่องนี้; Production/staging DB integration: ยังไม่รัน
- Visual QA: ผ่านด้วย local-only synthetic fixture บน desktop และ mobile; ไม่ได้เชื่อม production

## Maintenance UI ล่าสุด

- Handler Detail แยก Sensor Snapshot ตาม source: Vacuum Pump แถวล่างเฉพาะ Accel X/Y/Z (ไม่มีค่าแสดง No data); Compressor ใช้ Busy/Status/SV เดิม

- ส่วน Assigned Work ใช้การ์ดงานแบบเป็นทางการ: หมายเลขงาน, สถานะ Open/In progress มุมขวาบน, ชื่องาน, เครื่อง, โมดูล, ผู้รับผิดชอบ และ action; ป้าย Priority มุมขวาบนถูกแทนที่ตามคำขอผู้ใช้
- ใช้สี ADI blue กับโครงหลัก; amber/red เฉพาะงาน High/Critical
- ปุ่ม Delete work order ของ Admin อยู่ชิดซ้าย; Start work / Record service log ยังคงจับกลุ่มทางขวาเหมือนเดิมทั้ง User และ Admin และลงบรรทัดถัดไปเมื่อพื้นที่ไม่พอ
- Overview Compressor modules แสดงเฉพาะสีสถานะในช่อง โดยคง tooltip/aria label; หัวข้อ Vacuum Pump modules ใช้ชื่อเต็ม
- แผง Maintenance Logs และ Data → Logs มีระยะขอบซ้ายขวาเท่าแผงหลัก; ตารางกว้างเลื่อนภายในกรอบได้
- ตรวจ layout กับข้อมูลจำลองบน desktop 1280px และมือถือ 390px: Delete อยู่ซ้ายของกลุ่ม Start work / Record service log, กรอบ Logs ชิดแนวเดียวกับแผงหลัก และไม่มี horizontal page overflow; ไม่ใช่การยืนยันกับ production data
- การเปลี่ยนแปลงนี้อยู่ใน frontend เท่านั้น ไม่เปลี่ยน API หรือ workflow ของ work order
- ตรวจด้วย local synthetic data: build ผ่าน, Python tests 15/15 ผ่าน และหน้า Maintenance แสดงได้บน desktop/mobile โดย viewport 390px ไม่ล้นแนวนอน

## Local preview ล่าสุด (2026-09-23)

- เปิดหน้า Maintenance ใน in-app browser ที่ `http://127.0.0.1:5098/#maintenance`
- `scripts/_maintenance_preview.py` ให้ข้อมูลจำลองเฉพาะเครื่องนี้ ไม่เชื่อม MySQL หรือ production server

## Working repository และการทดสอบ MySQL (2026-09-23)

- โฟลเดอร์หลักสำหรับแก้โค้ดและ push ต่อจากนี้คือ `C:\Users\Book\OneDrive\Documents\ChatGPT\Compressor_and_VacuumPump` (Git branch `main`, remote `origin`); ไม่มีการ push ในรอบนี้
- ซิงก์โค้ดล่าสุดจากโฟลเดอร์เดิมเข้า root ของ repository โดยไม่คัดลอก `.env`; สำเนาไฟล์ที่ถูกแทนอยู่ที่ `C:\Users\Book\OneDrive\Documents\ChatGPT\Compressor_and_VacuumPump_before_sync_20260923_01`
- MySQL local `localhost:3306`: `predictive_maintenance`, `vacuum_pump_db.vacuum_pump_readings` (1,140 rows), `ht9046mx_iot.ht9046mx_readings` (276,888 rows), `ht9046mx_iot.compressor_health_scores` (39,706 rows) เชื่อมและอ่านได้ ณ เวลาตรวจ
- แอปที่ `http://127.0.0.1:5001` รายงาน Vacuum/Compressor ไม่มี source error, cache ML 30 scores; API login, summary, devices (22), alerts (6) ตอบสำเร็จ
- คง `COMPRESSOR_SENSOR_SCALE=1` ของเครื่องนี้ตามค่าจริงที่อ่านได้; test mapping ใช้ค่า scale จำลองใน test เพื่อไม่ขึ้นกับ `.env`
- Python tests 15/15 ผ่าน และ frontend production build ผ่านจากโฟลเดอร์ใหม่นี้
- ไม่ได้ทดสอบหรือ deploy `10.195.17.69`; source telemetry ไม่ถูกแก้ไข

## Alert → Maintenance, Threshold และภาษา (2026-09-23)

- `PATCH /api/alerts/{id}/acknowledge` ทำ transaction เดียว: lock Alert, สร้าง `pm_work_orders.source_alert_id` ที่ unique, assign ให้บัญชีช่างที่ active, แล้วบันทึกการรับทราบ 7 วัน; กดซ้ำไม่สร้างงานซ้ำหรือยืดเวลาระงับโดยไม่ตั้งใจ
- Work Order จาก Alert แสดงใน Assigned Work และมีปุ่มย้อนจาก Alert ไป Maintenance; ลบ Alert แล้ว Work Order ยังอยู่ โดย FK ตั้ง `source_alert_id` เป็น null
- `DELETE /api/maintenance-logs/{id}` จำกัด Admin; ลบเฉพาะบันทึก ไม่ย้อนสถานะ Work Order หรือโมดูล และ invalidate summary cost
- Advanced Threshold เป็น override ต่อโมดูล Vacuum เท่านั้น; ปิดแล้วใช้ค่า default แต่กฎ Estimated Pressure ที่ยืนยันแล้วทำงานเสมอ; Compressor M1–M8 ใช้ ML Health Score และ API ปฏิเสธการตั้ง rule threshold
- กราฟและการ์ด Compressor ไม่แสดงเส้น threshold ตัวอย่างหรืออ้างว่าเป็น expected range อีก; สรุปแนวโน้มแสดงวิธีประเมินเป็น ML Health Score โดยตรง
- Settings มี ENG/TH บันทึกใน browser, ปรับ `html.lang` และฟอนต์ไทย; แปลการนำทางและหน้าปฏิบัติการหลัก ส่วนชื่อ metric/ข้อความจาก telemetry และ diagnostics บางรายการยังคงเป็นศัพท์เทคนิคภาษาอังกฤษ
- WebSocket รับ token ผ่าน subprotocol `adi-v1` แทน query string; ทดสอบ handshake สำเร็จ
- Local migration เพิ่ม nullable unique `source_alert_id` กับ FK สำเร็จ; ไม่ได้กด Acknowledge Alert จริงหรือสร้าง Work Order จากข้อมูลจริงระหว่างทดสอบ
- Unit tests 21/21 ผ่าน, frontend build ผ่าน; API local ตรวจ user ลบ log ได้ 403, admin ลบ id ที่ไม่มีได้ 404, และ work-order payload มี field ใหม่
- หลังเก็บงานกราฟ Compressor และคำแปล Detail แล้ว Python tests 21/21 และ frontend production build ผ่านอีกครั้ง (`git diff --check` ผ่าน)
- พรีวิวข้อมูลจำลองตรวจ Alert → Work Order link, Assigned Work และไอคอนลบ Log; พรีวิว MySQL จริงตรวจสลับโมดูล Compressor/Vacuum และภาษา TH บนหน้า Admin
- ตรวจ viewport 390px บน Maintenance และ Admin ภาษา TH แล้ว ไม่มีการล้นแนวนอน (`scrollWidth` 375px)
- Read-only API 3 ครั้งต่อ endpoint (`db/status`, `summary`, `work-orders`, `maintenance-logs`, `alerts`) อยู่ในช่วงประมาณ 4–22 ms บนเครื่องนี้; ไม่ใช่ load test production

## Cross-system hardening และ production gate (2026-09-23)

- Dashboard ไม่สร้าง Compressor Alert อีกต่อไป; OPERATION เป็นเจ้าของ `compressor_ml_condition` ขณะที่ Dashboard ยังสร้าง Vacuum Alert ตามกฎเดิม. Dashboard อ่าน Compressor Health Score จาก `ht9046mx_iot.compressor_health_scores` เท่านั้น ไม่อ่าน Calibration Profile โดยตรง
- `PATCH /api/work-orders/{id}` ปฏิเสธ `DONE`; UI ไม่มี Mark complete. การส่ง Service Log ที่ผูกใบงาน lock Work Order, ตรวจสิทธิ์/เครื่อง/โมดูล, INSERT Log, ปิด Work Order และอัปเดตสถานะเครื่องใน transaction เดียว; การปิดซ้ำได้ 409
- Admin ลบ Maintenance Log ได้; ถ้าลบ Log ใบสุดท้ายของ Work Order ที่ `DONE` ระบบเปิดงานกลับเป็น `OPEN` ใน transaction เดียวเพื่อรักษากฎว่าปิดงานต้องมีบันทึก
- Poller broadcast หนึ่งครั้งต่อรอบแทนต่อ sample; WebSocket ส่งหลาย client พร้อมกันและตัด client ที่ส่งล้มเหลว. หน้าเว็บข้าม full refresh/กราฟใน hidden tab, ป้องกัน request กราฟซ้อน, และอ่าน source history ซ้ำข้ามแท็บจาก cache 3 วินาที (สูงสุด 16 keys). JSON ใหญ่ใช้ GZip
- Mock read-only กับ local MySQL: รอบก่อน cache 8 แท็บ 128 requests รวม chart มี 19 timeout, p95 ประมาณ 13.4s. รอบตรวจโค้ดล่าสุดโดยส่ง gzip: 8 แท็บ 128 requests ไม่มี error, p95 3.02s; 16 แท็บ 256 requests ไม่มี error, p95 3.62s. เป็นการทดสอบคนละรอบบนเครื่องเดียว ไม่ใช่ benchmark แบบควบคุมตัวแปร, SLA หรือ production load test. กราฟ Compressor response เฉลี่ยประมาณ 794 KB ก่อน compression
- ทดสอบคำขอแบบ browser ที่ส่ง `Accept-Encoding: gzip` กับกราฟ local 4 แท็บ: payload กราฟบนสายเฉลี่ยประมาณ 24.4 KB เทียบกับประมาณ 794 KB แบบไม่บีบอัด; ไม่ใช่การวัดเวลา render ECharts ใน browser
- Dashboard tests 35/35, OPERATION alert/API tests 17/17 และ frontend build ผ่านบนโค้ดล่าสุด; build ยังเตือน ECharts chunk ขนาด 603.61 KB (gzip 200.88 KB)
- ปิดช่อง token signing ด้วย key ว่าง/ค่าเริ่มต้น: local ที่ไม่ได้ตั้ง `SECRET_KEY` จะสุ่ม key ชั่วคราวต่อ process; `APP_ENV=production` จะไม่เริ่มระบบหากไม่ได้ตั้ง key เฉพาะที่ยาวอย่างน้อย 32 อักขระ. ต้องตั้ง key เดียวกันทุก instance และตรวจ deployment config ก่อนเปิดใช้งานจริง
- Compressor telemetry ไม่ infer scale จาก magnitude อีกแล้ว: `COMPRESSOR_SENSOR_SCALE` ต้องระบุเป็น `1` หรือ `0.1` (ค่าเริ่มต้น `1`); มี regression test สำหรับ row ที่ `Hp_2nd=314.8` เพื่อกันการหารค่าทั้งโมดูลผิด 10 เท่า. ต้องให้เจ้าของ data source ยืนยัน unit ของทุกคอลัมน์ก่อน production
- Bootstrap user เมื่อเริ่มระบบจะไม่เขียนทับ password, role หรือสถานะ active ของบัญชีเดิมแล้ว; `APP_ENV=production` ปฏิเสธ bootstrap passwords ที่เป็นค่าเริ่มต้น/สั้น/ซ้ำกัน. ต้องจัดการบัญชี production จริงผ่านขั้นตอน provisioning ที่อนุมัติ
- Service Log แบบไม่ผูกใบงานไม่เปลี่ยนสถานะโมดูล; แบบผูก Work Order จะปิดงานและรีเซ็ตโมดูลที่ซ่อมจาก `UNDER_MAINTENANCE` เป็น `NORMAL` ใน transaction เดียว แล้วข้อมูล ML/กฎ Vacuum ใหม่เป็นผู้กำหนดสถานะต่อไป. ค่านี้เป็นสถานะหลังปิดงาน ไม่ใช่หลักฐานว่าความผิดปกติทางกายภาพหายแล้ว
- ยัง **ไม่ production-ready**: OPERATION SOT ระบุ ML release/profile ยังไม่มี ACTIVE_FROZEN/rollback/timezone/alert budget ที่ยืนยัน; Dashboard ยังต้องแก้ token revocation/current-role verification, ตรวจ perimeter/TLS และบัญชีจริง, ยืนยัน unit ทุก source column, end-to-end staging, source index/query plan, long-run soak, chart time-window completeness, source freshness และ failover ก่อน deploy. การทดสอบโหลดนี้ใช้ Uvicorn worker เดียวเท่านั้น: หากเพิ่มหลาย worker ในสถาปัตยกรรมปัจจุบัน แต่ละ process จะมี poller/cache/WebSocket ของตนเอง จึงต้องแยก ingestion ให้มีเจ้าของเดียวและใช้ shared pub/sub ก่อน scale out

## Local isolated HT9046MX-777 integration test (2026-09-23)

- สร้างเฉพาะ MySQL บน `127.0.0.1`: `ht_mock777_source` (Compressor M1/M2, 2,880 synthetic history rows + 15 fresh rows และ Health Score output), `ht_mock777_analytics`, `pm_mock777_dashboard`. ไม่แตะ source schema จริงหรือ production server; scripts ใน `scripts/*mock777*` จำกัด host เป็น local
- หน้า Dashboard ที่ `127.0.0.1:5014`: ก่อน scoring แสดง `Awaiting ML Score`; หลังรัน OPERATION inference ด้วย shadow candidate ที่ inject ใน memory เฉพาะสคริปต์ทดสอบ แสดง M1/M2 Health Score 76 และ model version `MOCK_ONLY_*` ผ่าน UI. สถานะ Handler/ML ตรงกันเป็น GOOD/NORMAL หลังแก้ไม่ให้ local score band ทับ explicit `condition` จาก OPERATION. UI แสดงป้าย TEST DATA และเวลา score
- การทดสอบนี้พิสูจน์ data transport และ UI binding เท่านั้น **ไม่พิสูจน์ความถูกต้องของค่า Health Score หรืออนุมัติ Profile**. OPERATION API แบบปกติตอบ `NO_ACTIVE_PROFILES`; Calibration UI ได้ 2 candidates, 0 ready เพราะ version/state gate ยังไม่ยืนยัน
- Mock ขนานระหว่าง Dashboard กับ OPERATION: Dashboard 8 simulated tabs × 2 รอบ 128 reads รวมกราฟ/gzip ไม่มี error, p95 4.80s; OPERATION 32 GETs พร้อมกัน 8 workers ไม่มี error, p95 0.59s. เป็น local bounded test ไม่ใช่ browser render/staging/production SLA
- Dashboard tests 36/36 ผ่าน; source health-score query เลือก row ล่าสุดแบบ deterministic เมื่อ timestamp ซ้ำ. Synthetic data จะคงอยู่ใน schema ชื่อ mock เพื่อให้ตรวจย้อนหลัง ไม่รวมใน source ของการใช้งานจริง

## Overview priority และ status taxonomy (2026-09-23)

- Overview ใช้สถานะปัจจุบันจาก `pm_modules`/Compressor ML/กฎ Vacuum แสดง Compressor heatmap M1–M8 และ Vacuum attention list โดยเรียง Repair now → Warning → No Signal → Repairing → Good; No Signal เป็นสัญญาณแยกจากสถานะสุขภาพ
- ค่า Vibration ในรายการ Vacuum ใช้สีเดียวกับสถานะของโมดูล: Warning = amber, Repair now = red. ไม่ใช้สีแดงกับค่าในแถว Warning เพียงเพราะขนาดตัวเลข
- Top deteriorating แสดงเฉพาะโมดูลที่ Health Score ลดลงเทียบกับ snapshot ที่มีอายุ 24–48 ชั่วโมง; เมื่อไม่มี baseline จะเป็น empty state ไม่อนุมานแนวโน้มจากคะแนนล่าสุดเพียงค่าเดียว. SQL lookup ใช้ index `module_id, recorded_at` และจำกัดหนึ่งค่า baseline ต่อโมดูล
- ชื่อสถานะบน UI คือ Good / Warning / Repair now / Repairing / Offline. `WATCH` จาก ML แสดงเป็น Warning; migration แปลง `MONITORING` เก่าใน metadata เป็น `NORMAL` ก่อนเอาค่าออกจาก ENUM และ API ไม่รับการตั้งสถานะนี้ใหม่
- Linked Service Log ปิดใบงานและเปลี่ยนสถานะโมดูล/เครื่องใน transaction เดียว; telemetry/ML รอบถัดไปอาจเปลี่ยนกลับเป็น Warning/Repair now ถ้าปัญหายังอยู่. Manual Service Log ไม่เปลี่ยนสถานะ
- Local mock-only visual QA: Overview เปิดได้, M2 heatmap drill-down ไป M2 ถูกต้อง, viewport 1280px/390px ไม่ล้นแนวนอน. Mock HT9046MX-777 มีเฉพาะ Compressor M1/M2 สถานะ Good จึงยังไม่ได้ยืนยันภาพที่มี Vacuum Warning หรืออันดับหลายเครื่องจาก browser จริง
- Python tests 38/38, frontend production build และ `git diff --check` ผ่าน; isolated mock metadata startup/migration ตอบ `/api/health` 200. ไม่ได้ deploy. Build ยังเตือน ECharts chunk 603.61 KB

## Overview trend/layout รอบล่าสุด (2026-09-23)

- `GET /api/overview/health-trend?range=24h|1m` อ่านเฉพาะ `pm_diagnostic_snapshots` ผ่าน index `idx_pm_diag_module_time` ที่ 24 hourly หรือ 30 daily checkpoints; หนึ่งโมดูลนับเมื่อสร้างแล้วและมีผลวินิจฉัยภายใน 2 ชั่วโมง (24h) หรือ 48 ชั่วโมง (1m) ก่อน checkpoint. `WATCH` รวม Warning; ไม่มี coverage คืน `null` ไม่ใช่ศูนย์. ใช้เวลา MySQL `NOW()` และ cache 60/300 วินาที พร้อม lock กัน query ซ้ำข้ามแท็บใน process เดียว
- UI วางกราฟซ้าย/Handler status ขวา. Handler distribution ใช้ health status ที่ไม่ซ้ำกัน; No Signal ยังเป็น connectivity KPI แยกต่างหาก. Open Work Orders อยู่ท้ายหน้า, row และลิงก์หัวการ์ดเปิด Maintenance. Compressor/Vacuum แสดง preview สูงสุด 5 เครื่องแต่คลิก View all ได้. ไม่มี Wi-Fi glyph ใน Overview
- Query บน local `pm_mock777_dashboard` แบบอ่านอย่างเดียว: 24h มี 3 checkpoint ที่มีข้อมูลใน 24 จุด ประมาณ 43 ms; 1m มี 1 checkpoint ที่มีข้อมูลใน 30 จุด ประมาณ 3 ms. ความครอบคลุมจำกัดเพราะประวัติ mock สั้น; ไม่ใช่ performance benchmark production
- เรียก trend 24h พร้อมกัน 16 ครั้งบน local mock ได้ 24 จุดทุกคำขอและจบรวมประมาณ 42 ms ใน process เดียว; ยังไม่ใช่ multi-worker/staging load test
- Python tests 41/41 และ frontend production build ผ่าน; local synthetic browser 6 เครื่องตรวจ preview 5/6 ทั้งสองประเภท, สีและลำดับสถานะ, เลือก 1 month, chart canvas และลิงก์ Maintenance. Desktop 1366px วาง trend ซ้าย/status ขวา และ work orders ท้ายหน้า; mobile 390px ไม่ล้นแนวนอน. ยังต้องตรวจ staging query plan/ข้อมูลประวัติจริงก่อน deploy. ไม่มีการเปลี่ยน source telemetry หรือ deploy production

## Overview visual refinement (2026-09-23)

- Work Orders ยังอยู่ท้ายหน้า แต่กรอบกว้างเท่าคอลัมน์ Compressor ด้านบนบน desktop และเต็มคอลัมน์บนหน้าจอแคบ; ตัดเส้นบนสีฟ้า, ไอคอน/ขอบระดับปกติใช้ neutral ส่วน amber/red ใช้เฉพาะ priority
- Compressor M1–M8 เป็น status tiles สีพื้นอ่อนตาม Good/Warning/Repair now, แสดงจุดสีและป้าย M ในแต่ละช่อง. ห้าแถวขยายตามความสูงของการ์ดเพื่อไม่ปล่อยพื้นที่ล่างว่าง โดยยังเลื่อนได้ในแนวนอนบนมือถือ
- เป็นการเปลี่ยน presentation เท่านั้น ไม่เปลี่ยน source, status mapping, API หรือ workflow; verification รอบนี้ระบุใน checklist
- Python tests 41/41, frontend production build และ `git diff --check` ผ่าน; browser preview ข้อมูลสังเคราะห์ 6 เครื่องตรวจ Light/Dark ที่ 1366px และ 390px แล้ว: Work Orders จัดแนวกับ Compressor, แถว heatmap เต็มการ์ด, ไม่มี horizontal page overflow. ไม่ใช่การยืนยันกับ production data

## Compressor map hierarchy รอบล่าสุด (2026-09-23)

- ย้อนจาก tiles ที่มี M ซ้ำในทุกช่อง: ใช้หัว M1–M8 แถวเดียวเหนือ 5 เครื่อง. พื้น/กรอบช่องปกติถูกเอาออก เหลือจุดสีและเส้นแบ่งแถวบาง ๆ; เฉพาะ `MAINTENANCE_REQUIRED` ใช้พื้นแดงอ่อน. Warning ใช้จุด amber โดยไม่มีพื้นสี
- การเรียงเครื่อง, จำนวนตัวอย่าง 5 เครื่อง, drill-down, status mapping และ API คงเดิม. Python tests 41/41 และ frontend production build ผ่าน. Browser preview ธีม Light 1366px/390px และ Dark 390px ยืนยันมีหัวแถวเดียว, Normal/Warning พื้นโปร่งใส, Critical แดงจาง และหน้า mobile ไม่ล้นแนวนอน; fixture ไม่ครอบคลุม M6 จริงหรือ production data

## v1 repository snapshot (2026-09-24)

- Prepared the separate private `Compressor_and_VacuumPump_v1` repository with the implemented source tables, `pm_*` ownership, score/alert integration contract, Mermaid data flows and Server setup guide.
- Publication is not a production release. Staging source checks, Compressor model/profile approval, security review, UAT, sustained load and rollback remain open.
- Release QA on 2026-09-24: primary Python suite passed 41/41 and frontend production build passed. Added `pytest.ini` so root-level pytest excludes the nested legacy copy and live-server smoke script; no production database was contacted.
- Added the Server input checklist and explicit ignore rules for local secret handoffs. Passwords remain outside Git; generated values are not active until the DBA creates the matching accounts and staging acceptance passes.


## 2026-09-30 — Database / Analytics แยก source และโหลดตามคำสั่ง
- เริ่มต้นไม่เลือก source/เครื่อง/โมดูลและไม่ยิง telemetry history/metrics จนกด Load; metadata ของ dashboard ยัง refresh ตามเดิม
- Database: เลือก source → เครื่อง → โมดูล; เลือก dataset, ช่วงเวลา, จำกัด 100–1,000 rows; แสดงครั้งละ 100 แถว; export เฉพาะข้อมูลที่โหลด
- Analytics: เลือกได้สูงสุด 6 เครื่อง / 12 โมดูล / 4 metrics; กดโหลดเอง, ใช้ history request เดียวต่อโมดูลสูงสุด 2,000 ตัวอย่าง และจำกัด in-flight 4; ปรับ legend แบบ scroll, zoom, ชื่อ/ตัวเลือก wrap, ไม่เติม null เป็นศูนย์
- AbortController ยกเลิกผลล่าช้าเมื่อเปลี่ยน selection/ออกจากหน้า; identity ของกราฟใช้ device+module และ state แยกต่อแท็บ; memoize chart option เพื่อไม่ reset zoom จาก metadata refresh
- history response เพิ่ม source metric columns พร้อม Status/SV; Compressor ไม่ใช้คอลัมน์ Vacuum. UTC จาก browser แปลงเป็นเวลา source ตาม APP_TIMEZONE; since เป็นขอบเขตจริง ไม่เลื่อนไปหาข้อมูลเก่าและไม่ fallback เมื่อ source ว่าง
- ตรวจ SHOW COLUMNS/SHOW INDEX จาก DB ที่ตั้งค่าไว้แบบ read-only: Vacuum มี temperature/current_amp/accel_x,y,z/vibration; Compressor มี HP/LP/Valve/TempHi/TempLo/Status/Busy/SV ของ M1–M8; index devices_id+recorded_at และ machine_number+recorded_at มีจริง
- EXPLAIN ใช้ index ของ source ทั้งสอง. Vacuum query เรียง recorded_at/id; Compressor แชร์ wide rows ต่อ machine+limit (TTL 3s, LRU 8 เครื่อง) และ cache ชื่อคอลัมน์สูงสุด 512 ชื่อ
- วัด sample บน DB ที่ตั้งค่าไว้: Vacuum 60 ตัวอย่าง 5.8ms; Compressor 2,000 ตัวอย่าง read+map 398.8ms, โมดูลถัดไปที่ใช้ cached wide rows 130.7ms. เป็นการวัดเฉพาะครั้งบนเครื่องนี้ ไม่ใช่ SLA หรือผลโหลด production
- QA synthetic: ก่อนโหลดทั้ง Database/Analytics ไม่มี history request; แยกคอลัมน์สอง source, pagination, สองแท็บต่าง source, เปลี่ยน source ขณะโหลด, Accel Y ที่ null แสดง --, Snapshot ทั้งสองประเภท และจอ 390px
- ช่วงยาวอาจได้ข้อมูลไม่ครบช่วงเพราะขีดจำกัดล่าสุด 2,000 ตัวอย่าง/โมดูล; แสดงข้อจำกัดในหน้า Analytics. ยังไม่ได้ทำ production load test หรือเปลี่ยน source index/schema

- Analytics เพิ่มค้นหาเครื่อง และเลื่อนไปผลกราฟเมื่อโหลดเสร็จ เพื่อเห็นผลทันทีหลังเลือกหลายรายการ


## 2026-09-30 — Chart load QA หลายแท็บ
- ทดสอบเว็บที่ port 5001 กับ MySQL source ที่ตั้งค่าไว้: 6 แท็บ / 6 เครื่อง Compressor / 24 โมดูล / 4 metrics ต่อแท็บ; เลือก All available history เพราะข้อมูลบาง source เกิน 7 วัน
- ผล paired browser run: เวลา API/data load เฉลี่ย 5.94 → 2.45 วินาที; แท็บช้าที่สุด 7.40 → 4.19 วินาที; sample counts เท่ากันและไม่พบ toast error. First-finished ของ canvas ที่ถูก render อยู่ที่ 53–320ms; กราฟนอกจอวาดเมื่อเลื่อนใกล้ถึง
- แก้ shared lock ระหว่าง I/O/แปลงข้อมูล, connection pool สำหรับ history แยกจาก latest poller (สูงสุด 4/source), single-flight แบบ bounded แยก source, cache sample LRU 32
- Analytics ใช้ history-batch ต่อเครื่อง และส่งเฉพาะ signals ที่เลือก; Database endpoint แบบเดิมยังได้คอลัมน์ครบ. จำกัด batch 12 โมดูลและ validate signals ก่อนอ่าน
- Detail อ่าน history ครั้งเดียวสำหรับ primary charts; cache timeline/grouping และ chart options ด้วย WeakMap; เลิกยิง metrics ซ้ำสำหรับ primary graphs; correlation/relationship API คงเดิม
- ตรวจ Detail 6 แท็บที่ All: stage graphs และ HP2 summary มีข้อมูล; เลื่อนลงแล้วกราฟที่ defer ถูกสร้าง. จำกัดผลตรวจตาม load scenario นี้ ไม่ใช่ production SLA
- ป้องกัน 401 ของแท็บที่ใช้ token เก่าลบ token ใหม่ใน localStorage ของแท็บที่ login ใหม่
- Tests 51 ผ่าน / frontend build ผ่าน / local health ok; รายงานละเอียด artifacts/LOAD_TEST.md และ artifacts/load-browser-6-tabs.json; script อ่าน service/source แบบ read-only scripts/qa_chart_load.py

## 2026-09-30 — Handler history contract
- Default detail range คือ latest available history (bounded 2,000 samples), ไม่ใช่ 6h. UI แสดงวันที่จริงและไม่เปลี่ยน timestamp เก่าเป็นปัจจุบัน. ปุ่ม 1h–7d ใช้ขอบเขตปัจจุบันตาม API; empty ไม่แปลว่า request ยังโหลดอยู่
- Detail ใช้ compact history เดียวต่อ module/range/poll: Compressor HP/LP/TempHi/TempLo/Valve และ Vacuum temperature_c/pressure_kpa/current_a/vibration/accel_x,y,z. Snapshot metadata และกติกา source-specific คงเดิม
- Handler correlation/relationship คำนวณจากชุดที่ plot อยู่ (สูงสุด 2,000 time samples) แทน flattened metrics 3,000 rows ที่ตัดเหลือ time samples น้อยกว่า. Pearson ใช้คู่ค่าจริง finite, minimum 3 pairs; constant/missing correlation เป็น null; scatter downsample สูงสุด 1,200 ตามวิธีเดิม. Existing server analytics endpoints ไม่เปลี่ยน
- Identical polls ไม่ reset chart options/zoom; ค่าเปลี่ยนที่ timestamp เดิมยังตรวจพบ. History I/O ยังคง pool/cache/concurrency ของรอบก่อน; ไม่ deploy หรือ restart production
- ตรวจ service read-only พบข้อมูลล่าสุดของ HT9046MX-017: Compressor 2026-09-19 13:37:54 (480 samples), Vacuum 2026-09-16 18:20:04 (60 samples), recent 6h = 0 ทั้งคู่. ไม่มีการเติมข้อมูลทดแทน
- Database มี latest available range แบบ bounded ตามจำนวน rows ที่เลือก; ไม่เลือกเครื่องหรืออ่าน telemetry เองเมื่อเข้าหน้า. Database/Analytics บอกเมื่อช่วงไม่มีข้อมูล และชี้ไปช่วงย้อนหลังที่มีจริง
- Browser follow-up ยืนยันค่าเริ่มต้น Handler populated 6 เครื่อง, mixed 3 Compressor/3 Vacuum และ cross-page 4 Handler+Database+Analytics; ไม่พบ error ใน scenario. Handler relationships อิง timestamp timeline เดียวกับ plot (รวมแถว timestamp ซ้ำด้วยกติกาเดิม). ค่าที่วัดและข้อจำกัดอยู่ใน artifacts/LOAD_TEST.md; mobile override ไม่ได้เปลี่ยน observed width จึงไม่ verified รอบนี้

## 2026-09-30 — Handler summary visibility
- ผู้ใช้ให้เอากรอบสรุป telemetry ตามภาพออก: Handler ไม่แสดง sample count, request time, actual date range หรือ sample-limit caption หลังโหลดสำเร็จ. รายงาน QA ก่อนหน้าเป็นหลักฐานของรอบก่อนนำกรอบออก
- Loading/error/empty ยังคงแสดงข้อความเฉพาะสถานะ. Default latest history, source separation, request identity, polling และกราฟไม่เปลี่ยน

## 2026-10-01 — Compressor matrix / Handler loading presentation
- ผู้ใช้จำกัด Overview changes ไว้ที่ Compressor modules. Subtitle `Machines needing attention first · shown / total` เป็น English ตามคำสั่ง; observed count คือ 5 / 24. Vacuum panel, Fleet Trend และ KPI ไม่ได้อยู่ใน scope รอบนี้
- Matrix color/top bar = latest diagnostic status. Dashed bottom edge = existing Handler connection_state OFFLINE; ไม่ใช่ per-module heartbeat หรือข้อสรุปว่า Compressor เสีย. Legend อธิบายสองความหมายนี้แยกกัน
- Matrix hover/focus อ่าน module/status/Health Score/ML result timestamp/sensor timestamp/Handler signal จาก device metadata เดิมเท่านั้น. Missing score ระบุ Awaiting ML Score; ไม่แปลง Health Score เป็น Anomaly Score และไม่อนุมาน abnormal duration จากอายุข้อมูล
- Handler ทั้ง Compressor/Vacuum ไม่แสดง Loading chart data. Trend/chart slots อยู่ตั้งแต่ pending ด้วยขนาดเดิม และไม่สร้าง ECharts ระหว่างไม่มี history. aria-busy ยังบอกสถานะให้ assistive technology; resolved empty/error อยู่ในพื้นที่กราฟแรก
- QA: Python 51, Node 5, production build ผ่าน; actual browser Compressor pending/populated geometry ตรงกัน 8 panels, Vacuum populated/empty/populated ตรงกัน 4 panels. Pending ของ Vacuum ไม่ทัน captured ในรอบนี้; ใช้ component จองพื้นที่เดียวกันทั้งสอง source. API/source/threshold/formula contracts ไม่เปลี่ยน
