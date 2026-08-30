import fs from 'node:fs';
import path from 'node:path';
export const root = process.cwd();
export function read(p){return fs.readFileSync(path.join(root,p),'utf8');}
export function json(p){return JSON.parse(read(p));}
export function writeJson(p,v){fs.writeFileSync(path.join(root,p),JSON.stringify(v,null,2)+'\n');}
export function fail(message){console.error(message);process.exit(1);}
export function headings(markdown){return [...markdown.matchAll(/^##\s+(.+)$/gm)].map(m=>m[1].trim().toLowerCase());}
