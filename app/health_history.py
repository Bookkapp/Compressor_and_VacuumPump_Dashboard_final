"""Bounded module evidence and durable hourly fleet end-state snapshots."""
import hashlib,json,threading,time
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from .config import settings
from .db import connection,fetch_all

SCHEMA=[
'''CREATE TABLE IF NOT EXISTS pm_system_settings (key_name VARCHAR(64) PRIMARY KEY,value_text TEXT,updated_at DATETIME)''',
'''CREATE TABLE IF NOT EXISTS pm_operation_cursor (source_key VARCHAR(190) PRIMARY KEY,last_seq BIGINT NOT NULL,updated_at DATETIME NULL)''',
'''CREATE TABLE IF NOT EXISTS pm_operation_source_identity (source_key VARCHAR(190) PRIMARY KEY,stream_id VARCHAR(64) NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS pm_operation_receipts (source_key VARCHAR(190) NOT NULL,event_id CHAR(64) NOT NULL,seq BIGINT NOT NULL,kind VARCHAR(16) NOT NULL,machine_number VARCHAR(64) NOT NULL,module_number INT NULL,occurred_at DATETIME(6) NOT NULL,payload_json MEDIUMTEXT NOT NULL,PRIMARY KEY(source_key,event_id),UNIQUE KEY uq_pull_seq(source_key,seq))''',
'''CREATE TABLE IF NOT EXISTS pm_operation_latest (module_id INT PRIMARY KEY,occurred_at DATETIME(6) NOT NULL,status VARCHAR(32) NOT NULL,payload_json MEDIUMTEXT NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS pm_operation_unmapped (source_key VARCHAR(190) NOT NULL,machine_number VARCHAR(64) NOT NULL,module_number INT NOT NULL,event_id CHAR(64) NOT NULL,occurred_at DATETIME(6) NOT NULL,payload_json MEDIUMTEXT NOT NULL,PRIMARY KEY(source_key,machine_number,module_number))''',
'''CREATE TABLE IF NOT EXISTS pm_module_status_events (event_id CHAR(64) PRIMARY KEY,module_id INT NOT NULL,occurred_at DATETIME(6) NOT NULL,signal_at DATETIME(6) NULL,status VARCHAR(32) NOT NULL,source VARCHAR(16) NOT NULL,model_version VARCHAR(128) NULL,mode VARCHAR(32) NULL,payload_json MEDIUMTEXT NOT NULL,KEY ix_status_module_time(module_id,occurred_at))''',
'''CREATE TABLE IF NOT EXISTS pm_module_status_latest (module_id INT PRIMARY KEY,occurred_at DATETIME(6) NOT NULL,event_at DATETIME(6) NOT NULL,status VARCHAR(32) NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS pm_module_health_hourly (hour_end DATETIME NOT NULL,module_id INT NOT NULL,status VARCHAR(32) NOT NULL,signal_state VARCHAR(32) NOT NULL,evidence_at DATETIME(6) NULL,PRIMARY KEY(hour_end,module_id))''',
'''CREATE TABLE IF NOT EXISTS pm_fleet_health_hourly (hour_end DATETIME PRIMARY KEY,good INT NOT NULL,warning INT NOT NULL,repair_now INT NOT NULL,offline INT NOT NULL,not_evaluated INT NOT NULL,no_signal INT NOT NULL,maintenance INT NOT NULL,total_modules INT NOT NULL)''',
'''CREATE TABLE IF NOT EXISTS pm_health_capture (id INT PRIMARY KEY,started_at DATETIME NOT NULL,last_hour DATETIME NOT NULL)'''
 ,'''CREATE TABLE IF NOT EXISTS pm_health_dirty_hour (hour_end DATETIME PRIMARY KEY)'''
]

