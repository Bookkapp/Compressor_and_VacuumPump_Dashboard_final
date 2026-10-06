# UX Specification

## Current Data flow — 2 October 2026

Historical Charts, Database and Analytics select machines before their mapped Compressor M1–M8 / Vacuum Pump modules; no initial telemetry query. Date/time controls use Bangkok time and explicit loading. Analytics keeps source-family charts separate. Chart slots reserve height while loading and metric lists scroll instead of expanding without bounds. Raw Database records paginate at the source; exports are the current page. Detector evidence graph entry points were removed from Alerts, Maintenance and Logs; Start/Record work actions stay right and Delete stays left. See `docs/HISTORY_BROWSER.md` for sampling and time semantics.


**1 Oct contributor review:** Red sensor panels name only their stored feature z values meeting >= threshold during global persistence; score graph retains the global result. Tooltip shows measured/baseline/signed z/threshold and dominant feature; evidence table retains all crossers. Summary above charts provides attribution on narrow screens without overlapping canvas labels. No root cause or per-feature persistence claim; missing z is unknown. Startup/steady validation remains a proposed next step. Read `docs/DETECTOR_EVIDENCE_INTEGRATION.md`; no custom automatic page updater added.

## Incident reporting — 2026-10-01

ใช้ Dashboard เป็นหน้ารายงานเดียวสำหรับงานช่าง; Operation ดูแล Profiles ไม่ต้องกรอก Description ซ้ำ Manual Assign Work เพิ่มเวลาเริ่ม/สิ้นสุดที่พบอาการ พร้อมข้อความ Asia/Bangkok และเลือกเวลาประมาณได้ ไม่ทราบให้เว้นว่าง Assigned Work แสดงช่วงนี้แยกจาก Alert/creation time Service Logs ขยาย Original incident report จาก snapshot เดิมได้ การปิดงานไม่เปลี่ยนเป็น detector-recovery label และไม่แสดง cause/probability จากข้อความอิสระ Build/tests ผ่าน แต่ browser workflow UAT/graph-link ยังรอทดสอบ ดู `docs/INCIDENT_REPORT_WORKFLOW.md`.

## Maintenance / Logs — 2026-09-30

- Warning Alert มีปุ่ม Acknowledge อย่างเดียว; Critical ใช้ Acknowledge และสร้าง Work Order.
- Assigned Work เรียงเปิดก่อนอยู่บน, แสดงวันเวลา Alert/เปิดงาน และแสดงสถานะ Open/In progress ที่มุมขวาบนแทนป้าย Priority; Admin มีปุ่ม Delete work order ชิดซ้าย สีเป็นกลางจน hover. Start work / Record service log อยู่ในกลุ่มเดิมทางขวา; เมื่อการ์ดแคบ กลุ่มปุ่มนี้ลงบรรทัดถัดไป.
- Service Log เพิ่ม Used Part ได้หลายรายการ (ชื่อ, จำนวน, ราคาต่อหน่วย) และค่าแรง/ค่าใช้จ่ายอื่นแยก. Maintenance Logs แสดงเฉพาะค่าใช้จ่ายรวม, Work Order # และปุ่มแก้ไข/ลบเฉพาะ Admin.
- Data → Logs แสดงรายละเอียดประวัติแต่ละรายการพร้อมอะไหล่ จำนวน ราคาต่อหน่วย ยอดต่อรายการ และยอดรวม; ระบุค่าใช้จ่ายเดิมที่ไม่แยกรายการตามจริง. กรอบ Data → Logs และ Maintenance Logs ใช้ระยะขอบเดียวกับแผงอื่น พร้อมเลื่อนตารางภายในบนหน้าจอแคบ.
- Fleet Health Trend เลือก 7 วันเท่านั้น; วันไม่มี diagnostic เป็นช่องว่างพร้อมคำอธิบาย.
- Compressor modules ใช้พื้นสีอ่อนตามสถานะโดยไม่มีไอคอนในช่อง; tooltip และชื่อที่โปรแกรมอ่านหน้าจออ่านยังระบุสถานะ. หัวข้อ Vacuum Pump modules ใช้ชื่อเต็ม.

## Visual language

