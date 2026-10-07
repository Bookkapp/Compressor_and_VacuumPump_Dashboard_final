> **Final private Server release — 6 Oct 2026:** On “Set up ระบบนี้ให้หน่อย”, read `HANDOFF_SERVER.md` first. Owner explicitly authorized real deploy secrets/config in this PRIVATE `_final` repository. This supersedes older secret-exclusion instructions for this release. Server .69 Dashboard / .73 Operation; no Server installation or Profile approval has occurred in packaging.

# Project — ADI Predictive Maintenance Dashboard

## Compressor Online window — 2026-10-06

Owner requested Compressor Handler signal stay Online through 30 minutes since the last real reading, replacing the former 20–30 minute No signal interval. More than 30 minutes remains Offline; missing timestamps remain Offline and Vacuum policy is unchanged. Shared connection state keeps Handler, summaries and overview consistent. Boundary tests updated; validation and installed API acceptance recorded in deployment/SERVER_ACCEPTANCE.md.

Actual Handler IDs are canonical `HT9046MX-...`, so Compressor cadence now uses stored module source membership in list/summary APIs rather than relying on a `compressor:` ID prefix. Mixed Handlers containing Compressor modules use that Handler cadence; pure Vacuum retains its own policy.

## Server .69 portable setup — 2026-10-06

Owner requested setup, then an alternative without elevation. Dashboard/MySQL/nginx now run under a hidden user-task supervisor; verified separate SELECT-only accounts read Compressor and Vacuum. Owner supplied the Vacuum username; configured its actual `device_id` column. Discovered 21 Handlers/162 modules (160 Compressor, two Vacuum). Both logins, proxy WebSocket, concurrent API histories and API restart recovery passed. Added Windows timezone/development dependencies, metadata backup and setup/check scripts. 70 unittest / 82 pytest tests and production build passed. Browser/remote LAN verification and boot-before-login remain pending; Operation was not changed. See [actual Server acceptance](deployment/SERVER_ACCEPTANCE.md).

Historical page/chart APIs also return distinct real-source fields for both families. Vacuum mapping regression now verifies both configurable identity column names independently of Server `.env`; final suites pass with the deployed configuration.

## Log page scrolling & viewport height fix — 2026-10-06

- Fixed unnatural jitter / bounce and sticky sidebar detachment on short pages (especially Data Logs `#logs`): removed unzoomed `body` from `min-height: calc(100vh / var(--dashboard-scale))` in `frontend/src/styles.css` (keeping it scoped strictly to `.app-shell, .login-shell`), eliminating a 79px phantom scroll overflow under 90% dashboard zoom.
- Added automatic scroll reset (`window.scrollTo(0, 0)`) on view navigation in `frontend/src/main.jsx`.
- Verified via headless browser CDP: `htmlScrollHeight == htmlClientHeight`, sidebar stays pinned at `top: 0`, and no phantom scrollbar appears.

## Numbering reset & Vacuum Pump tooltip — 2026-10-06

- Admin-only capability to clear/reset Work Order # and Alert # auto-increment sequence numbers back to 1 via /api/admin/numbering and /api/admin/numbering/reset. Work orders are archived in pm_deletion_audit, while service history in pm_maintenance_logs remains intact.
- Vacuum Pump module list on Overview dashboard now provides interactive diagnostic tooltips matching Compressor modules, showing module condition, awaiting ML score status, last sensor reading, and handler connection state.
- 82 Python tests passing and production frontend build verified.

## Dashboard display 90% — 2026-10-06

Owner chose a 90% desktop display with the existing component arrangement instead of a scrollable sidebar. Root scaling, viewport-height compensation and portal coordinates are updated. Actual 1280 x 720/browser-100% check: Logout fully visible, navigation has no scrollbar, document has no horizontal overflow; tooltip remains in the viewport. 65 Python tests and final production build pass. Evidence: docs/DASHBOARD_90_PERCENT_20261006.md and artifacts/dashboard-90-percent-qa/overview.png.


## Offline status — 2026-10-06

