"""Disposable local MySQL integration QA; never touches telemetry or real Profiles."""
import sys,os,json,uuid,time,threading
from pathlib import Path
from datetime import datetime,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pymysql
from pymysql.cursors import DictCursor
from sqlalchemy import create_engine,select
from sqlalchemy.engine import URL

root=Path(__file__).resolve().parents[1]
env={}
for line in (root/'.env.local_backup').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.startswith('#'):
        k,v=line.split('=',1);env[k]=v.strip().strip('"')
assert env['DB_HOST'] in {'localhost','127.0.0.1'}
name='pm_pull_qa_20261007_'+uuid.uuid4().hex[:8]
admin=pymysql.connect(host='127.0.0.1',port=3306,user=env['DB_USER'],password=env['DB_PASSWORD'],autocommit=True,cursorclass=DictCursor)
with admin.cursor() as cur:cur.execute(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4')
os.environ.update(DB_HOST='127.0.0.1',DB_PORT='3306',DB_USER=env['DB_USER'],DB_PASSWORD=env['DB_PASSWORD'],DB_NAME=name,
    TELEMETRY_ENABLED='false',OPERATION_PULL_ENABLED='false')
from app.config import settings
from app.db import init_database,fetch_all,fetch_one,execute,connection
from app.operation_pull import apply_page,OperationPull,reconcile_unmapped
from app import health_history
init_database()
op=Path('C:/Users/Book/OneDrive/Documents/ChatGPT/release_final_20261006/CompressorML_and_AutomaticCalibration_final')
sys.path.insert(0,str(op))
from apps.api.app.unified_events import metadata,dashboard_feed,dashboard_sequence,dashboard_identity
from apps.api.app.dashboard_export import publish,publish_points
engine=create_engine(URL.create('mysql+pymysql',username=env['DB_USER'],password=env['DB_PASSWORD'],host='127.0.0.1',database=name))
metadata.create_all(engine)
now=datetime.now();end=now.replace(minute=0,second=0,microsecond=0)
device=execute("INSERT INTO pm_devices (device_uid,machine_code,display_name,status,first_seen,last_seen) VALUES ('compressor:HT9046MX-058','HT9046MX-058','QA MX058','NORMAL',%s,%s)",(end-timedelta(hours=4),now))
modules={n:execute("INSERT INTO pm_modules (device_id,module_code,module_name,module_type,status,telemetry_source) VALUES (%s,%s,%s,'Compressor','NORMAL','compressor')",(device,f'compressor-m{n}',f'M{n}')) for n in (1,2,4)}
args=dict(profile_id='QA_ONLY_NOT_REAL_ACTIVE',approved=True,mode='DETECTOR_LIVE',run_id='qa',timezone_name='Asia/Bangkok')
point=dict(time=(now-timedelta(minutes=2)).replace(microsecond=0).isoformat(),category='STEADY_DEVIATION')
with engine.begin() as c:
    publish_points(c,'MX058',1,[point],**args)
    publish_points(c,'MX058',2,[dict(point,category='WITHIN_PROPOSED_STEADY')],**dict(args,mode='DETECTOR_SHADOW'))
    publish_points(c,'MX058',8,[dict(point,category='STATE_GATE_EXCLUDED')],**args)
rows=fetch_all('SELECT * FROM ht9046mx_dashboard_feed ORDER BY seq')
bad=[dict(r) for r in rows];bad[1]['seq']+=99
try:apply_page(bad,0,source_key='qa')
except ValueError:pass
assert fetch_one('SELECT COUNT(*) AS n FROM pm_operation_receipts')['n']==0
assert apply_page(rows,0,source_key='qa')==3
assert apply_page(rows,0,source_key='qa')==0
assert fetch_one('SELECT COUNT(*) AS n FROM pm_operation_receipts')['n']==3
assert fetch_one('SELECT status FROM pm_operation_latest WHERE module_id=%s',(modules[2],))['status']=='NOT_EVALUATED'
assert fetch_one('SELECT COUNT(*) AS n FROM pm_operation_unmapped')['n']==1
modules[8]=execute("INSERT INTO pm_modules (device_id,module_code,module_name,module_type,status,telemetry_source) VALUES (%s,'compressor-m8','M8','Compressor','NORMAL','compressor')",(device,))
assert reconcile_unmapped('qa')==1
# Alert creation is QA-only and must respect daily dedupe, clear and maintenance.
from app.operation_pull import insert_active_alert
settings.operation_pull_alerts_enabled=True
warning=json.loads(rows[0]['payload_json'])
with connection() as c:
    c.begin()
    with c.cursor() as cur:
        m={'id':modules[1],'device_id':device,'status':'WARNING'}
        stamp=datetime.fromisoformat(point['time'])
        insert_active_alert(cur,m,warning,stamp)
        insert_active_alert(cur,m,warning,stamp)
        cur.execute("SELECT COUNT(*) AS n FROM pm_alerts WHERE module_id=%s",(modules[1],))
        assert cur.fetchone()['n']==1
        cur.execute('DELETE FROM pm_alerts')
        cur.execute("INSERT INTO pm_system_settings (key_name,value_text) VALUES ('alerts_cleared_at',%s) ON DUPLICATE KEY UPDATE value_text=VALUES(value_text)",(now.isoformat(),))
        insert_active_alert(cur,m,warning,stamp)
        cur.execute("SELECT COUNT(*) AS n FROM pm_alerts");assert cur.fetchone()['n']==0
        cur.execute("DELETE FROM pm_system_settings WHERE key_name='alerts_cleared_at'")
        insert_active_alert(cur,dict(m,status='UNDER_MAINTENANCE'),warning,stamp)
        cur.execute("SELECT COUNT(*) AS n FROM pm_alerts");assert cur.fetchone()['n']==0
    c.commit()
settings.operation_pull_alerts_enabled=False
# Concurrent SQL producers serialize commits through the transactional sequence row.
locked=threading.Event();release=threading.Event();errors=[]
def writer(label,hold):
    try:
        with engine.begin() as c:
            publish(c,[dict(event_id=label,kind='EVENT',machine_number='MX058',module=1,occurred_at=point['time'],payload={})])
            if hold:locked.set();release.wait(3)
    except Exception as e:errors.append(type(e).__name__)
a=threading.Thread(target=writer,args=('qa-a',True));b=threading.Thread(target=writer,args=('qa-b',False));a.start();assert locked.wait(3);b.start();time.sleep(.1);release.set();a.join();b.join();assert not errors
assert [r['seq'] for r in fetch_all('SELECT seq FROM ht9046mx_dashboard_feed ORDER BY seq')]==list(range(1,6))
# Failure rolls back allocation; next committed message is contiguous.
try:
    with engine.begin() as c:
        publish(c,[dict(event_id='rollback',kind='EVENT',machine_number='MX058',module=1,occurred_at=point['time'],payload={})]);raise RuntimeError('QA')
except RuntimeError:pass
assert fetch_one('SELECT last_seq FROM ht9046mx_dashboard_sequence')['last_seq']==5
settings.telemetry_db_host='127.0.0.1';settings.telemetry_db_port=3306
settings.operation_db_schema=name;settings.operation_db_user=env['DB_USER'];settings.operation_db_password=env['DB_PASSWORD']
consumer=OperationPull();assert consumer.cycle()==5;assert consumer.cycle()==0
before=fetch_one('SELECT SUM(last_seq) AS n FROM pm_operation_cursor')['n']
settings.telemetry_db_port=1
try:consumer.cycle()
except pymysql.OperationalError:pass
assert fetch_one('SELECT SUM(last_seq) AS n FROM pm_operation_cursor')['n']==before
settings.telemetry_db_port=3306;consumer=OperationPull();assert consumer.cycle()==0
# Restoring a different producer database must not silently reuse old receipts.
identity=fetch_one('SELECT stream_id FROM ht9046mx_dashboard_identity')['stream_id']
execute("UPDATE ht9046mx_dashboard_identity SET stream_id='qa-replacement'")
try:consumer.cycle();raise AssertionError('Stream replacement was accepted')
except ValueError:pass
assert fetch_one('SELECT SUM(last_seq) AS n FROM pm_operation_cursor')['n']==before
settings.operation_stream_namespace='qa_recovery'
assert consumer.cycle()==5
assert consumer.cycle()==0
settings.operation_stream_namespace=''
execute('UPDATE ht9046mx_dashboard_identity SET stream_id=%s',(identity,))
assert consumer.cycle()==0
# Durable hour capture and late evidence repair, without filling unobserved days.
execute('INSERT INTO pm_health_capture (id,started_at,last_hour) VALUES (1,%s,%s)',(end-timedelta(hours=3),end-timedelta(hours=3)))
with connection() as c:
    c.begin()
    with c.cursor() as cur:
        health_history.record_state(cur,module_id=modules[4],source='compressor',at=end-timedelta(minutes=31),status='NORMAL',evidence_id='qa-offline')
    c.commit()
health_history._last=0;health_history.collect_hourly()
assert fetch_one('SELECT status FROM pm_module_health_hourly WHERE module_id=%s AND hour_end=%s',(modules[4],end))['status']=='OFFLINE'
late=end-timedelta(hours=1,minutes=2)
with connection() as c:
    c.begin()
    with c.cursor() as cur:health_history.record_state(cur,module_id=modules[1],source='compressor',at=late,status='WARNING',evidence_id='qa-late')
    c.commit()
health_history._last=0;health_history.collect_hourly()
assert fetch_one('SELECT status FROM pm_module_health_hourly WHERE module_id=%s AND hour_end=%s',(modules[1],end-timedelta(hours=1)))['status']=='WARNING'
result=health_history.hourly_trend(now)
assert len(result['points'])==168 and result['points'][0]['good'] is None
report=dict(database=name,isolated=True,source_writes=0,profile_writes=0,checks=['transaction rollback','duplicate retry','Shadow nonvoting','unmapped replay','alert dedupe/clear/maintenance','concurrent sequence commit','restart cursor','connection outage','producer identity replacement rejected','explicit recovery namespace replay','hour-end Offline','late hour repair','168 hourly gaps'])
folder=root/'artifacts/operation-pull-qa';folder.mkdir(parents=True,exist_ok=True)
(folder/'mysql.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(folder/'qa_database.txt').write_text(name,encoding='utf-8')
print(json.dumps(report))
