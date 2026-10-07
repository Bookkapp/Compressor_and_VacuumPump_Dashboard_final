"""Read-only deployed API checks; credentials/tokens remain in memory."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import httpx
from websockets.asyncio.client import connect
from app.config import settings

def main():
    client = httpx.Client(base_url='http://127.0.0.1', timeout=60)
    result = {'frontend_status':client.get('/').status_code}
    for role,user,password in [('admin',settings.admin_username,settings.admin_password),
                               ('user',settings.user_username,settings.user_password)]:
        response = client.post('/api/auth/login',json={'username':user,'password':password})
        result[role+'_login_status'] = response.status_code
        response.raise_for_status()
        if role=='admin':
            token=response.json()['token']
    client.headers['Authorization']='Bearer '+token
    result['db_status']=client.get('/api/db/status').json()
    result['production_status']=client.get('/api/production/status').json()
    devices=client.get('/api/devices').json()
    result['device_count']=len(devices)
    result['module_count']=sum(len(d.get('modules',[])) for d in devices)
    result['modules_by_source']={source:sum(1 for d in devices for m in d.get('modules',[])
        if m.get('telemetry_source')==source) for source in ['compressor','vacuum']}
    result['history_checks']=[]
    compressor_devices=[d for d in devices if any(m.get('telemetry_source')=='compressor' for m in d.get('modules',[]))]
    targets=[(d,m) for d in compressor_devices[:4] for m in d.get('modules',[])[:2]
             if m.get('telemetry_source')=='compressor']
    targets += [(d,m) for d in devices for m in d.get('modules',[])
                if m.get('telemetry_source')=='vacuum'][:2]
    def history(target):
        d,m=target
        started=time.perf_counter()
        r=client.get(f'/api/devices/{d["id"]}/history',params={'module_id':m['id'],'limit':200})
        return {'device_id':d['id'],'module_id':m['id'],'source':m.get('telemetry_source'),'status':r.status_code,
                'elapsed_ms':round((time.perf_counter()-started)*1000,1),
                'samples':len(r.json()) if isinstance(r.json(),list) else None}
    with ThreadPoolExecutor(max_workers=4) as pool:
        result['history_checks']=list(pool.map(history,targets))
    result['historical_browser_api_checks']=[]
    for source in ['compressor','vacuum']:
        d,m=next((d,m) for d in devices for m in d.get('modules',[])
                 if m.get('telemetry_source')==source)
        for endpoint in ['history-page','history-chart']:
            r=client.get(f'/api/devices/{d["id"]}/{endpoint}',params={'module_id':m['id'],'limit':100})
            r.raise_for_status()
            payload=r.json()
            assert payload['source']==source and payload['module_id']==m['id']
            result['historical_browser_api_checks'].append({'source':source,'endpoint':endpoint,
                'status':r.status_code,'samples':len(payload['rows']),
                'fields':list(payload['rows'][0]) if payload['rows'] else []})
    async def websocket():
        async with connect('ws://127.0.0.1/ws',subprotocols=['adi-v1',token]) as ws:
            return ws.subprotocol
    result['websocket_subprotocol']=asyncio.run(websocket())
    result['lan_ip_local_health_status']=client.get('http://10.195.17.69/api/health').status_code
    result['external_lan_connectivity']='NOT_VERIFIED_FROM_ANOTHER_MACHINE'
    report=ROOT/'deployment/runtime/acceptance-api.json'
    report.write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print(json.dumps(result,indent=2,default=str))

if __name__=='__main__':
    main()
