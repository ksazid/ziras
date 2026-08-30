import fs from 'node:fs';
import {buildDashboardData,loadDelivery,validateDelivery,writeDashboardData} from './governance-lib.mjs';

const checkOnly = process.argv.includes('--check');
const delivery = loadDelivery();
const validation = validateDelivery(delivery);
if (validation.errors.length) {
  for (const error of validation.errors) console.error(`ERROR: ${error}`);
  process.exit(1);
}
for (const required of ['dashboard/index.html','dashboard/app.js','dashboard/styles.css']) {
  if (!fs.existsSync(required)) {
    console.error(`ERROR: missing dashboard asset ${required}`);
    process.exit(1);
  }
}

const data = buildDashboardData(delivery);
const now = Date.now();

data.summary.completed = data.slices.filter(slice =>
  ['released','observed','validated'].includes(slice.lifecycle)
).length;

data.notifications = data.notifications.map(notification => {
  if (notification.type !== 'post-release-review') return notification;
  const slice = data.slices.find(item => item.sliceId === notification.sliceId);
  const reviewAt = Date.parse(slice?.postRelease?.reviewAt ?? '');
  if (Number.isFinite(reviewAt) && reviewAt <= now) {
    return {
      ...notification,
      severity:'high',
      type:'post-release-review-overdue',
      title:'Post-release review overdue',
      message:`${slice.sliceId} ${slice.title} outcome review was due ${slice.postRelease.reviewAt}.`
    };
  }
  return {
    ...notification,
    severity:'low',
    type:'post-release-review-scheduled',
    title:'Post-release review scheduled'
  };
});

const severityOrder = {high:0,medium:1,low:2};
data.notifications.sort((a,b) =>
  severityOrder[a.severity] - severityOrder[b.severity] || a.sliceId.localeCompare(b.sliceId)
);

if (checkOnly) {
  console.log(`Dashboard check passed for ${data.summary.slices} slice(s) and ${data.notifications.length} notification(s)`);
  process.exit(0);
}
writeDashboardData(data);
console.log(`Dashboard data generated at dashboard/data.json (${data.summary.slices} slice(s))`);
