import { createHash } from 'node:crypto';
import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';

const root = process.cwd();
const outputRoot = join(root, 'dist', 'knowledge');
const sources = [
  'README.md',
  'AGENTS.md',
  'CONTRIBUTING.md',
  'docs/OPERATING-MODES.md',
  'docs/integrations/NOTEBOOKLM.md',
  'docs/integrations/CAVEMAN.md',
  '.agents/skills/using-superpowers/SKILL.md',
  '.agents/skills/design-taste-frontend/SKILL.md',
  'security/SECURITY.md',
  'security/THREAT-MODEL.md',
  'security/DATA-CLASSIFICATION.md',
  'security/TRUST-BOUNDARIES.md'
];

function gitSha() {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
  } catch {
    return 'unavailable';
  }
}

await rm(outputRoot, { recursive: true, force: true });
await mkdir(outputRoot, { recursive: true });

const manifestSources = [];
for (const source of sources) {
  try {
    const sourcePath = join(root, source);
    const content = await readFile(sourcePath);
    const destination = join(outputRoot, source);
    await mkdir(dirname(destination), { recursive: true });
    await cp(sourcePath, destination);
    manifestSources.push({
      path: source,
      sha256: createHash('sha256').update(content).digest('hex'),
      bytes: content.byteLength
    });
  } catch (error) {
    if (error?.code !== 'ENOENT') throw error;
  }
}

const manifest = {
  generatedAt: new Date().toISOString(),
  repositoryCommit: gitSha(),
  authorityNotice: 'GitHub is authoritative. This bundle is explanatory and must not override repository documents, approved decisions, current code, or release evidence.',
  sources: manifestSources
};

await writeFile(join(outputRoot, 'SOURCE-MANIFEST.json'), `${JSON.stringify(manifest, null, 2)}\n`);
await writeFile(join(outputRoot, 'START-HERE.md'), `# PES Team Knowledge Bundle\n\n${manifest.authorityNotice}\n\nGenerated from commit: \`${manifest.repositoryCommit}\`\nGenerated at: \`${manifest.generatedAt}\`\n\nUpload this curated directory to NotebookLM or another approved team-learning tool. Review the source manifest and exclude any material that should not be shared.\n`);

console.log(`Knowledge bundle created at ${outputRoot}`);
console.log(`Included ${manifestSources.length} source files.`);
