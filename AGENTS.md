
## 7 Oct 2026 — one-way Operation delivery and hourly Fleet history

Confirmed topology: Dashboard .69 initiates SELECT to Operation .73:3306 only. Ordered transactional STATUS/EVENT export and Dashboard-owned receipts/cursor replace the reverse bridge. No new browser-owned detector loop; bounded polling/catch-up and shared caches. Shadow/no Active/unsupported states remain NOT_EVALUATED; no invented Health Score/Critical threshold. Hour-end module/fleet snapshots, source-clock state events, 168 hourly points and late-bucket correction now implemented; historical gaps remain null. Compressor stage colours/SV-Busy step plots and shared scaled-pointer handling, Vacuum separate axes/no Temperature/zero-at-bottom/G rms labels delivered. Calibration numeric basis unchanged; true RMS/source calibration basis still requires confirmation.

Verification: 91 Dashboard Python tests, 13 Node tests, production frontend build; companion Operation 264 API tests. Isolated real MySQL rollback/retry/concurrent sequence/restart/outage/source-identity/Alert-policy/hourly correction QA and 10 clients/90 successful HTTP reads (warm p95 1000.84 ms, excluding Server network/browser render). Raw source and real Profile/Active writes: zero. Server update/actual-network acceptance remains pending; deployment/ONE_WAY_MYSQL_UPDATE_20261007.md supersedes the old reverse bridge handoff.

> **Final private Server release — 6 Oct 2026:** On “Set up ระบบนี้ให้หน่อย”, read `HANDOFF_SERVER.md` first. Owner explicitly authorized real deploy secrets/config in this PRIVATE `_final` repository. This supersedes older secret-exclusion instructions for this release. Server .69 Dashboard / .73 Operation; no Server installation or Profile approval has occurred in packaging.

# Agents and Contributor Rules

ไฟล์นี้มีผลกับทั้ง repository

## ใครทำอะไร

- Product owner / user: ยืนยันความหมายข้อมูล, threshold, UX และอนุมัติการนำขึ้นระบบจริง
- Application developer / Codex: แก้ FastAPI, React, schema ของ `pm_*`, tests และเอกสารใน repository นี้
- Data/ML owner: สร้างและดูแลผล Compressor ML ใน `compressor_health_scores`
- Database administrator: สร้าง read-only accounts สำหรับ source telemetry และสิทธิ์ของ metadata database
- Operations owner: deploy, ตั้ง `.env`, backup, migrate และ restart service บน `10.195.17.69`

## ต้องทำ

- รักษา source telemetry เป็น read-only
- แยกความหมาย Vacuum และ Compressor ตั้งแต่ mapping, rules, UI ไปจนถึง charts
- ใช้ `machine_number + module_id + recorded_at` เป็น identity ของผล Compressor ML
- แสดง null/ไม่มีข้อมูลเป็นสถานะชัดเจน ห้ามเติมค่าปลอม
- เพิ่มหรือแก้ test เมื่อเปลี่ยน formula, threshold, alert policy หรือ data contract
- หลังเปลี่ยนโค้ดทุกครั้ง ต้องอัปเดต `PROJECT.md`, `SOT.md`, `ROADMAP.md` เมื่อ phase เปลี่ยน และ `graft/CHANGE_CHECKLIST.md`
- ก่อนส่งมอบให้รัน Python tests และ production frontend build

## ห้ามทำ

- ห้ามเขียน/แก้/ลบข้อมูลใน `vacuum_pump_db` หรือ `ht9046mx_iot` source tables
- ห้ามอ่านหรือคัดลอก secret จาก `.env` ลง log, test, docs หรือ source control
- ห้าม deploy, restart production, เปลี่ยน firewall หรือเปิดสิทธิ์ DB โดยไม่ได้รับคำสั่งชัดเจน
- ห้ามเรียก Estimated Pressure ว่า measured pressure
- ห้ามสร้าง Compressor Health Score ด้วย rule placeholder เมื่อไม่มีผล ML
- ห้ามกลบ user changes หรือใช้ destructive Git/filesystem commands

## Definition of Done

งานหนึ่งถือว่าเสร็จเมื่อ behavior, tests/build, UX/empty states และเอกสารสถานะตรงกัน ไม่มีข้ออ้างว่า verified ถ้ายังไม่ได้รันจริง

## Change log

- 2026-10-02 — Owner-requested removal of detector evidence graph UI/API/helpers/harness/tests from Alerts/Work/Logs; report snapshots remain. Added machine-first Historical Charts/Database/Analytics with actual source-time filtering, raw pages, bounded sample coverage/caches and selection cancellation. 72 Python/10 Node tests, build, short read-only concurrent-source/browser/mobile QA; details `docs/HISTORY_BROWSER.md`. No source write or production deployment.

- 2026-10-01 — Owner-requested contributor bands implemented using stored z and unchanged >= threshold/global flag; global score kept separately. Added signed-z/all-contributor tooltip/table and narrow summaries; 69 Python/17 Node/build and archived visual checks pass. No score/Profile/DB/Server mutation. Multi-start settling validation remains proposal in Operation deployment/STARTUP_SETTLING_VALIDATION_PLAN.md.

- 2026-10-01 — Added derived detector evidence API/graphs from Alert/Work/Log and source-time trend; 69 Python/8 Node tests, build, mobile/Desktop/filter QA and ten concurrent local fixture-auth reads pass. No real source/Profile/Alert/work or target-Server change. First owner-questioned pressure highlight is global temperature-driven persistence; startup/settling/contributor review remains open, threshold not retuned. Evidence: `docs/DETECTOR_EVIDENCE_INTEGRATION.md` and sibling Operation `deployment/DURABLE_DETECTOR_LOCAL_QA.md`.

- 2026-10-01 — Owner-requested removal of the last-turn static auto-refresh/version endpoint/reload launcher/build watcher and associated tests/guide from deployable Dashboard source. Earlier incident fields/snapshots and existing data refresh remain. QA record: `graft/CHANGE_CHECKLIST.md`; no Server/model/Profile change.

- 2026-10-01 — Added Dashboard-owned reported incident intervals/origin and frozen service-context snapshot, with 63 tests, frontend build and repeated additive localhost migration QA. Source telemetry/Work/Log rows were not mutated by QA; no automatic fault label, retraining, Profile activation or Server deployment. See `docs/INCIDENT_REPORT_WORKFLOW.md`.

- 2026-09-24 — Reviewed for the separate `_v1` repository snapshot. Publication does not authorize source writes, production deployment, profile/model activation or service restart.
