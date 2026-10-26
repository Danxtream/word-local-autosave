Local AutoSave — experimental v0.1 for Word on this Apple Silicon Mac

Start with Local AutoSave Test.app. Full installation and live testing steps:
web/help.html (also accessible from the test app).

The launcher installs a Word add-in manifest, offers a machine-generated localhost
certificate for manual SSL trust in Keychain Access, and installs a native Word lifecycle watcher. The loopback-only HTTPS server
starts when Word opens and stops when Word quits. The watcher starts at login;
the setup app can be closed after enabling automatic mode. The add-in saves through supported Word APIs.
No custom document launcher, keyboard shortcut simulation, activation, telemetry,
document upload, or external backup file is used by the saving code.

This is a test package, not a validated protection tool. Actual Word save, pane
closure, background operation, Finder reopen, and typing tests remain pending.
Use only disposable local .docx files. Do not rely on it for important work yet.

Source:
  web/engine.js          scheduler, path guard, operation lock, state
  web/office-host.js     Office.js adapter
  web/taskpane.*         Word UI
  manifest.xml          long shared runtime and Home ribbon control
  macos/Launcher.swift  native installer/server controller
  macos/server.py       static HTTPS server, no uploads
  macos/certificates.py  atomic TLS renewal and explicit constrained trust setup
  macos/WordWatcher.swift native app lifecycle watcher and server supervision
  macos/manage-watcher.py installs/removes this user's LaunchAgent
  macos/build.py        build launcher, watcher and generated icons
  tests/engine.test.cjs  Node's built-in test runner; no third-party test modules

Automated test command (with Node available):
  node --test tests/engine.test.cjs

Build on this Mac:
  python3 macos/build.py
The build explicitly selects the installed MacOSX26.5 SDK because the default
MacOSX27 SDK doesn't match this Mac's installed Swift compiler. Change that SDK
path and architecture target when building on another machine.

Office add-in manifest version is 1.0.0.1 because Microsoft's validator rejects
manifest versions below 1.0. The user-facing experimental release is v0.1.

No certificate/private key is distributed in this package. Those are generated
on first use under ~/Library/Application Support/Local AutoSave Test with a
90-day validity. Use button 4 in the setup app for one-time localhost-only SSL
trust setup and automatic server-certificate renewal. New server certificates last 825 days and renew 30 days early; it
checks at most daily, and preserves the previous pair on failure. The local
signing certificate lasts approximately 100 years and needs explicit approval when replaced.
Python 3 from this Mac's developer tools is needed to serve it.
Automatic mode uses ~/Library/LaunchAgents/local.autosave.word.watcher.plist.
Disable it through the setup app before uninstalling. No production installer yet.

See TEST-RESULTS.txt for the precise validation boundary.