Owner-requested Offline after more than 30 minutes without signal now projects into device/module status, summary and filters. Earlier transient loss is NO_SIGNAL. Compressor Overview cells are grey with solid borders and a matching Offline legend; caption counts all Compressor machines. 65 Python tests, final build and actual local web checks pass. Details and screenshots: docs/OFFLINE_STATUS_20261006.md. Local API restart only; source data and Profile/Active policies unchanged. Earlier connectivity descriptions below are historical.


## 2 October — Historical page card alignment

Historical Charts, Database and Analytics now share the Maintenance/Alerts/Logs panel frame, 17 px headings and page insets (28 px desktop, 12 px mobile). Database filters form aligned machine/module, date/time and dataset/action rows; narrower screens stack controls to keep date values readable. Local desktop/900 px/390 px browser checks, 72 Python tests and production frontend build pass. Evidence: `artifacts/history-layout-qa/`. Project phase is unchanged.

## 2 October — Historical browsing and evidence graph removal

Removed detector evidence graph entry points/dialog/API from Alerts, Maintenance and Logs. Added Data → Historical Charts and replaced Database/Analytics with machine-first mapped-module/date-time selection and explicit loading. Historical SQL filters source/time before limiting; raw pages and bounded graph coverage are separate. Existing incident reports, work actions, source separation, null semantics and Handler graphs remain. Local QA, API contracts and sampling limits: `docs/HISTORY_BROWSER.md`. This current scope supersedes the earlier evidence-graph UI checkpoint below; project phase is unchanged.

**Contributor task completed — 1 Oct:** Added per-panel contributor bands, signed-z/threshold/actual-baseline tooltip, accessible summary and all-contributor evidence column. Global result remains on score graph. Missing z is not invented; UI attribution is not root cause or per-feature persistence. Next: execute multi-start/regime validation and real workflow/Server UAT. No runtime detector changes.

**1 Oct integration:** Evidence graph/API from Alert/Assign Work/Service Log and source-time trend implemented/tested locally. Latest69 Python/8 Node tests; actual archived replay in dedicated QA metadata, no real report creation. Next: contributor-aware highlights/startup specificity, real login-to-work UAT and eventual Server acceptance. See `docs/DETECTOR_EVIDENCE_INTEGRATION.md`; no custom static updater reintroduced.

อัปเดตล่าสุด: 2026-10-02

## Owner-requested rollback — 2026-10-01

Removed the last-turn custom static-page updater, version API, local reload launcher and build watcher from this deployable Dashboard source. Original Vite development HMR and existing data refresh remain; incident dates/report snapshots from the earlier request remain. No Server, detector, Profile or source-data change. Tests/build and local runtime checks are recorded in `graft/CHANGE_CHECKLIST.md`.

## รอบ 2026-10-01 — Dashboard-owned incident reporting

- [x] Manual Assign Work เพิ่ม reported occurrence interval/Asia-Bangkok/precision และ origin; ไม่บังคับทราบ onset
- [x] Service Log เก็บ original report snapshot ใน transaction เดียวกับ DONE และแสดงรายละเอียดขยายดูได้
- [x] Backend ตรวจ device/module, ไม่ให้ client ปลอม report origin/PM Alert และยังคง role policy เดิม
- [x] Local additive metadata migration ผ่านซ้ำ 2 ครั้ง; tests 63/63 และ temporary-output frontend build ผ่าน ไม่ทับ public ที่มี user changes
- [ ] Browser workflow UAT, integrated Episode/manual graph link และ production retention/Server acceptance; Operation รุ่น 1m ยังต้องเชื่อม live Alert bridge

คู่มือ: `docs/INCIDENT_REPORT_WORKFLOW.md`. ไม่เปลี่ยน Description/DONE เป็น fault label หรือ detector recovery และไม่มี retrain จาก Log รอบนี้

## รอบปัจจุบัน — Maintenance / Logs / Fleet Trend (2026-09-30)

