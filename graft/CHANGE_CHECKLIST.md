## 9 October 2026 — Empty-feed receiver diagnostic handoff

Added deployment/EMPTY_FEED_RECEIVER_HANDOFF_20261009.md. Diagnose producer .73 first; no Active can still export NOT_EVALUATED/Pending. Then verify actual nonempty payload/cursor/identity/receipt progression on .69. Historical empty-feed connectivity/restart is not delivery acceptance. Documentation only; no new Server check, runtime/DB/Profile change or restart.


## 7 Oct 2026 — one-way Operation delivery and hourly Fleet history

Confirmed topology: Dashboard .69 initiates SELECT to Operation .73:3306 only. Ordered transactional STATUS/EVENT export and Dashboard-owned receipts/cursor replace the reverse bridge. No new browser-owned detector loop; bounded polling/catch-up and shared caches. Shadow/no Active/unsupported states remain NOT_EVALUATED; no invented Health Score/Critical threshold. Hour-end module/fleet snapshots, source-clock state events, 168 hourly points and late-bucket correction now implemented; historical gaps remain null. Compressor stage colours/SV-Busy step plots and shared scaled-pointer handling, Vacuum separate axes/no Temperature/zero-at-bottom/G rms labels delivered. Calibration numeric basis unchanged; true RMS/source calibration basis still requires confirmation.

Verification: 91 Dashboard Python tests, 13 Node tests, production frontend build; companion Operation 264 API tests. Isolated real MySQL rollback/retry/concurrent sequence/restart/outage/source-identity/Alert-policy/hourly correction QA and 10 clients/90 successful HTTP reads (warm p95 1000.84 ms, excluding Server network/browser render). Raw source and real Profile/Active writes: zero. Server update/actual-network acceptance remains pending; deployment/ONE_WAY_MYSQL_UPDATE_20261007.md supersedes the old reverse bridge handoff.

# Change Checklist

## Operation grant and receiver restart checks — 2026-10-08

- [x] Actual .69 reader SELECT on feed/sequence/identity succeeds; former 1044 resolved; both raw sources work.
- [x] Receiver status checked twice ten seconds apart: connected, no error, cursor 0/backlog 0.
- [x] Metadata backup and installed API restart passed; cursor and identity/receipt/Alert counts retained without extra delivery.
- [ ] Producer tables are empty: real export/identity publication, cursor progression and populated-feed deduplication remain unverified.

## GitHub pull and installed Dashboard update — 2026-10-08

- [x] Fast-forward eb3b097 -> 5bfa10a; private config/frontend and metadata backups preserved.
- [x] Existing environment values retained; new Operation keys added; dependencies installed; 91 Python/13 Node tests and production build passed.
- [x] Installed API restarted; Admin login/frontend/device/hourly trend endpoints and both raw-source reads pass; additive metadata tables are InnoDB.
- [ ] Companion `.73` export migration/SELECT grants and feed ingestion acceptance: configured analytics reader denied with MySQL 1044. No fabricated result or source/Profile/model mutation.

## Pending label & Fleet Health Trend cleanup — 2026-10-07

- [x] Renamed user-facing "Not evaluated" label to "Pending" across frontend Handler filters (`HANDLER_FILTER_OPTIONS`), `Handler status distribution` bar (`systemStatusBars`), `conditionLabel`, and module map legends.
- [x] Added Thai translations for "Pending" / "PENDING" ("รอดำเนินการ") in `frontend/src/i18n.js`.
- [x] Removed `not_evaluated`, `no_signal`, and `maintenance` from `FleetHealthTrend` series and legend, focusing chart exclusively on 4 core conditions: Good, Warning, Repair now, Offline.
- [x] Confirmed and verified strict separation between Pending and Offline: signal loss >30m always defaults to Offline; Pending only applies when machine is actively Online/connected and awaiting ML evaluation.
- [x] 91 backend tests and production frontend build pass cleanly.

## Compressor signal Online through 30 minutes — 2026-10-06

- [x] Owner-requested removal of Compressor 20–30 minute NO_SIGNAL state in shared connection policy.
- [x] Boundary regression covers <=30 minute Online and >30 minute Offline; Vacuum/missing-time rules retained.
- [x] Real canonical HT9046MX IDs use explicit stored source membership in Handler and summary APIs; source-specific regression prevents treating pure Vacuum as Compressor.
- [x] Updated PROJECT.md and SOT.md; no phase change or source telemetry mutation. Actual test/build/restart outcomes recorded in deployment/SERVER_ACCEPTANCE.md.

## Actual Server .69 portable setup — 2026-10-06

