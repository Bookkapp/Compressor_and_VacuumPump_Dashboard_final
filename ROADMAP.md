> **Final private Server release — 6 Oct 2026:** On “Set up ระบบนี้ให้หน่อย”, read `HANDOFF_SERVER.md` first. Owner explicitly authorized real deploy secrets/config in this PRIVATE `_final` repository. This supersedes older secret-exclusion instructions for this release. Server .69 Dashboard / .73 Operation; no Server installation or Profile approval has occurred in packaging.

# Roadmap



## Numbering reset & Vacuum Pump tooltip — 2026-10-06



- [x] Admin sequence & ID numbering management and reset (/api/admin/numbering, /api/admin/numbering/reset)

- [x] Vacuum Pump interactive diagnostic tooltip in VacuumAttentionList

- [x] 82 Python tests and production frontend build verified



## Offline status — 2026-10-06



Owner-requested Offline after more than 30 minutes without signal now projects into device/module status, summary and filters. Earlier transient loss is NO_SIGNAL. Compressor Overview cells are grey with solid borders and a matching Offline legend; caption counts all Compressor machines. 65 Python tests, final build and actual local web checks pass. Details and screenshots: docs/OFFLINE_STATUS_20261006.md. Local API restart only; source data and Profile/Active policies unchanged. Earlier connectivity descriptions below are historical.





## Local detector evidence — 1 Oct



- [x] Authenticated bounded/UTC-indexed evidence from linked Alert or manual reported interval

- [x] Pressure/differential/temperature/valve/score graph, exact baseline, quality gaps, shared zoom and paged evidence table

- [x] Latest tests69 Python/8 Node, temp build, narrow/Desktop/filter verification; actual local MySQL fixture API10 concurrent reads

- [x] Global-vs-panel contributor highlights, stored signed-z attribution, narrow/Desktop/filter QA, 17 Node/69 Python tests and build

- [ ] Startup/steady validation across independent starts; proposed method in Operation STARTUP_SETTLING_VALIDATION_PLAN.md, no gate/threshold change yet

- [ ] Login/role/ACK/work/service browser UAT, primary-vs-legacy Health reconciliation and Server/fleet acceptance

- [ ] Profile qualification and report-aware retention remain Operation/platform tasks; no auto-training from notes



Guide: `docs/DETECTOR_EVIDENCE_INTEGRATION.md` and sibling Operation Server runbook.



อัปเดตล่าสุด: 2026-10-01



## Owner-requested rollback — 2026-10-01



- [x] Remove the last-turn static-page updater, added tooling/tests/guide and custom local watchers

- [x] Preserve the earlier incident date/time and Service Log snapshot implementation

- [x] Python 63 tests, Node 5 tests, frontend build and ordinary local API/static-bundle checks pass; production acceptance phases stay unchanged



## Incident evidence checkpoint — 2026-10-01



- [x] Dashboard manual Work Order occurrence interval/origin และ original report snapshot in Service Log

- [x] Additive localhost migration/repeated check, 63 tests and frontend build

- [ ] Browser UAT: Admin/assigned tech/legacy logs/timezone/invalid input

- [ ] Explicit analytics Episode → PM Alert → Work Order mapping และ integrated graph time-link/highlight เมื่อ Operation live bridge พร้อม

- [ ] Review/export training dataset with timing and label QA; no auto fault/cause inference from notes



ไม่มี production deployment หรือการยกระดับ detector readiness จากรอบนี้ ดู `docs/INCIDENT_REPORT_WORKFLOW.md`.



## Checkpoint 2026-09-30



- Maintenance/Logs workflow และ Warning-only acknowledgement อยู่ใน working copy พร้อม migration metadata localhost แล้ว; ยังไม่ใช่ Production release.

- ถัดไป: browser UAT ของ Maintenance/Data Logs, ทดสอบสิทธิ์ Admin กับหลายแท็บ, และ event-time freshness สำหรับ Fleet Trend. ต้องวัด query/p95 บนข้อมูล staging ขนาดจริงก่อน deploy.



## Phase 1 — Domain separation (เสร็จใน working copy)



- Module-aware detail page

- Vacuum estimated pressure + rule-based status

- Compressor ML result contract + Awaiting ML Score

- Alert dedupe/acknowledgement

- Multi-machine, multi-module, multi-metric Analytics

- Full-width ADI-style layout and removal of Additional Telemetry



## Phase 2 — Integration verification (ถัดไป)



- Normal-port localhost MX777 transport ผ่าน API แล้ว (43,212 source timestamps, 8 test-only profiles, 212 scores/โมดูล, 12/12 accelerated updates); ยังไม่ผ่าน browser UI/staging/model validation

- แก้ mismatch `ARX-Ridge__seed_13` กับ runtime max-relative-z scoring ฝั่ง OPERATION ก่อนอ้างว่าเป็น ML release จริง

