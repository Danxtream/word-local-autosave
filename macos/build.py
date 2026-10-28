# Copyright (C) 2026 Danxtream.
# Licensed under GPL-3.0-only with an additional term under section 7(b); see LICENSE and NOTICE.md.
"""Build the test launcher using Apple's installed command line tools."""
from pathlib import Path
import plistlib
import shutil
import subprocess
import zlib
import struct

root = Path(__file__).resolve().parents[1]
app = root / 'Local AutoSave Test.app'
contents = app / 'Contents'
resources = contents / 'Resources'
(contents / 'MacOS').mkdir(parents=True, exist_ok=True)
resources.mkdir(parents=True, exist_ok=True)

# Code-generated raster save icon; no downloaded assets.
def png(size):
    def chunk(kind, data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            white = (size*.24<x<size*.76 and size*.18<y<size*.78)
            green = (size*.35<x<size*.65 and size*.2<y<size*.39) or (size*.35<x<size*.65 and size*.52<y<size*.71)
            row.extend((255,255,255,255) if white and not green else (38,105,75,255))
        rows.append(bytes(row))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
for size in (16,32,80):
    (root/'web'/f'icon-{size}.png').write_bytes(png(size))

shutil.copytree(root/'web', resources/'web', dirs_exist_ok=True)
shutil.copy2(root/'manifest.xml', resources/'manifest.xml')
shutil.copy2(root/'LICENSE', resources/'LICENSE')
shutil.copy2(root/'NOTICE.md', resources/'NOTICE.md')
shutil.copy2(root/'macos/server.py', resources/'server.py')
shutil.copy2(root/'macos/manage-watcher.py', resources/'manage-watcher.py')
shutil.copy2(root/'macos/certificates.py', resources/'certificates.py')
info = dict(CFBundleExecutable='LocalAutoSaveTest', CFBundleIdentifier='local.autosave.word.test',
            CFBundleName='Local AutoSave Test', CFBundlePackageType='APPL', CFBundleShortVersionString='0.1.0',
            CFBundleVersion='1', LSMinimumSystemVersion='13.0', NSHighResolutionCapable=True,
            NSHumanReadableCopyright='© 2026 Danxtream. Free software under GNU GPL version 3 only, with an author-attribution term under section 7(b). You may share and change it under those terms. No warranty. See the installation guide for legal notices and https://www.gnu.org/licenses/gpl-3.0.html for the license.')
(contents/'Info.plist').write_bytes(plistlib.dumps(info))
subprocess.run(['xcrun','swiftc','-sdk','/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk','-target','arm64-apple-macos13.0','-O',str(root/'macos/WordWatcher.swift'),'-o',str(resources/'WordWatcher'),'-framework','AppKit'],check=True)
subprocess.run(['codesign','--force','--sign','-',str(resources/'WordWatcher')],check=True)
subprocess.run(['xcrun','swiftc','-sdk','/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk','-target','arm64-apple-macos13.0','-O',str(root/'macos/Launcher.swift'),'-o',str(contents/'MacOS/LocalAutoSaveTest'),'-framework','AppKit'],check=True)
subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
print(app)