- [x] Read HANDOFF_SERVER first; inspected actual .69 hostname/IP/OS/timezone/listeners/tasks and preserved existing HT9046MX configuration.
- [x] Python 3.12 venv, locked npm install/build; fixed missing Windows tzdata and separate httpx/pytest test requirements.
- [x] New loopback metadata MySQL/dedicated schema account, private original config backup, nginx /api and /ws proxy, hidden per-user supervisor and local metadata-only scheduled backups.
- [x] Verified SELECT-only Compressor source access; real login and proxy WebSocket, eight concurrent histories and API restart recovery; no source writes/Operation/Profile/model changes.
- [x] 70 unittest and 82 pytest tests passed; production frontend build passed; deployed API evidence stored privately in ignored runtime.
- [x] Owner-supplied Vacuum username verified with prepared private password; SELECT-only table grant and actual `device_id` mapping confirmed; both sources read and ten concurrent histories pass.
- [x] Historical page/chart APIs pass for both source families; Vacuum test covers both configurable identity columns, Estimated Pressure and null preservation. Final 70 unittest / 82 pytest / 19 subtests passed with current Server `.env`; final frontend build passed.
- [ ] Actual browser/remote LAN checks, reboot/boot-before-login and sustained load. Browser launch was blocked by automatic approval review; Windows denied noninteractive boot task.
- [x] Updated PROJECT/SOT/ROADMAP and deployment/SERVER_ACCEPTANCE.md with actual partial deployment status and limitations.

## Log page scrolling & viewport height fix — 2026-10-06

- [x] Removed `body` from `min-height: calc(100vh / var(--dashboard-scale))` in `frontend/src/styles.css` (keeping it scoped strictly to `.app-shell, .login-shell`), eliminating a 79px phantom body overflow caused by unzoomed `body` having `111.11vh` min-height.
- [x] Added `window.scrollTo(0, 0)` on view changes in `frontend/src/main.jsx` (`useEffect([view])` and `safeSetView`).
- [x] Verified via headless Edge CDP on `#logs`: `htmlScrollHeight == htmlClientHeight == 707px`, `scrollY == 0`, `.topbar` pinned at `(0, 0)`, eliminating sticky sidebar detachment and navbar desynchronization.
- [x] Full test suite (82 Python tests) and production frontend build pass cleanly.

## Numbering reset & Vacuum Pump tooltip — 2026-10-06

- [x] Admin sequence & ID numbering reset: clear_alerts() resets AUTO_INCREMENT to 1; reset_work_orders(actor) archives orders to pm_deletion_audit, unlinks pm_maintenance_logs (preserving all service history), restores module states, and resets AUTO_INCREMENT to 1.
- [x] Admin endpoints: GET /api/admin/numbering and POST /api/admin/numbering/reset strictly restricted to require_admin.
- [x] Admin UI: Added "Sequence & ID Numbering" panel in admin-grid with live stats (counts, max ID, next ID), refresh button, individual and joint reset buttons with confirm dialogs.
- [x] Vacuum Pump tooltip: Integrated interactive diagnostic portal tooltip into VacuumAttentionList matching CompressorHealthMap styling (.compressor-module-diagnostic), layout, theme compatibility, and fields (showing Awaiting ML Score for Vacuum Pump until model is available).
- [x] Full test suite (82 Python tests) passes cleanly; production frontend build (npm run frontend:build) succeeds.

## Dashboard display 90% — 2026-10-06

Owner chose a 90% desktop display with the existing component arrangement instead of a scrollable sidebar. Root scaling, viewport-height compensation and portal coordinates are updated. Actual 1280 x 720/browser-100% check: Logout fully visible, navigation has no scrollbar, document has no horizontal overflow; tooltip remains in the viewport. 65 Python tests and final production build pass. Evidence: docs/DASHBOARD_90_PERCENT_20261006.md and artifacts/dashboard-90-percent-qa/overview.png.


## Offline status — 2026-10-06

Owner-requested Offline after more than 30 minutes without signal now projects into device/module status, summary and filters. Earlier transient loss is NO_SIGNAL. Compressor Overview cells are grey with solid borders and a matching Offline legend; caption counts all Compressor machines. 65 Python tests, final build and actual local web checks pass. Details and screenshots: docs/OFFLINE_STATUS_20261006.md. Local API restart only; source data and Profile/Active policies unchanged. Earlier connectivity descriptions below are historical.


## Historical card layout — 2026-10-02

- [x] Historical Charts/Database/Analytics outer cards align with Maintenance/Alerts/Logs: shared frame, padding and 17 px heading style; 28 px desktop/12 px mobile insets
- [x] Database filters grouped into machine/module, date/time and dataset/load rows; 900 px date controls stack to avoid clipped values
- [x] Desktop reference measurements match; 390 px Analytics/Database stay within document width; real historical Database and chart loads return 60 source readings
- [x] Existing fixed 340 px desktop chart slots retained; no selection/query/source contract changes
- [x] 72 Python tests and final production frontend build pass (existing ECharts chunk-size warning); Thai localhost:5001 serves rebuilt assets without console errors
- [x] PROJECT/SOT/history guide updated; screenshots and measurements in `artifacts/history-layout-qa/`

## Historical browser and owner-requested graph removal — 2026-10-02

