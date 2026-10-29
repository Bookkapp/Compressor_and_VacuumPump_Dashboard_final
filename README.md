# Compressor & Vacuum Pump — Predictive Maintenance Dashboard

ระบบเว็บสำหรับดูสถานะและข้อมูลย้อนหลังของ HT9046MX Compressor M1–M8 และ Vacuum Pump รวมถึง Alerts, Work Orders และ Service Logs ใช้ **FastAPI + React + ECharts + MySQL** และส่งข้อมูลที่เปลี่ยนแปลงไปยังหน้าเว็บผ่าน WebSocket

Repository นี้เป็น **Dashboard** ส่วนการสร้าง Reference, Calibration Profile, การอนุมัติ Active Profile และ Worker วิเคราะห์ Compressor อยู่ใน [CompressorML_and_AutomaticCalibration_final](https://github.com/Bookkapp/CompressorML_and_AutomaticCalibration_final)

README นี้รวมคู่มือติดตั้งและ Deploy แทนเอกสาร Markdown เดิมทั้งหมด อ้างอิงโค้ด `main` และบันทึกการติดตั้งเดิม การปรับเอกสารวันที่ 29 ตุลาคม 2026 ไม่ได้เป็นการ Deploy หรือทดสอบ Server ซ้ำ

## 1. ระบบติดตั้งที่ไหน

| ส่วนประกอบ | IP / Port | หน้าที่ |
| --- | --- | --- |
| Dashboard สำหรับผู้ใช้งาน | **http://10.195.17.69** | Overview, Handler Detail, Historical Charts, Database, Analytics, Alerts และ Maintenance |
| nginx บน Dashboard Server | `10.195.17.69:80` | รับเว็บและส่งต่อ HTTP/WebSocket ไป API |
| Dashboard API | `127.0.0.1:5001` บน `.69` | ให้บริการ API/Frontend และรันตัวอ่าน telemetry/Operation feed |
| Dashboard metadata MySQL | `127.0.0.1:3306` บน `.69` | `predictive_maintenance` เก็บผู้ใช้, Alerts, Work Orders, Service Logs, receipts/cursor และประวัติสถานะ |
| Operation และแหล่งข้อมูล MySQL | **`10.195.17.73:3306`** | เก็บ Raw readings และผลวิเคราะห์ที่ Dashboard มีสิทธิ์ SELECT |

Topology ใช้การเชื่อมต่อทางเดียว: **`.69` เป็นผู้เปิดการเชื่อมต่อไป `.73:3306`** ส่วน Operation ไม่ต้องเปิดการเชื่อมต่อกลับ `.69` และไม่ต้องเรียก Dashboard HTTP API เพื่อส่งผลวิเคราะห์

```text
Compressor / Vacuum Pump
          |
          v
10.195.17.73 — MySQL
  ht9046mx_iot.ht9046mx_readings       <--- Compressor raw logging
  vacuum_pump_db.vacuum_pump_readings <--- Vacuum raw logging
          |
          +--> Operation Worker --> ht9046mx_analytics dashboard feed
          |
          |  SELECT only; connection initiated by .69
          v
10.195.17.69 — Dashboard API (one process)
          |
          +--> Local MySQL: predictive_maintenance
          |    users / status / alerts / work orders / service logs
          |    feed receipts / cursor / hourly history
          |
          v
nginx :80 --> Browser / WebSocket
```

Dashboard อ่าน Raw data เพื่อแสดงค่าและกราฟย้อนหลัง และอ่านผล Compressor จาก Operation อีกเส้นทางหนึ่ง การเปิดหลายแท็บใช้ตัวรับ feed ร่วมกันใน API process เดียว ไม่มี Worker วิเคราะห์ใหม่ต่อแท็บ

## 2. ฐานข้อมูลและสิทธิ์ที่ต้องเตรียม

| ข้อมูล | Server / Schema / Table | สิทธิ์ของ Dashboard |
| --- | --- | --- |
| Dashboard metadata | `.69` / `predictive_maintenance` / ตาราง `pm_*` | อ่านและเขียน metadata รวมถึงสิทธิ์ additive schema ที่แอปต้องใช้ |
| Compressor raw | `.73` / `ht9046mx_iot.ht9046mx_readings` | **SELECT เท่านั้น** |
| Vacuum raw | `.73` / `vacuum_pump_db.vacuum_pump_readings` | **SELECT เท่านั้น** |
| Operation feed | `.73` / `ht9046mx_analytics.ht9046mx_dashboard_feed` | **SELECT เท่านั้น** |
| Operation sequence | `.73` / `ht9046mx_analytics.ht9046mx_dashboard_sequence` | **SELECT เท่านั้น** |
| Operation identity | `.73` / `ht9046mx_analytics.ht9046mx_dashboard_identity` | **SELECT เท่านั้น** |

Operation เป็นผู้เขียน feed และใช้ `ht9046mx_dashboard_latest` ประกอบการควบคุม export ภายใน Dashboard reader ไม่จำเป็นต้องได้สิทธิ์เขียนหรืออ่านตารางภายในทั้งหมดของ Operation

บัญชี reader บน `.73` ต้องอนุญาตการเชื่อมต่อจาก host `10.195.17.69` โดยเฉพาะ และ MySQL/network ต้องรับ connection ดังกล่าวได้ Metadata account บน `.69` ใช้สิทธิ์เฉพาะฐานของ Dashboard เช่น `SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES` ตาม schema ที่ติดตั้ง

Compressor และ Vacuum มีคนละ column contract: Compressor ใช้ `machine_number` กับ wide columns ของ M1–M8 ส่วน Vacuum ใช้ `device_id` หรือ `devices_id` ตามฐานจริง บันทึก Server เดิมใช้ **`device_id`** จึงต้องตั้ง `VACUUM_DEVICE_COLUMN=device_id`

## 3. Configuration ที่สำคัญ

แอปอ่าน `.env` ที่ repository root ส่วนค่าที่ตั้งใน environment ของ service ไว้แล้วมีลำดับเหนือ `.env` กระบวนการที่รันต้องใช้ root และ Python environment ของ installation เดียวกัน

Private repository นี้มี `.env` สำหรับการติดตั้งเดิมอยู่แล้ว หากอัปเดต Server เดิมให้สำรองและรักษาค่าจริงของ Server แล้ว merge เฉพาะค่าที่จำเป็น ส่วน `.env.example` ใช้เป็นต้นแบบสำหรับ installation ใหม่ รหัสผ่านและ signing key ไม่ต้องคัดลอกลง README หรือ log

ตัวอย่าง **ค่าที่ไม่ใช่ secret** ของ topology ปัจจุบัน:

```dotenv
APP_ENV=production
APP_HOST=127.0.0.1
PORT=5001
APP_TIMEZONE=Asia/Bangkok
ALLOWED_ORIGINS=http://10.195.17.69,http://localhost,http://127.0.0.1

DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=predictive_maintenance

TELEMETRY_ENABLED=true
TELEMETRY_DB_HOST=10.195.17.73
TELEMETRY_DB_PORT=3306
TELEMETRY_POLL_INTERVAL_SECONDS=5

COMPRESSOR_SCHEMA=ht9046mx_iot
COMPRESSOR_TABLE=ht9046mx_readings
COMPRESSOR_MACHINE_COLUMN=machine_number
COMPRESSOR_TIMESTAMP_COLUMN=recorded_at
COMPRESSOR_SENSOR_SCALE=1

VACUUM_SCHEMA=vacuum_pump_db
VACUUM_TABLE=vacuum_pump_readings
VACUUM_DEVICE_COLUMN=device_id

OPERATION_PULL_ENABLED=true
OPERATION_DB_SCHEMA=ht9046mx_analytics
OPERATION_PULL_INTERVAL_SECONDS=5
OPERATION_PULL_BATCH_SIZE=500
OPERATION_PULL_ALERTS_ENABLED=true

COMPRESSOR_HEALTH_ENABLED=false
MQTT_ENABLED=false
SEED_DEMO_DATA=false
```

| Config เพิ่มเติม | ใช้ทำอะไร |
| --- | --- |
| `DB_USER`, `DB_PASSWORD` | บัญชีเขียน metadata บน `.69` |
| `COMPRESSOR_DB_USER`, `COMPRESSOR_DB_PASSWORD` | บัญชี SELECT Compressor raw บน `.73` |
| `VACUUM_DB_USER`, `VACUUM_DB_PASSWORD` | บัญชี SELECT Vacuum raw บน `.73` |
| `OPERATION_DB_USER`, `OPERATION_DB_PASSWORD` | บัญชี SELECT feed/sequence/identity บน `.73`; ใช้บัญชีเดียวกับ Compressor ได้เมื่อมี grant ครบ |
| `SECRET_KEY` | signing key ของระบบ login; production ต้องเป็นค่าที่ไม่ซ้ำและยาวอย่างน้อย 32 ตัวอักษร |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | ค่า bootstrap บัญชี Admin |
| `USER_USERNAME`, `USER_PASSWORD` | ค่า bootstrap บัญชีผู้ใช้งาน Maintenance |
| `OPERATION_STREAM_NAMESPACE` | ปกติปล่อยว่าง; ใช้เฉพาะการกู้คืนเมื่อเปลี่ยน producer database โดยตั้ง namespace ใหม่อย่างตั้งใจ |
| `TELEMETRY_CONNECT_TIMEOUT_SECONDS`, `TELEMETRY_READ_TIMEOUT_SECONDS` | timeout การอ่าน source; ค่าเริ่มต้นในโค้ดคือ 10 และ 30 วินาที |

Production ต้องใช้ Admin/User password ที่ต่างกันและยาวอย่างน้อย 12 ตัวอักษร การแก้ bootstrap password ใน `.env` แล้ว restart **ไม่ได้ reset บัญชีที่อยู่ในฐานข้อมูลแล้ว** ต้องใช้ขั้นตอนจัดการบัญชีที่เหมาะสมแยกต่างหาก

`COMPRESSOR_SENSOR_SCALE` รับค่า `1` หรือ `0.1` เท่านั้น ให้ใช้ตามหน่วยข้อมูลจริง หากเปิด Operation pull โค้ดจะไม่ใช้ optional legacy `compressor_health_scores` เป็นเส้นทางหลัก ไม่ต้องสร้าง Health Score ทดแทนเมื่อผลวิเคราะห์ยังไม่พร้อม

## 4. เตรียมเครื่องและติดตั้ง Dashboard

การติดตั้งเดิมบน `.69` ใช้ Windows Server 2022, Python 3.12 และ Node 24 ใช้ Python 3.12 และ Node ที่รองรับ Vite ใน lockfile; Node 22.12 ขึ้นไปเหมาะกับชุดนี้ ต้องมี MySQL สำหรับ metadata และ nginx หรือ reverse proxy ของ installation

ตัวอย่างสำหรับ **clone ใหม่** บน `.69`:

```powershell
git clone https://github.com/Bookkapp/Compressor_and_VacuumPump_final.git C:\Compressor_and_VacuumPump_final-main
Set-Location C:\Compressor_and_VacuumPump_final-main
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
npm run frontend:build
```

หากมี installation อยู่แล้วให้เข้าถึง directory เดิม ตรวจ working changes และสำรองก่อนอัปเดต ห้าม clone ทับหรือแทน `.env` ด้วยค่าของเครื่องพัฒนา `public/` คือ frontend ที่ build แล้วและ API ใช้ให้บริการหน้าเว็บ

สำหรับฐาน metadata ใหม่ ให้ DBA เตรียม `predictive_maintenance` และบัญชีที่ระบุใน `DB_USER` ก่อนเปิดแอป แอปสร้างตาราง metadata ที่ต้องใช้ระหว่าง startup; installation เดิมต้อง backup และตรวจความเข้ากันได้ของ schema ก่อน **ไม่ต้อง import Raw telemetry หรือรัน `schema.sql` ทับฐานเดิม**

ตรวจ Config ตามข้อ 3 และเตรียม grant จาก `.73` ตามข้อ 2 จากนั้นทดสอบ API ของ installation ใหม่ด้วยคำสั่ง:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 5001 --workers 1
```

เปิด `http://127.0.0.1:5001` บน Server เพื่อตรวจ frontend/login เบื้องต้น คำสั่งนี้เป็น foreground check; การติดตั้งใช้งานต่อเนื่องให้ใช้ service/supervisor ตามข้อถัดไป **รันหนึ่ง API worker** เพราะ telemetry ingestion และ Operation receiver อยู่ใน process ของ API ห้ามเปิด foreground instance ซ้อนกับ service เดิม

## 5. Deploy บน `.69` และเชื่อม Operation `.73`

1. **เตรียม Operation `.73` ก่อน:** ตรวจ Worker หนึ่ง instance, analytics migrations และ feed/sequence/identity ให้พร้อม ใช้คู่มือติดตั้งของ Operation repository การติดตั้ง Dashboard ไม่ได้อนุมัติ Profile หรือเปลี่ยน Shadow เป็น Live
2. **ตรวจทางเชื่อม `.69` ไป `.73`:** ทดสอบ network และ authenticated SELECT ด้วยบัญชีที่กำหนดใน Config ให้ครบทั้ง Raw tables และ Operation export tables
3. **ตั้ง Dashboard `.69`:** ใช้ local metadata DB, `OPERATION_PULL_ENABLED=true`, ค่า reader ที่ถูกต้อง และ `COMPRESSOR_HEALTH_ENABLED=false` ตาม Config ด้านบน
4. **ติดตั้ง frontend/API:** ลง dependency และ build จาก revision ที่จะ deploy ใช้ API `127.0.0.1:5001`, หนึ่ง worker ผ่าน service manager ของ installation
5. **ตั้ง reverse proxy:** ใช้ [deployment/nginx-portable.conf](deployment/nginx-portable.conf) เป็นตัวอย่าง รองรับ `/`, `/api` และ `/ws` พร้อม WebSocket Upgrade URL เดิมคือ `http://10.195.17.69`; หากเพิ่ม HTTPS ต้องตั้ง certificate/proxy และปรับ `ALLOWED_ORIGINS` ให้ตรง
6. **ตรวจรับจากเครื่องอื่นใน LAN:** login/logout, Raw freshness, Operation cursor/receipts, กราฟ, หลายแท็บ และ Maintenance workflow การตอบ HTTP 200 บน Server เองยังไม่ยืนยันว่า LAN/firewall ใช้งานได้

จาก `.69` ตรวจ port ได้ด้วย:

```powershell
Test-NetConnection 10.195.17.73 -Port 3306
Invoke-RestMethod http://127.0.0.1:5001/api/health
```

ผล `Test-NetConnection` ยืนยันได้เฉพาะ TCP ส่วนสิทธิ์/schema ต้องตรวจด้วยบัญชี MySQL จริงอีกครั้ง และ `/api/db/status` ต้องเรียกพร้อม authentication เพื่อดู receiver/source status

### Portable installation เดิมบน Windows

โค้ดที่ให้มารองรับ installation เดิมที่ `C:\Compressor_and_VacuumPump_final-main` โดยมี prerequisites:

```text
deployment/runtime/
  mysql-8.4.11-winx64/bin/     MySQL portable binaries
  mysql-data/                 metadata data directory
  my.ini                     local-only MySQL configuration
  nginx-1.30.5/               nginx portable binaries
  logs/
  backups/
```

`deployment/portable_supervisor.py` เริ่ม **MySQL + API + nginx** และ restart เมื่อ process หยุดด้วย backoff 2–60 วินาที พร้อมหมุน log ขนาดประมาณ 5 MB เก็บสำรอง 4 ชุดต่อ component มี lock ป้องกัน supervisor ซ้ำต่อ installation

เมื่อ runtime ข้างต้นเตรียมครบ และ installation นี้ใช้ portable stack สามารถติดตั้ง user task ด้วย:

```powershell
.\deployment\install-user-task.ps1
```

Task ชื่อ `ADI-PM-Dashboard-Portable` ใช้ Python แบบไม่มีหน้าต่าง เริ่มเมื่อผู้ใช้ที่ลงทะเบียน **log in** และปฏิเสธการสร้าง task ชื่อซ้ำ สคริปต์นี้ไม่ได้ดาวน์โหลด binaries หรือสร้าง metadata instance ให้เอง และไม่ใช่การติดตั้ง Windows service ที่รับรองการรันก่อน login/หลัง logout หากต้องการคุณสมบัตินั้นให้ใช้ service หรือ boot task ที่ผู้ดูแล Server อนุมัติ

หาก installation ใช้ MySQL/nginx service อยู่แล้ว ให้รักษา service manager เดิม ไม่เปิด portable supervisor ซ้อน เพราะจะเกิดการแย่ง port/process

`deployment/bootstrap_portable.py` เป็น helper เฉพาะการติดตั้งเดิมที่ยังไม่มี portable data/admin config และ port 3306 ว่าง มี dependency ต่อ path/config เดิมบน Server จึงไม่ใช่ installer ทั่วไป และไม่ใช้สำหรับอัปเดตหรือ reset installation ที่กำลังใช้งาน

## 6. ตรวจหลัง Deploy และแก้ปัญหาเบื้องต้น

| สิ่งที่ตรวจ | ผลที่ต้องเห็น / จุดที่ควรไล่ดู |
| --- | --- |
| หน้าเว็บและ login | `http://10.195.17.69` เปิดได้จาก LAN, Admin/User login ได้, logout ได้ |
| Raw sources | `/api/db/status` แสดงผลอ่านล่าสุดและข้อผิดพลาดของแต่ละ source; เปรียบเทียบเวลาอ่านสำเร็จกับ timestamp ของข้อมูลจริง |
| Operation receiver | `operation_pull.enabled=true`, เชื่อมต่อได้, cursor เดินเมื่อมี export ใหม่ และ backlog ระบายได้ |
| MySQL 1044/1045 | ตรวจ grant/account/host/schema/password ของ reader; การเปิด port ได้อย่างเดียวไม่พอ |
| Feed ว่าง | เริ่มตรวจ `.73`: Worker, source lag, checkpoint/finalization, observed minutes, transaction/export และตาราง feed แล้วจึงตรวจ receiver บน `.69` |
| ไม่มี Active Profile | อาจได้ผล `NOT_EVALUATED` / Pending; **ไม่ใช่เหตุผลที่ feed ต้องว่างเสมอ** เส้นทาง Operation สามารถ export `NO_ACTIVE_CONTEXT_PROFILE` ได้ |
| มี Raw แต่ขึ้น Pending | ตรวจ Active/Live scope, supported context และความสดของ analysis; Pending ไม่ได้แปลว่า Good |
| Offline | Compressor ใช้เวลาจาก Raw reading; ถึง 30 นาทีรวมขอบเขตยัง Online เกิน 30 นาทีเป็น Offline หรือ Offline เมื่อไม่มีเวลาอ้างอิงที่ใช้ได้ |
| หน้าขาว / WebSocket ไม่เชื่อม | ตรวจ build ใน `public/`, nginx upstream, Upgrade headers, API log และ allowed origins |
| Fleet history ไม่ครบ 7 วัน | ตรวจการ capture ชั่วโมง; ข้อมูลที่ไม่เคย capture เป็น gap ระบบไม่เติมประวัติ Good ย้อนหลังจากสถานะปัจจุบัน |

ก่อนรับงาน integration ให้มี **export จริงที่ไม่ว่าง** และตรวจว่า receipt/cursor/mapping เดินถูกต้อง การเชื่อมต่อได้ขณะ feed ว่างยังไม่พิสูจน์การส่ง payload หรือ deduplication เมื่อ restart ห้าม reset cursor/identity หรือสร้าง Active Profile เพื่อบังคับให้ผ่านการตรวจ

### ความหมายของสถานะและข้อมูลบนหน้าเว็บ

Compressor ใช้ผล Operation ที่มีสิทธิ์ตัดสินจริง: supported steady/transition ใน Live อาจแสดง Good ส่วน deviation/unexpected transition/new steady level อาจแสดง Warning แต่ Shadow/no Active/unsupported/excluded หรือผลหมดอายุเป็น Pending/`NOT_EVALUATED` การเปิด pull ไม่ทำให้มี Health Score 0–100 โดยอัตโนมัติ และ Context exporter ไม่สร้าง Critical จาก score ratio เอง Repair now ต้องอาศัยผลที่รองรับสถานะดังกล่าวอย่างชัดเจน

Vacuum ประมวลผลแยกใน Dashboard แหล่งข้อมูลที่บันทึกไว้ไม่มี pressure sensor โดยตรง ค่า **Estimated Pressure** คำนวณจาก vibration ตาม calibration เดิม `V = -0.0439P - 2.2098` (`R² = 0.9764`) ช่วง Normal เดิมคือ −90 ถึง −70 kPa; ต่ำกว่า −90 หรือมากกว่า −70 ถึง −60 เป็น Warning และมากกว่า −60 เป็น Critical การแสดงหน่วย Vibration เป็น `G rms` ไม่ใช่หลักฐานยืนยันหน่วยที่ใช้สร้าง calibration ต้องตรวจหน่วย/firmware กับผู้ดูแลข้อมูลก่อนรับรองค่าความดันจริง

Fleet Health Trend ใช้ snapshot **สิ้นชั่วโมงที่ปิดแล้ว 168 จุด / 7 วัน** ตาม `Asia/Bangkok` เก็บใน `pm_module_health_hourly` และ `pm_fleet_health_hourly` ส่วนการเปลี่ยนสถานะอยู่ใน `pm_module_status_events` จำนวนในกราฟเป็น Module ไม่ใช่จำนวนเครื่อง และ Warning ที่เกิดแล้วจบภายในชั่วโมงยังอยู่ใน event history แม้ snapshot สิ้นชั่วโมงกลับเป็น Good

Alerts ใช้นโยบาย deduplicate ตามเครื่อง/Module/issue/severity ต่อวัน และการ acknowledge กดระงับ issue เดิม 7 วันตามนโยบายเดิม โดย severity escalation/new issue ยังพิจารณาได้ ขั้นตอน Maintenance ใช้ Work Order → Start Work (`IN_PROGRESS`) → Service Log (`DONE`) แยกจากการอนุมัติ Profile ใน Operation

## 7. Backup, Update และ Rollback

ก่อนอัปเดตให้เก็บ revision, `.env`, proxy/service configuration และ backup ของ `predictive_maintenance` คง Raw telemetry, Operation analytics, Profiles และ model pointers ไว้ การอัปเดตเอกสารหรือ Dashboard ไม่ใช่การสั่งฝึก/เปิดใช้โมเดลใหม่

สำหรับ **portable installation ที่มี runtime/binaries ครบ** รันจาก repository root:

`check_portable.py` ต้องมี `httpx` ซึ่งระบุใน `requirements-dev.txt` หาก environment มีเฉพาะ runtime dependencies ให้ติดตั้งชุด development requirements ก่อนใช้สคริปต์ตรวจนี้

```powershell
.venv\Scripts\python.exe deployment\backup_metadata.py
.venv\Scripts\python.exe deployment\check_portable.py
.venv\Scripts\python.exe deployment\restart_api.py
```

- `backup_metadata.py` สำรองเฉพาะ metadata ไป `deployment/runtime/backups/` โดยใช้ `mysqldump` ของ portable runtime
- `check_portable.py` ตรวจ login/API/WebSocket/source-history ผ่าน proxy บน port 80 และเขียนผลลง `deployment/runtime/acceptance-api.json`; ใช้เมื่อ Config และบัญชี login ที่เก็บไว้ยังตรงกับบัญชีจริง
- `restart_api.py` backup ก่อนหยุดเฉพาะ listener API ที่ตรวจ command line แล้ว เพื่อให้ **supervisor ที่กำลังทำงาน** เปิดใหม่ สคริปต์นี้ไม่ได้ติดตั้งหรือเริ่ม supervisor ให้

หากใช้ service manager/backup tooling อื่น ให้ใช้ขั้นตอนของ installation นั้นแทน ควรทดสอบ restore และมีสำเนา backup นอกเครื่องตามนโยบายหน่วยงาน

Rollback โดยคืน revision/config ที่บันทึกไว้แล้ว restart ผ่าน service manager เดิม โดยรักษา source data และ additive metadata การย้อน schema/restore ฐานข้อมูลต้องประเมินแยกจากการย้อนโค้ด ไม่ลบตาราง/receipts/cursor เพื่อทำให้ error หาย

ไฟล์ `RELEASE_MANIFEST.json` และ `RELEASE_SHA256.json` เป็นหลักฐานแพ็กเกจเดิม ไม่ใช่ inventory/checksum ที่รับรอง checkout ปัจจุบันหลังมี commit เพิ่มเติม หากต้องการแพ็กเกจติดตั้งที่ตรวจ checksum ได้ ให้จัดทำ manifest ใหม่จาก revision ที่จะส่งมอบจริง

## 8. ไฟล์หลักและการตรวจสำหรับ Developer

| Path | หน้าที่ |
| --- | --- |
| `app/main.py` | FastAPI endpoints, lifecycle และ frontend serving |
| `app/config.py` | `.env`, settings และ production configuration validation |
| `app/telemetry_sources.py` | อ่าน Compressor/Vacuum จาก MySQL แบบ read-only |
| `app/operation_pull.py` | อ่าน ordered feed, ตรวจ stream และประสาน receipts/cursor |
| `app/services.py`, `app/diagnostics.py` | สถานะ, workflow และ Vacuum rules |
| `app/health_history.py` | ประวัติสถานะรายชั่วโมง |
| `frontend/` | React UI และ frontend tests |
| `deployment/` | proxy, supervisor, backup และ verification scripts |

ก่อนส่งมอบการแก้โค้ดให้รัน tests ใน environment แยกที่ไม่มี production credentials/ฐานข้อมูลจริง แล้ว build frontend ของ revision นั้น:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
node --test (Get-ChildItem -Path frontend/tests/*.test.mjs).FullName
npm run frontend:build
```

สคริปต์เก่า เช่น `server.js`, firmware/MQTT examples และ mock/import/QA scripts ไม่ใช่ entrypoint ของ Production Dashboard ชุดนี้ ไม่ต้องรันเพื่อ Deploy และไม่ใช้สร้างสถานะทดแทนข้อมูลจริง
