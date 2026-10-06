# Detector evidence ใน Dashboard — local integration

> **Archived checkpoint:** On 2 October 2026 the owner requested removal of these graph actions/dialog/API and their dedicated helpers/tests/harness. This document records the earlier implementation, not the current UI. Use `HISTORY_BROWSER.md` for the separate historical sensor browser. Incident report context/storage and existing detector integration remain.

วันที่ 1 ตุลาคม 2026 · รอบนี้ยังไม่ได้ติดตั้งบน Server หรือ push Git

Operation สร้าง one-minute scores/Episodes จาก observed seconds และส่งผ่าน durable outbox มายัง `pm_detector_windows`, `pm_detector_episodes`, `pm_detector_data_issues`, `pm_detector_delivery_receipts` ใน metadata schema ของ Dashboard ส่วนช่างยังทำงานผ่าน Alert → Assign Work → Service Log หรือ Admin เปิด manual work เมื่อ detector ไม่แจ้ง

## เปิดหลักฐาน

ปุ่ม **กราฟหลักฐาน** อยู่ใน Compressor Alert, Assigned Work และ Service Log (ทั้งตารางเดิมและหน้า Data Logs) ใช้ API authenticated `GET /api/detector-evidence/{alerts|work-orders|logs}/{id}`; เลือก module/time เมื่อรายงานไม่มีค่า มีช่วงวันที่สูงสุดเจ็ดวันและไม่รวมปลายช่วง

Report event-time เป็นเวลาที่ผู้ใช้ระบุ ไม่ใช้เวลาเปิดใบงานแทน เมื่อมี log snapshot จะอ่านรายงานต้นฉบับที่เก็บไว้ ไม่พึ่งใบงานที่อาจถูกแก้หรือลบแล้ว ข้อมูลต่าง scoring run/Profile ไม่ถูกรวมให้ดูเป็นเส้นเดียวกัน

Pressure, differential, temperature, valve และ score ratio แยกหน่วย เส้น baseline ใช้ medians ของ Profile ใน packet ที่ให้คะแนนนั้นจริง Missing/unqualified เป็น null ไม่ interpolate. แถบแดงบน sensor panel ต้องมี stored `|z_j| >= primary_threshold` ของตัวแปรในกราฟนั้น **และ** global persistence เป็น true. ระบุชื่อทุก contributor ไม่แสดงเฉพาะ dominant; ผล global อยู่ที่ score panel. ฟ้าคือ reported period, เหลืองคือ review-required source correction/lateness. Tooltip/table แสดง actual/baseline/signed z/threshold และตัวแปรสูงสุด; เป็น score attribution ไม่ใช่สาเหตุเครื่องเสียหรือ per-feature 3-window rule. หาก z ไม่พร้อม ไม่สร้าง contributor ปลอม

Owner review แถบแรก MX080/M6 พบ TempLo เป็น dominant (12:10 z189.25 เทียบ threshold7.86) ระหว่าง possible startup/transition เทียบกับ four-day narrow candidate จึงเป็นข้อจำกัดเรื่อง false-positive/regime ไม่ใช่ fault proof. Pressure บางตัวเกิน local envelope ด้วยจริง จึงยังมี pressure band พร้อมชื่อ. Contributor-specific UI ทำแล้ว; cross-minute settling/multi-start validation ยังเป็นแผนใน sibling `deployment/STARTUP_SETTLING_VALIDATION_PLAN.md`. ไม่เปลี่ยน detector threshold/Profile จากกราฟนี้

## สิ่งที่ระบบนี้ไม่ได้นำมาแสดงแทน

Evidence ใหม่เป็น Anomaly Score ไม่ได้เพิ่ม cause %, ไม่ train จาก Description ทันที และไม่สร้าง Health % ใหม่ Legacy Health overview/table ยังเป็นอีกเส้นที่ต้องตรวจเทียบก่อน live Fleet Trend snapshot ใหม่ใช้ nullable `source_recorded_at`; ไม่ย้ายข้อมูลเก่าที่ไม่ทราบ source clock มานับวันนี้

## ทดสอบและส่งต่อ

ล่าสุด contributor change: 69 Dashboard Python/17 Node tests และ final temp build ผ่าน; archived MX080 75 windows ตรวจ Desktop/390px และตัวกรอง12:00–12:40 ได้40 windows. Global 47/75 นาที แต่ Valve contributor 11/75 นาที ไม่ shade ตาม global อีกต่อไป. Narrow screen ใช้ summary/tooltip แทน in-band labels ที่ทับกัน. Build ไม่แทน public bundle ของผู้ใช้ ภาพ/รายงานอยู่ใน Operation `deployment/DURABLE_DETECTOR_LOCAL_QA.md`. Earlier bridge QA fixture-auth parallel10/10 HTTP200/no writes ยังเป็นหลักฐานรอบก่อน ไม่อ้างว่า rerun DB ใน presentation change นี้

`frontend/tests/evidence-qa.html`/`evidence-qa.jsx` เป็น development-only visual harness ใช้ git-ignored generated fixtureจาก archived data ไม่ใช่หน้า production/API auth bypass `scripts/qa_detector_database.py` ใช้เฉพาะ named localhost QA schemaและ auth override ของ TestClient

การตั้งค่าฐานข้อมูล/สิทธิ์/migrate-only/shadow/live/rollback/Server checklist อธิบายใน sibling `../OPERATION_P/deployment/SERVER_DETECTOR_RUNBOOK.md`. New evidence tables สร้างโดย Operation bridge; Dashboard ไม่เปิด model/profile activation ให้เอง No actual target-Server or approved-Profile acceptance claimed