- [x] Removed graph evidence buttons/dialog/helper/API and dedicated harness/tests from Alerts, Assigned Work, Maintenance tables and Data Logs; incident fields/snapshots remain
- [x] Historical Charts added under Data; Database/Analytics select machines before mapped modules, with no initial history selection/load
- [x] Source-specific fields, OFF module histories, nulls, Bangkok time and half-open up-to-31-day windows retained; date filter precedes source SQL LIMIT
- [x] Raw source pagination/page exports; bounded time-bucket first/last real points across custom graph ranges; latest charts avoid full-source scans
- [x] Bounded caches/connection pools, shared wide Compressor rows, four client request workers and stale-selection cancellation
- [x] 72 Python and 10 Node tests; production frontend build (existing ECharts size warning)
- [x] Read-only actual-source short load: 28 requests/12 workers; p95 1,103 ms; old hour outside latest-N visible and source pages do not overlap
- [x] Four browser tabs: historical Compressor, historical Vacuum, Database, Analytics (two Compressor machines plus Vacuum on separate family charts); source/module selections and results remain independent
- [x] Chart slots measured at 340 px during and after load; selection changes clear pending/results; 390 px mobile has no document overflow and readable graphs
- [x] Alerts/Maintenance/expanded Logs show no graph action; Delete stays left and Start/Record share the right row (verified equal top coordinates)
- [x] PROJECT/SOT/UX/code map/archive notes updated; local API restarted and local static assets rebuilt; no source telemetry writes or production deployment

Details and sampling limitations: `docs/HISTORY_BROWSER.md`. Browser/load artifacts: `artifacts/history-browser-qa/`. This replaces the earlier evidence-graph UI scope below; the detector integration/report data are retained.

## Contributor presentation — 2026-10-01

- [x] Same stored >= threshold/global flag; no new per-feature persistence or hidden global scores
- [x] Panel-only names, signed-z/actual/baseline tooltip and all-contributor evidence table; missing vector stays unknown
- [x] 69 Python tests (3.16 s), 17 Node tests and final temp-output frontend build pass (existing ECharts large-chunk warning remains)
- [x] Actual MX080 75-window fixture reviewed; 40-point time filter and Desktop/mobile attribution verified, crowded labels/tooltip overflow repaired
- [x] Both systems' SOT/Project/Roadmap/UX/Agents/code maps updated; documented startup/settling proposal
- [ ] Execute multi-start validation; no state gate/Profile/threshold/retrain/DB/Server change in this task

Evidence/screenshots: sibling Operation `deployment/DURABLE_DETECTOR_LOCAL_QA.md` and `notebooks/outputs/durable_detector_qa_v1/contributor-*.png`. Builds do not replace Dashboard public bundle; ordinary Vite HMR updates the local QA entry.

## Local durable detector integration — 2026-10-01

- [x] Added authenticated evidence review from Alerts, Work Orders and immutable Service Log report context; source-time/module/Profile context is explicit
- [x] Added idempotent Episode/evidence bridge in Operation; default opt-in disabled/shadow, tested in dedicated localhost QA schema only
- [x] Dashboard Python 69/69 and Node/chart 8/8; ten concurrent fixture-auth requests return 200 without writes
- [x] Actual archived MX080/M6 charts reviewed at desktop/390px; null gaps, baseline colours, shared zoom and 40-point time filter verified
- [x] Explained first global red band: dominant TempLo vs narrow four-day candidate, not pressure fault proof; no threshold/Profile change
- [x] Fleet Trend now uses source_recorded_at; legacy unknown source times are not invented/backfilled
- [x] Updated SOT/Project/Roadmap/UX/code map/data flow and separate future Server runbook; no Git push or target Server access
- [ ] Validate normal startup/settling across multiple runs and expose panel-specific contributors before claiming specificity
- [ ] Real account login → ACK → work → Service Log UAT, real Active Profile parity, sustained fleet load and Server acceptance
- [ ] Reconcile legacy Health overview and manual report retention intervals before live enablement/purge

This checkpoint supersedes the older pending local bridge/graph items below, not their Server acceptance gates. Local replay uses an INSUFFICIENT_DATA candidate, not a newly approved Active Profile.

## Owner-requested rollback — 2026-10-01

- [x] Removed only the last-turn custom UI updater/version endpoint/reload launcher/build watcher and their seven new helper/test/doc files
- [x] Restored Vite config/package scripts/document caching; preserved original data refresh and earlier incident-date/snapshot work
- [x] Stopped the two agent-started local watcher sessions; did not stop unrelated services or touch production
- [x] Python 63/63 (2.99 s), existing Node 5/5, frontend build pass; served `index-Dha7kDUB.js` retains incident fields/snapshot and has no updater
- [x] Ordinary local API :5001/page return 200; removed version endpoint returns 404; original API-only cache policy restored; Vite/package diffs are empty and custom watcher processes are absent
- [x] Retained the pre-update public backup in temporary storage; no Git reset, DB/profile/model or Server change

