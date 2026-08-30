import { readFile } from 'node:fs/promises';
import process from 'node:process';

const graphPath = new URL('../.engineering/DELIVERY-GRAPH.json', import.meta.url);
const profilePath = new URL('../.engineering/PROFILE.yaml', import.meta.url);

function getMode(profile) {
  const match = profile.match(/^mode:\s*(lite|standard|enterprise)\s*$/m);
  if (!match) throw new Error('Unable to resolve mode from .engineering/PROFILE.yaml');
  return match[1];
}

try {
  const [graphRaw, profileRaw] = await Promise.all([
    readFile(graphPath, 'utf8'),
    readFile(profilePath, 'utf8'),
  ]);
  const config = JSON.parse(graphRaw);
  const mode = getMode(profileRaw);

  console.log(`PES delivery graph — mode: ${mode}`);
  if (mode === 'lite') {
    console.log('DISABLED');
    console.log(config.lite.reason);
    console.log('Use single-agent Superpowers execution for routine slices.');
    process.exit(0);
  }

  const selected = config[mode];
  console.log(`Activation: ${selected.activation}`);
  console.log(`Graph: ${selected.graph.join(' -> ')}`);
  console.log(`Maximum specialists: ${selected.maxSpecialists}`);
  console.log(`Maximum review cycles: ${selected.maxReviewCycles}`);
  console.log(`Parallel execution: ${selected.parallelExecution ? 'allowed' : 'disabled'}`);
  console.log('\nActivate only when one or more reviewed triggers apply:');
  for (const trigger of config.triggers) console.log(`- ${trigger}`);
  console.log('\nCost controls: focused context reuse, deterministic checks first, unchanged-node skipping, capped retries and budget stop.');
  console.log('Recommendation only: a human must approve activation for the active slice.');
} catch (error) {
  console.error(`Delivery graph check failed: ${error.message}`);
  process.exitCode = 1;
}
