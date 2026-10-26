/* global Office, Word, LocalAutoSave, makeOfficeHost */
'use strict';
let engine, ready = false, paintedAt = Date.now();
let paneVisible = !document.hidden, latest;
let displayedSave, watchdog = null;
const $ = id => document.getElementById(id);
const put = (id, property, value) => { const node = $(id); if (node[property] !== value) node[property] = value; };
function render(s) {
  latest = { ...s };
  if (!paneVisible || document.hidden) return;
  paintedAt = Date.now();
  put('enabled', 'checked', s.enabled);
  put('onoff', 'textContent', s.enabled ? 'ON' : 'OFF');
  put('interval', 'value', String(s.interval));
  put('enabled', 'disabled', !ready || !!s.configuring);
  put('interval', 'disabled', !ready || !!s.configuring);
  put('retry', 'disabled', !ready || !s.enabled || !!s.configuring);
  const normal = s.enabled && ['Checking', 'Saving', 'Saved', 'Active'].includes(s.phase);
  put('badge', 'textContent', s.error ? 'Error' : normal ? 'Active' : s.phase);
  put('badge', 'className', 'badge' + (s.error || s.phase === 'Error' ? ' error' : ''));
  put('message', 'textContent', s.error || (s.phase === 'Disabled' ? 'Automatic saving is disabled for this document.' :
    normal ? 'AutoSave is running. Changes are saved automatically.' : s.phase + '…'));
  if (displayedSave !== s.lastSave) {
    displayedSave = s.lastSave;
    put('last', 'textContent', 'Last confirmed save: ' + (s.lastSave ? new Date(s.lastSave).toLocaleTimeString() : 'none this session'));
  }
  // No per-tick date formatting, JSON allocation or diagnostic DOM updates
  // unless the user has expanded diagnostics in the visible task pane.
  if ($('details').open) {
    put('heartbeat', 'textContent', s.lastCheck ? 'Last scheduler check: ' + new Date(s.lastCheck).toLocaleTimeString() : 'No scheduler check this session.');
    put('activity', 'textContent', 'Live activity: ' + s.phase);
    put('diagnostics', 'textContent', JSON.stringify({ ...s,
      wordVersion: typeof Office !== 'undefined' && Office.context && Office.context.diagnostics.version,
      visibility: document.visibilityState }, null, 2));
  }
}
async function change() {
  try { await engine.configure($('enabled').checked, Number($('interval').value)); }
  catch (error) { engine.failure(error); }
}
$('enabled').addEventListener('change', change);
$('interval').addEventListener('change', change);
$('retry').addEventListener('click', () => engine.tick());
$('details').addEventListener('toggle', () => { if (latest) render(latest); });
function resume() {
  updateWatchdog();
  if (!engine || !paneVisible || document.hidden) return;
  render({ ...engine.state, busy: engine.busy });
  if (engine.state.enabled) void engine.tick();
}
if (typeof Office !== 'undefined') Office.onReady(async () => {
  engine = new LocalAutoSave.Engine(makeOfficeHost(Office, Word), render);
  try { await engine.host.checkSupport(); ready = true; } catch (error) { engine.failure(error); return; }
  await engine.init();
  try {
    Office.addin.onVisibilityModeChanged(args => {
      paneVisible = args.visibilityMode === Office.VisibilityMode.taskpane;
      resume();
    });
  } catch (error) { engine.failure(new Error('Shared runtime visibility hook failed: ' + error.message)); }
});
// A hidden pane still saves; only interface work is suppressed.
document.addEventListener('visibilitychange', resume);
window.addEventListener('pagehide', () => { if (engine) engine.dispose(); });
function checkRuntime() {
  if (!paneVisible || document.hidden) return;
  if (!engine) {
    if (Date.now() - paintedAt > 20000) put('message', 'textContent', 'Word has not connected. Check automatic server mode, certificate trust, and internet access to Microsoft’s Office.js CDN.');
    return;
  }
  const s = engine.state;
  if (s.enabled && s.lastCheck && Date.now() - s.lastCheck > Math.max(s.interval * 3000, 15000)) {
    put('badge', 'textContent', 'Unconfirmed');
    put('message', 'textContent', 'No recent scheduler check. Automatic saving is not confirmed; use Word’s normal Save command.');
  }
}
function updateWatchdog() {
  const visible = paneVisible && !document.hidden;
  if (visible && watchdog === null) watchdog = setInterval(checkRuntime, 5000);
  else if (!visible && watchdog !== null) { clearInterval(watchdog); watchdog = null; }
}
updateWatchdog();
window.addEventListener('pagehide', () => clearInterval(watchdog));
