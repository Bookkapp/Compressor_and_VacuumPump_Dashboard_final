"""Consistent metadata-only backup; no passwords in command lines or output."""
from pathlib import Path
from datetime import datetime
import subprocess
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.config import settings as s

def main():
    runtime=ROOT/'deployment/runtime'
    backups=runtime/'backups'
    backups.mkdir(exist_ok=True)
    config=runtime/('backup-client-'+uuid.uuid4().hex+'.cnf')
    # Values are generated portable credentials, escaped for MySQL option files.
    def quote(value):
        return '"'+str(value).replace('\\','\\\\').replace('"','\\"')+'"'
    config.write_text('[client]\nhost='+quote(s.db_host)+'\nport='+str(s.db_port)+
        '\nuser='+quote(s.db_user)+'\npassword='+quote(s.db_password)+'\n',encoding='utf-8')
    target=backups/('predictive_maintenance-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sql')
    try:
        with target.open('wb') as output:
            proc=subprocess.run([str(runtime/'mysql-8.4.11-winx64/bin/mysqldump.exe'),
                '--defaults-extra-file='+str(config),'--single-transaction','--no-tablespaces',
                '--skip-lock-tables','--set-gtid-purged=OFF',s.db_name],
                stdout=output,stderr=subprocess.PIPE,creationflags=0x08000000)
        if proc.returncode:
            raise SystemExit('Metadata backup failed; incomplete backup file retained for inspection.')
        print('Metadata backup:',target.name,'bytes:',target.stat().st_size)
    finally:
        config.unlink(missing_ok=True)

if __name__=='__main__':
    main()