Removed the three generated updater JS bundles only; other pre-existing assets were retained. Pre-update public backup: `C:\Users\Book\AppData\Local\Temp\dashboard-public-before-live-update-772b94dd35e64c24a3d8df301dec8bd9`. Ordinary local API/Vite services replace the previous custom watcher sessions; the unrelated Operation :8000/:5174 processes remain running. Existing development ephemeral-key policy may require login again. Browser workflow UAT and production deployment are not claimed.

## รอบ 2026-10-01 — Incident report evidence

- [x] อ่าน source contract/สองระบบ; daily reporting อยู่ใน Dashboard
- [x] เพิ่ม occurrence start/end/timezone/precision/origin ใน Work Order และ frozen incident_context_json ใน linked Service Log
- [x] ตรวจ machine/module, time ordering, unknown onset, timezone edits และ origin spoofing; label/cause ยัง UNREVIEWED/UNKNOWN
- [x] Schema/migration localhost เรียกซ้ำ 2 ครั้ง; ไม่เปลี่ยน source หรือ Work/Log rows
- [x] Python 63/63 tests และ production frontend build ผ่าน (temporary output ไม่ทับ existing public changes)
- [x] Final QA ขยาย original-report disclosure ให้มีใน Maintenance และ Data → Logs พร้อม origin/precision; snapshot เก็บผู้สร้าง/ผู้รับงาน; rerun 63 tests ผ่าน (2.25 s), frontend build ผ่าน
- [x] อัปเดต Project/SOT/Roadmap/UX/code map/data flow และคู่มือ
- [ ] Browser workflow UAT, new 1m Episode→PM Alert mapping, integrated graphs และ Server acceptance

## รอบ 2026-09-30 — Maintenance / Logs / Trend

- [x] อ่าน source contract และ MySQL metadata localhost ก่อนแก้; ไม่เขียน source telemetry
- [x] Warning ACK ไม่เปิดใบงาน, Critical ACK เปิดใบงานเพียงครั้งเดียว
- [x] แยกรายการอะไหล่/ราคา, แก้ไข Log โดย Admin, ลบ Log/active Work Order พร้อม audit snapshot ใน MySQL
- [x] ลบ Log ไม่คืน Work Order ไป Assigned Work; ลบ IN_PROGRESS order คืนสถานะโมดูลตาม diagnostic ล่าสุด
- [x] เพิ่ม schema/migration ทั้ง `app/db.py` และ `schema.sql`
- [x] Fleet Trend 7 วันจาก diagnostic snapshots; ไม่เติมข้อมูลวันว่าง
- [x] Query จริงบน MySQL localhost ผ่าน; Python tests 43/43 และ frontend production build ผ่าน
- [ ] Browser visual/UAT, staging load/permissions และ event-time freshness ก่อน Production

## รอบ 2026-09-23 — Normal-port localhost MX777 integration rehearsal

- [x] ตรวจ config ว่า MySQL/ports ปกติชี้ localhost; append เฉพาะ 777 ลง `ht9046mx_iot.ht9046mx_readings` (43,212 timestamps) ตามคำสั่งเจ้าของโครงการ; ไม่แตะ Server
- [x] Calibration ผ่าน API ปกติได้ 8 test-only ACTIVE_FROZEN profiles, inference เขียน score 212/โมดูล และ Dashboard อ่านได้
- [x] Accelerated 12 × 5-minute stream ส่งถึง Dashboard 12/12 ช่วง; 40 parallel GET / 10 workers ไม่มี HTTP error
- [x] Dashboard tests 41/41, OP tests 19/19 และ frontend production builds สองระบบผ่าน
- [x] แก้การเปิด OP web :5173 ให้ใช้ Vite `--port`; หน้า Calibration เห็น MX777 8/8 Active และ 43,212 rows
- [ ] ตรวจการคลิกดู Profile/กราฟและหลายแท็บจนจบ; browser client timeout หลังเลือก MX777, Dashboard ยังอยู่หน้า login
- [ ] แก้กราฟ 7 วัน/เดือนที่ถูก limit 2,000 timestamps และ 3,000 metric rows; ทำ downsampling/pagination แบบ event-time
- [ ] แก้ Fleet Trend freshness ให้ยึด source event time และแก้ runtime model provenance (`max(abs(relative_z))` ไม่ใช่ ARX-Ridge artifact)
- [ ] เพิ่ม test-data provenance/ป้ายแยกข้อมูลสังเคราะห์ 777 ใน Dashboard/OP UI; ปัจจุบันรุ่น `ARX-Ridge__seed_13` ไม่ถูกระบุว่า mock
- [ ] ยืนยัน production profile/model, timezone, rollback, security/TLS, sustained load และ staging ก่อน deploy


ใช้ checklist นี้กับทุกการเปลี่ยนแปลงหลังจาก 2026-09-16

## ก่อนแก้

- [ ] อ่าน `SOT.md` และไฟล์ใน `graft/` ที่เกี่ยวข้อง
- [ ] ระบุ source family และ machine/module grain
- [ ] ยืนยันว่าไม่ต้องเขียน source telemetry หรือเปิดเผย secret

## ระหว่างแก้

