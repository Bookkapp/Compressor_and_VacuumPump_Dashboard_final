"""Per-user persistent supervisor with bounded logs and one instance per root."""
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import msvcrt
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'deployment/runtime'
LOGS = RUNTIME / 'logs'
LOGS.mkdir(exist_ok=True)
lock = (RUNTIME / 'supervisor.lock').open('a+b')
lock.seek(0)
lock.write(b'0')
lock.flush()
lock.seek(0)
try:
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    raise SystemExit('A supervisor already owns this installation.')

def logger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOGS / (name+'.log'), maxBytes=5_000_000, backupCount=4, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
    log.addHandler(handler)
    return log

stop = threading.Event()
children = []

def supervise(name, args, cwd=ROOT):
    log = logger(name)
    delay = 2
    while not stop.is_set():
        started = time.monotonic()
        proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace', creationflags=0x08000000)
        children.append(proc)
        log.info('Started PID %s', proc.pid)
        for line in proc.stdout:
            log.info('%s', line.rstrip())
        code = proc.wait()
        children.remove(proc)
        log.info('Exited %s; restart in %ss', code, delay)
        if time.monotonic() - started > 60:
            delay = 2
        stop.wait(delay)
        delay = min(60, delay * 2)

def main():
    mysql = RUNTIME / 'mysql-8.4.11-winx64/bin/mysqld.exe'
    nginx = RUNTIME / 'nginx-1.30.5'
    jobs = [('mysql', [str(mysql), f'--defaults-file={RUNTIME / "my.ini"}', '--console'], ROOT)]
    threads = []
    for name,args,cwd in jobs:
        thread = threading.Thread(target=supervise,args=(name,args,cwd),daemon=True)
        thread.start()
        threads.append(thread)
    import socket
    for _ in range(60):
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',3306)) == 0:
                break
        time.sleep(1)
    jobs = [
        ('dashboard', [str(ROOT / '.venv/Scripts/python.exe'), '-m', 'uvicorn', 'app.main:app',
                       '--host','127.0.0.1','--port','5001','--workers','1'], ROOT),
        ('proxy', [str(nginx / 'nginx.exe'), '-p', nginx.as_posix()+'/',
                   '-c', str(ROOT / 'deployment/nginx-portable.conf'), '-g', 'daemon off;'], nginx),
    ]
    for name,args,cwd in jobs:
        thread=threading.Thread(target=supervise,args=(name,args,cwd),daemon=True)
        thread.start()
        threads.append(thread)
    try:
        while True:
            time.sleep(30)
    finally:
        stop.set()
        for proc in list(children):
            proc.terminate()

if __name__ == '__main__':
    main()
