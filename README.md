<p align="center">
  <img src="docs/assets/app-icon.svg" width="112" height="112" alt="Local AutoSave app icon">
</p>

<h1 align="center">Local AutoSave</h1>

<p align="center">
  Timed saving for local Word documents on your Mac.<br>
  Save to the original file through Word's own API.
</p>

<p align="center">
  <img src="docs/assets/badge-version.svg" alt="Version 0.1">
  <img src="docs/assets/badge-status.svg" alt="Experimental build">
  <img src="docs/assets/badge-platform.svg" alt="macOS, Apple Silicon">
  <a href="LICENSE"><img src="docs/assets/badge-license.svg" alt="GPL-3.0 license"></a>
</p>

<p align="center">
  <a href="#overview">Overview</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#usage">Usage</a> ·
  <a href="#limitations">Limitations</a> ·
  <a href="#development">Development</a> ·
  <a href="https://danxtream.gumroad.com/coffee">Donate</a>
</p>

## Overview

Local AutoSave adds timed saving to existing local Word documents. It saves to the original file through Word's API, with an interval and on/off setting for each document.

The current version is an experimental Mac build. Automated checks cover the scheduler and local helpers, but reliable background saving and operation with the task pane closed still need live Word testing. Use disposable documents while testing and keep saving important work manually.

## Features

- Saves to the existing document without changing its name or creating a separate backup file.
- Keeps the enable/disable preference and save interval per document. The default is off, with a 30-second interval; a one-second setting is available for testing.
- Skips unchanged documents and prevents overlapping saves within a document's runtime.
- Shows the last acknowledged save and errors in a Word task pane.
- Starts a local HTTPS asset server when Word opens and stops it when Word quits. A small native watcher stays resident while automatic mode is enabled.

## Requirements

- **Mac:** Apple Silicon. The launcher targets macOS 13 or newer; the recorded test environment is macOS 26.6. Other macOS versions have not been broadly tested.
- **Word:** a licensed installation with WordApi 1.5 and SharedRuntime 1.1 support. The add-in checks these APIs when it loads.
- **Local helper:** Python 3 available at `/usr/bin/python3`.
- **Network:** access to Microsoft's Office.js CDN when loading the add-in.

## Installation

A compiled Mac app is planned for Gumroad. There is no published download linked here yet; the current version must be built from source.

1. Install Apple's command-line development tools and check the SDK path in [macos/build.py](macos/build.py). It currently selects **MacOSX26.5.sdk** explicitly.
2. From the source directory, build the launcher:

   ```sh
   python3 macos/build.py
   ```

3. Open `Local AutoSave Test.app` and follow the included test guide to install the Word add-in, approve localhost certificate trust, and enable the local helper.
4. Restart Word after saving your open work, then open a disposable local `.docx` and select **Local AutoSave** from Word's Home/add-ins menu.

The app is locally signed, not Developer ID signed or notarized. Building it does not install the add-in or grant certificate trust. Automatic certificate renewal requires a separate one-time approval in the launcher.

The [full setup and test guide](web/help.html) covers certificate approval and removal. Open your local copy in a browser to read it; GitHub displays the HTML source.

## Usage

1. Save a new document normally before enabling Local AutoSave.
2. Open the add-in, select an interval, and turn it on for that document.
3. Check the last acknowledged save and any errors in the task pane. While testing, verify the original file's contents on disk while Word is still open.

A visible “Active” status alone does not prove a save occurred. Enable or disable the add-in separately for each document. Changing its settings also requests a save of current edits.

For removal, turn the add-in off in enabled documents and follow the guide's **Remove** section. It covers the background watcher, add-in manifest, local certificates, and application-support files.

## Limitations

- It is a separate add-in, not a switch that enables Microsoft's built-in AutoSave. It does not provide version history, crash recovery, or a guaranteed final save when Word closes.
- The interval is a scheduling target, not a physical disk-flush guarantee. Sleep, dialogs, and Word's runtime can delay work.
- Background operation, closed-pane saving, Finder reopen behavior, and real file-error handling need live Word tests.
- New unsaved documents and recognized cloud URLs are refused. A synced directory reported as a local path cannot be distinguished from an ordinary local directory.
- Initial add-in loading can race the local server's startup. New loads require the server to be available.
- There is no automatic application updater. Source changes must be rebuilt and installed; certificate renewal updates certificates, not application code.

## Security and privacy

The add-in requests read/write access to the current Word document so it can save it. The helper serves static assets over HTTPS on `127.0.0.1:43187`; the saving code does not upload document contents or add telemetry. Office.js loads from Microsoft's CDN, so this setup is not fully offline. Word and separate folder-sync software may make their own network requests.

Certificates and private keys are generated on the user's Mac. Automatic renewal uses user-level trust restricted to SSL for `localhost`. Server certificates last 825 days and renew 30 days early. The approximately 100-year local signing certificate is a personal-use convenience tradeoff: keep its private key private and remove its trust if the key is exposed. Replacing its trust requires approval.

Local AutoSave has not received an independent security audit. More implementation detail is in the [engineering review](ENGINEERING-REVIEW.txt).

## Development

The add-in UI and save scheduler are in `web/`. The native launcher, background watcher, local server and certificate code are in `macos/`; `manifest.xml` registers the Word add-in.

See [CONTRIBUTING.md](CONTRIBUTING.md) for build/test commands. Node.js is needed for the JavaScript tests. The Python test scripts in this snapshot assume a temporary `dev/work` location; path corrections are being reviewed separately.

See [TEST-RESULTS.txt](TEST-RESULTS.txt) and [ENGINEERING-REVIEW.txt](ENGINEERING-REVIEW.txt) for the recorded results and remaining checks.

## Maintenance

This is a personal project developed with AI assistance and shared for others who find it useful. The software is provided as-is. I do not promise technical support, bug fixes, new features or ongoing maintenance. I update it at my discretion, when I consider it worthwhile; there is no release schedule. Donations do not create any entitlement to support or updates.

## License

Local AutoSave is licensed under the [GNU General Public License, version 3 only](LICENSE) (GPL-3.0-only); see [NOTICE.md](NOTICE.md). Third-party components and Microsoft services retain their own terms.

Local AutoSave is independently developed and is not affiliated with or endorsed by Microsoft. Users need their own licensed Word installation.

## Donate

If you find Local AutoSave useful and would like to support my work, please consider [making a donation](https://danxtream.gumroad.com/coffee).
