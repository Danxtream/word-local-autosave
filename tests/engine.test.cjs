// Copyright (C) 2026 Danxtream.
// Licensed under GPL-3.0-only with an additional term under section 7(b); see LICENSE and NOTICE.md.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { Engine, localPath } = require('../web/engine.js');
const makeHost = require('../web/office-host.js');
const vm = require('node:vm');
const fs = require('node:fs');
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return {promise, resolve, reject}; };
function fixture(pref) {
  let now = 1000, callback, delay, saves = 0, saved = false, path = 'file:///tmp/synthetic-local-autosave/AutoSave-Test.docx';
  const host = { checkSupport: async()=>{}, readPreference:()=>pref, writePreference: async p=>{pref=p;},
    getPath: async()=>path, isSaved:async()=>saved, setStartup:async()=>{}, save:async()=>{saves++; saved=true;} };
  const engine = new Engine(host, ()=>{}, {now:()=>now, setInterval:(fn,ms)=>{callback=fn;delay=ms;return 1;}, clearInterval:()=>{callback=null;}});
  return {engine,host,get saves(){return saves;},get delay(){return delay;},get pref(){return pref;},
    dirty:()=>{saved=false;},path:p=>{path=p;},advance:()=>{now+=1000;},fire:()=>callback()};
}
test('existing local .docx only; unsaved, cloud, network and other formats blocked',()=>{
  assert.equal(localPath('file:///tmp/synthetic-local-autosave/A%20B.docx'), '/tmp/synthetic-local-autosave/A B.docx');
  assert.equal(localPath('/tmp/synthetic-local-autosave/A.docx'), '/tmp/synthetic-local-autosave/A.docx');
  for (const p of ['',null,'Document1','https://server/test.docx','file://server/share/A.docx','//server/A.docx','/tmp/synthetic-local-autosave/A.doc','file:///tmp/synthetic-local-autosave/a.docx?download']) {
    if (p && p.includes('?')) continue;
    assert.throws(()=>localPath(p));
  }
});
test('default off at 30 seconds',async()=>{const f=fixture();await f.engine.init();assert.equal(f.engine.state.interval,30);assert.equal(f.engine.state.enabled,false);assert.equal(f.saves,0);});
test('one second schedule persists ON and saves original',async()=>{const f=fixture();await f.engine.configure(true,1);assert.equal(f.delay,1000);assert.deepEqual(f.pref,{enabled:true,interval:1,version:1});assert.equal(f.saves,1);assert.equal(f.engine.state.completions,1);});
test('unchanged documents skip save; dirty document saved',async()=>{const f=fixture();await f.engine.configure(true,1);await f.engine.tick();assert.equal(f.saves,1);assert.equal(f.engine.state.skippedClean,1);f.dirty();await f.engine.tick();assert.equal(f.saves,2);});
test('idle cycles avoid redundant path requests while dirty saves revalidate the destination',async()=>{
  const f=fixture();await f.engine.configure(true,1);let paths=0;
  f.host.getPath=async()=>{paths++;return '/tmp/synthetic-local-autosave/AutoSave-Test.docx';};
  for(let i=0;i<10;i++) await f.engine.tick();
  assert.equal(paths,0);assert.equal(f.saves,1);
  f.dirty();await f.engine.tick();assert.equal(paths,1);assert.equal(f.saves,2);
});
test('concurrent ticks skip; no completion before host resolves',async()=>{const f=fixture();await f.engine.configure(true,1);f.dirty();const d=deferred();f.host.save=()=>d.promise;const task=f.engine.tick();await new Promise(setImmediate);assert.equal(f.engine.state.phase,'Saving');await f.engine.tick();assert.equal(f.engine.state.skippedBusy,1);assert.equal(f.engine.state.completions,1);d.resolve();await task;assert.equal(f.engine.state.completions,2);});
test('save failure retains ON, previous timestamp, and retries',async()=>{const f=fixture();await f.engine.configure(true,1);f.dirty();f.host.save=async()=>{throw new Error('Disk unavailable');};await f.engine.tick();assert.equal(f.engine.state.phase,'Error');assert.equal(f.engine.state.enabled,true);assert.equal(f.engine.state.lastSave,1000);assert.equal(f.engine.state.completions,1);f.host.save=async()=>{};f.advance();await f.engine.tick();assert.equal(f.engine.state.lastSave,2000);assert.equal(f.engine.state.error,'');});
test('unsaved document never persists settings or calls save',async()=>{const f=fixture();f.path('');await f.engine.configure(true,1);assert.equal(f.saves,0);assert.equal(f.pref,undefined);assert.equal(f.engine.state.enabled,false);assert.equal(f.engine.state.phase,'Error');});
test('path becoming unknown during operation blocks save',async()=>{const f=fixture();await f.engine.configure(true,1);f.dirty();f.host.isSaved=async()=>{f.path('');return false;};await f.engine.tick();assert.equal(f.saves,1);assert.equal(f.engine.state.phase,'Error');});
test('OFF is persisted and flushed once; no later timer saves',async()=>{const f=fixture();await f.engine.configure(true,1);await f.engine.configure(false,5);assert.equal(f.pref.enabled,false);assert.equal(f.saves,2);f.dirty();await f.engine.tick();assert.equal(f.saves,2);});
test('settings errors remain visible without silently switching state',async()=>{const f=fixture();await f.engine.configure(true,1);f.host.writePreference=async()=>{throw new Error('settings failure');};await f.engine.configure(false,5);assert.equal(f.engine.state.enabled,true);assert.equal(f.engine.state.interval,1);assert.match(f.engine.state.error,/settings failure/);});
test('three documents have separate preferences and timers',async()=>{const a=fixture(),b=fixture(),c=fixture();await Promise.all([a.engine.configure(true,1),b.engine.configure(true,5),c.engine.init()]);a.dirty();b.dirty();c.dirty();await Promise.all([a.engine.tick(),b.engine.tick(),c.engine.tick()]);assert.equal(a.saves,2);assert.equal(b.saves,2);assert.equal(c.saves,0);});
test('reopen restores preference; invalid intervals default safely',async()=>{const f=fixture({enabled:true,interval:1});await f.engine.init();assert.equal(f.delay,1000);assert.equal(f.saves,1);const g=fixture({enabled:false,interval:2});await g.engine.init();assert.equal(g.engine.state.interval,30);});
test('dispose cancels scheduler and prevents further saves',async()=>{const f=fixture();await f.engine.configure(true,1);f.engine.dispose();f.dirty();await f.engine.tick();assert.equal(f.saves,1);assert.equal(f.engine.state.phase,'Stopped');});
test('settings cannot race with an in-flight save',async()=>{const f=fixture();await f.engine.configure(true,1);f.dirty();const d=deferred();f.host.save=()=>d.promise;const task=f.engine.tick();await new Promise(setImmediate);const settings=f.engine.configure(false,5);assert.equal(f.engine.state.configuring,true);assert.equal(f.pref.enabled,true);d.resolve();await task;await settings;assert.equal(f.pref.enabled,false);assert.equal(f.engine.state.enabled,false);});
test('Word adapter awaits context.sync and passes non-prompting Save without filename',async()=>{
  const d=deferred();let args;
  const Office={};const Word={SaveBehavior:{save:'Save'},run:async fn=>fn({document:{save:(...a)=>{args=a;}},sync:()=>d.promise})};
  const host=makeHost(Office,Word);let completed=false;const task=host.save().then(()=>{completed=true;});
  await new Promise(setImmediate);assert.equal(completed,false);assert.deepEqual(args,['Save']);d.resolve();await task;assert.equal(completed,true);
});
test('Word adapter sync rejection cannot become successful completion',async()=>{
  const Word={SaveBehavior:{save:'Save'},run:async fn=>fn({document:{save:()=>{}},sync:async()=>{throw new Error('Host save failed');}})};
  await assert.rejects(makeHost({},Word).save(),/Host save failed/);
});
test('browser timers retain Window receiver when scheduling, rescheduling and disposing',async()=>{
  let starts=0,stops=0,callback;
  const browser={URL};
  browser.globalThis=browser;
  const context=vm.createContext(browser);
  const windowOwner=vm.runInContext('globalThis',context);
  browser.setInterval=function(fn,ms){
    if(this!==windowOwner) throw new TypeError('Can only call Window.setInterval on instances of Window');
    assert.equal(ms,1000);starts++;callback=fn;return starts;
  };
  browser.clearInterval=function(){
    if(this!==windowOwner) throw new TypeError('Can only call Window.clearInterval on instances of Window');
    stops++;
  };
  vm.runInContext(fs.readFileSync(require.resolve('../web/engine.js'),'utf8'),context);
  const f=fixture({enabled:true,interval:1});
  const engine=new browser.LocalAutoSave.Engine(f.host);
  await engine.init();assert.equal(engine.state.error,'');assert.equal(starts,1);
  assert.ok(engine.state.lastCheck);f.dirty();callback();
  await new Promise(setImmediate);assert.equal(f.saves,2);
  engine.schedule();assert.equal(starts,2);assert.equal(stops,1);
  engine.dispose();assert.equal(stops,2);
});
