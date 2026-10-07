"""Read-only API concurrency QA against the disposable localhost preview."""
import concurrent.futures,json,time,statistics,urllib.request
from pathlib import Path

root=Path(__file__).resolve().parents[1]
env={}
for line in (root/'.env').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.startswith('#'):
        k,v=line.split('=',1);env[k]=v.strip().strip('"')
base='http://127.0.0.1:5091'
payload=json.dumps({'username':env['ADMIN_USERNAME'],'password':env['ADMIN_PASSWORD']}).encode()
login=urllib.request.Request(base+'/api/auth/login',data=payload,headers={'Content-Type':'application/json'})
with urllib.request.urlopen(login,timeout=15) as response:token=json.load(response)['token']
def read(path):
    start=time.perf_counter()
    req=urllib.request.Request(base+path,headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=40) as response:data=json.load(response)
    return data,(time.perf_counter()-start)*1000
devices,_=read('/api/devices')
targets=[]
for machine in ('058','017','024','041','080','081'):
    d=next(x for x in devices if str(x['machine_code']).endswith(machine))
    for source in ('compressor','vacuum'):
        m=next((x for x in d['modules'] if x.get('telemetry_source')==source),None)
        if m:targets.append(f"/api/devices/{d['id']}/history?module_id={m['id']}&limit=2000")
cold=[]
for path in targets:
    data,ms=read(path);cold.append({'path':path,'rows':len(data),'ms':round(ms,2)})
def client(number):
    durations=[]
    for _ in range(3):
        for path in ('/api/devices','/api/overview/health-trend?range=7d',targets[number%len(targets)]):
            _,ms=read(path);durations.append(ms)
    return durations
start=time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    results=list(pool.map(client,range(10)))
values=sorted(x for result in results for x in result)
report={'clients':10,'successful_reads':len(values),'elapsed_seconds':round(time.perf_counter()-start,2),
    'warm_median_ms':round(statistics.median(values),2),'warm_p95_ms':round(values[int(.95*(len(values)-1))],2),
    'initial_history_reads':cold,'scope':'Local QA metadata; source SELECT only; excludes browser rendering and Server network; initial harness pass may hit shared cache','source_writes':0,'profile_writes':0}
(root/'artifacts/operation-pull-qa/http.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
