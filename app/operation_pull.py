"""One Dashboard-owned SELECT-only feed consumer with transactional receipts."""
import json
import logging
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import pymysql
from pymysql.cursors import DictCursor
from .config import settings
from .db import connection, fetch_one
from .cache import cache

log=logging.getLogger('adi.operation_pull')

def source_time(value, zone='Asia/Bangkok'):
    stamp=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    return stamp.astimezone(ZoneInfo(settings.app_timezone)).replace(tzinfo=None) if stamp.tzinfo else stamp.replace(tzinfo=ZoneInfo(zone)).astimezone(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)

def validate_message(row):
    data=json.loads(row['payload_json'])
    if row['kind']=='STATUS':
        if not 1<=int(data['module'])<=8 or data['status'] not in {'NORMAL','WARNING','MAINTENANCE_REQUIRED','NOT_EVALUATED'}:
            raise ValueError('Invalid Operation status contract')
        if row.get('module') is not None and int(row['module'])!=int(data['module']):
            raise ValueError('Operation module identity mismatch')
        if row.get('machine_number') is not None and row['machine_number']!=data.get('machine_number'):
            raise ValueError('Operation machine identity mismatch')
        # Fail closed: even a malformed Shadow producer cannot certify health.
        supported={'NORMAL':{'WITHIN_PROPOSED_STEADY','WITHIN_PROPOSED_TRANSITION'},
            'WARNING':{'STEADY_DEVIATION','UNEXPECTED_TRANSITION','NEW_STEADY_LEVEL'}}
        if (data.get('mode')!='DETECTOR_LIVE' or data.get('approved') is not True or not data.get('profile_id')
            or data['status'] in supported and data.get('category') not in supported[data['status']]):
            data['status']='NOT_EVALUATED'
    elif row['kind']!='EVENT':
        raise ValueError('Unknown Operation feed message kind')
    source_time(row['occurred_at'],data.get('source_timezone','Asia/Bangkok'))
    return data

def apply_status(cur,data,stamp,event_id):
    from .health_history import record_state
    digits=''.join(c for c in str(data['machine_number']) if c.isdigit())[-3:]
    machine='MX'+digits
    cur.execute('SELECT m.id,d.id AS device_id,m.status FROM pm_modules m JOIN pm_devices d ON d.id=m.device_id WHERE m.module_code=%s AND (d.machine_code IN (%s,%s,%s) OR d.device_uid IN (%s,%s)) FOR UPDATE',
        (f"compressor-m{data['module']}",machine,'HT9046MX-'+digits,'HT9046'+machine,'compressor:HT9046MX-'+digits,'compressor:'+machine))
    mapped=cur.fetchall()
    if len(mapped)>1:raise ValueError('Ambiguous Operation machine/module mapping')
    if not mapped:return False
    m=mapped[0]
    cur.execute('SELECT occurred_at FROM pm_operation_latest WHERE module_id=%s FOR UPDATE',(m['id'],))
    old=cur.fetchone()
    if not old or old['occurred_at']<stamp:
        cur.execute('INSERT INTO pm_operation_latest (module_id,occurred_at,status,payload_json) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE occurred_at=VALUES(occurred_at),status=VALUES(status),payload_json=VALUES(payload_json)',(m['id'],stamp,data['status'],json.dumps(data)))
        if data['status']!='NOT_EVALUATED' and m['status']!='UNDER_MAINTENANCE':
            cur.execute("UPDATE pm_modules SET status=%s WHERE id=%s AND status<>'UNDER_MAINTENANCE'",(data['status'],m['id']))
        insert_active_alert(cur,m,data,stamp)
    record_state(cur,module_id=m['id'],source='compressor',at=stamp,status='UNDER_MAINTENANCE' if m['status']=='UNDER_MAINTENANCE' else data['status'],evidence_id=event_id,
        model_version=data.get('profile_id'),mode=data.get('mode'),payload=data,signal_at=stamp)
    return True


