import {loadDelivery,validateDelivery} from './governance-lib.mjs';

const result = validateDelivery(loadDelivery());
for (const warning of result.warnings) console.warn(`WARN: ${warning}`);
if (result.errors.length) {
  for (const error of result.errors) console.error(`ERROR: ${error}`);
  process.exit(1);
}
console.log(`Governance validation passed${result.warnings.length ? ` with ${result.warnings.length} warning(s)` : ''}`);
