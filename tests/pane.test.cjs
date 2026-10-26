const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function pane(){
  let writes=0,jsons=0;const nodes=new Map();
  const get=id=>{
    if(!nodes.has(id))nodes.set(id,new Proxy({open:false,addEventListener:()=>{}},{set(target,key,value){writes++;target[key]=value;return true;}}));
    return nodes.get(id);
  };
  const document={hidden:false,visibilityState:'visible',getElementById:get,addEventListener:()=>{}};
  const ctx=vm.createContext({document,window:{addEventListener:()=>{}},setInterval:()=>1,clearInterval:()=>{},
    JSON:{stringify:(...args)=>{jsons++;return JSON.stringify(...args);}}});
  vm.runInContext(fs.readFileSync(require.resolve('../web/taskpane.js'),'utf8'),ctx);
  const render=state=>{ctx.snapshot=state;vm.runInContext('render(snapshot)',ctx);};
  return {get,document,render,get writes(){return writes;},get jsons(){return jsons;}};
}
const state={enabled:true,interval:1,phase:'Active',configuring:false,error:'',lastSave:1000,lastCheck:2000};
test('collapsed pane does not format diagnostic JSON or rewrite unchanged status while polling',()=>{
  const p=pane();p.render(state);const writes=p.writes;
  for(let i=0;i<20;i++)p.render({...state,phase:i%2?'Checking':'Active',lastCheck:3000+i*1000});
  assert.equal(p.jsons,0);assert.equal(p.writes,writes);assert.equal(p.get('badge').textContent,'Active');
});
test('hidden pane does no DOM work; expanded visible diagnostics update on demand',()=>{
  const p=pane();p.render(state);const writes=p.writes;
  p.document.hidden=true;p.render({...state,phase:'Saving'});assert.equal(p.writes,writes);
  p.document.hidden=false;p.get('details').open=true;p.render(state);
  assert.equal(p.jsons,1);assert.match(p.get('diagnostics').textContent,/lastCheck/);
});
