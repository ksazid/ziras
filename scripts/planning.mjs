import fs from 'node:fs';
import {json, fail} from './lib.mjs';
const req=json('delivery/requirements.json');
if(!Array.isArray(req.requirements)) fail('Invalid requirements registry');
fs.writeFileSync('planning/DELIVERY-STATUS.md',`# Delivery Status\n\nProject health: ${req.requirements.length ? 'AMBER' : 'BLOCKED'}\n\nRequirements: ${req.requirements.length}\n\nActive slice: none\n`);
console.log('Planning artifacts refreshed. Requirement and slice generation remains approval-driven.');