- [x] Warning Alert รับทราบได้โดยไม่สร้าง Work Order; Critical เท่านั้นที่สร้างใบงานอัตโนมัติ
- [x] Assigned Work เรียงใบงานเก่าก่อน, แสดง status มุมขวาบนแทน priority, Admin มีปุ่มลบชิดซ้าย โดย Start work / Record service log อยู่ในกลุ่มเดิมทางขวาสำหรับทุกบทบาท
- [x] Service Log เพิ่มอะไหล่หลายรายการพร้อมจำนวน/ราคาต่อหน่วย; ยอดรวม = ค่าอะไหล่ + ค่าแรง/ค่าใช้จ่ายอื่น
- [x] Maintenance Logs แสดง Work Order ID และค่าใช้จ่ายรวม, Admin แก้ไข/ลบได้; ลบ Log ไม่เปิดใบงาน DONE ใหม่
- [x] Data → Logs มีรายละเอียดอะไหล่ ต้นทุนต่อรายการ และแบ่งหน้า
- [x] MySQL `pm_deletion_audit` เก็บผู้ลบ เวลา และ snapshot ก่อนลบ (ไม่มีหน้าจอ audit)
- [x] Compressor modules ใช้สีสถานะของช่องโดยไม่แสดงไอคอน และคงชื่อสถานะใน aria label/tooltip
- [x] เปลี่ยนหัวข้อ Overview เป็น Vacuum Pump modules และจัดระยะขอบกรอบ Maintenance Logs / Data → Logs ให้ตรงกับแผงอื่น
- [x] Sensor Snapshot แยก source: Vacuum Pump แถวล่างเฉพาะ Accel X/Y/Z; Compressor คืน Busy/Status/SV เดิม
- [x] Fleet Health Trend เหลือ 7 วันจาก `pm_diagnostic_snapshots`; วันไม่มี snapshot เป็นช่องว่างจริง
- [x] ทดสอบ migration/query กับ MySQL localhost และ Python tests 43/43 ผ่าน; frontend production build ผ่าน
- [ ] ตรวจ UX ผ่าน browser กับข้อมูลจริงและทดสอบ staging ก่อน deploy

สถานะทดสอบล่าสุด: ใช้ MySQL localhost schemas และ API ports ปกติของ OPERATION/Dashboard ทดสอบ HT9046MX-777 ด้วยข้อมูลสังเคราะห์ 30 วัน + 12 ช่วงเร่งเวลา, Active Profile 8 โมดูลเฉพาะ local, Health Score และ Dashboard API. ผลละเอียดและข้อจำกัด production อยู่ใน `SOT.md`; ยังไม่ได้ deploy หรือรับรอง browser UI/model accuracy.

## เป้าหมายที่กำลังทำ

ทำให้ Web Application บน `10.195.17.69` แสดงข้อมูลจาก MySQL แบบอ่านอย่างเดียว โดยแยกประสบการณ์ของ Compressor และ Vacuum Pump ตามข้อมูลจริงของแต่ละโมดูล รวมทั้งลดการแจ้งเตือนซ้ำและเตรียมรับผล Compressor ML จากตารางแยก

## ขอบเขตที่ตกลงแล้ว

- Handler เดียวสามารถมีทั้ง Vacuum Pump และ Compressor และสลับดูได้จากหน้าเดียว
- Compressor เลือกดู M1–M8 แยกกันได้
- Vacuum Pump ใช้ Vibration หน่วย `mm/s` และ Estimated Pressure ซึ่งคำนวณจาก `V = -0.0439P - 2.2098`
- Vacuum rule: Normal `-90..-70`, Warning `< -90` หรือ `(-70, -60]`, Critical `> -60 kPa`
- Compressor แสดง Health Score เฉพาะผลจาก MySQL contract จริงเท่านั้น
- Analytics เลือก source family, หลายเครื่อง, หลาย machine×module และหลาย metric ได้
- Alert เดิมซ้ำได้ไม่เกินวันละครั้ง; acknowledge ระงับ issue เดิม 7 วัน แต่ issue ใหม่หรือ severity สูงขึ้นยังแจ้ง
- ใช้สีและรูปแบบ Analog Devices เดิม และใช้พื้นที่หน้ารายละเอียดเต็มความกว้าง

## Checklist

