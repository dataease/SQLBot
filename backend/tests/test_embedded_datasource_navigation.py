"""Offline navigation regressions using actual TS handlers and Vue Router.

Requires Node and the existing frontend npm dependencies; no server or LLM calls.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const frontend = path.join(process.cwd(), 'frontend');
const ts = require(path.join(frontend, 'node_modules/typescript'));
const {createRouter, createMemoryHistory} = require(path.join(frontend, 'node_modules/vue-router'));
const source = file => fs.readFileSync(path.join(frontend, 'src', file), 'utf8');
function declaration(file, name) {
  const raw = source(file).replace(/^.*?<script[^>]*>/s, '').split('</script>')[0];
  const ast = ts.createSourceFile(file+'.ts', raw, ts.ScriptTarget.Latest, true);
  const node = ast.statements.find(n => n.name?.getText(ast) === name ||
    n.declarationList?.declarations.some(d => d.name.getText(ast) === name));
  assert.ok(node, `missing declaration ${name}`);
  return node.getText(ast).replace(/^export /, '');
}
function evaluate(code, bindings, name) {
  const js = ts.transpileModule(code, {compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;
  return new Function(...Object.keys(bindings), js+'; return '+name)(...Object.values(bindings));
}
async function navigation({embedded=false, token='', uid=42, model=true, target, admin=false, spaceAdmin=true}) {
  const router = createRouter({history:createMemoryHistory(),routes:[
    '/embeddedCommon','/embeddedPage','/assistant','/chat/index','/login','/admin-login',
    '/401','/system/model','/set/member','/ds/index',
    {path:'/chat',redirect:'/chat/index'},
  ].map(route=>typeof route === 'string' ? {path:route,component:{}} : route)});
  const trace=[];
  router.beforeEach(to=> {trace.push(to.fullPath); return trace.length>8 ? false:undefined;});
  const watchSource = source('router/watch.ts').replace(/^import .*$/gm,'')
    .replace(/export const /g,'const ').split('const loadXpackStatic =')[0];
  const userStore={getUid:uid,isSpaceAdmin:spaceAdmin,isAdmin:admin,info:async()=>{userStore.getUid=42;}};
  evaluate(watchSource,{
    useAppearanceStoreWithOut:()=>({setAppearance:async()=>{}}),useUserStore:()=>userStore,
    useCache:()=>({wsCache:{get:()=>token}}),LicenseGenerator:{generateRouters(){}},
    loadXpackStatic:async()=>{},generateDynamicRouters:()=>{},
    toLoginPage:evaluate(declaration('utils/utils.ts','toLoginPage'),{},'toLoginPage'),
  },'watchRouter')(router);
  await router.push('/embeddedCommon?id=fixture&lang=en');
  let pending;
  const events=[];
  let dialogs=0;
  const handle=evaluate(declaration('views/ds/Datasource.vue','handleQuestion'),{
    router:{push:to=>(pending=router.push(to))},
    chatApi:{checkLLMModel:async()=>{if(!model) throw new Error('unavailable');}},
    props:{pageEmbedded:embedded},emits:(...args)=>events.push(args),userStore,
    t:key=>key,ElMessageBox:{confirm:()=>{dialogs++;}},console:{error(){}},
  },'handleQuestion');
  if (target) await router.push(target);
  else {await handle('9007199254740993'); await pending;}
  assert.ok(trace.length<=8, 'navigation must terminate: '+JSON.stringify(trace));
  return {route:router.currentRoute.value,events,dialogs};
}
(async()=>{
  const mode=process.argv[1];
  if(mode==='embedded') {
    for (const token of ['', 'ordinary-fixture']) {
      const result=await navigation({embedded:true,token});
      assert.equal(result.route.fullPath,'/embeddedCommon?id=fixture&lang=en');
      assert.deepEqual(result.events,[['start-chat','9007199254740993']]);
    }
    const result=await navigation({embedded:true,model:false});
    assert.deepEqual(result.events,[]);
    assert.equal(result.dialogs,1);
    assert.equal(result.route.path,'/embeddedCommon');
  } else if(mode==='authentication') {
    for(const uid of [42,null]) {
      const result=await navigation({uid});
      assert.equal(result.route.path,'/login');
      assert.equal(result.route.query.redirect,'/chat/index?start_chat=9007199254740993');
    }
    const normal=await navigation({token:'ordinary-fixture'});
    assert.equal(normal.route.fullPath,'/chat/index?start_chat=9007199254740993');
    assert.deepEqual(normal.events,[]);
    for (const target of ['/login?redirect=/chat/index','/admin-login','/assistant','/embeddedPage','/401']) {
      const result=await navigation({target});
      assert.equal(result.route.path,target.split('?')[0]);
    }
    const loggedIn=await navigation({token:'ordinary-fixture',target:'/login?redirect=/chat/index'});
    assert.equal(loggedIn.route.path,'/chat/index');
    for(const target of ['/system/model','/set/member','/ds/index']) {
      const rejected=await navigation({token:'ordinary-fixture',target,spaceAdmin:false});
      assert.equal(rejected.route.path,'/chat/index');
      const allowed=await navigation({token:'ordinary-fixture',target,admin:true});
      assert.equal(allowed.route.path,target);
    }
  } else if(mode==='component') {
    const vue = require(path.join(frontend, 'node_modules/vue'));
    const {parse,compileScript} = require(path.join(frontend, 'node_modules/@vue/compiler-sfc'));
    const {descriptor} = parse(source('views/embedded/common.vue'));
    const compiled = compileScript(descriptor,{id:'embedded-test',inlineTemplate:true});
    const js = ts.transpileModule(compiled.content,{compilerOptions:{
      target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,
    }}).outputText;
    for(const permitted of [true,false]) {
      const listeners = new Map();
      const assistant = {setPageEmbedded(){},setType(){},setId(){},setAssistant(){},setToken(){}};
      const user = vue.reactive({isAdmin:false,isSpaceAdmin:permitted,info:async()=>{},setLanguage(){}});
      const ds = {props:['pageEmbedded'],emits:['start-chat'],setup:(props,{emit})=>()=>
        vue.h('start-button',{onClick:()=>emit('start-chat','9007199254740993')})};
      const chat = {props:['pageEmbedded','startChatDsId'],setup:props=>()=>vue.h('chat-view',{
        datasource:props.startChatDsId,embedded:props.pageEmbedded,
      })};
      const imports = {
        'vue':vue,'vue-router':{useRoute:()=>({query:{id:'fixture',lang:'en'}})},
        'vue-i18n':{useI18n:()=>({t:key=>key})},
        '@/views/ds/Datasource.vue':{default:ds},'@/views/chat/index.vue':{default:chat},
        '@/views/error/index.vue':{default:{render:()=>vue.h('denied-view')}},
        '@/stores/assistant':{useAssistantStore:()=>assistant},'@/stores/user':{useUserStore:()=>user},
      };
      const exports = {};
      new Function('require','exports','window','setTimeout',js)(name=>{
        assert.ok(imports[name],`unexpected import ${name}`); return imports[name];
      },exports,{
        addEventListener:(name,fn)=>listeners.set(name,fn),
        removeEventListener:name=>listeners.delete(name),parent:{postMessage(){}},
      },fn=>fn());
      const node = type=>({type,children:[],props:{},style:{}});
      const renderer = vue.createRenderer({
        createElement:node,createText:()=>node('text'),createComment:()=>node('comment'),
        setText(){},setElementText(){},patchProp:(el,key,old,value)=>{el.props[key]=value;},
        insert(el,parent,anchor){el.parent=parent;const i=parent.children.indexOf(anchor);
          if(i<0) parent.children.push(el); else parent.children.splice(i,0,el);},
        remove(el){el.parent.children.splice(el.parent.children.indexOf(el),1);},
        parentNode:el=>el.parent,nextSibling:el=>el.parent?.children[el.parent.children.indexOf(el)+1],
      });
      const root=node('root');
      const app=renderer.createApp(exports.default);
      app.component('el-button',{setup:(_,{attrs,slots})=>()=>vue.h('back-button',attrs,slots.default?.())});
      app.directive('loading',{});
      app.mount(root);
      const find=(type,el=root)=>el.type===type ? el : el.children.map(child=>find(type,child)).find(Boolean);
      assert.equal(find('start-button'),undefined,'wait for embedded certificate');
      await listeners.get('message')({data:{eventName:'sqlbot_embedded_event',messageId:'fixture',
        busiFlag:'ds',busi:'certificate',type:4,certificate:'synthetic-fixture'}});
      await vue.nextTick();
      if(permitted) {
        for(let i=0;i<2;i++) {
          find('start-button').props.onClick(); await vue.nextTick();
          assert.ok(find('chat-view'), 'start-chat must open the embedded chat view');
          assert.deepEqual(find('chat-view').props,{datasource:'9007199254740993',embedded:true});
          assert.equal(find('start-button').parent.style.display,'none');
          find('back-button').props.onClick(); await vue.nextTick();
          assert.equal(find('chat-view'),undefined);
          assert.ok(find('start-button'));
          assert.notEqual(find('start-button').parent.style.display,'none');
        }
      } else {
        assert.ok(find('denied-view'));
        assert.equal(find('start-button'),undefined);
        assert.equal(find('chat-view'),undefined);
      }
      app.unmount();
      assert.equal(listeners.size,0,'release message listener');
    }
  } else if(mode==='chat-context') {
    for(const pageEmbedded of [true,false]) {
      const calls=[];
      const replacements=[];
      evaluate(declaration('views/chat/index.vue','jumpCreatChat'),{
        props:{pageEmbedded,startChatDsId:'9007199254740993'},nextTick:fn=>fn(),
        hiddenChatCreatorRef:{value:{createChat:id=>calls.push(id)}},
        window:{location:{hash:'#/embeddedCommon?id=fixture&lang=en'}},
        history:{replaceState:(...args)=>replacements.push(args)},
      },'jumpCreatChat')();
      assert.deepEqual(calls,['9007199254740993']);
      if(pageEmbedded) assert.deepEqual(replacements,[], 'preserve embedded handshake id and language');
    }
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
"""


@pytest.mark.parametrize(
    "mode", ["embedded", "authentication", "chat-context", "component"]
)
def test_embedded_navigation(mode):
    if (
        not shutil.which("node")
        or not (ROOT / "frontend/node_modules/typescript").exists()
    ):
        pytest.skip("Node and frontend npm dependencies are required")
    result = subprocess.run(
        ["node", "-e", SCRIPT, mode],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