- คงรูปแบบ Analog Devices เดิม: industrial dark/light neutral, ADI blue เป็น primary, teal/green = Good, amber = Warning, red = Repair now
- ใช้พื้นที่ Detail 100% ของ content area โดยมี padding ที่อ่านง่าย
- ข้อมูลสำคัญต้องมองเห็นทันที ไม่ซ่อนใน Additional Telemetry
- ทุก empty/loading/error state ต้องบอกสาเหตุและไม่สร้างตัวเลขแทน

## Overview และชื่อสถานะ

- Desktop: Fleet Health Trend อยู่ซ้าย, Handler status distribution อยู่ขวา; หน้าจอแคบเรียงเป็นคอลัมน์เดียว. Trend แสดง 7 วัน, สี Good/Warning/Repair now และ gap ที่สื่อว่าไม่มี diagnostic coverage ไม่วาดศูนย์แทน
- Compressor heatmap และ Vacuum list แสดงตัวอย่างอย่างละไม่เกิน 5 เครื่อง เรียงปัญหาก่อน พร้อม View all; แถวไม่ใช้ไอคอน Wi-Fi กำกับเครื่อง. No Signal ยังคงเป็นตัวเลข connectivity แยกจากสถานะสุขภาพ
- Open Work Orders อยู่ท้ายสุด กว้างเท่าคอลัมน์ Compressor บน desktop และเต็มคอลัมน์บนมือถือ; ใช้ neutral เป็นโครง, amber/red เฉพาะ priority สูง, อ่านชื่อเครื่อง/โมดูล/สถานะง่าย และคลิกแถวหรือ Open Maintenance เพื่อไปหน้าบำรุงรักษา
- Compressor map ใช้หัวคอลัมน์ M1–M8 แถวเดียวและจัด 5 แถวให้เต็มความสูงการ์ด; ช่องปกติพื้นเขียวจาง ไม่มีจุด. เฉพาะ Warning/Repair now มีพื้นจางและไอคอนเตือน. ชื่อเครื่องกับหัวคอลัมน์และ tooltip/aria label ยังระบุตำแหน่งโมดูลได้
- คง Handler status distribution รูปแบบเดิม และใช้ Good / Warning / Repair now / Repairing / Offline; ไม่มี Monitoring ในตัวกรอง การ์ด หรือ Admin status selector
- Compressor module health map เป็นตารางเครื่อง × M1–M8; Vacuum เป็นรายการโมดูลแยกกัน. เรียงเครื่องที่ Repair now/Warning ก่อน และแสดง No Signal แยกจากสุขภาพโมดูล; คลิกช่อง/แถวเพื่อเปิดโมดูลตรงตัว
- สีตัวเลข Vibration ในรายการ Vacuum ต้องตรงกับสถานะรวมของโมดูล: Warning = amber, Repair now = red, Good = green; ไม่ใช้สีแดงกับ Warning โดยไม่มีเหตุผลจากสถานะ
- Top deteriorating แสดงคะแนนที่ลดลงเทียบกับ baseline 24–48 ชั่วโมงก่อนเท่านั้น; ถ้าไม่มีคู่เปรียบเทียบให้แสดง empty state ชัดเจน. Active alerts ยังคงรูปแบบการ์ดเดิมและเรียงความรุนแรง
- ไม่เพิ่มตัวกรองที่มุมขวาบนของ Overview; ปุ่ม Refresh เดิมยังอยู่
- หลัง Service Log ปิดงานที่ผูก Work Order ให้ Repairing กลับ Good ทันทีในเชิง workflow; ML Score/กฎ Vacuum ที่เข้ามาใหม่ยังเป็นผู้ตัดสินสถานะสุขภาพต่อ

## Handler Detail

- แถวแรกเป็น source tabs: `Compressor` และ `Vacuum Pump` เฉพาะที่ Handler นั้นมีจริง
- เมื่อเลือก Compressor ให้แสดง tabs M1–M8 ที่พบ และคง charts/labels เฉพาะ Compressor
- เมื่อเลือก Vacuum ให้แสดง Temperature, Current, Vibration `mm/s`, Acceleration และ `Estimated Pressure`
- Sensor Snapshot ของ Vacuum Pump คงการ์ดหลักและแถวล่าง Accel X/Y/Z เท่านั้น (ไม่มีค่าแสดง No data); Compressor คง Busy/Status/SV ตามเดิม
- ห้ามแสดง Health Score บน Vacuum
- Compressor ที่ยังไม่มี ML row ต้องแสดง `Awaiting ML Score`
- แสดงเวลาของ ML result; ถ้า model version เป็น `MOCK_ONLY_*` ต้องแสดง `TEST DATA — not an approved active profile` ชัดเจน และสถานะจาก OPERATION `condition` ต้องไม่ขัดกับ badge ของโมดูล
- Vacuum ต้องแสดง disclosure ว่า pressure คำนวณจาก vibration และไม่มี pressure sensor

