import { readFile } from 'node:fs/promises';
import process from 'node:process';

const profilePath = new URL('../deployment/PROFILE.json', import.meta.url);
const deploymentModes = ['single-provider', 'split', 'advisor-recommended'];
const appProviders = ['cloudflare', 'netlify', 'vercel', 'render'];
const databaseProviders = ['neon', 'supabase', 'render-postgres', 'provider-managed-postgres'];

function addScore(map, provider, points, reason) {
  const entry = map.get(provider);
  entry.score += points;
  entry.reasons.push(reason);
}

function scoreAppProviders(profile) {
  const scores = new Map(appProviders.map((provider) => [provider, { score: 0, reasons: [] }]));

  if (['static', 'spa'].includes(profile.frontend)) {
    addScore(scores, 'cloudflare', 4, 'Strong static and edge delivery fit.');
    addScore(scores, 'netlify', 3, 'Strong static-site and preview fit.');
  }
  if (profile.frontend === 'nextjs') {
    addScore(scores, 'vercel', 4, 'Strong Next.js and preview-deployment fit.');
    addScore(scores, 'netlify', 2, 'Supports Next.js and previews.');
    addScore(scores, 'cloudflare', 2, 'Suitable when runtime features are edge-compatible.');
  }
  if (['aspnet-container', 'container'].includes(profile.backend)) {
    addScore(scores, 'render', 5, 'Strong fit for containerized APIs and persistent services.');
  }
  if (profile.edgeExecutionRequired) {
    addScore(scores, 'cloudflare', 5, 'Edge execution is required.');
    addScore(scores, 'vercel', 2, 'Supports compatible edge workloads.');
  }
  if (profile.previewDeploymentsRequired) {
    addScore(scores, 'vercel', 3, 'Strong pull-request previews.');
    addScore(scores, 'netlify', 3, 'Strong deploy previews.');
  }
  if (profile.backgroundJobsRequired) {
    addScore(scores, 'render', 3, 'Supports persistent workers and background jobs.');
    addScore(scores, 'cloudflare', -1, 'May require provider-specific queue or workflow services.');
  }
  if (profile.coldStartsAccepted === false) {
    addScore(scores, 'render', 2, 'A continuously running service can avoid cold starts.');
    for (const provider of ['cloudflare', 'netlify', 'vercel']) {
      addScore(scores, provider, -1, 'Function execution characteristics require validation.');
    }
  }

  return [...scores.entries()]
    .map(([provider, value]) => ({ provider, ...value }))
    .sort((a, b) => b.score - a.score);
}

function scoreDatabaseProviders(profile) {
  const scores = new Map(databaseProviders.map((provider) => [provider, { score: 0, reasons: [] }]));

  if (profile.database === 'postgresql') {
    addScore(scores, 'neon', 4, 'Serverless PostgreSQL with separation from application hosting.');
    addScore(scores, 'supabase', 3, 'Managed PostgreSQL with optional platform services.');
    addScore(scores, 'render-postgres', 3, 'Operationally simple when the API is also on Render.');
    addScore(scores, 'provider-managed-postgres', 2, 'Can reduce vendor count when the chosen application host offers suitable managed PostgreSQL.');
  }
  if (profile.stage === 'pilot' || profile.stage === 'prototype') {
    addScore(scores, 'neon', 1, 'Potential low-usage pilot fit; verify current quotas.');
    addScore(scores, 'supabase', 1, 'Potential pilot fit; verify current quotas.');
  }
  if (profile.databaseRequirements?.connectionPooling) {
    addScore(scores, 'neon', 1, 'Pooling options may fit serverless or bursty clients; verify configuration.');
    addScore(scores, 'supabase', 1, 'Pooling options are available; verify transaction-mode constraints.');
  }
  if (profile.databaseRequirements?.sameProviderPreferred) {
    addScore(scores, 'render-postgres', 2, 'Reduces provider count when API hosting is Render.');
    addScore(scores, 'provider-managed-postgres', 2, 'Favors a single-provider topology.');
  }
  if (profile.databaseRequirements?.dataResidencyRequired) {
    for (const provider of databaseProviders) {
      addScore(scores, provider, 0, 'Region and data-residency availability must be verified before selection.');
    }
  }

  return [...scores.entries()]
    .map(([provider, value]) => ({ provider, ...value }))
    .sort((a, b) => b.score - a.score);
}

