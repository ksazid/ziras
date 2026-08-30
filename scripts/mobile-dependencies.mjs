import fs from 'node:fs';
import path from 'node:path';
import { root } from './lib.mjs';

const mobilePackagePath = path.join(root, 'apps/mobile/package.json');
if (!fs.existsSync(mobilePackagePath)) {
  console.error('ERROR: apps/mobile/package.json is missing.');
  process.exit(1);
}

const mobile = JSON.parse(fs.readFileSync(mobilePackagePath, 'utf8'));
const required = ['expo', 'expo-router', 'react', 'react-native'];
for (const name of required) {
  if (!mobile.dependencies?.[name]) {
    console.error(`ERROR: apps/mobile/package.json is missing ${name}.`);
    process.exit(1);
  }
}

const installedRoot = path.join(root, 'node_modules');
if (!fs.existsSync(installedRoot)) {
  console.error('ERROR: dependencies are not installed. Run `npm install` from the repository root.');
  process.exit(1);
}

for (const name of required) {
  const installed = path.join(installedRoot, name, 'package.json');
  if (!fs.existsSync(installed)) {
    console.error(`ERROR: ${name} is not installed. Run \`npm install\`, then \`npx expo install --fix --cwd apps/mobile\`.`);
    process.exit(1);
  }
}

console.log('Mobile dependency installation is present.');
