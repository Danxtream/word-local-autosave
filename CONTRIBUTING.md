# Contributing

Local AutoSave is a personal, experimental Word for Mac add-in developed with AI assistance and shared as-is. You can inspect, build and adapt the code under its license. I am not requesting routine bug reports or feature requests, and I do not promise to review, respond to or merge contributions.

## Before making changes

Read the [README](README.md), [test results](TEST-RESULTS.txt), and [engineering review](ENGINEERING-REVIEW.txt). They distinguish automated coverage from behavior that has not been verified inside Word.

The project uses the [GPL-3.0-only license](LICENSE). Submit only code you have the right to contribute and identify third-party code with its source and license. Unless explicitly stated otherwise, contributions submitted for incorporation are provided under the project's GPL-3.0-only license.

## Development setup

The native build requires Apple Silicon, Apple's command-line tools, and Python 3. The current script explicitly selects the MacOSX26.5 SDK. Review [the build instructions](README.md#build-from-source) before running it on a different development environment. Node.js is needed for JavaScript tests.

The private harness used by the maintainer is not required to build or test this project.

```sh
node --test tests/engine.test.cjs tests/pane.test.cjs
python3 tests/installer.test.py
python3 tests/certificates.test.py
python3 tests/watcher.test.py
python3 macos/build.py
```

The original Python test snapshot assumes a temporary `dev/work` location; path corrections are being reviewed separately. Record this prerequisite if a fresh checkout cannot run those tests. Do not alter installed certificates or broaden system trust just to make a test pass.

## Testing saving behavior

Use disposable `.docx` files and the [live test guide](web/help.html). To demonstrate a save, verify the original file's contents on disk while Word is still open. A timer tick, an “Active” status, a mock API response, or choosing Save when closing Word is not equivalent evidence.

When documenting your own behavior changes, record the Word/macOS versions, the document's local or synced location, pane visibility, interval, and whether Word was foregrounded. Check failure cases as well as successful saves. Automated tests must not modify personal documents or installed trust settings.

## Your own changes

Keep your own development notes and tests free of personal documents, secrets and machine-specific details. Forks and local adaptations do not create an obligation for this project to maintain or support them.

If you choose to submit a change, keep it focused and include applicable test results; review or acceptance is not promised. Describe any new permissions, network destinations, background processes or installation steps. Preserve third-party attribution and avoid committing generated builds, private keys or machine-specific configuration.

Optional security reporting is described in [SECURITY.md](SECURITY.md). No response, investigation or fix is promised.
