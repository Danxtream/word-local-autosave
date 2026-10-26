<p align="center">
  <img src="docs/assets/app-icon.svg" width="112" height="112" alt="Local AutoSave app icon">
</p>

<h1 align="center">Local AutoSave</h1>

<p align="center">
  Timed saving for local Word documents on your Mac.<br>
  Save to the original file through Word's own API.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1-27694b" alt="Version 0.1">
  <img src="https://img.shields.io/badge/status-experimental-d49a35" alt="Experimental build">
  <img src="https://img.shields.io/badge/platform-macOS%20%C2%B7%20Apple%20Silicon-555555" alt="macOS, Apple Silicon">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-27694b" alt="GPL-3.0 license"></a>
</p>

<p align="center">
  <a href="#get-started">Get started</a> ·
  <a href="#what-it-does">Features</a> ·
  <a href="#build-from-source">Build</a> ·
  <a href="#testing-and-known-limits">Testing</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="SECURITY.md">Security</a> ·
  <a href="https://danxtream.gumroad.com/coffee">Support</a>
</p>

**Status: personal test build, v0.1.** Automated checks cover the scheduler and local infrastructure. Scheduled writes to real documents, operation with the task pane closed, and background saving still need live validation. Use disposable documents while testing and keep saving important work manually.

## Get started

This is a source-build preview, with no public release download linked yet. Start with [Build from source](#build-from-source), then follow [Set up and test](#set-up-and-test) using a disposable document. The [full test guide](web/help.html) covers setup, certificate approval, live checks and removal.

## What it does

- Requests saves to the document's existing local destination, without creating a backup copy or changing its name.
- Keeps the enable/disable preference and save interval per document. The default is off, with a 30-second interval; a one-second setting is available for testing.
- Skips unchanged documents and prevents overlapping saves within a document's runtime.
- Shows the last acknowledged save and errors in a Word task pane.
- Starts a local HTTPS asset server when Word opens and stops it when Word quits. A small native watcher stays resident while automatic mode is enabled.

It is a separate add-in, not a switch that enables Microsoft's built-in AutoSave. It does not provide version history, crash recovery, or a guaranteed final save when Word closes.

## Requirements

- An Apple Silicon Mac. The native launcher targets macOS 13 or newer; the recorded test environment is macOS 26.6.
- Microsoft Word licensed to edit and save documents, with WordApi 1.5 and SharedRuntime 1.1 support. The add-in checks these APIs at runtime; broad version compatibility has not been tested.
- Python 3 available at `/usr/bin/python3` for the local server, and Apple's command-line development tools to build the native launcher.
- Internet access to Microsoft's Office.js CDN when loading the add-in.
- Node.js to run the JavaScript tests; it is not used by the installed save scheduler.

## Build from source

There is no public release download linked here yet. This checkout includes a build script for the experimental launcher:

```sh
python3 macos/build.py
```

The script currently selects the **MacOSX26.5 SDK explicitly** and builds for Apple Silicon. Check the SDK path in [macos/build.py](macos/build.py) against your installed tools before building. The build is not yet portable across arbitrary Mac development setups.

The output is `Local AutoSave Test.app`. It is locally signed, not Developer ID signed or notarized. Building does not install the Word add-in or grant certificate trust.

## Set up and test

Open the built launcher and follow the [test guide](web/help.html), which is also available through the app. GitHub displays that file as source; open your local copy in a browser to read the formatted guide.

The current setup installs an add-in manifest, asks you to trust a certificate for the local HTTPS server, and offers automatic server operation with Word. Automatic certificate renewal has a separate one-time approval step. These steps are still being refined.

After setup, open a disposable, already-saved local `.docx` in Word and open **Local AutoSave** from the Home ribbon/add-ins menu. Enable it for that document and verify the original file on disk independently. A visible “Active” status alone does not prove a save occurred.

For removal, turn the add-in off in enabled documents and follow the guide's **Remove** section. It covers the background watcher, add-in manifest, local certificates, and application-support files.

## Permissions and data

The add-in requests read/write access to the current Word document so it can save it. The save adapter uses supported Office.js APIs; it does not simulate keystrokes or activate Word to press Save.

The helper serves static assets over HTTPS on `127.0.0.1:43187`. Document contents are not sent to that server, and the saving code does not upload documents or add telemetry. Office.js loads from Microsoft's CDN, so this setup is not fully offline. A document in a locally mounted synced folder may still be uploaded by the user's separate sync software.

Certificates and private keys are generated on the user's Mac. Automatic renewal uses user-level trust restricted to SSL for `localhost`, rather than a shared private key. Server certificates last 825 days and renew 30 days early; the local signing certificate's approximately 100-year lifetime is a personal-use convenience tradeoff that needs review before wider distribution. Replacing its trust requires approval.

## Testing and known limits

Recorded checks cover scheduling, path eligibility, per-document preferences, save-adapter behavior, installation rollback, temporary certificate renewal, and a synthetic Word-lifecycle test using real verified TLS. They do not establish reliable unattended saving inside Word.

Run the automated checks from the source directory:

```sh
node --test tests/engine.test.cjs tests/pane.test.cjs
python3 tests/installer.test.py
python3 tests/certificates.test.py
python3 tests/watcher.test.py
```

The Python test scripts in this original snapshot assume a temporary `dev/work` location. Repairs are being reviewed separately; these commands may need that path correction on a fresh checkout.

Important limits remain:

- The interval is a scheduling target, not a physical disk-flush guarantee. Sleep, dialogs, and Word's runtime can delay work.
- Background operation, closed-pane saving, Finder reopen behavior, and real file-error handling need live Word tests.
- New unsaved documents and recognized cloud URLs are refused. A synced directory reported as a local path cannot be distinguished from an ordinary local directory.
- Initial add-in loading can race the local server's startup. New loads require the server to be available.
- There is no automatic application updater. Source changes must be rebuilt and installed; the existing certificate-renewal process updates certificates, not application code.

See [TEST-RESULTS.txt](TEST-RESULTS.txt) and [ENGINEERING-REVIEW.txt](ENGINEERING-REVIEW.txt) for the recorded results and remaining checks.

## Source layout

| Location | Purpose |
| --- | --- |
| `web/engine.js` | Scheduler, path checks, preferences and operation locking |
| `web/office-host.js` | Word API adapter |
| `web/taskpane.*` | Add-in interface |
| `manifest.xml` | Word add-in registration and shared runtime |
| `macos/` | Native launcher/watcher, local server, certificates and build scripts |
| `tests/` | Automated behavior and infrastructure checks |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development requirements, useful bug reports and the distinction between automated tests and live Word validation. Installation and certificate setup can be improved without changing the saving behavior.

## Security

See [SECURITY.md](SECURITY.md) for the trust model, sensitive files and vulnerability reporting. Do not include documents, certificate private keys or private logs in public reports.

## License and project status

Local AutoSave is licensed under the [GNU General Public License, version 3 only](LICENSE) (GPL-3.0-only); see [NOTICE.md](NOTICE.md). This README previews the planned project page.

Local AutoSave is independently developed and is not affiliated with or endorsed by Microsoft. Users need their own licensed Word installation.

## Support development

If this project is useful to you, you can [leave an optional contribution on Gumroad](https://danxtream.gumroad.com/coffee). Contributions support development and do not purchase support, a release date, or promised features.