- เพิ่ม event-time-aware downsampling/pagination สำหรับกราฟย้อนหลัง 7 วัน/เดือน และให้ Fleet Trend ใช้เวลา sensor/score จริง ไม่ใช่ poll-time snapshot ที่อาจทำให้ดูสดเกินจริง



- ตรวจชื่อ column และ datatype ของ `compressor_health_scores` กับ ML owner

- รัน migration ของ `pm_alerts` บน staging หลัง backup

- ทดสอบ Handler ที่มีทั้ง Vacuum และ Compressor จริง

- ตรวจ timezone ของ MySQL และ application ให้ตรง `Asia/Bangkok`

- ทดสอบ alert warning → critical และ acknowledge ข้าม browser/user

- ทดสอบ OPERATION↔Dashboard จริงบน staging: Alert เจ้าของเดียว, Service Log transaction, การ restart/replay และ error recovery

- ตรวจ source `EXPLAIN`/index และ latency กราฟบนข้อมูลขนาดจริง; แก้ข้อจำกัดที่กราฟอาจไม่ครอบคลุม time range ที่เลือก

- ตรวจ freshness/timezone ของ Health Score, calibration profile รุ่นที่อนุมัติ, alert budget และ rollback ก่อนเปิด Compressor alert จริง

- ใช้ HT9046MX-777 isolated mock เป็น regression test ของ `source → calibration candidate → test-only inference → health-score table → Dashboard` โดยห้ามนับ mock profile/score เป็น production evidence

- ทดสอบ Overview priority กับ staging ที่มีหลายเครื่องและ Vacuum Warning/Repair now จริง; ยืนยันสี Vibration และลำดับ Heatmap ด้วยข้อมูลหลายสถานะ

- ทดสอบหลังปิด Service Log: สถานะกลับ Good แล้วได้รับ ML Score/telemetry ใหม่ที่ยังผิดปกติ ต้องกลับ Warning/Repair now โดยไม่ค้าง Repairing

- ตรวจแผน query ของ Top deteriorating บน `pm_diagnostic_snapshots` ข้อมูลใหญ่ และพิจารณา materialized/latest-score cache หาก p95 เพิ่มขึ้น

- ตรวจ `EXPLAIN`/p95 ของ Fleet Health Trend 7 วันแบบ daily latest ต่อ module บน staging; ยืนยัน timezone DB, source-event freshness และ coverage จริงก่อนใช้เป็นตัวชี้วัดปฏิบัติการ



## Phase 3 — UAT and release



- UAT บน desktop และ tablet กับ maintenance team

- ตรวจความอ่านง่ายของกราฟเมื่อเลือก 6 เครื่อง / 12 module series / 4 metrics

- รัน multi-tab browser soak/load test ยาวพร้อม WebSocket, วัด p95/p99, CPU/RAM, DB QPS และ error rate บน staging

- ก่อนเพิ่ม Uvicorn worker ต้องแยก poller/ingestion ให้รันเพียงชุดเดียว และกระจาย WebSocket events ผ่าน shared pub/sub; ตรวจ duplicate writes และ event delivery ข้าม worker

- ให้ operations owner ตั้ง secret, distinct strong bootstrap passwords และ least-privilege accounts; ตรวจบัญชีเดิมที่เคยถูก startup seed เขียนทับ

- ทำ token/session revocation และตรวจ active role จากฐานข้อมูลสำหรับ privileged operations; ตรวจ TLS, login throttling, security headers และ public diagnostics endpoint ก่อนเปิด network กว้าง

- ตั้ง `APP_ENV=production` และ `SECRET_KEY` ที่ไม่ซ้ำ/ยาวอย่างน้อย 32 อักขระเหมือนกันทุก instance แล้วทดสอบ restart/login; ห้ามใช้ ephemeral local key บน production

- Deploy ไป `10.195.17.69`, smoke test และจัด rollback point



## Phase 4 — ML expansion ภายหลัง



- เชื่อม producer จาก Compressor ML and Automatic Calibration

- เพิ่ม provenance/freshness ของ model result

- กำหนด policy สำหรับ stale ML score

- ประเมิน ML สำหรับ Vacuum Pump โดยไม่เปลี่ยนความหมาย rule-based เดิมจนกว่าจะได้รับอนุมัติ



## Repository handoff checkpoint — 2026-09-24



- Publish the current architecture to the new private `_v1` repository without changing the original remotes.

- Next: run staging contract tests against `10.195.17.73`, close the cross-repository Compressor score-schema debt, then complete security/UAT/rollback gates before Server deployment.

- DBA/server owner must create least-privilege accounts and populate on-host secrets from the ignored handoff before the staging run; credentials in a local file are not proof of connectivity or authority.