- [ ] รักษา null/empty/error states
- [ ] ไม่ผสมหน่วยหรือความหมายของ Compressor/Vacuum
- [ ] ถ้าเปลี่ยน formula/threshold/contract ให้แก้ test และ `UX.md`
- [ ] ถ้าเปลี่ยน schema ให้แก้ทั้ง `app/db.py` และ `schema.sql`
- [ ] ถ้าเปลี่ยน frontend ให้แก้ source ใน `frontend/src/` ไม่แก้ generated asset โดยตรง

## ก่อนส่งมอบ

- [x] รอบ 2026-09-16: Python compile ผ่าน
- [x] รอบ 2026-09-16: frontend production build ผ่าน
- [x] รอบ 2026-09-16: tests ทั้งหมดผ่านหลังเพิ่ม regression tests
- [x] รอบ 2026-09-16: visual QA desktop/mobile ด้วย local synthetic fixture
- [ ] อัปเดต `PROJECT.md` checklist
- [ ] อัปเดต `SOT.md` verification และ `ROADMAP.md` ถ้า phase เปลี่ยน
- [ ] ระบุสิ่งที่ยังไม่ได้ deploy/verify อย่างตรงไปตรงมา

## รอบ 2026-09-23 — Maintenance Assigned Work

- [x] ตรวจ source ของหน้า Maintenance และ fields จาก work order API
- [x] ปรับเฉพาะ frontend และคง action เดิมของ work order
- [x] อัปเดต `PROJECT.md`, `SOT.md`, `UX.md` และ `graft/CODE_MAP.md`
- [x] Production frontend build ผ่าน
- [x] Python tests 15/15 ผ่าน (ปรับ mock test ให้รองรับ query ของ Clear Alerts ที่มีอยู่แล้ว)
- [x] Visual QA desktop/mobile ผ่านด้วย synthetic work orders; viewport 390px ไม่มีแนวนอนล้น

## รอบ 2026-09-23 — Local preview

- [x] เพิ่ม `scripts/_maintenance_preview.py` สำหรับเปิดหน้าที่ build แล้วด้วย API ข้อมูลจำลอง
- [x] เปิดหน้า Maintenance ให้ดูใน in-app browser; ไม่เชื่อมต่อฐานข้อมูลจริง

## รอบ 2026-09-23 — Working repository และ local MySQL

- [x] ตรวจ Git status และเก็บ backup ของไฟล์เดิมก่อนซิงก์เข้า `Compressor_and_VacuumPump`
- [x] ซิงก์โค้ดล่าสุดโดยคง `.env` ของโฟลเดอร์ปลายทางและไม่แตะ nested project เดิม
- [x] ตรวจ schema, columns และจำนวนแถวของ Vacuum, Compressor, Health Score แบบ read-only
- [x] แก้ test mapping ให้ไม่ขึ้นกับ scale ใน `.env`; Python tests 15/15 ผ่าน
- [x] Build frontend ผ่านจาก repository ใหม่
- [x] เปิดแอปที่ `127.0.0.1:5001` และตรวจ source status/API กับ MySQL local
- [ ] ตรวจ UX กับผู้ใช้งานและทดสอบบน staging/production ก่อน deploy

## รอบ 2026-09-23 — Alert → Work Order, Admin Log, Threshold, Language

- [x] เพิ่ม schema/migration สำหรับ `pm_work_orders.source_alert_id` (unique + FK)
- [x] Acknowledge ทำ transaction และสร้าง Work Order ไม่ซ้ำ พร้อม assign ช่าง
- [x] Admin-only DELETE Maintenance Log และปุ่มถังขยะพร้อม confirmation
- [x] แยก Advanced Threshold ของ Vacuum ออกจาก Compressor ML; เลือก module และเปิด/ปิด override ได้
- [x] เพิ่ม ENG/TH ใต้ Color Theme, ฟอนต์ไทย และคำแปลหน้าหลัก
- [x] เอา threshold ตัวอย่างออกจาก Compressor trend/card และแปลข้อความหน้า Detail เพิ่ม
- [x] ย้าย WebSocket token ออกจาก URL
- [x] Python tests 21/21 ผ่าน; frontend build ผ่าน; `git diff --check` ผ่าน
- [x] ตรวจ local schema migration, API role 403/404, WebSocket handshake และ latency เบื้องต้น
- [x] Visual QA desktop: Alert link, Assigned Work, Log trash, threshold ทั้งสอง module และภาษา TH
- [x] Visual QA mobile 390px ของ Maintenance และ Admin ภาษา TH; ไม่ล้นแนวนอน
- [ ] UAT กับผู้ใช้งานและตรวจ staging ก่อน deploy

## รอบ 2026-09-23 — Cross-system correctness และ multi-tab performance

