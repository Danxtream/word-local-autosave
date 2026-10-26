(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.makeOfficeHost = factory;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Office, Word) {
  'use strict';
  const key = 'LocalAutoSave.v1';
  const asyncCall = (fn) => new Promise((resolve, reject) => fn(result => {
    if (result.status === Office.AsyncResultStatus.Succeeded) resolve(result.value);
    else reject(new Error(result.error ? result.error.message : 'Word API request failed.'));
  }));
  return {
    async checkSupport() {
      if (Office.context.host !== Office.HostType.Word || Office.context.platform !== Office.PlatformType.Mac) {
        throw new Error('This test build requires desktop Word on macOS.');
      }
      if (!Office.context.requirements.isSetSupported('WordApi', '1.5') ||
          !Office.context.requirements.isSetSupported('SharedRuntime', '1.1') || !Office.addin) {
        throw new Error('This Word installation must support WordApi 1.5 and SharedRuntime 1.1.');
      }
    },
    readPreference() { return Office.context.document.settings.get(key); },
    async writePreference(pref) {
      const settings = Office.context.document.settings;
      const old = settings.get(key);
      settings.set(key, pref);
      try { await asyncCall(cb => settings.saveAsync(cb)); }
      catch (error) { if (old === undefined || old === null) settings.remove(key); else settings.set(key, old); throw error; }
    },
    async getPath() {
      const props = await asyncCall(cb => Office.context.document.getFilePropertiesAsync(cb));
      return props && props.url;
    },
    async setStartup(enabled) {
      await Office.addin.setStartupBehavior(enabled ? Office.StartupBehavior.load : Office.StartupBehavior.none);
    },
    async isSaved() {
      return Word.run(async context => {
        context.document.load('saved');
        await context.sync();
        return context.document.saved;
      });
    },
    async save() {
      // save() queues the operation; sync() is the awaited host completion.
      // No filename is supplied, and callers must validate an existing path first.
      await Word.run(async context => {
        context.document.save(Word.SaveBehavior.save);
        await context.sync();
      });
    }
  };
});
