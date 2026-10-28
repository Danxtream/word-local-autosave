# Copyright (C) 2026 Danxtream.
# Licensed under GPL-3.0-only with an additional term under section 7(b); see LICENSE and NOTICE.md.
"""Real process/TLS lifecycle test; synthetic Word state, separate loopback port."""
from pathlib import Path
import json
import os
import signal
import shutil
import ssl
import subprocess
import tempfile
import time
import urllib.request
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT/'Local AutoSave Test.app/Contents/Resources'
CERTS = Path.home()/'Library/Application Support/Local AutoSave Test'

def until(predicate, description):
    end = time.monotonic() + 12
    while time.monotonic() < end:
        if predicate(): return
        time.sleep(0.1)
    raise AssertionError('Timeout: ' + description)

with tempfile.TemporaryDirectory(prefix='watcher-test-', dir=ROOT.parents[1]/'work') as temporary:
    support = Path(temporary)
    for name in ('localhost.crt','localhost.key'):
        shutil.copy2(CERTS/name, support/name)
    state = support/'word-state'; state.write_text('closed')
    spec=importlib.util.spec_from_file_location('certificates',ROOT/'macos/certificates.py')
    certificates=importlib.util.module_from_spec(spec); spec.loader.exec_module(certificates)
    pki=certificates.Certificates(support)
    pki.rotate(validity_days=1)
    pki.enabled.write_text('{"testOnly":true}')
    previous_generation=pki.current.resolve()
    context = ssl.create_default_context(cafile=str(pki.root))
    def status():
        try: return json.loads((support/'watcher-status.json').read_text())
        except (FileNotFoundError, json.JSONDecodeError): return {}
    errors=[]
    def healthy():
        try:
            with urllib.request.urlopen('https://localhost:43188/health',context=context,timeout=0.3) as response:
                return response.read() == b'Local AutoSave v0.1'
        except Exception as error:
            errors.append(str(error)); return False
    log = (support/'test.log').open('w')
    process = subprocess.Popen([str(RESOURCES/'WordWatcher'),'--runtime',str(RESOURCES),'--support',str(support),'--port','43188','--test-word-state-file',str(state)],stdout=log,stderr=log)
    try:
        until(lambda: status().get('state')=='waiting','idle state')
        assert not healthy(), 'Server must stay off with Word closed'
        state.write_text('open')
        until(healthy,'server starts with Word')
        assert pki.current.resolve()!=previous_generation,'Due certificate must renew before server starts'
        first_pid = status()['serverPID']
        # A crash of our child must recover, without touching Word.
        os.kill(first_pid, signal.SIGTERM)
        until(lambda: status().get('serverPID',0) not in (0,first_pid) and healthy(),'child restart after failure')
        state.write_text('closed')
        until(lambda: status().get('state')=='waiting' and not healthy(),'server stops with Word')
        state.write_text('open')
        until(healthy,'second Word open restarts server')
        process.terminate(); process.wait(timeout=5)
        until(lambda: not healthy(),'watcher shutdown stops child')
        print('PASS: idle, due-certificate renewal, open/start, child-crash recovery, quit/stop, reopen/start, watcher shutdown; real CA-verified TLS on isolated port')
    except Exception:
        print('Last HTTPS error:',errors[-1] if errors else 'none')
        for name in ('test.log','server.log','watcher-status.json'):
            path=support/name
            if path.exists(): print(name+':\n'+path.read_text()[-6000:])
        raise
    finally:
        if process.poll() is None:
            process.terminate(); process.wait(timeout=5)
        log.close()
