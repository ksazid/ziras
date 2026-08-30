import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const build = spawnSync(process.execPath,['scripts/dashboard.mjs'],{stdio:'inherit'});
if (build.status !== 0) process.exit(build.status ?? 1);
const root = path.resolve('dashboard');
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
const port = Number(process.env.PORT ?? 4173);
const server = http.createServer((request,response) => {
  const requested = decodeURIComponent((request.url ?? '/').split('?')[0]);
  const relative = requested === '/' ? 'index.html' : requested.replace(/^\/+/, '');
  const file = path.resolve(root,relative);
  if (!file.startsWith(root + path.sep) && file !== root) {
    response.writeHead(403); response.end('Forbidden'); return;
  }
  fs.readFile(file,(error,content) => {
    if (error) { response.writeHead(error.code === 'ENOENT' ? 404 : 500); response.end(error.code === 'ENOENT' ? 'Not found' : 'Server error'); return; }
    response.writeHead(200,{'Content-Type':types[path.extname(file)] ?? 'application/octet-stream','Cache-Control':'no-store'});
    response.end(content);
  });
});
server.listen(port,'127.0.0.1',() => console.log(`PES dashboard: http://127.0.0.1:${port}`));
