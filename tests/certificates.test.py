"""Tests use temporary PKI only; no keychain or trust modifications."""
from pathlib import Path
import importlib.util
import ssl
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('certificates', ROOT/'macos/certificates.py')
cert=importlib.util.module_from_spec(spec); spec.loader.exec_module(cert)

class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='pki-test-',dir=ROOT.parents[1]/'work')
        self.manager=cert.Certificates(self.temporary.name)
    def tearDown(self): self.temporary.cleanup()
    def activate(self):
        self.manager.rotate()
        self.manager.enabled.write_text('{"testOnly":true}')
    def test_legacy_untouched_until_approval(self):
        result=self.manager.ensure()
        self.assertEqual(result['mode'],'legacy')
        self.assertFalse(self.manager.root.exists())
    def test_valid_generation_no_unnecessary_renewal(self):
        self.activate(); before=self.manager.current.resolve()
        result=self.manager.ensure()
        self.assertFalse(result['renewed']); self.assertEqual(before,self.manager.current.resolve())
        self.assertEqual(self.manager.root_key.stat().st_mode & 0o777,0o600)
        ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(result['cert'],result['key'])
    def test_due_certificate_rotates_atomically_retains_root(self):
        self.activate(); old=self.manager.current.resolve(); root=self.manager.root.read_bytes()
        with patch.object(cert,'RENEW_BEFORE',826*86400): result=self.manager.ensure()
        self.assertTrue(result['renewed']); self.assertNotEqual(old,self.manager.current.resolve())
        self.assertTrue(old.exists()); self.assertEqual(root,self.manager.root.read_bytes())
        cert.command([cert.OPENSSL,'verify','-purpose','sslserver','-CAfile',str(self.manager.root),result['cert']])
    def test_signing_failure_keeps_current_pair(self):
        self.activate(); old=self.manager.current.resolve(); original=cert.command
        def fail(args):
            if '-req' in args: raise RuntimeError('Simulated signing failure')
            return original(args)
        with patch.object(cert,'command',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'Simulated'): self.manager.ensure(force=True)
        self.assertEqual(old,self.manager.current.resolve())
        ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(str(old/'fullchain.pem'),str(old/'localhost.key'))
    def test_cancelled_trust_keeps_legacy_mode(self):
        original=cert.command
        def deny(args):
            if args[0]=='/usr/bin/security': raise RuntimeError('User cancelled')
            return original(args)
        with patch.object(cert,'command',side_effect=deny):
            with self.assertRaisesRegex(RuntimeError,'cancelled'): self.manager.enable_trust()
        self.assertFalse(self.manager.enabled.exists()); self.assertEqual(self.manager.ensure()['mode'],'legacy')
    def test_generation_cleanup_is_bounded(self):
        self.activate()
        for _ in range(3): self.manager.ensure(force=True)
        self.assertEqual(len(list(self.manager.pki.glob('tls-*'))),2)
    def test_expiring_root_requires_explicit_trust_update(self):
        self.activate(); old=self.manager.current.resolve(); original=cert.valid_for
        with patch.object(cert,'valid_for',side_effect=lambda path,seconds: False if path==self.manager.root else original(path,seconds)):
            with self.assertRaisesRegex(RuntimeError,'one-time'): self.manager.ensure(force=True)
        self.assertEqual(old,self.manager.current.resolve())
    def test_ca_rejects_non_localhost_dns(self):
        self.manager.prepare_root(); p=self.manager.pki
        (p/'bad.cnf').write_text('[req]\ndistinguished_name=dn\nprompt=no\n[dn]\nCN=example.com\n[leaf]\nbasicConstraints=CA:FALSE\nsubjectAltName=DNS:example.com\nextendedKeyUsage=serverAuth\n')
        cert.command([cert.OPENSSL,'req','-new','-newkey','rsa:2048','-nodes','-config',str(p/'bad.cnf'),'-keyout',str(p/'bad.key'),'-out',str(p/'bad.csr')])
        cert.command([cert.OPENSSL,'x509','-req','-in',str(p/'bad.csr'),'-CA',str(self.manager.root),'-CAkey',str(self.manager.root_key),'-set_serial','42','-days','1','-extfile',str(p/'bad.cnf'),'-extensions','leaf','-out',str(p/'bad.crt')])
        with self.assertRaises(RuntimeError): cert.command([cert.OPENSSL,'verify','-purpose','sslserver','-CAfile',str(self.manager.root),str(p/'bad.crt')])
    def test_long_lifetimes_and_macos_ssl_acceptance(self):
        self.activate()
        for path,days in [(self.manager.root,36525),(self.manager.current/'localhost.crt',825)]:
            decoded=ssl._ssl._test_decode_cert(str(path))
            lifetime=ssl.cert_time_to_seconds(decoded['notAfter'])-ssl.cert_time_to_seconds(decoded['notBefore'])
            self.assertEqual(lifetime,days*86400)
        # Explicit temporary anchor; this does not install trust in the keychain.
        cert.command(['/usr/bin/security','verify-cert','-c',str(self.manager.current/'localhost.crt'),
                      '-r',str(self.manager.root),'-p','ssl','-n','localhost','-N','-L'])

if __name__=='__main__': unittest.main(verbosity=2)
