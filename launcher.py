"""Desktop entry point: one local instance, owned socket, browser UI."""
import fcntl
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
import uvicorn
from shared import DATA_DIR
from apps.webui.main import app


def main():
    os.environ['PATH'] = '/opt/homebrew/bin:/usr/local/bin:' + os.environ.get('PATH', '/usr/bin:/bin')
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock = (DATA_DIR / 'instance.lock').open('a+')
    state = DATA_DIR / 'instance.json'
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        for _ in range(50):
            try:
                url = json.loads(state.read_text())['url']
                with urllib.request.urlopen(url + '/health', timeout=1) as response:
                    if json.load(response).get('app') == 'MambaFlow':
                        webbrowser.open(url)
                        return
            except (OSError, ValueError, KeyError):
                time.sleep(.1)
        raise RuntimeError('MambaFlow sigue iniciando. Intenta abrirlo otra vez.')
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(128)
    url = 'http://127.0.0.1:' + str(sock.getsockname()[1])
    state.write_text(json.dumps({'url': url, 'pid': os.getpid()}))
    def ready():
        for _ in range(100):
            try:
                with urllib.request.urlopen(url + '/health', timeout=1):
                    if '--no-browser' not in sys.argv:
                        webbrowser.open(url)
                    return
            except OSError:
                time.sleep(.1)
    threading.Thread(target=ready, daemon=True).start()
    try:
        uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False)).run(sockets=[sock])
    finally:
        state.unlink(missing_ok=True)
        lock.close()

if __name__ == '__main__':
    main()