function buildTopologies(profile, appRanked, databaseRanked) {
  const bestApi = appRanked.find((x) => x.provider === 'render') ?? appRanked[0];
  const bestDatabase = databaseRanked[0];
  return [
    {
      mode: 'split',
      score: bestApi.score + bestDatabase.score,
      selection: {
        mobile: 'eas',
        api: bestApi.provider,
        database: bestDatabase.provider,
      },
      reason: 'EAS owns Android/iOS builds while API and PostgreSQL use independently selected managed providers.',
    },
    {
      mode: 'single-provider',
      score: bestApi.score - 1,
      selection: {
        mobile: 'eas',
        api: bestApi.provider,
        database: 'provider-managed-postgres',
      },
      reason: 'Mobile builds remain on EAS; API and database share one application provider where supported.',
    },
  ].sort((a, b) => b.score - a.score);
}

function validate(profile) {
  const required = ['stage', 'platform', 'deploymentMode', 'frontend', 'backend', 'database', 'traffic', 'monthlyBudgetUsd'];
  const missing = required.filter((key) => profile[key] === undefined || profile[key] === '');
  if (missing.length) throw new Error(`Deployment profile missing: ${missing.join(', ')}`);
  if (profile.platform !== 'mobile') throw new Error('This starter requires platform=mobile.');
  if (profile.frontend !== 'expo-react-native') throw new Error('Mobile frontend must be expo-react-native.');
  if (profile.mobile?.buildProvider !== 'eas') throw new Error('Mobile buildProvider must be eas.');
  if (!deploymentModes.includes(profile.deploymentMode)) {
    throw new Error(`deploymentMode must be one of: ${deploymentModes.join(', ')}`);
  }
  if (profile.approvedSelection && profile.deploymentMode === 'single-provider' && !profile.singleProvider) {
    throw new Error('Approved single-provider selection requires singleProvider.');
  }
  if (profile.approvedSelection && profile.deploymentMode === 'split') {
    const missingSplit = ['frontend', 'api', 'database'].filter((key) => !profile.splitProviders?.[key]);
    if (missingSplit.length) throw new Error(`Approved split selection missing: ${missingSplit.join(', ')}`);
  }
  const policy = profile.releasePolicy ?? {};
  for (const key of ['sameCertifiedSha', 'apiFirst', 'requireApiHealthCheck', 'requireEndToEndSmokeTest', 'requireRollbackPlan']) {
    if (policy[key] !== true) throw new Error(`releasePolicy.${key} must be true.`);
  }
}

try {
  const profile = JSON.parse(await readFile(profilePath, 'utf8'));
  validate(profile);
  const appRanked = scoreAppProviders(profile);
  const databaseRanked = scoreDatabaseProviders(profile);
  const topologies = buildTopologies(profile, appRanked, databaseRanked);

  console.log('PES deployment advisor');
  console.log(`Selected mode: ${profile.deploymentMode}`);
  console.log(`Human-approved: ${profile.approvedSelection ? 'yes' : 'no'}\n`);

  console.log('Mobile delivery: EAS Build/Submit for Android and iOS.');
  console.log('API/database topology recommendations:');
  for (const [index, topology] of topologies.entries()) {
    console.log(`${index + 1}. ${topology.mode} (fit score ${topology.score})`);
    console.log(`   ${JSON.stringify(topology.selection)}`);
    console.log(`   - ${topology.reason}`);
  }

  console.log('\nDatabase provider ranking:');
  for (const [index, result] of databaseRanked.entries()) {
    console.log(`${index + 1}. ${result.provider} (fit score ${result.score})`);
    for (const reason of result.reasons) console.log(`   - ${reason}`);
  }

  if (!profile.approvedSelection) {
    console.log('\nBLOCKED: Review current prices and constraints, choose a topology and database provider, then set approvedSelection=true.');
  } else {
    console.log('\nSelection is recorded, but this command still performs no provisioning or deployment.');
  }

  console.log('\nRequired release order: database/migrations → API → health check → certified mobile build → device smoke test → store submission or approved OTA update.');
  console.log('All components must reference the same certified Git SHA and have independent rollback instructions.');
} catch (error) {
  console.error(`Deployment advisor failed: ${error.message}`);
  process.exitCode = 1;
}