def insert_active_alert(cur,module,data,stamp):
    status=data['status']
    now=datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None)
    if not settings.operation_pull_alerts_enabled or status not in {'WARNING','MAINTENANCE_REQUIRED'} or not 0<=(now-stamp).total_seconds()<=900 or module['status']=='UNDER_MAINTENANCE':return
    rank=2 if status=='MAINTENANCE_REQUIRED' else 1
    day=now.replace(hour=0,minute=0,second=0,microsecond=0)
    cur.execute("SELECT value_text FROM pm_system_settings WHERE key_name='alerts_cleared_at'")
    cleared=cur.fetchone()
    if cleared and cleared.get('value_text') and stamp<=source_time(cleared['value_text']):return
    cur.execute("SELECT severity FROM pm_alerts WHERE device_id=%s AND module_id=%s AND issue_key='compressor_ml_condition' AND (recorded_at>=%s OR suppressed_until>%s) FOR UPDATE",(module['device_id'],module['id'],day,now))
    if any({'critical':2,'warning':1,'info':0}.get(r['severity'],0)>=rank for r in cur.fetchall()):return
    cur.execute("INSERT INTO pm_alerts (device_id,module_id,issue_key,severity,title,message,recorded_at) VALUES (%s,%s,'compressor_ml_condition',%s,'Compressor condition requires review',%s,%s)",
        (module['device_id'],module['id'],'critical' if rank==2 else 'warning',f"Approved frozen Context: {data['category']}; profile {data['profile_id']}; source {stamp.isoformat()}",now))


def reconcile_unmapped(source_key):
    count=0
    with connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM pm_operation_unmapped WHERE source_key=%s ORDER BY occurred_at LIMIT 256 FOR UPDATE',(source_key,))
                rows=cur.fetchall()
                for row in rows:
                    if apply_status(cur,json.loads(row['payload_json']),row['occurred_at'],row['event_id']):
                        cur.execute('DELETE FROM pm_operation_unmapped WHERE source_key=%s AND machine_number=%s AND module_number=%s',(source_key,row['machine_number'],row['module_number']));count+=1
            conn.commit()
        except Exception:conn.rollback();raise
    return count


