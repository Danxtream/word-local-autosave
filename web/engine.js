(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.LocalAutoSave = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const intervals = [1, 5, 10, 30, 60];
  function localPath(value) {
    if (typeof value !== 'string' || !value) throw new Error('Save this document manually to a local .docx file first, then try again.');
    let path = value;
    if (/^file:\/\//i.test(value)) {
      const url = new URL(value);
      if (url.hostname && url.hostname !== 'localhost') throw new Error('Network file locations are not supported in this test version.');
      path = decodeURIComponent(url.pathname);
    }
    if (!path.startsWith('/') || path.startsWith('//') || !/\.docx$/i.test(path)) {
      throw new Error('Word must report an existing local .docx path. Save locally once, then try again.');
    }
    return path;
  }
  class Engine {
    constructor(host, changed = () => {}, clock = {}) {
      this.host = host;
      this.changed = changed;
      this.now = clock.now || Date.now;
      // WKWebView requires Window as the receiver for native timer methods.
      // Storing the methods directly here would call them with Engine as `this`.
      this.setInterval = clock.setInterval
        ? (...args) => clock.setInterval(...args)
        : (...args) => globalThis.setInterval(...args);
      this.clearInterval = clock.clearInterval
        ? (...args) => clock.clearInterval(...args)
        : (...args) => globalThis.clearInterval(...args);
      this.state = { enabled: false, interval: 30, phase: 'Starting', configuring: false, error: '', lastSave: null,
        lastCheck: null, requests: 0, completions: 0, skippedBusy: 0, skippedClean: 0, path: '' };
      this.busy = false;
      this.idleWaiters = [];
      this.disposed = false;
      this.timer = null;
    }
    emit() { this.changed({ ...this.state, busy: this.busy }); }
    failure(error) {
      this.state.phase = 'Error';
      this.state.error = error && error.message ? error.message : String(error);
      this.emit();
    }
    async init() {
      try {
        await this.host.checkSupport();
        const pref = this.host.readPreference();
        this.state.interval = pref && intervals.includes(pref.interval) ? pref.interval : 30;
        this.state.enabled = !!(pref && pref.enabled === true);
        this.state.phase = this.state.enabled ? 'Checking' : 'Disabled';
        if (this.state.enabled) { this.schedule(); await this.tick(); }
        else this.emit();
      } catch (error) { this.failure(error); }
    }
    schedule() {
      if (this.timer !== null) this.clearInterval(this.timer);
      this.timer = null;
      if (this.state.enabled && !this.disposed) {
        this.timer = this.setInterval(() => { void this.tick(); }, this.state.interval * 1000);
      }
    }
    async configure(enabled, interval) {
      if (this.disposed) throw new Error('The document runtime has stopped.');
      if (this.state.configuring) throw new Error('Wait for the settings update to finish.');
      if (!intervals.includes(interval)) throw new Error('Unsupported interval.');
      this.state.configuring = true;
      // A user can turn OFF while a save is running. Queue that preference
      // behind the existing host request instead of presenting a false error.
      if (this.busy) { this.emit(); await new Promise(resolve => this.idleWaiters.push(resolve)); }
      if (this.disposed) { this.state.configuring = false; throw new Error('The document runtime has stopped.'); }
      this.busy = true;
      const previous = { enabled: this.state.enabled, interval: this.state.interval };
      this.state.configuring = true;
      this.state.phase = 'Updating settings'; this.state.error = ''; this.emit();
      try {
        await this.host.checkSupport();
        this.state.path = localPath(await this.host.getPath());
        // All host mutations and saves share this lock. User setting changes save the
        // original document once so both ON and OFF preferences reach the disk.
        await this.host.writePreference({ enabled, interval, version: 1 });
        this.state.enabled = enabled;
        this.state.interval = interval;
        await this.host.setStartup(enabled);
        localPath(await this.host.getPath());
        this.state.requests++;
        this.state.phase = 'Saving'; this.emit();
        await this.host.save();
        this.state.completions++;
        this.state.lastSave = this.now();
        this.state.phase = enabled ? 'Saved' : 'Disabled';
        this.state.error = '';
      } catch (error) {
        // If preference persistence failed, keep the previous live preference.
        // If startup or disk saving failed, retain the newly requested setting
        // and expose the failure; enabled saves keep retrying on schedule.
        if (this.state.phase === 'Updating settings' && this.state.enabled === previous.enabled && this.state.interval === previous.interval) {
          this.state.enabled = previous.enabled; this.state.interval = previous.interval;
        }
        this.failure(error);
      } finally {
        this.busy = false;
        this.state.configuring = false;
        this.schedule(); this.emit();
      }
    }
    async tick() {
      if (!this.state.enabled || this.disposed || this.state.configuring) return;
      if (this.busy) { this.state.skippedBusy++; return; }
      this.busy = true;
      this.state.lastCheck = this.now();
      this.state.phase = 'Checking'; this.emit();
      try {
        if (!this.state.path) this.state.path = localPath(await this.host.getPath());
        if (await this.host.isSaved()) {
          this.state.skippedClean++;
          // An earlier error stays visible until an actual successful save.
          this.state.phase = this.state.error ? 'Error' : 'Active';
        } else {
          this.state.path = localPath(await this.host.getPath());
          this.state.requests++;
          this.state.phase = 'Saving'; this.emit();
          await this.host.save();
          this.state.completions++;
          this.state.lastSave = this.now();
          this.state.error = ''; this.state.phase = 'Saved';
        }
      } catch (error) { this.failure(error); }
      finally {
        this.busy = false;
        for (const resolve of this.idleWaiters.splice(0)) resolve();
        if (!this.disposed) this.emit();
      }
    }
    dispose() {
      this.disposed = true;
      for (const resolve of this.idleWaiters.splice(0)) resolve();
      if (this.timer !== null) this.clearInterval(this.timer);
      this.timer = null;
      this.state.phase = 'Stopped'; this.emit();
    }
  }
  return { Engine, intervals, localPath };
});