def record_state(cur,*,module_id,source,at,status,evidence_id,model_version=None,mode=None,payload=None,signal_at=None):
    # Persistent five-minute heartbeat bounds storage and makes freshness reconstructible.
    cur.execute('SELECT * FROM pm_module_status_latest WHERE module_id=%s FOR UPDATE',(module_id,))
    old=cur.fetchone()
    late=bool(old and old['occurred_at']>at)
    if old and old['occurred_at']==at:return
    export=late or not old or old['status']!=status or at-old['event_at']>=timedelta(seconds=30 if source=='vacuum' else 300)
    if export:
        event_id=hashlib.sha256(f'{source}:{module_id}:{at.isoformat()}:{evidence_id}:{status}'.encode()).hexdigest()
        cur.execute('INSERT IGNORE INTO pm_module_status_events (event_id,module_id,occurred_at,signal_at,status,source,model_version,mode,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (event_id,module_id,at,signal_at or at,status,source,model_version,mode,json.dumps(payload or {},default=str)))
        # A delayed state/heartbeat can affect its hour and next boundary's freshness.
        hour=at.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
        for end in (hour,hour+timedelta(hours=1)):
            cur.execute('INSERT IGNORE INTO pm_health_dirty_hour (hour_end) SELECT hour_end FROM pm_fleet_health_hourly WHERE hour_end=%s',(end,))
    if late:return
    cur.execute('INSERT INTO pm_module_status_latest (module_id,occurred_at,event_at,status) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE occurred_at=VALUES(occurred_at),event_at=VALUES(event_at),status=VALUES(status)',
        (module_id,at,at if export else old['event_at'],status))

def bucket_status(row,end,source):
    if not row:return 'NOT_EVALUATED','UNKNOWN'
    age=(end-row['signal_at']).total_seconds()
    if age>1800:return 'OFFLINE','OFFLINE'
    signal='ONLINE' if source=='compressor' or age<=15 else 'STALE' if age<=90 else 'NO_SIGNAL'
    if signal=='NO_SIGNAL':return 'NO_SIGNAL',signal
    return row['status'],signal

_lock=threading.Lock();_last=0.
def collect_hourly():
    global _last
    if time.monotonic()-_last<60 or not _lock.acquire(False):return
    try:
        now=datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)
        end=now.replace(minute=0,second=0,microsecond=0)
        with connection() as conn:
            conn.begin()
            try:
                with conn.cursor() as cur:
                    cur.execute('INSERT IGNORE INTO pm_health_capture (id,started_at,last_hour) VALUES (1,%s,%s)',(now,end))
                    cur.execute('SELECT * FROM pm_health_capture WHERE id=1 FOR UPDATE');capture=cur.fetchone()
                    cur.execute('SELECT hour_end FROM pm_health_dirty_hour WHERE hour_end<=%s ORDER BY hour_end LIMIT 6',(end,))
                    dirty=[r['hour_end'] for r in cur.fetchall()]
                    hours=sorted(set(dirty+[capture['last_hour']+timedelta(hours=n) for n in range(1,7) if capture['last_hour']+timedelta(hours=n)<=end]))[:6]
                    # Six buckets per cycle, caught up without making an unbounded startup query.
                    for hour in hours:
                        cur.execute('SELECT m.id,m.telemetry_source FROM pm_modules m JOIN pm_devices d ON d.id=m.device_id WHERE d.first_seen<%s AND m.telemetry_source IN (\'compressor\',\'vacuum\')',(hour,))
                        modules=cur.fetchall();counts=dict(good=0,warning=0,repair_now=0,offline=0,not_evaluated=0,no_signal=0,maintenance=0)
                        for module in modules:
                            cur.execute('SELECT status,signal_at,occurred_at FROM pm_module_status_events WHERE module_id=%s AND occurred_at<%s ORDER BY occurred_at DESC LIMIT 1',(module['id'],hour))
                            row=cur.fetchone();status,signal=bucket_status(row,hour,module['telemetry_source'])
                            category={'NORMAL':'good','WATCH':'warning','WARNING':'warning','MAINTENANCE_REQUIRED':'repair_now','OFFLINE':'offline','NO_SIGNAL':'no_signal','UNDER_MAINTENANCE':'maintenance'}.get(status,'not_evaluated');counts[category]+=1
                            cur.execute('INSERT INTO pm_module_health_hourly (hour_end,module_id,status,signal_state,evidence_at) VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE status=VALUES(status),signal_state=VALUES(signal_state),evidence_at=VALUES(evidence_at)',(hour,module['id'],status,signal,row['occurred_at'] if row else None))
                        columns=list(counts)
                        cur.execute('INSERT INTO pm_fleet_health_hourly (hour_end,'+','.join(columns)+',total_modules) VALUES ('+','.join(['%s']*9)+') ON DUPLICATE KEY UPDATE '+','.join(c+'=VALUES('+c+')' for c in columns)+',total_modules=VALUES(total_modules)',(hour,*counts.values(),len(modules)))
                        if hour>capture['last_hour']:
                            cur.execute('UPDATE pm_health_capture SET last_hour=%s WHERE id=1',(hour,))
                        cur.execute('DELETE FROM pm_health_dirty_hour WHERE hour_end=%s',(hour,))
                conn.commit()
            except Exception:conn.rollback();raise
        _last=time.monotonic()
    finally:_lock.release()

def hourly_trend(now):
    end=now.replace(minute=0,second=0,microsecond=0)
    start=end-timedelta(hours=167)
    rows=fetch_all('SELECT * FROM pm_fleet_health_hourly WHERE hour_end>=%s AND hour_end<=%s ORDER BY hour_end',(start,end))
    by_time={r['hour_end']:r for r in rows};points=[]
    keys=('good','warning','repair_now','offline','not_evaluated','no_signal','maintenance')
    for offset in range(168):
        at=start+timedelta(hours=offset);r=by_time.get(at)
        points.append(dict(at=at.replace(tzinfo=ZoneInfo(settings.app_timezone)).isoformat(),
            **{k:r[k] if r else None for k in keys},observed=r['total_modules'] if r else 0))
    return dict(range='7d',source='pm_fleet_health_hourly',granularity='1h',time_basis='End of completed hour; Asia/Bangkok; captured evidence only',points=points)
