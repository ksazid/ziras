import assert from 'node:assert/strict';
import fs from 'node:fs';
const profile=JSON.parse(fs.readFileSync('.engineering/PLATFORM.json','utf8'));
assert.equal(profile.platform,'mobile');
assert.equal(fs.existsSync('apps/web'),false);
for(const path of ['apps/mobile/package.json','apps/mobile/app.json','apps/mobile/eas.json']) assert.equal(fs.existsSync(path),true,path);
console.log('Mobile platform structure test passed');
