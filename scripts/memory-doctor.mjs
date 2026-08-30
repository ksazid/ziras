import { spawnSync } from 'node:child_process';

const result = spawnSync('mempalace', ['--version'], {
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe']
});

if (result.error?.code === 'ENOENT') {
  console.log('MemPalace is not installed.');
  console.log('Optional install: uv tool install mempalace');
  console.log('Then initialize this project explicitly: mempalace init .');
  console.log('PES will continue to work without MemPalace.');
  process.exit(0);
}

if (result.status !== 0) {
  console.error('MemPalace was found but did not respond successfully.');
  console.error((result.stderr || result.stdout || '').trim());
  process.exit(1);
}

console.log(`MemPalace available: ${(result.stdout || result.stderr).trim()}`);
console.log('Safe next step: review docs/integrations/MEMPALACE.md before indexing content.');
