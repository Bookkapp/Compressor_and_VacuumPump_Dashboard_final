# Incident reports ผ่าน Dashboard

อัปเดต 2026-10-01 · Implemented/tested locally; Server และ browser workflow UAT ยังไม่ผ่าน

## บทบาทของสองระบบ

Dashboard นี้เป็นระบบประจำวันของผู้ใช้: ดู Alerts, รับงาน, เขียนรายละเอียด และบันทึก Service Log ส่วน Operation ใช้สำหรับ calibration candidate, Shadow Validation 3 วัน, Active Profile approval และ recalibration ของเครื่องเดิม งาน backend ไม่จำเป็นต้องมีคนเปิดหน้าจอไว้

```text
Alert → Critical Acknowledge ────────┐
                                    ↓
Admin พบอาการเอง → Create Work → Assigned Work → Start Work → Service Log
                                    ↓                           ↓
                         pm_work_orders                 pm_maintenance_logs
                     รายละเอียด/ช่วงเวลาที่พบ          ผลงาน + original report snapshot
                                    └───────── review / future dataset ─────┘
```

Warning Acknowledge ไม่สร้างใบงาน (suppression 7 วัน) Critical Acknowledge สร้างได้หนึ่งใบต่อ PM Alert ตาม policy เดิม ไม่ใช่ Alert ทุก severity จะสร้างใบงานเองทันที

## ฟอร์มและข้อมูลที่เก็บ

Admin สร้างใบงานด้วยเครื่อง/โมดูล/ผู้รับงาน/Description ตามเดิม เพิ่มช่องช่วงเวลาที่พบอาการ:

- เวลาเริ่ม (`event_started_at`), เวลาสิ้นสุด (`event_ended_at`) ว่างได้เมื่อไม่ทราบ; end ที่กรอกต้องไม่ก่อน start
- เวลาในฟอร์มเป็น **Asia/Bangkok** ไม่ใช่ timezone ของ browser
- เลือกเวลาประมาณได้; precision เป็น MINUTE หรือ APPROXIMATE ในฟอร์ม API รองรับ SECOND/UNKNOWN ด้วย
- ถ้าไม่รู้ onset จะเก็บ null/UNKNOWN ไม่ใช้เวลาเปิดงานแทน

API ตรวจ module อยู่ในเครื่องที่เลือกก่อน insert และกำหนด `report_origin=ADMIN_WORK_ORDER` เอง ไม่รับ source Alert/origin ที่ client ส่งมา Critical ACK สร้าง `report_origin=ALERT_LINKED` โดยไม่สมมติ physical onset จาก Alert timestamp

Assigned Work แสดงช่วงอาการแยกจากเวลา Alert/เปิดใบงาน ใน Maintenance และ Data → Logs เปิดรายละเอียด **Original incident report** เพื่อดู origin, ข้อความและช่วงเวลา/precision เดิม ณ ตอนส่งรายงานได้ Snapshot เก็บผู้สร้าง/ผู้รับงานและเวลาเปิดใบงานเป็น provenance เพิ่มเติม โดยไม่ใช้ creation time แทน onset

## Schema และ transaction

Metadata DB `predictive_maintenance`:

| Table | New columns |
|---|---|
| `pm_work_orders` | `report_origin VARCHAR(32) NULL`, `event_started_at DATETIME(6) NULL`, `event_ended_at DATETIME(6) NULL`, `event_timezone VARCHAR(64) NULL`, `event_time_precision VARCHAR(16) DEFAULT 'UNKNOWN'` |
| `pm_maintenance_logs` | `incident_context_json JSON NULL` |

`maintenance_evidence.py::incident_snapshot` เก็บ work ID, machine/module IDs, PM Alert ID, origin, Description, reported interval/timezone/precision เป็น JSON พร้อม `label_status=UNREVIEWED`, `cause_status=UNKNOWN` การ submit linked Service Log ล็อก Work Order และ commit snapshot/log/สถานะ DONE ใน transaction เดียว การแก้ Description ของใบงานภายหลังไม่แก้ snapshot เดิม Service Log ที่ไม่ผูกใบงานและข้อมูล legacy ไม่มี snapshot ได้