- [x] แยกหน้า Detail ตาม Compressor/Vacuum
- [x] สลับ source ภายใน Handler เดียวกันได้
- [x] เอา Additional Sensor Metrics ออก
- [x] เพิ่ม Vacuum Estimated Pressure และ rule bands
- [x] แก้หน่วย Vibration เป็น `mm/s`
- [x] เตรียม read-only Compressor ML output contract
- [x] เพิ่ม alert daily dedupe และ acknowledge 7 วัน
- [x] ปรับ Analytics เป็น multi-select machine×module×metric
- [x] เพิ่ม automated tests สำหรับกฎสำคัญ
- [x] ปรับ Assigned Work ในหน้า Maintenance ให้ใช้ visual hierarchy และสี Analog Devices อย่างเรียบง่าย
- [x] เปิด local preview หน้า Maintenance ด้วยข้อมูลจำลองผ่าน `scripts/_maintenance_preview.py` (2026-09-23)
- [x] ย้ายฐานการพัฒนาไปที่ Git repository `C:\Users\Book\OneDrive\Documents\ChatGPT\Compressor_and_VacuumPump` และเก็บไฟล์ก่อนซิงก์ไว้แยกต่างหาก
- [x] ทดสอบแอปบน `127.0.0.1:5001` กับ MySQL ในเครื่อง: metadata, Vacuum, Compressor และ ML Health Score เชื่อมได้
- [x] Critical Acknowledge สร้าง Work Order ผูกกับ Alert แบบไม่ซ้ำและมอบหมายช่างโดยอัตโนมัติ; Warning Acknowledge อย่างเดียว
- [x] Admin ลบ Maintenance Log ได้จากไอคอนถังขยะในหน้า Maintenance
- [x] Advanced Threshold เปิด/ปิดเกณฑ์เพิ่มเติมต่อ Vacuum module ได้; Compressor ยังคงใช้ ML Health Score
- [x] เพิ่มตัวเลือกภาษา ENG/TH ใต้ Color Theme พร้อมฟอนต์ไทยและคำแปลหน้าหลัก
- [x] ลบเส้นเกณฑ์ Compressor ที่เป็นค่าตัวอย่างออกจากกราฟ และระบุว่าใช้ ML Health Score ประเมินสถานะ
- [x] ย้าย WebSocket token ออกจาก URL เพื่อไม่ให้ปรากฏใน request log
- [x] แยกเจ้าของ Alert: Dashboard สร้าง Vacuum Alert; OPERATION เป็นผู้สร้าง Compressor Alert
- [x] ปิด Work Order ได้ผ่าน Service Log ที่ผูกใบงานเท่านั้น พร้อม transaction เดียว
- [x] ลด query/broadcast ซ้ำจากหลายแท็บและเพิ่ม cache ระยะสั้นสำหรับกราฟ
- [x] เพิ่ม mock ทดสอบ 8/16 แท็บกับ API local และบันทึกข้อจำกัด production
- [x] สร้าง HT9046MX-777 ใน schema จำลองบน MySQL เครื่องนี้เท่านั้น; กดหน้า Calibration และ Dashboard จริงเพื่อตรวจ Health Score M1/M2 โดยไม่อนุมัติ Profile
- [x] ใช้ `condition` ที่ OPERATION ส่งมาเป็นสถานะ Compressor หลัก; แสดงเวลา ML และป้าย TEST DATA เมื่อผลมาจาก mock profile
- [x] หน้า Overview เพิ่ม Compressor M1–M8 heatmap, Vacuum attention list และ Top deteriorating โดยเรียงเครื่องมีปัญหาก่อน; ไม่เพิ่มตัวกรองมุมขวาบน
- [x] ใช้ชื่อสถานะ Good / Warning / Repair now / Repairing / Offline ทุกหน้าปฏิบัติการ โดยไม่เสนอ Monitoring หรือ Watch เป็นตัวเลือกใหม่
- [x] เมื่อปิดงานผ่าน Service Log โมดูลออกจาก Repairing เป็น Good ใน transaction เดียว; ข้อมูล ML/กฎ Vacuum รอบใหม่ยังประเมินให้กลับเป็น Warning/Repair now ได้
- [x] Overview วาง Fleet Health Trend ซ้ายและ Handler status distribution ขวา; กราฟอ่าน diagnostic snapshots จริงแบบ 7 วันและแสดง gap เมื่อไม่มีข้อมูล
- [x] ย้าย Open work orders ลงท้าย Overview, ปรับการ์ดตามสี ADI และคลิกไป Maintenance; จำกัดตัวอย่าง Compressor/Vacuum อย่างละ 5 เครื่องและเอาไอคอน Wi-Fi ออกจากรายการ
- [x] ปรับรอบ UX: Work Orders เป็นการ์ดกว้างเท่าคอลัมน์ Compressor ด้านบน ไม่มีแถบ/ไอคอนฟ้า; Compressor ใช้พื้นที่การ์ดเต็มขึ้น
- [x] คืนหัวตาราง Compressor M1–M8 แถวเดียว ตัดป้าย/กรอบซ้ำในช่อง; ปกติพื้นเขียวจางไม่มีจุด และมี icon/pale highlight เฉพาะช่องผิดปกติ
- [ ] ตรวจเชื่อมต่อ schema/table จริงใน staging
- [ ] User Acceptance Test กับผู้ใช้งานหน้างาน
- [ ] Deploy โดยผู้ดูแลระบบไปยัง `10.195.17.69`

