"""Initialize a NEW local-only portable metadata instance; never touch source data."""
from pathlib import Path
import json
import secrets
import subprocess
import time
import pymysql

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'deployment/runtime'
MYSQL = RUNTIME / 'mysql-8.4.11-winx64'

def read_env(path):
    values = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values

def main():
    data = RUNTIME / 'mysql-data'
    admin_file = RUNTIME / 'mysql-admin.json'
    if data.exists() or admin_file.exists():
        raise SystemExit('Existing portable data/config detected; refusing to reinitialize.')
    # An occupied metadata port may be an existing installation: preserve it.
    import socket
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1', 3306)) == 0:
            raise SystemExit('Port 3306 already occupied; inspect existing metadata before continuing.')
    (RUNTIME / 'logs').mkdir(exist_ok=True)
    ini = RUNTIME / 'my.ini'
    ini.write_text('[mysqld]\n' +
        f'basedir={MYSQL.as_posix()}\ndatadir={data.as_posix()}\n' +
        'bind-address=127.0.0.1\nport=3306\nmysqlx=0\n' +
        'character-set-server=utf8mb4\nmax-connections=60\n' +
        'innodb-buffer-pool-size=128M\n' +
        f'log-error={(RUNTIME / "logs/mysql-error.log").as_posix()}\n', encoding='utf-8')
    subprocess.run([str(MYSQL / 'bin/mysqld.exe'), f'--defaults-file={ini}',
                    '--initialize-insecure'], check=True, creationflags=0x08000000)
    proc = subprocess.Popen([str(MYSQL / 'bin/mysqld.exe'), f'--defaults-file={ini}'],
                            creationflags=0x08000000)
    try:
        for _ in range(60):
            try:
                conn = pymysql.connect(host='127.0.0.1', user='root', connect_timeout=2, autocommit=True)
                break
            except pymysql.Error:
                if proc.poll() is not None:
                    raise RuntimeError('Portable MySQL exited; inspect its local error log.')
                time.sleep(1)
        else:
            raise RuntimeError('Portable MySQL startup timed out.')
        admin_password, app_password = secrets.token_urlsafe(40), secrets.token_urlsafe(40)
        admin_file.write_text(json.dumps({'user': 'root', 'password': admin_password}), encoding='utf-8')
        with conn.cursor() as cur:
            cur.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (admin_password,))
            cur.execute('CREATE DATABASE predictive_maintenance CHARACTER SET utf8mb4')
            cur.execute("CREATE USER 'pm_dashboard'@'localhost' IDENTIFIED BY %s", (app_password,))
            cur.execute("GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON predictive_maintenance.* TO 'pm_dashboard'@'localhost'")
        conn.close()
        env = ROOT / '.env'
        archive = ROOT / 'deployment/configuration_archive/.env.before-portable-20261006'
        if archive.exists():
            raise RuntimeError('Config backup already exists; refusing to overwrite it.')
        archive.write_bytes(env.read_bytes())
        existing = read_env(Path('C:/HT9046MX/app/compressor_fastapi_react_dashboard/backend/.env'))
        # This existing account was checked to have SELECT on Compressor readings only.
        updates = {'DB_USER':'pm_dashboard', 'DB_PASSWORD':app_password,
                   'VACUUM_DB_USER':'vacuum_pump_db_reader',
                   'VACUUM_DEVICE_COLUMN':'device_id',
                   'COMPRESSOR_DB_USER':existing['MYSQL_USER'],
                   'COMPRESSOR_DB_PASSWORD':existing['MYSQL_PASSWORD'],
                   'COMPRESSOR_HEALTH_ENABLED':'false',
                   'APP_HOST':'127.0.0.1',
                   'ALLOWED_ORIGINS':'http://10.195.17.69,http://localhost,http://127.0.0.1'}
        lines = env.read_text(encoding='utf-8-sig').splitlines()
        written = set()
        for i, line in enumerate(lines):
            key = line.split('=',1)[0].strip()
            if key in updates:
                lines[i] = key + '=' + updates[key]
                written.add(key)
        lines += [key+'='+value for key,value in updates.items() if key not in written]
        env.write_text('\n'.join(lines)+'\n', encoding='utf-8')
        print('New local metadata initialized; private config backed up; source tables unchanged.')
    finally:
        if admin_file.exists():
            saved = json.loads(admin_file.read_text(encoding='utf-8'))
            try:
                shutdown = pymysql.connect(host='127.0.0.1',user='root',password=saved['password'])
                with shutdown.cursor() as cur:
                    cur.execute('SHUTDOWN')
                shutdown.close()
            except pymysql.Error:
                proc.terminate()
        else:
            proc.terminate()
        proc.wait(timeout=30)

if __name__ == '__main__':
    main()
