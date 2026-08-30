import fs from 'node:fs';
import path from 'node:path';
const root = process.cwd();
const readJson = (p, fallback) => { try { return JSON.parse(fs.readFileSync(path.join(root, p), 'utf8')); } catch { return fallback; } };
const countArray = (value) => Array.isArray(value) ? value.length : 0;
const requirements = readJson('delivery/requirements.json', []);
const backlog = readJson('delivery/backlog.json', []);
const state = readJson('.engineering/STATE.json', {});
const requirementCount = countArray(requirements.requirements ?? requirements);
const sliceCount = countArray(backlog.slices ?? backlog);
const attempts = Number(state.attempts ?? 0);
const blockers = countArray(state.blockers);
const recommendations = [];
if (requirementCount >= 40 || sliceCount >= 8) recommendations.push({priority:'medium',capability:'standard mode',reason:`Project size is ${requirementCount} requirements and ${sliceCount} slices; ADR, evidence and certification controls may now add value.`});
if (attempts >= 3 || blockers >= 3) recommendations.push({priority:'high',capability:'maker-checker plugin',reason:`Current state records ${attempts} attempts and ${blockers} blockers; independent verification may reduce repeated rework.`});
if (recommendations.length === 0) { console.log('Engineering advisor: remain in Lite mode. No evidence-based upgrades are currently justified.'); process.exit(0); }
console.log('Engineering advisor recommendations (advisory only):');
for (const item of recommendations) console.log(`- [${item.priority.toUpperCase()}] ${item.capability}: ${item.reason}`);
console.log('\nNo capability was enabled automatically. Update .engineering/PROFILE.yaml only after human approval.');
