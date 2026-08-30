import { access, cp, mkdir } from 'node:fs/promises';
import { constants } from 'node:fs';
import { basename, dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';

const root = process.cwd();
const apply = process.argv.includes('--apply');
const approved = process.env.PES_CONTEXT_COMPRESSION_APPROVED === '1';
const eligible = [
  'AGENTS.md',
  'docs/OPERATING-MODES.md',
  'docs/integrations/CAVEMAN.md'
];
const protectedPatterns = [
  'README.md',
  'product/PRD.md',
  'product/TRD.md',
  'docs/adr/',
  'security/',
  'docs/evidence/',
  'openapi',
  'swagger'
];

async function exists(path) {
  try {
    await access(path, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

console.log('PES optional context-compression guard');
console.log(`Mode: ${apply ? 'apply' : 'preview'}`);
console.log('\nEligible files:');
for (const file of eligible) console.log(`- ${file}`);
console.log('\nProtected exclusions:');
for (const item of protectedPatterns) console.log(`- ${item}`);

if (!apply) {
  console.log('\nPreview only. No files changed.');
  console.log('To apply after installing caveman-compress:');
  console.log('PES_CONTEXT_COMPRESSION_APPROVED=1 npm run optimize:context -- --apply');
  process.exit(0);
}

if (!approved) {
  console.error('\nRefusing to modify files: set PES_CONTEXT_COMPRESSION_APPROVED=1 after human approval.');
  process.exit(1);
}

const probe = spawnSync('caveman-compress', ['--help'], { encoding: 'utf8', shell: process.platform === 'win32' });
if (probe.error || probe.status !== 0) {
  console.error('\n`caveman-compress` is unavailable. Install Caveman for your agent and confirm the command is on PATH.');
  process.exit(1);
}

const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const backupRoot = join(root, '.engineering', 'backups', 'context', stamp);

for (const file of eligible) {
  const source = join(root, file);
  if (!(await exists(source))) {
    console.log(`Skip missing: ${file}`);
    continue;
  }

  const backup = join(backupRoot, file);
  await mkdir(dirname(backup), { recursive: true });
  await cp(source, backup);

  console.log(`Compressing ${file} (backup: ${backup})`);
  const result = spawnSync('caveman-compress', [source], {
    cwd: root,
    stdio: 'inherit',
    shell: process.platform === 'win32'
  });

  if (result.status !== 0) {
    console.error(`Compression failed for ${basename(file)}. Restore from ${backup}.`);
    process.exit(result.status ?? 1);
  }
}

console.log('\nCompression complete. Review the Git diff, verify authority and policy meaning, then run npm run preflight.');