## นอกขอบเขตของรอบนี้

- ไม่ deploy หรือ restart service production
- ไม่เขียนกลับ source telemetry tables
- ไม่ย้าย Compressor ML runtime เข้ามาใน Web App
- ไม่สร้าง Pressure เป็นค่าที่วัดจริง; ต้องเรียกว่า Estimated Pressure เสมอ

ทุกครั้งที่แก้โค้ด ให้ปรับ `SOT.md`, checklist นี้ และไฟล์ใน `graft/CHANGE_CHECKLIST.md` ให้ตรงกับสถานะจริง

## 2026-09-24 — v1 repository handoff

- [x] Documented source schemas, Dashboard metadata tables, OPERATION score/alert contract, data flows and deployment topology.
- [x] Kept `.env`, credentials, raw telemetry, local databases, dependencies and caches outside Git.
- [ ] Complete staging integration and production acceptance gates before deployment.
- [x] Added a Dashboard-specific Server input checklist and local-secret ignore rule; no production credential or database change was made.


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

## 2026-09-30 — Handler รายเครื่อง: ข้อมูลว่างและโหลดซ้ำ
- ตรวจพบค่าเริ่มต้น 6h ไม่ครอบคลุม source ที่เก่า: ตัวอย่าง HT9046MX-017 มี Compressor ล่าสุด 19 ก.ย. และ Vacuum ล่าสุด 16 ก.ย.; ทั้งสองคืน 0 ตัวอย่างใน 6h แม้ service ตอบเร็ว. รอบ QA เดิมตรวจ Detail เฉพาะ All จึงยังไม่ครอบคลุมข้อผิดพลาดนี้
- Handler เริ่มที่ “ข้อมูลล่าสุดที่มี” สูงสุด 2,000 ตัวอย่าง พร้อมจำนวน, เวลาโหลดและช่วงวันที่จริง; ช่วง 1h–7d ยังคงนับจากปัจจุบัน. แสดง loading/error/empty พร้อมทางเลือกดูข้อมูลล่าสุด
- ใช้ compact history request เดียว แยก signals ตาม source; Pearson/scatter ของ Handler ใช้ข้อมูลเดียวกับกราฟหลักและ actual data window โดยคงสูตร paired Pearson, minimum 3 pairs และ scatter cap 1,200. Analytics API เดิมยังรองรับ client อื่น
- ไม่กรองช่วงซ้ำโดยอิงวันสุดท้ายของข้อมูล; ป้องกันผลข้ามเครื่อง/โมดูล/ช่วงด้วย request key และ AbortController. Reuse rows/options เมื่อทุกค่าเท่ากัน แต่ตรวจพบค่าที่แก้แม้ timestamp เดิม; ปิด animation ของ trend/sparkline
- Node numerical/contract tests 5 ผ่าน, Python tests 51 ผ่าน และ frontend production build ผ่าน; รายงาน browser QA เพิ่มใน artifacts/LOAD_TEST.md. Source DB read-only และ phase ไม่เปลี่ยน
- Database เพิ่ม latest available range ตาม row limit เดิม (ยังเลือกเอง/กดโหลดเอง) และแยกยังไม่โหลดจากโหลดแล้วว่าง; Analytics เพิ่มคำแนะนำเมื่อทุก series ว่างในช่วงที่เลือก
- Browser QA: Handler default 6 เครื่องพร้อมกัน เฉลี่ย 1.40s สูงสุด 2.18s; Stage first render 148–264ms. สลับ 3 แท็บเป็น Vacuum ได้ 60 samples ใน 129–177ms; mixed Handler/Database/Analytics ไม่พบ error. กราฟ Stage ที่ข้อมูลไม่เปลี่ยนคง optionUpdates=1 ระหว่าง polls; รายละเอียด artifacts/LOAD_TEST.md และ load-handler-6-tabs.json
- ระหว่าง QA local backend port 5001 หยุดฟังโดยยังไม่ทราบสาเหตุ; เปิด local development service กลับและ health=ok. ไม่ใช่การยืนยัน production; browser viewport override ไม่เปลี่ยนขนาดจึงไม่อ้างผลมือถือรอบนี้