- [x] ให้ OPERATION เป็นเจ้าของ Compressor Alert และ Dashboard เป็นเจ้าของ Vacuum Alert
- [x] ลบ Mark complete; API ไม่รับ DONE โดยตรง และ linked Service Log ปิด Work Order ใน transaction เดียว
- [x] ลบ Log ใบสุดท้ายของงานที่ปิดแล้วจะเปิด Work Order กลับใน transaction เดียว
- [x] Broadcast หนึ่งครั้งต่อ telemetry cycle; ข้ามการดึงซ้ำใน hidden tab และ coalesce source history query ข้ามแท็บ
- [x] เพิ่ม GZip สำหรับ JSON ขนาดใหญ่, mock multi-tab แบบ read-only และ test batch/cache/WebSocket
- [x] รอบล่าสุด Dashboard tests 35/35, OPERATION tests 17/17, frontend build ผ่าน; local mock 8/16 แท็บรวมกราฟและ gzip ไม่มี request error (รายละเอียดใน `SOT.md`)
- [x] กัน token signing ด้วย key ว่าง/ค่าเริ่มต้น; production mode ต้องมี strong `SECRET_KEY`, local ใช้ ephemeral key
- [x] ปิด magnitude-based auto scale ของ Compressor; บังคับ explicit scale และเพิ่ม regression test
- [x] Startup bootstrap ไม่ reset password/role/active ของบัญชีเดิม และ production mode ไม่รับ default/weak passwords
- [x] Service Log ไม่ลบสถานะ fault ของโมดูล/เครื่องโดยอัตโนมัติ
- [ ] ตรวจ query plan/index, full-history chart window และ latency บน staging ที่ใช้ schema/index จริง
- [ ] แยก ingestion/poller ให้มีเจ้าของเดียวและใช้ shared pub/sub ก่อนเพิ่มหลาย Uvicorn worker
- [ ] ยืนยัน source timezone, calibration/profile release, alert budget และ rollback ก่อนเปิด Compressor alert production

## รอบ 2026-09-23 — HT9046MX-777 isolated mock

- [x] สร้าง source/analytics/dashboard mock schemas เฉพาะ MySQL เครื่องนี้ และทดสอบหน้าเว็บสองระบบพร้อมกัน
- [x] ยืนยัน `Awaiting ML Score` → M1/M2 มี Health Score จาก OPERATION mock scoring; แสดง provenance `MOCK_ONLY` และเวลาผล
- [x] ให้ explicit ML condition คุม status และ tie-break ผล Health Score ที่ timestamp ซ้ำแบบ deterministic; Dashboard tests 36/36 ผ่าน
- [x] รัน local read-only parallel requests ทั้งสองระบบ ไม่มี request error (รายละเอียดใน `SOT.md`)
- [ ] ยังต้องมี approved `ACTIVE_FROZEN` release/profile, staging replay และ sustained multi-worker test ก่อน Production

## รอบ 2026-09-23 — Overview priority และสถานะเดิม

- [x] Compressor heatmap M1–M8 และ Vacuum module list เรียงปัญหาก่อน; No Signal แสดงแยก
- [x] เพิ่ม Top deteriorating จาก Health Score ที่มี baseline 24–48 ชั่วโมงจริง; ไม่มี baseline ไม่สร้าง trend ปลอม
- [x] คง Active alerts/Handler status distribution ตามธีมเดิม และไม่เพิ่มตัวกรองมุมขวาบน
- [x] เอา Monitoring/Watch ออกจากชื่อสถานะที่ผู้ใช้เลือกหรือเห็น; migration แปลง Monitoring เก่าเป็น Good ก่อนแก้ ENUM; Critical severity แสดง Repair now ในหน้าการแจ้งเตือน
- [x] สี Vibration ของ Vacuum Warning เป็น amber ให้ตรง badge
- [x] Linked Service Log นำ Repairing กลับ Good แบบ transaction และให้ข้อมูล ML/กฎ Vacuum ใหม่ประเมินต่อ; เพิ่ม regression tests
- [x] Python tests 38/38, frontend build, diff check; mock metadata startup/migration ตอบ health 200; visual QA local mock ที่ 1280px/390px และกด heatmap M2 สำเร็จ
- [ ] ยืนยันข้อมูลหลายเครื่อง/หลาย severity กับ staging รวมทั้ง query plan ของ baseline ก่อน production

## รอบ 2026-09-23 — Fleet trend และ Overview work queue

- [x] แยก connectivity No Signal ออกจาก Handler health distribution ไม่ให้นับซ้ำ
- [x] สร้าง trend จาก diagnostic snapshots จริงโดยไม่เติมข้อมูลช่วงว่าง; query มีขอบเขต, index, TTL และ lock กันหลายแท็บ
- [x] วาง trend ซ้าย/status ขวา, Work Orders ท้ายหน้าและคลิก Maintenance ได้
- [x] จำกัด Compressor/Vacuum preview อย่างละ 5 เครื่อง; ตัด Wi-Fi glyph ออกจาก Overview
- [x] เพิ่ม test สำหรับ 24h/1m/null/invalid range; Python tests 41/41 ผ่าน, frontend build ผ่าน
- [x] ทดสอบ query บน local mock MySQL และกดเลือกเดือน/ไป Maintenance ผ่าน browser synthetic preview
- [x] Browser preview 6 เครื่องยืนยัน Compressor/Vacuum แสดง 5/6, desktop 1366px และ mobile 390px ไม่ล้นแนวนอน
- [x] เรียก trend พร้อมกัน 16 ครั้งบน mock local ไม่มี error; ปิด server และแท็บพรีวิวที่เปิดเองหลังตรวจ
- [ ] ตรวจ query plan, p95 และ coverage บน staging ที่มีประวัติ 1 เดือนจริง; ทดสอบหลายแท็บและ accessibility ก่อน production

