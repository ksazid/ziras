import {json} from './lib.mjs';
import {buildDashboardData,loadDelivery} from './governance-lib.mjs';
const delivery = loadDelivery();
const dashboard = buildDashboardData(delivery);
const state = json('.engineering/STATE.json');
console.log(JSON.stringify({
  slice:delivery.current,
  state,
  summary:dashboard.summary,
  notifications:dashboard.notifications
},null,2));
