# Copyright (C) 2026 Danxtream.
# Licensed under GPL-3.0-only with an additional term under section 7(b); see LICENSE and NOTICE.md.
"""Install/remove this user's Word lifecycle watcher. Never controls Word itself."""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import time

LABEL = 'local.autosave.word.watcher'
SUPPORT = Path.home() / 'Library/Application Support/Local AutoSave Test'
PLIST = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')

def manage(install, resources):
    domain = 'gui/' + str(os.getuid())
    if not install:
        subprocess.run(['/bin/launchctl', 'bootout', domain + '/' + LABEL], capture_output=True)
        if PLIST.exists():
            PLIST.unlink()
        print('Automatic server disabled. Documents and certificate were kept.')
        return
    SUPPORT.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime = SUPPORT / 'runtime'
    # Validate and stage the complete update before stopping the working service.
    for required in ('WordWatcher', 'server.py', 'certificates.py', 'web/taskpane.html'):
        if not (resources/required).is_file():
            raise RuntimeError('Update incomplete: missing '+required)
    stage = Path(tempfile.mkdtemp(prefix='runtime-update-', dir=SUPPORT))
    backup = SUPPORT/'runtime.previous'
    for name in ('WordWatcher','server.py','certificates.py'):
        shutil.copy2(resources/name, stage/name)
    shutil.copytree(resources/'web', stage/'web')
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(Label=LABEL, ProgramArguments=[str(runtime / 'WordWatcher')],
                   RunAtLoad=True, KeepAlive=True, ThrottleInterval=10,
                   LimitLoadToSessionType='Aqua', ProcessType='Background',
                   StandardOutPath=str(SUPPORT/'watcher.log'),
                   StandardErrorPath=str(SUPPORT/'watcher.log'))
    old_plist = PLIST.read_bytes() if PLIST.exists() else None
    subprocess.run(['/bin/launchctl', 'bootout', domain + '/' + LABEL], capture_output=True)
    had_runtime = runtime.exists()
    try:
        if backup.exists(): shutil.rmtree(backup)
        if had_runtime: runtime.rename(backup)
        stage.rename(runtime)
        temporary = PLIST.with_suffix('.tmp')
        temporary.write_bytes(plistlib.dumps(payload)); temporary.replace(PLIST)
        # Logs contain lifecycle/errors only; cap growth during installation.
        for name in ('watcher.log','server.log'):
            log = SUPPORT/name
            if log.exists() and log.stat().st_size > 1024*1024:
                log.write_bytes(log.read_bytes()[-512*1024:])
        # launchd can briefly reject a bootstrap while the previous instance's
        # process group is still being torn down. Retry only that transient case.
        for pause in (0.25, 0.75, 1.5, 3):
            time.sleep(pause)
            result = subprocess.run(['/bin/launchctl', 'bootstrap', domain, str(PLIST)], capture_output=True, text=True)
            if result.returncode == 0 or 'Bootstrap failed: 5:' not in result.stderr:
                break
        if result.returncode:
            raise RuntimeError('Could not start automatic mode: '+result.stderr.strip())
    except Exception:
        subprocess.run(['/bin/launchctl', 'bootout', domain + '/' + LABEL], capture_output=True)
        if backup.exists():
            if runtime.exists(): shutil.rmtree(runtime)
            backup.rename(runtime)
        if old_plist is not None:
            PLIST.write_bytes(old_plist)
            subprocess.run(['/bin/launchctl','bootstrap',domain,str(PLIST)],capture_output=True)
        elif PLIST.exists(): PLIST.unlink()
        raise
    finally:
        if stage.exists(): shutil.rmtree(stage)
    print('Automatic server enabled for this login and future logins. It follows Word opening and quitting.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--resources', type=Path, required=True)
    parser.add_argument('--disable', action='store_true')
    args = parser.parse_args()
    manage(not args.disable, args.resources)