def apply_page(rows, expected_cursor, *, source_key, stream_id=None):
    from .health_history import record_state
    with connection() as conn:
        conn.begin()
        try:
            with conn.cursor() as cur:
                cur.execute('INSERT IGNORE INTO pm_operation_cursor (source_key,last_seq) VALUES (%s,0)',(source_key,))
                cur.execute('SELECT last_seq FROM pm_operation_cursor WHERE source_key=%s FOR UPDATE',(source_key,))
                current=int(cur.fetchone()['last_seq'])
                if stream_id:
                    cur.execute('INSERT IGNORE INTO pm_operation_source_identity (source_key,stream_id) VALUES (%s,%s)',(source_key,stream_id))
                    cur.execute('SELECT stream_id FROM pm_operation_source_identity WHERE source_key=%s FOR UPDATE',(source_key,))
                    if cur.fetchone()['stream_id']!=stream_id:
                        raise ValueError('Operation stream replaced; explicit recovery required')
                if current!=expected_cursor:
                    conn.rollback();return 0
                for row in rows:
                    if int(row['seq'])!=current+1:
                        raise ValueError('Operation feed gap; checkpoint not advanced')
                    data=validate_message(row)
                    stamp=source_time(row['occurred_at'],data.get('source_timezone','Asia/Bangkok'))
                    if stamp>datetime.now(ZoneInfo(settings.app_timezone)).replace(tzinfo=None):
                        raise ValueError('Future Operation result; checkpoint not advanced')
                    cur.execute('INSERT IGNORE INTO pm_operation_receipts (source_key,event_id,seq,kind,machine_number,module_number,occurred_at,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                        (source_key,row['event_id'],row['seq'],row['kind'],row['machine_number'],row['module'],stamp,json.dumps(data)))
                    if row['kind']=='STATUS':
                        if not apply_status(cur,data,stamp,row['event_id']):
                            cur.execute('INSERT INTO pm_operation_unmapped (source_key,machine_number,module_number,event_id,occurred_at,payload_json) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE event_id=IF(VALUES(occurred_at)>occurred_at,VALUES(event_id),event_id),payload_json=IF(VALUES(occurred_at)>occurred_at,VALUES(payload_json),payload_json),occurred_at=GREATEST(occurred_at,VALUES(occurred_at))',
                                (source_key,data['machine_number'],data['module'],row['event_id'],stamp,json.dumps(data)))
                    current=int(row['seq'])
                cur.execute('UPDATE pm_operation_cursor SET last_seq=%s,updated_at=NOW() WHERE source_key=%s',(current,source_key))
            conn.commit()
        except Exception:
            conn.rollback();raise
    if rows:cache.invalidate('devices','summary','fleet_health_trend:7d')
    return len(rows)

class OperationPull:
    def __init__(self):
        self.stop_event=threading.Event();self.thread=None
        self.status={'enabled':False,'connected':False,'last_seq':None,'last_success_at':None,'error_type':None}
    def cycle(self):
        schema=settings.operation_db_schema
        key=f'{settings.telemetry_db_host}:{settings.telemetry_db_port}/{schema}'
        if settings.operation_stream_namespace:key+='@'+settings.operation_stream_namespace
        saved=fetch_one('SELECT last_seq FROM pm_operation_cursor WHERE source_key=%s',(key,))
        seq=int(saved['last_seq']) if saved else 0
        conn=pymysql.connect(host=settings.telemetry_db_host,port=settings.telemetry_db_port,
            user=settings.operation_db_user,password=settings.operation_db_password,database=schema,
            cursorclass=DictCursor,autocommit=True,connect_timeout=3,read_timeout=5)
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT stream_id FROM ht9046mx_dashboard_identity WHERE id=1')
                identity=cur.fetchone()
                cur.execute('SELECT last_seq FROM ht9046mx_dashboard_sequence WHERE id=1')
                head=cur.fetchone()
                if head and int(head['last_seq'])<seq:raise ValueError('Producer database reset; explicit recovery required')
                cur.execute('SELECT seq,event_id,kind,machine_number,module,occurred_at,payload_json FROM ht9046mx_dashboard_feed WHERE seq>%s ORDER BY seq LIMIT %s',(seq,settings.operation_pull_batch_size))
                rows=cur.fetchall()
            count=apply_page(rows,seq,source_key=key,stream_id=identity['stream_id'] if identity else None)
            reconciled=reconcile_unmapped(key)
            self.status.update(connected=True,last_seq=seq+count,last_success_at=datetime.now().isoformat(),error_type=None,
                backlog=max(0,int(head['last_seq'])-seq-count) if head else 0,has_more=len(rows)==settings.operation_pull_batch_size)
            return count+reconciled
        finally:conn.close()
    def start(self,on_change=None):
        if not settings.operation_pull_enabled or self.thread and self.thread.is_alive():return
        self.status['enabled']=True;self.stop_event.clear()
        def run():
            from .health_history import collect_hourly
            last_broadcast=0
            while not self.stop_event.is_set():
                try:
                    changed=self.cycle()
                    started=time.monotonic()
                    for _ in range(3):
                        if not self.status.get('has_more') or time.monotonic()-started>2:break
                        changed+=self.cycle()
                except Exception as exc:
                    self.status.update(connected=False,error_type=type(exc).__name__);changed=0
                    log.warning('Operation pull unavailable (%s); checkpoint retained',type(exc).__name__)
                try:collect_hourly()
                except Exception as exc:log.warning('Hourly health capture failed (%s)',type(exc).__name__)
                if on_change and (changed or time.monotonic()-last_broadcast>=60):
                    try:
                        cache.invalidate('devices','summary','fleet_health_trend:7d')
                        on_change()
                        last_broadcast=time.monotonic()
                    except Exception:log.warning('Operation state broadcast deferred')
                self.stop_event.wait(settings.operation_pull_interval_seconds)
        self.thread=threading.Thread(target=run,name='operation-pull',daemon=True);self.thread.start()
    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=8)

operation_pull=OperationPull()
