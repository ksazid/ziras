import {read, headings, fail} from './lib.mjs';
const specs=[['product/PRD.md',['product objective','target users','user roles','core journeys','functional requirements','business rules','out of scope','release scope','open decisions']],['product/TRD.md',['architecture','technology stack','modules and data ownership','authentication','authorization','persistence and migrations','external integrations','deployment','observability','security','testing strategy','open decisions']]];
let errors=[];
for(const [file,required] of specs){ const doc=read(file); const found=new Set(headings(doc)); for(const h of required) if(!found.has(h)) errors.push(`${file}: missing heading "${h}"`); if(/Status:\s*Draft/i.test(doc)) errors.push(`${file}: status remains Draft`); }
if(errors.length) fail(`INTAKE: BLOCKED\n- ${errors.join('\n- ')}`);
console.log('INTAKE: PASS');