`pm_work_orders.source_alert_id` อ้าง `pm_alerts.id` เท่านั้น **ไม่ใช่ analytics Episode UUID** สถานะงานและ detector Episode แยกกัน DONE หมายถึงจบ workflow งาน ไม่ยืนยันว่ากราฟกลับเข้า Profile แล้ว การปรับ module status หลังส่ง Log เป็น behavior เดิมของ Dashboard ไม่ใช่ label สำหรับ train

ระบบ Episode รุ่นใหม่ใน Operation อยู่ใน **local rehearsal** และยังไม่เชื่อม Alert writer รุ่นหนึ่งนาทีใหม่มายัง Dashboard การมีเส้นทาง Alerts/Work Orders เดิมจึงไม่พิสูจน์ว่า live bridge ใหม่เสร็จแล้ว

## ทำไม manual Work Order สำคัญ

เก็บอาการที่คนพบแม้ไม่มี Alert เพื่อเปรียบเทียบกับ telemetry ภายหลัง แต่ไม่มี Alert อาจเกิดจากไม่มี matching Active Profile, state/coverage ไม่ผ่าน, notification suppression หรือ detector ตรวจไม่พบจริง ต้องจับคู่เวลา/เครื่อง/โมดูลและตรวจสถานะก่อนนับ false negative

Description และ action_taken เก็บเป็นหลักฐาน ไม่แปลงเป็น fault/cause/probability หรือยืนยัน baseline โดยอัตโนมัติ เมื่อมีข้อมูลมากพอให้ทำ Label QA และ episode-grouped time/machine split ก่อน supervised training ปัจจุบันไม่มี retrain จาก log นี้

## Setup และ QA

1. Backup metadata DB และใช้ `.env` ตาม deployment guide เดิม Source telemetry credentials/read-only access ไม่เปลี่ยน
2. `schema.sql` และ `app/db.py` มี additive columns ครบแล้ว Startup migration เรียก `migrate_incident_evidence(cur)` แบบ idempotent หาก runtime DB account ไม่มี ALTER TABLE ให้ DBA apply additive columns ก่อน restart
3. Local targeted check: `python -m scripts.qa_incident_context_migration` สคริปต์นี้จำกัด localhost และเรียก migration 2 ครั้งเพื่อเช็คซ้ำ ไม่สร้าง/แก้ Work Order/Service Log content
4. `python -m pytest -q` และ frontend build ตาม README Deploy backend และ frontend รุ่นเดียวกัน เพื่อไม่ให้ฟอร์มใหม่คุย backend เก่า
5. UAT บน staging: Admin manual work รู้เวลา/ไม่รู้เวลา, invalid end/module, technician ที่ถูก assign ส่ง Log, role อื่นไม่มีสิทธิ์, original report คงเดิมเมื่อแก้ใบงาน, legacy logs อ่านได้ และตรวจกราฟ/time-link ในขั้น integration ถัดไป

ผลรอบนี้: **63 tests passed (final repeat 2.25 s)**, frontend production build ผ่าน โดยใช้ temporary output เพื่อรักษา user-edited `public/`; มี warning ECharts chunk 603.61 kB การ migrate localhost 2 ครั้งผ่าน ไม่มี source telemetry หรือ Work Order/Service Log row ถูกแก้โดย QA ไม่มี Server deployment/browser workflow UAT ในรอบนี้

Code: `app/maintenance_evidence.py`, `app/services.py`, `app/db.py`, `schema.sql`, `frontend/src/main.jsx`, `frontend/src/i18n.js`, `tests/test_maintenance_evidence.py`, `scripts/qa_incident_context_migration.py`

Change log — 2026-10-01: Dashboard-owned incident intervals/origin and frozen context for service logs; no automatic training label/cause/recovery or new live detector bridge.