## รอบ 2026-09-23 — ปรับสัดส่วนการ์ด Overview

- [x] Work Orders กว้างตรงคอลัมน์ Compressor บน desktop, เต็มคอลัมน์บน mobile; เอา blue accent ออกจากกรอบและรายการ
- [x] Compressor ใช้ความสูงการ์ดเต็มขึ้นและแสดง tiles สีสถานะอ่อนพร้อมป้าย M1–M8 โดยไม่เปลี่ยนข้อมูลหรือ action
- [x] Python tests 41/41, production frontend build, diff check และ visual QA Light/Dark บน desktop 1366px/mobile 390px ผ่านด้วย synthetic preview

## รอบ 2026-09-23 — Compressor header และ fault-only highlight

- [x] คืนหัว M1–M8 แถวเดียวและเอาป้าย M ซ้ำจากทุกช่องออก
- [x] เอากรอบ/พื้นของ Normal, Warning และช่องว่างออก; แสดงพื้นแดงอ่อนเฉพาะ Repair now พร้อมจุดสีและ aria label เดิม
- [x] Python tests 41/41 และ production frontend build ผ่าน; browser preview ธีม Light desktop 1366px/mobile 390px และ Dark mobile 390px ผ่าน

## รอบ 2026-09-24 — `_v1` repository handoff

- [x] เพิ่ม architecture/schema/data-flow/deployment guide และ cross-repository contract
- [x] ยืนยัน `.env`, secrets, raw telemetry, local DB, dependencies และ cache ไม่อยู่ใน release scope
- [x] Python tests 41/41 และ frontend production build ผ่าน; build มีเพียงคำเตือน ECharts chunk 603.61 kB
- [x] ตรวจ staged-file/secret/large-file inventory ก่อน push; มีเพียง `.env.example` ที่เป็น placeholder และไม่มี raw telemetry/credential/ไฟล์เกิน GitHub limit

## รอบ 2026-09-24 — Server input and secret handoff

- [x] เพิ่ม Dashboard Server input checklist และอ้างอิง combined checklist ของทั้งสองระบบ
- [x] เพิ่ม ignore rule สำหรับ local secret Markdown
- [x] ไม่เก็บ credential จริงใน Git; generated values ยังไม่ถือว่าเป็น account จริงจนกว่า DBA จะ apply

## รอบ 2026-09-30 — คืน Status ใน Assigned Work

- [x] เปลี่ยนป้ายมุมขวาบนจาก Priority เป็นสถานะ Open/In progress ในโค้ดชุดที่ Vite ใช้งานอยู่
- [x] รักษาการเรียงงาน เวลา Alert/เปิดงาน และ action เดิม; อัปเดต `PROJECT.md`, `SOT.md`, `UX.md`
- [x] Python tests ผ่าน 43/43, frontend production build ผ่าน และ Vite พอร์ต 5173 ส่งโค้ด Status ใหม่ (2026-09-30)

## รอบ 2026-09-30 — ปรับ Maintenance และ Overview

- [x] วาง Delete work order ชิดซ้ายโดยคงสิทธิ์ Admin และ callback เดิม; คืนกลุ่ม Start work / Record service log ทางขวาเมื่อผู้ใช้ทักท้วงตำแหน่ง
- [x] เอาไอคอนในช่อง Compressor modules ออกโดยคงสี สถานะ tooltip และ aria label; เปลี่ยนชื่อ Vacuum Pump modules
- [x] จัดระยะขอบกรอบ Maintenance Logs และ Data → Logs ให้ตรงกับแผงอื่นและรองรับจอแคบ
- [x] อัปเดต `PROJECT.md`, `SOT.md` และ `UX.md`
- [x] Python tests 43/43, frontend production build และ `git diff --check` ผ่าน
- [x] ตรวจ local synthetic preview ที่ desktop 1280px และ mobile 390px: กรอบ Logs ตรงแนวและไม่มี page overflow
- [x] ตรวจปุ่มหลังคืนตำแหน่งด้วย preview บทบาท Admin และ User ที่ desktop 1280px: Start work / Record service log อยู่กลุ่มขวา; User ไม่เห็น Delete

## รอบ 2026-09-30 — Sensor Snapshot มาตรฐาน

- [x] แถวค่าด้านล่างของ Handler Detail แสดงเฉพาะ Accel X/Y/Z เฉพาะ Vacuum Pump โดยไม่ซ้ำกับการ์ดหลัก
- [x] แสดง No data เมื่อไม่มีค่าจริง; Compressor คืน Busy/Status/SV
- [x] อัปเดต `PROJECT.md`, `SOT.md` และ `UX.md`
- [ ] รัน Python tests, frontend production build และตรวจ detail หลายโมดูลด้วยข้อมูลจำลอง


