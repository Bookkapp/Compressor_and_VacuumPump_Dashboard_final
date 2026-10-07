"""Local-only preview using the explicitly created disposable QA metadata DB."""
import os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
values={}
for line in (root/'.env.local_backup').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.startswith('#'):
        k,v=line.split('=',1);values[k]=v.strip().strip('"')
assert values['DB_HOST'] in {'localhost','127.0.0.1'}
db=(root/'artifacts/operation-pull-qa/qa_database.txt').read_text().strip()
assert db.startswith('pm_pull_qa_20261007_') and db.replace('_','').isalnum()
os.environ.update(DB_HOST='127.0.0.1',DB_USER=values['DB_USER'],DB_PASSWORD=values['DB_PASSWORD'],DB_NAME=db,
    TELEMETRY_DB_HOST='127.0.0.1',COMPRESSOR_DB_USER=values['COMPRESSOR_DB_USER'],COMPRESSOR_DB_PASSWORD=values['COMPRESSOR_DB_PASSWORD'],
    VACUUM_DB_USER=values['VACUUM_DB_USER'],VACUUM_DB_PASSWORD=values['VACUUM_DB_PASSWORD'],
    OPERATION_PULL_ENABLED='true',OPERATION_DB_SCHEMA=db,OPERATION_DB_USER=values['DB_USER'],OPERATION_DB_PASSWORD=values['DB_PASSWORD'],
    VACUUM_DEVICE_COLUMN='devices_id',COMPRESSOR_HEALTH_ENABLED='false',SEED_DEMO_DATA='false',OPERATION_PULL_ALERTS_ENABLED='false',ALLOWED_ORIGINS='http://127.0.0.1:5091')
import uvicorn
uvicorn.run('app.main:app',host='127.0.0.1',port=5091)
