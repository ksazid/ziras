import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const readJson = path => JSON.parse(fs.readFileSync(path, 'utf8'));

test('mobile workspace uses the Expo SDK 57 baseline', () => {
  const root = readJson('package.json');
  const mobile = readJson('apps/mobile/package.json');
  const app = readJson('apps/mobile/app.json');

  assert.ok(root.workspaces.includes('apps/mobile'));
  assert.equal(mobile.main, 'expo-router/entry');
  assert.match(mobile.dependencies.expo, /^~57\./);
  assert.equal(mobile.dependencies.react, '19.2.3');
  assert.match(mobile.dependencies['react-native'], /^0\.86\./);
  assert.equal(app.expo.newArchEnabled, true);
});

test('mobile application has routable screens and secure storage', () => {
  for (const path of [
    'apps/mobile/app/_layout.tsx',
    'apps/mobile/app/index.tsx',
    'apps/mobile/app/(tabs)/_layout.tsx',
    'apps/mobile/app/(tabs)/index.tsx',
    'apps/mobile/src/lib/secure-storage.ts'
  ]) {
    assert.equal(fs.existsSync(path), true, `${path} must exist`);
  }
});
