import http from 'node:http'
import { createRequire } from 'node:module'
import path from 'node:path'
const root = process.env.SQLBOT_XPACK_TEST_ROOT
if (!root || !path.isAbsolute(root))
  throw new Error('Set SQLBOT_XPACK_TEST_ROOT to the xpack checkout')
const require = createRequire(path.join(root, 'xpack_static/package.json'))
const { build } = require('esbuild')
const result = await build({
  entryPoints: [path.join(root, 'xpack_static/src/assistant/ui.ts')],
  bundle: true,
  format: 'esm',
  write: false,
})
const port = Number(process.env.SQLBOT_DRAG_BROWSER_PORT || 4288)
http
  .createServer((req, res) => {
    if (req.url === '/ui.js') {
      res.setHeader('Content-Type', 'text/javascript')
      res.end(result.outputFiles[0].text)
      return
    }
    res.setHeader('Content-Type', 'text/html')
    res.end(`<body style="margin:0"><button id="host" style="position:fixed;inset:0;width:100%;height:100%" onclick="window.hostClicks=(window.hostClicks||0)+1">Host</button><script type="module">
  import {initsqlbot_assistant} from '/ui.js';
  const p=new URLSearchParams(location.search);
  initsqlbot_assistant({id:'drag-test',x_type:p.get('x')||'right',y_type:p.get('y')||'bottom',x_val:30,y_val:30,float_icon_drag:p.get('drag')!=='false',domain_url:location.origin,float_icon:p.has('custom')?'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2250%22 height=%2250%22%3E%3C/svg%3E':'',name:'test'});
  document.querySelector('iframe').src='about:blank';

  </script>`)
  })
  .listen(port, '127.0.0.1')