## รอบ 2026-09-30 — Source-specific Database / Analytics
- [x] เริ่มต้นว่างและ explicit load ทั้งสองหน้า
- [x] ตรวจ columns/indexes จริงแบบ read-only และ EXPLAIN
- [x] source-specific history columns, strict time bounds และ timezone conversion
- [x] ยกเลิก stale request, bounded concurrency, cache wide rows แยก machine, chart option memoization
- [x] Database pagination 100 แถว; Analytics legend/zoom/empty/null/responsive
- [x] ตรวจ synthetic UI: source switch ระหว่างโหลด, สองแท็บต่าง source, Snapshot Vacuum และ Compressor
- [x] Python tests 47 ผ่าน; frontend build ผ่าน (ECharts chunk warning เดิม)
- [x] อัปเดต PROJECT/SOT/UX; phase ไม่เปลี่ยน
- [ ] production load test (อยู่นอก scope; ไม่ deploy production)

- [x] ช่องค้นหาเครื่องและเลื่อนไปกราฟหลังโหลด ตรวจ UI รอบสุดท้าย; local API health=ok ที่ port 5001 หลังโหลดโค้ดใหม่


## 2026-09-30 — Multi-tab chart load QA
- [x] ทดสอบ UI ที่ local port 5001 6 แท็บ / 6 เครื่อง / 24 โมดูล พร้อมข้อมูลจาก configured DB; paired sample counts ตรงกัน
- [x] บันทึก baseline/final API wait และ canvas timing ใน artifacts/LOAD_TEST.md
- [x] ตรวจ Detail 6 แท็บและ lazy render หลัง scroll
- [x] แก้ lock scope, bounded history pool, compact batch API, repeated grouping/options และ stale-tab token clearing
- [x] เพิ่ม tests สำหรับ compact response, batch mapping, independent source/state locks และ connection/cursor ownership
- [x] Python tests 51 ผ่าน; production build ผ่าน; local health ok; docs อัปเดต; phase ไม่เปลี่ยน

## 2026-09-30 — Handler default / shared graph data
- [x] ตรวจ default 6h ว่างบนหน้าเว็บจริงและ source timestamps ทั้ง Compressor/Vacuum
- [x] Default latest available + actual date range + loading/error/empty UI
- [x] Compact request เดียวสำหรับ primary/correlation/relationship, paired Pearson/null/cap tests
- [x] Request identity/abort ป้องกันข้อมูลคนละโมดูล; identical polls ไม่วาดใหม่
- [x] Node tests 5, Python tests 51, frontend build ผ่าน
- [x] Browser Handler 6 แท็บ / สอง source / เปลี่ยน module+range / identical-poll options stable
- [x] Browser Database latest available + Analytics ร่วมกับ Handler tabs; recent empty/actual available และ source-specific columns
- [x] บันทึก aggregate Handler QA ใน artifacts/load-handler-6-tabs.json และ LOAD_TEST.md; 1.40s mean / 2.18s max ใน local measured run
- [ ] Mobile follow-up (viewport override ไม่เปลี่ยน observed width; ไม่อ้างว่า verified)
- [x] PROJECT/SOT อัปเดต; phase ไม่เปลี่ยน; source read-only

## 2026-09-30 — Remove Handler telemetry summary
- [x] เอากรอบ samples / load timing / date range / limit caption ออกจาก Handler ทุก source
- [x] คงข้อความ loading/error/empty และการโหลดกราฟตามเดิม
- [x] อัปเดต PROJECT/SOT; phase ไม่เปลี่ยน
- [x] Python tests 51 ผ่าน และ production frontend build ผ่าน
- [x] Browser ตรวจ Compressor/Vacuum: ไม่มีกรอบสรุป กราฟ 6/4 แผงยังโหลดได้

## 2026-10-01 — Compressor matrix / stable Handler graph space
- [x] Compressor subtitle English `Machines needing attention first · 5 / 24` ตามจำนวนจริง
- [x] Matrix legend/strong status edge/dashed Handler no-signal edge; tooltip real metadata, keyboard focus/Escape, selected-module click-through
- [x] ไม่มี per-cell telemetry request, fake anomaly score, evidence หรือ abnormal duration
- [x] เอา Loading chart data ออกทั้ง Compressor/Vacuum; จองพื้นที่ trend/correlation/relationship ด้วย chart-size placeholder และเก็บ empty/error ใน featured chart
- [x] Browser Compressor pending/populated 8 panel positions/heights ตรงกัน; Vacuum populated/empty/populated 4 panels ตรงกัน; no loading text ทั้งสอง source
- [x] Python 51 และ Node 5 tests ผ่าน; production build ผ่าน (existing chunk warning)
- [x] PROJECT/SOT อัปเดต; phase ไม่เปลี่ยน; source contracts/read-only คงเดิม
