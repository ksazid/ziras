import fs from 'node:fs';
const files = [
  'delivery/requirements.json',
  'delivery/epics.json',
  'delivery/backlog.json',
  'delivery/traceability.json',
  'delivery/current-slice.json',
  'delivery/completed-slices.json',
  'delivery/governance.json',
  'delivery/decisions.json',
  'delivery/releases.json',
  'delivery/rollbacks.json',
  '.engineering/STATE.json'
];
for (const file of files) JSON.parse(fs.readFileSync(file,'utf8'));
console.log(`JSON validation passed (${files.length} files)`);
