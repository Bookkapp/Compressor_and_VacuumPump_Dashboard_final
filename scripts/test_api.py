import json
import urllib.request

req = urllib.request.Request(
    'http://127.0.0.1:5001/api/auth/login',
    data=json.dumps({'username': 'ADIadmin', 'password': 'ADIIOT'}).encode(),
    headers={'Content-Type': 'application/json'},
)
res = urllib.request.urlopen(req)
token = json.loads(res.read())['token']

req2 = urllib.request.Request(
    'http://127.0.0.1:5001/api/devices',
    headers={'Authorization': f'Bearer {token}'},
)
devices = json.loads(urllib.request.urlopen(req2).read())
print(f'Total devices discovered: {len(devices)}')
for d in devices[:6]:
    modules = [m['module_name'] for m in d.get('modules', [])]
    print(f"  {d['machine_code']} ({d['display_name']}): {len(modules)} modules -> {modules[:4]}...")
