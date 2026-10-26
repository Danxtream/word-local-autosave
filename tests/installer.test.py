from pathlib import Path
import importlib.util
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('manage',ROOT/'macos/manage-watcher.py')
manage=importlib.util.module_from_spec(spec);spec.loader.exec_module(manage)

class InstallerTests(unittest.TestCase):
    def test_failed_service_update_restores_previous_runtime_and_plist(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parents[1]/'work') as temporary:
            base=Path(temporary); support=base/'support'; runtime=support/'runtime'; runtime.mkdir(parents=True)
            (runtime/'old-version').write_text('working'); plist=base/'agent.plist';plist.write_bytes(b'original plist')
            source=base/'source';source.mkdir();(source/'web').mkdir()
            for name in ('WordWatcher','server.py','certificates.py','web/taskpane.html'): (source/name).write_text('new')
            attempts=[]
            def run(args,**kwargs):
                attempts.append(args)
                # New bootstrap fails; rollback bootstrap succeeds.
                fail='bootstrap' in args and sum('bootstrap' in a for a in attempts)==1
                return subprocess.CompletedProcess(args,1 if fail else 0,stdout='',stderr='simulated startup failure' if fail else '')
            with patch.object(manage,'SUPPORT',support),patch.object(manage,'PLIST',plist),patch.object(manage.subprocess,'run',side_effect=run):
                with self.assertRaisesRegex(RuntimeError,'simulated'): manage.manage(True,source)
            self.assertEqual((runtime/'old-version').read_text(),'working')
            self.assertEqual(plist.read_bytes(),b'original plist')
            self.assertEqual(sum('bootstrap' in a for a in attempts),2)
    def test_incomplete_update_never_stops_working_agent(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parents[1]/'work') as temporary:
            base=Path(temporary)
            with patch.object(manage,'SUPPORT',base/'support'),patch.object(manage.subprocess,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'incomplete'):manage.manage(True,base/'missing')
                run.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
