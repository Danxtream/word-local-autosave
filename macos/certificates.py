# Copyright (C) 2026 Danxtream.
# Licensed under GPL-3.0-only with an additional term under section 7(b); see LICENSE and NOTICE.md.
"""Local-only TLS lifecycle. No keychain changes except explicit --enable-trust.

Legacy TLS remains untouched until the user approves the one-time CA setup.
Renewals publish validated certificate/key generations with one atomic symlink.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import secrets
import shutil
import ssl
import subprocess
import tempfile
import time

OPENSSL = '/usr/bin/openssl'
RENEW_BEFORE = 30 * 86400
ROOT_VALIDITY_DAYS = 36525  # Approximately 100 years; deliberately local/private.
SERVER_VALIDITY_DAYS = 825  # Longest server lifetime verified with macOS SSL policy.

def command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Certificate operation failed')
    return result.stdout

def valid_for(cert, seconds):
    return subprocess.run([OPENSSL, 'x509', '-in', str(cert), '-noout', '-checkend', str(seconds)],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5).returncode == 0

def atomic_text(path, text):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(text)
    os.chmod(temporary, 0o600)
    temporary.replace(path)

class Certificates:
    def __init__(self, support):
        self.support = Path(support)
        self.pki = self.support / 'pki'
        self.pki.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.pki, 0o700)
        self.root = self.pki / 'root.crt'
        self.root_key = self.pki / 'root.key'
        self.current = self.pki / 'current'
        self.enabled = self.pki / 'enabled.json'

    def prepare_root(self):
        if self.root.exists() or self.root_key.exists():
            if not (self.root.exists() and self.root_key.exists()):
                raise RuntimeError('Local signing certificate/key is incomplete. Existing trust will not be silently replaced.')
            command([OPENSSL, 'verify', '-CAfile', str(self.root), str(self.root)])
            # Verify the private key belongs to this root before any signing.
            cert_public = command([OPENSSL, 'x509', '-in', str(self.root), '-pubkey', '-noout'])
            key_public = command([OPENSSL, 'pkey', '-in', str(self.root_key), '-pubout'])
            if cert_public.strip() != key_public.strip():
                raise RuntimeError('Local signing certificate/key mismatch.')
            return
        with tempfile.TemporaryDirectory(prefix='root-', dir=self.pki) as temporary:
            folder = Path(temporary)
            config = folder / 'root.cnf'
            config.write_text('''[req]
distinguished_name=dn
x509_extensions=ca
prompt=no
[dn]
CN=Local AutoSave localhost Renewal CA
[ca]
basicConstraints=critical,CA:TRUE,pathlen:0
keyUsage=critical,keyCertSign,cRLSign
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always
nameConstraints=critical,permitted;DNS:localhost
''')
            command([OPENSSL, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256', '-days', str(ROOT_VALIDITY_DAYS),
                     '-keyout', str(folder/'root.key'), '-out', str(folder/'root.crt'), '-config', str(config)])
            os.chmod(folder/'root.key', 0o600)
            (folder/'root.key').replace(self.root_key)
            (folder/'root.crt').replace(self.root)

    def rotate(self, validity_days=SERVER_VALIDITY_DAYS):
        self.prepare_root()
        if validity_days < 1 or validity_days > SERVER_VALIDITY_DAYS:
            raise ValueError('Server certificate lifetime must be between 1 and 825 days.')
        if not valid_for(self.root, (validity_days + 1) * 86400):
            raise RuntimeError('Local signing certificate needs a one-time trust update before it expires. Open the setup app. Existing certificate was kept.')
        name = 'tls-' + str(int(time.time())) + '-' + secrets.token_hex(4)
        generation = self.pki / name
        generation.mkdir(mode=0o700)
        try:
            config = generation / 'leaf.cnf'
            config.write_text('''[req]
distinguished_name=dn
prompt=no
[dn]
CN=localhost
[leaf]
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
''')
            key, leaf = generation/'localhost.key', generation/'localhost.crt'
            command([OPENSSL, 'req', '-new', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key),
                     '-out', str(generation/'request.csr'), '-config', str(config)])
            os.chmod(key, 0o600)
            command([OPENSSL, 'x509', '-req', '-in', str(generation/'request.csr'), '-CA', str(self.root),
                     '-CAkey', str(self.root_key), '-set_serial', '0x'+secrets.token_hex(16), '-days', str(validity_days), '-sha256',
                     '-extfile', str(config), '-extensions', 'leaf', '-out', str(leaf)])
            command([OPENSSL, 'verify', '-purpose', 'sslserver', '-CAfile', str(self.root), str(leaf)])
            # Loading the pair validates its match. Hostname is checked by live TLS tests.
            ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(str(leaf), str(key))
            (generation/'fullchain.pem').write_bytes(leaf.read_bytes()+self.root.read_bytes())
            link = self.pki/'current.next'
            if link.is_symlink(): link.unlink()
            link.symlink_to(name, target_is_directory=True)
            link.replace(self.current)
            # Keep current plus the previous generation for recovery; prevent key accumulation.
            generations = sorted(self.pki.glob('tls-*'), key=lambda p:p.stat().st_mtime, reverse=True)
            for old in generations[2:]:
                if old.is_dir() and not old.is_symlink(): shutil.rmtree(old)
        except Exception:
            if not self.current.exists() or self.current.resolve() != generation:
                shutil.rmtree(generation)
            raise

    def ensure(self, force=False):
        if not self.enabled.exists():
            return dict(cert=str(self.support/'localhost.crt'), key=str(self.support/'localhost.key'),
                        renewed=False, mode='legacy', warning='Automatic renewal needs one-time setup in the app.')
        self.prepare_root()
        renewed = force or not valid_for(self.current/'localhost.crt', RENEW_BEFORE)
        if renewed: self.rotate()
        warning = '' if valid_for(self.root, (SERVER_VALIDITY_DAYS + 31) * 86400) else 'Local signing certificate is approaching the end of its usable issuing period; a one-time trust update is needed.'
        return dict(cert=str(self.current/'fullchain.pem'), key=str(self.current/'localhost.key'), renewed=renewed,
                    mode='automatic', warning=warning)

    def enable_trust(self):
        self.prepare_root()
        # Stage a real leaf before the user approves trust. Never alter global security policy.
        if not valid_for(self.current/'localhost.crt', RENEW_BEFORE): self.rotate()
        command(['/usr/bin/security', 'add-trusted-cert', '-r', 'trustRoot', '-p', 'ssl', '-s', 'localhost',
                 '-k', str(Path.home()/'Library/Keychains/login.keychain-db'), str(self.root)])
        command(['/usr/bin/security', 'verify-cert', '-c', str(self.current/'localhost.crt'),
                 '-p', 'ssl', '-s', 'localhost'])
        atomic_text(self.enabled, json.dumps(dict(enabledAt=int(time.time()), version=1)))
        return self.ensure()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--support', type=Path, default=Path.home()/'Library/Application Support/Local AutoSave Test')
    parser.add_argument('--enable-trust', action='store_true')
    args = parser.parse_args()
    manager = Certificates(args.support)
    with (manager.pki/'manager.lock').open('a') as lock:
        os.chmod(manager.pki/'manager.lock', 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = manager.enable_trust() if args.enable_trust else manager.ensure()
        print(json.dumps(result))