## 2026-09-30 — Remove Handler telemetry summary banner
- ตามภาพที่ผู้ใช้ระบุ เอากรอบจำนวน samples / Loaded in / ช่วงวันที่ / คำอธิบาย 2,000 samples ออกจาก Handler ทั้ง Compressor และ Vacuum Pump
- เมื่อโหลดสำเร็จ แท็บประเภทโมดูลต่อจาก topbar โดยไม่มีกรอบสรุป; loading/error/empty ใช้ข้อความเฉพาะสถานะ. การโหลดและกราฟยังใช้ข้อมูลชุดเดียวตามเดิม; phase ไม่เปลี่ยน

## 2026-10-01 — Compressor matrix clarity / stable Handler charts
- ขอบเขตตามผู้ใช้: ปรับเฉพาะ Compressor modules บน Overview และเอาข้อความ Loading chart data ออกจาก Handler ทั้งสอง source
- Compressor subtitle ใช้ข้อความ English `Machines needing attention first · 5 / 24` โดยจำนวนมาจาก preview/จำนวนเครื่องจริง. เพิ่ม legend, แถบสีเข้มด้านบน และขอบเส้นประสำหรับ Handler ที่ connection_state เป็น OFFLINE; สี cell ยังหมายถึงผลวินิจฉัยล่าสุด
- Tooltip ใช้ metadata ที่โหลดอยู่: module name, status, Health Score 0–100, เวลาผล ML, เวลา Sensor และ Handler signal; รองรับ focus/Escape และกดเข้า module เดิม. ไม่มี request เพิ่มต่อ cell และไม่มี score/evidence/duration ที่แต่งขึ้น
- Handler จองพื้นที่ trend/correlation/relationship panels ตั้งแต่กำลังโหลดด้วย placeholder ที่สูงเท่ากราฟ. ข้อความ empty/error เมื่อไม่มี history อยู่ใน featured chart; ไม่แสดง loading paragraph เหนือ module tabs. Background error ที่มี history ยังแสดงได้
- Python tests 51 และ Node telemetry tests 5 ผ่าน; production build ผ่าน (ECharts chunk warning เดิม). Browser ตรวจ Compressor pending → populated: ตำแหน่ง/ความสูงทั้ง 8 chart panels เท่าเดิม; Vacuum populated → empty 7d → populated: ทั้ง 4 panels เท่าเดิม. Vacuum response จบก่อน snapshot จึงไม่ได้วัด pending ของ Vacuum แยกในรอบนี้
- ตรวจ tooltip/focus/Escape และเปิด M5 SH1; ภาพผลอยู่ใน Codex visualizations และผล geometry ใน `artifacts/qa-compressor-matrix-handler-layout.json`. Phase ไม่เปลี่ยน