## Vacuum status

- Normal: `-90 <= P <= -70 kPa`
- Warning: `P < -90` หรือ `-70 < P <= -60 kPa`
- Critical: `P > -60 kPa`
- Estimated Pressure และ Vibration ต้องอยู่ใกล้กันเพื่อให้เห็นความสัมพันธ์

## Analytics

- เลือก source family ก่อน เพื่อไม่ผสม metric ที่ความหมาย/หน่วยต่างกัน
- เลือก machines ได้ไม่เกิน 6
- เลือก machine×module series ได้ไม่เกิน 12 รวมถึงเครื่องเดียวกันคนละโมดูล
- เลือก metrics ได้ไม่เกิน 4
- หนึ่ง chart ต่อหนึ่ง metric เพื่อไม่วางหน่วยต่างกันบนแกนเดียว
- Legend ต้องบอกทั้ง machine และ module

## Alerts

- แสดง active/acknowledged ชัดเจน
- ปุ่ม `Acknowledge + create work order` อยู่ที่ alert แต่ละรายการ; หลังรับทราบมีลิงก์ Work Order ไปหน้า Maintenance
- การเปิดรายละเอียดห้ามถือเป็นการ acknowledge
- Acknowledged row ต้องยังอ่านย้อนหลังได้ พร้อมวันสิ้นสุด suppression
- กดรับทราบซ้ำต้องไม่สร้างใบสั่งงานซ้ำ

## Maintenance — Assigned Work

- การ์ดหนึ่งใบต่อ work order โดยเรียงหมายเลขงาน/ระดับความสำคัญ, ชื่องาน, เครื่อง/โมดูล/ผู้รับผิดชอบ, รายละเอียด, สถานะและปุ่มทำงาน
- ใช้ ADI blue สำหรับโครงและ action; amber/red ใช้เฉพาะ High/Critical ไม่ใช้สีสดกับทุกการ์ด
- ปุ่ม `Start work` และ `Record service log` เป็นข้อความตรงไปตรงมา ไม่มีปุ่มปิดงานโดยไม่ลงบันทึก
- ถ้าไม่มีงานให้แสดง empty state ที่อ่านเข้าใจทันที
- บนมือถือรายละเอียดและปุ่มเรียงลงมา โดยปุ่มยังมีพื้นที่กดเพียงพอ
- Work Order ที่เกิดจาก Alert ระบุหมายเลข Alert ต้นทาง
- ตาราง Maintenance Logs มีปุ่มถังขยะเฉพาะ Admin พร้อมข้อความยืนยันก่อนลบ
- หาก Admin ลบ Service Log ใบสุดท้ายของงานที่ปิดแล้ว แจ้งว่า Work Order ถูกเปิดกลับเป็น `OPEN`

## Settings และ Advanced Threshold

- ENG/TH อยู่ใต้ Color Theme ใช้ segmented control แบบเดียวกัน; ภาษาไทยใช้ฟอนต์ระบบที่รองรับอักษรไทยและไม่เปลี่ยนโทน ADI
- Advanced Threshold เลือกเครื่องและโมดูลได้ โดยจัดกลุ่ม Compressor/Vacuum ชัดเจน
- Vacuum Pump มีสวิตช์เปิด/ปิด override อุณหภูมิ กระแส และการสั่น; ปิดแล้วยังใช้ default และกฎ Estimated Pressure หลัก
- Compressor แสดงข้อความว่า ML Health Score เป็นผู้ประเมิน ไม่มีฟอร์ม rule threshold ที่ใช้ไม่ได้จริง

## Responsive behavior

- Desktop: ใช้พื้นที่แนวนอนเต็มที่และกราฟอย่างน้อย 360 px
- Tablet/mobile: panels เรียงหนึ่งคอลัมน์; action ของ alert ย้ายใต้เนื้อหา; source/module tabs wrap ได้

## v1 handoff review — 2026-09-24

- Repository documentation does not change status wording, alert ownership or chart behavior. Missing/stale ML remains explicit, Estimated Pressure remains labelled as estimated, and Compressor cause diagnosis is not displayed.
