# Security

## Project status

Local AutoSave v0.1 is experimental. It has not received an independent security audit, and no security response time or long-term maintenance commitment is promised. Use disposable documents until live saving and recovery behavior has been verified for your environment.

## Optional security reports

You may report a suspected security vulnerability through **Security → Report a vulnerability**, if that private option is available. No dedicated security email or alternate private reporting channel is published here. Do not put sensitive vulnerability details in a public issue.

Reporting is optional. I do not promise acknowledgment, investigation, a fix, a response time or continuing maintenance. This is a personal project shared as-is, not a supported product. If you choose to report, use a minimal synthetic example and do not send personal documents, certificate private keys or unredacted logs. This document does not assert that private reporting is currently enabled.

## Data and trust model

- The Word add-in requests read/write access to its current document and calls Word's save API.
- The HTTPS helper binds to `127.0.0.1` and serves a fixed allowlist of static add-in files. It has no document-upload endpoint. The save adapter does not send document contents to this helper.
- Office.js is loaded from Microsoft's CDN. This is a network dependency; the app is not fully offline. Other software, including a user's folder-sync service, can still transmit documents independently.
- Certificate private keys are generated per Mac. Automatic renewal uses a locally generated signing certificate and user-level trust constrained to SSL for `localhost`. It does not require disabling Gatekeeper or trusting every certificate purpose.
- The local signing certificate currently lasts approximately 100 years. Its long lifetime is a personal-use tradeoff, not a reviewed public-release policy. Private-key compromise matters even though trust is constrained.
- A user LaunchAgent runs the watcher; the HTTPS server follows Word's lifetime. Closing a Word window is not equivalent to quitting Word.
- There is no automatic application updater. Rebuilding and installing code is separate from automatic TLS certificate renewal.

## Sensitive local files

Treat the contents of `~/Library/Application Support/Local AutoSave Test` as private. It includes runtime files, certificates, private keys and lifecycle information. Never upload private keys or copy one machine's signing material into a public release. Redact user names and paths from diagnostics.

The saving code adds no telemetry, but this is not a claim that Word, macOS or Microsoft's CDN makes no network requests.

## Removal and suspected compromise

Follow the **Remove** section of the [test guide](web/help.html) to disable the watcher and remove the add-in and its local certificate trust. Keep your documents. If you suspect a private key was exposed, stop using that certificate and remove its trust; deleting a leaked file alone does not revoke copies of its key.
