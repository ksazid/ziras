import fs from 'node:fs';
import {json,writeJson,fail} from './lib.mjs';
import {loadDelivery,validateDelivery} from './governance-lib.mjs';

const [action,arg] = process.argv.slice(2);
const currentPath = 'delivery/current-slice.json';

function titleFromMarkdown(file,id) {
  const markdown = fs.readFileSync(file,'utf8');
  const match = markdown.match(/^#\s+(.+)$/m);
  return match?.[1]?.trim() || id;
}

function pendingApproval(type) {
  return {
    type,
    status:'pending',
    version:null,
    commitSha:null,
    by:null,
    at:null,
    rationale:null
  };
}

function freshSlice(id,file,title,governance) {
  return {
    schemaVersion:2,
    sliceId:id,
    title,
    status:'active',
    lifecycle:'approved',
    riskLevel:'low',
    implementationMode:'specification-only',
    requirements:[],
    owners:{product:null,engineering:null,operations:null,security:null},
    dependencies:[],
    blockers:[],
    allowedPaths:[],
    protectedPaths:['.github/workflows/release.yml'],
    impact:{areas:[],notes:[]},
    approvals:governance.approvalTypes.map(pendingApproval),
    decisionIds:[],
    progress:{discovery:0,decisions:0,implementation:0,testing:0,certification:0,release:0,validation:0},
    certification:{status:'not-started',commitSha:null,evidence:[]},
    release:{status:'not-authorized',releaseId:null},
    rollback:{status:'not-applicable',rollbackId:null},
    postRelease:{status:'not-started',reviewAt:null,expectedOutcome:null,metrics:[]},
    links:{specification:file,implementationPr:null,evidence:[]},
    maxAttempts:3
  };
}

function ensureValid() {
  const result = validateDelivery(loadDelivery());
  if (result.errors.length) fail(result.errors.map(error => `- ${error}`).join('\n'));
  for (const warning of result.warnings) console.warn(`WARN: ${warning}`);
}

if (action === 'status') {
  const delivery = loadDelivery();
  const active = delivery.current;
  const linked = (delivery.decisions.decisions ?? []).filter(item => (active.decisionIds ?? []).includes(item.id));
  console.log(JSON.stringify({slice:active,decisions:linked},null,2));
  process.exit(0);
}

if (action === 'activate') {
  const id = arg;
  if (!id || !/^VS-\d+$/.test(id)) fail('Usage: slice activate VS-01');
  const file = `docs/slices/${id}.md`;
  if (!fs.existsSync(file)) fail(`${file} does not exist`);
  const delivery = loadDelivery();
  const current = delivery.current;
  if (current.sliceId && current.status === 'active' && current.sliceId !== id) fail(`${current.sliceId} is already active`);

  if (current.sliceId === id) {
    current.status = 'active';
    current.links = {...(current.links ?? {}),specification:file};
    writeJson(currentPath,current);
    console.log(`${id} reactivated without changing its existing governance state.`);
    process.exit(0);
  }

  const next = freshSlice(id,file,titleFromMarkdown(file,id),delivery.governance);
  writeJson(currentPath,next);
  console.log(`${id} activated with fresh governance state at approved/specification-only. Add requirement IDs and record typed approvals before runtime implementation.`);
  process.exit(0);
}

if (action === 'transition') {
  const target = arg;
  const delivery = loadDelivery();
  const current = delivery.current;
  if (!current.sliceId || current.status !== 'active') fail('No active slice');
  if (!delivery.governance.lifecycleStates.includes(target)) fail(`Unknown lifecycle state: ${target}`);
  const allowed = delivery.governance.transitions[current.lifecycle] ?? [];
  if (!allowed.includes(target)) fail(`Transition ${current.lifecycle} → ${target} is not allowed`);
  const previous = structuredClone(current);
  current.lifecycle = target;
  current.status = ['validated','rejected','superseded','rolled-back'].includes(target) ? 'completed' : 'active';
  writeJson(currentPath,current);
  const validation = validateDelivery(loadDelivery());
  if (validation.errors.length) {
    writeJson(currentPath,previous);
    fail(`Transition rejected:\n${validation.errors.map(error => `- ${error}`).join('\n')}`);
  }
  console.log(`${current.sliceId} transitioned ${previous.lifecycle} → ${target}`);
  process.exit(0);
}

if (action === 'validate') {
  const current = json(currentPath);
  if (current.status !== 'active' || !current.sliceId) fail('No active slice');
  if (!Array.isArray(current.requirements) || !current.requirements.length) fail('Active slice has no requirement IDs');
  ensureValid();
  console.log(`Slice validation passed (${current.sliceId}, ${current.lifecycle}, ${current.implementationMode})`);
  process.exit(0);
}

fail('Use: slice status | activate VS-01 | transition <state> | validate');
