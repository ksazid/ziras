import fs from 'node:fs';
import path from 'node:path';
import {json, root} from './lib.mjs';

const SHA_PATTERN = /^[0-9a-f]{40}$/i;
const SLICE_PATTERN = /^VS-\d+$/;
const ACTIVE_LIFECYCLES = new Set([
  'ready-for-implementation',
  'implementing',
  'testing',
  'certification',
  'certified',
  'release-pending',
  'released',
  'observed',
  'validated'
]);
const CERTIFICATION_STAGE_LIFECYCLES = new Set(['certification','certified','release-pending','released','observed','validated']);
const CERTIFICATION_REQUIRED_LIFECYCLES = new Set(['certified','release-pending','released','observed','validated']);
const RELEASE_STAGE_LIFECYCLES = new Set(['release-pending','released','observed','validated']);
const RELEASE_AUTHORIZED_LIFECYCLES = new Set(['released','observed','validated']);

export function loadDelivery() {
  const governance = json('delivery/governance.json');
  const current = json('delivery/current-slice.json');
  const backlog = json('delivery/backlog.json');
  const completed = json('delivery/completed-slices.json');
  const decisions = json('delivery/decisions.json');
  const releases = json('delivery/releases.json');
  const rollbacks = json('delivery/rollbacks.json');
  const slices = [
    ...(Array.isArray(backlog.slices) ? backlog.slices : []),
    ...(current.sliceId ? [current] : []),
    ...(Array.isArray(completed.slices) ? completed.slices : [])
  ];
  return {governance,current,backlog,completed,decisions,releases,rollbacks,slices};
}

function approval(slice, type) {
  return Array.isArray(slice.approvals) ? slice.approvals.find(item => item?.type === type) : undefined;
}

function approved(slice, type) {
  return approval(slice,type)?.status === 'approved';
}

function decisionMap(delivery) {
  return new Map((delivery.decisions.decisions ?? []).map(item => [item.id,item]));
}

function releaseMap(delivery) {
  return new Map((delivery.releases.releases ?? []).map(item => [item.id,item]));
}

function rollbackMap(delivery) {
  return new Map((delivery.rollbacks.rollbacks ?? []).map(item => [item.id,item]));
}

function isNonEmpty(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function record(errors, condition, message) {
  if (!condition) errors.push(message);
}

function warn(warnings, condition, message) {
  if (!condition) warnings.push(message);
}

function validateApproval(item, model, label, errors) {
  record(errors, item && typeof item === 'object', `${label}: approval must be an object`);
  if (!item || typeof item !== 'object') return;
  record(errors, model.approvalTypes.includes(item.type), `${label}: unknown approval type ${item.type}`);
  record(errors, model.approvalStatuses.includes(item.status), `${label}: invalid approval status ${item.status}`);
  if (item.status === 'approved') {
    record(errors, isNonEmpty(item.by), `${label}: approved ${item.type} approval requires by`);
    record(errors, isNonEmpty(item.at), `${label}: approved ${item.type} approval requires at`);
    record(errors, isNonEmpty(item.rationale), `${label}: approved ${item.type} approval requires rationale`);
    if (['certification','release','production-enable'].includes(item.type)) {
      record(errors, SHA_PATTERN.test(item.commitSha ?? ''), `${label}: approved ${item.type} approval requires an exact 40-character commit SHA`);
    } else {
      record(errors, isNonEmpty(item.version) || SHA_PATTERN.test(item.commitSha ?? ''), `${label}: approved ${item.type} approval requires a version or exact commit SHA`);
    }
  }
}

function validateSlice(slice, delivery, label, errors, warnings) {
  const model = delivery.governance;
  record(errors, slice && typeof slice === 'object', `${label}: slice must be an object`);
  if (!slice || typeof slice !== 'object') return;
  record(errors, slice.schemaVersion === 2, `${label}: schemaVersion must be 2`);
  record(errors, SLICE_PATTERN.test(slice.sliceId ?? ''), `${label}: sliceId must match VS-<number>`);
  record(errors, isNonEmpty(slice.title), `${label}: title is required`);
  record(errors, model.lifecycleStates.includes(slice.lifecycle), `${label}: unknown lifecycle ${slice.lifecycle}`);
  record(errors, model.riskLevels.includes(slice.riskLevel), `${label}: invalid riskLevel ${slice.riskLevel}`);
  record(errors, model.implementationModes.includes(slice.implementationMode), `${label}: invalid implementationMode ${slice.implementationMode}`);
  record(errors, Array.isArray(slice.requirements) && slice.requirements.length > 0, `${label}: at least one requirement ID is required`);
  record(errors, Array.isArray(slice.dependencies), `${label}: dependencies must be an array`);
  record(errors, Array.isArray(slice.blockers), `${label}: blockers must be an array`);
  record(errors, Array.isArray(slice.decisionIds), `${label}: decisionIds must be an array`);
  record(errors, slice.owners && typeof slice.owners === 'object', `${label}: owners are required`);
  record(errors, slice.impact && Array.isArray(slice.impact.areas), `${label}: impact.areas must be an array`);
  record(errors, slice.impact && Array.isArray(slice.impact.notes), `${label}: impact.notes must be an array`);
  for (const area of slice.impact?.areas ?? []) {
    record(errors, model.impactAreas.includes(area), `${label}: unknown impact area ${area}`);
  }
  if (slice.riskLevel === 'medium' || slice.riskLevel === 'high') {
    record(errors, (slice.impact?.areas ?? []).length > 0, `${label}: ${slice.riskLevel}-risk slices require an impact declaration`);
    record(errors, isNonEmpty(slice.owners?.product), `${label}: ${slice.riskLevel}-risk slices require a product owner`);
    record(errors, isNonEmpty(slice.owners?.engineering), `${label}: ${slice.riskLevel}-risk slices require an engineering owner`);
  }
  if (slice.riskLevel === 'high') {
    record(errors, isNonEmpty(slice.owners?.operations), `${label}: high-risk slices require an operations owner`);
    record(errors, isNonEmpty(slice.owners?.security), `${label}: high-risk slices require a security owner`);
  }

  record(errors, Array.isArray(slice.approvals), `${label}: approvals must be an array`);
  const seenApprovalTypes = new Set();
  for (const item of slice.approvals ?? []) {
    validateApproval(item,model,label,errors);
    if (seenApprovalTypes.has(item?.type)) errors.push(`${label}: duplicate ${item.type} approval`);
    seenApprovalTypes.add(item?.type);
  }
  for (const type of model.approvalTypes) {
    record(errors, seenApprovalTypes.has(type), `${label}: missing ${type} approval record`);
  }

  const decisions = decisionMap(delivery);
  for (const id of slice.decisionIds ?? []) {
    record(errors, decisions.has(id), `${label}: references unknown decision ${id}`);
  }
  const linkedDecisions = (slice.decisionIds ?? []).map(id => decisions.get(id)).filter(Boolean);
  const pendingBlocks = new Set(linkedDecisions.filter(item => ['pending','changes-requested'].includes(item.status)).flatMap(item => item.blocks ?? []));
  if (pendingBlocks.has('implementation')) {
    record(errors, !ACTIVE_LIFECYCLES.has(slice.lifecycle) && ['specification-only','contracts-only'].includes(slice.implementationMode), `${label}: unresolved decisions block implementation`);
  }
  if (pendingBlocks.has('certification')) {
    record(errors, !CERTIFICATION_STAGE_LIFECYCLES.has(slice.lifecycle), `${label}: unresolved decisions block certification`);
  }
  if (pendingBlocks.has('release')) {
    record(errors, !RELEASE_STAGE_LIFECYCLES.has(slice.lifecycle) && ['not-authorized','pending'].includes(slice.release?.status), `${label}: unresolved decisions block release`);
  }
  if (pendingBlocks.has('production-enable')) {
    record(errors, slice.implementationMode !== 'production-enabled', `${label}: unresolved decisions block production enablement`);
  }

  if (ACTIVE_LIFECYCLES.has(slice.lifecycle) || ['runtime-disabled','runtime-enabled','production-enabled'].includes(slice.implementationMode)) {
    record(errors, approved(slice,'scope'), `${label}: scope approval is required before implementation`);
    record(errors, approved(slice,'implementation'), `${label}: implementation approval is required before runtime work`);
  }
  if (slice.implementationMode === 'production-enabled') {
    record(errors, approved(slice,'production-enable'), `${label}: production-enabled mode requires production-enable approval`);
  }

  const progress = slice.progress ?? {};
  for (const key of ['discovery','decisions','implementation','testing','certification','release','validation']) {
    const value = progress[key];
    record(errors, Number.isInteger(value) && value >= 0 && value <= 100, `${label}: progress.${key} must be an integer from 0 to 100`);
  }

  record(errors, model.certificationStatuses.includes(slice.certification?.status), `${label}: invalid certification status ${slice.certification?.status}`);
  if (slice.certification?.status === 'passed') {
    record(errors, SHA_PATTERN.test(slice.certification.commitSha ?? ''), `${label}: passed certification requires an exact commit SHA`);
    record(errors, approved(slice,'certification'), `${label}: passed certification requires certification approval`);
    const certificationApproval = approval(slice,'certification');
    record(errors, certificationApproval?.commitSha === slice.certification.commitSha, `${label}: certification approval must bind the certified SHA`);
  }
  if (CERTIFICATION_REQUIRED_LIFECYCLES.has(slice.lifecycle)) {
    record(errors, slice.certification?.status === 'passed', `${label}: lifecycle ${slice.lifecycle} requires passed certification`);
  }

  record(errors, model.releaseStatuses.includes(slice.release?.status), `${label}: invalid release status ${slice.release?.status}`);
  record(errors, model.rollbackStatuses.includes(slice.rollback?.status), `${label}: invalid rollback status ${slice.rollback?.status}`);
  record(errors, model.postReleaseStatuses.includes(slice.postRelease?.status), `${label}: invalid post-release status ${slice.postRelease?.status}`);

  const releases = releaseMap(delivery);
  if (slice.release?.releaseId) record(errors, releases.has(slice.release.releaseId), `${label}: references unknown release ${slice.release.releaseId}`);
  const rollbacks = rollbackMap(delivery);
  if (slice.rollback?.rollbackId) record(errors, rollbacks.has(slice.rollback.rollbackId), `${label}: references unknown rollback ${slice.rollback.rollbackId}`);

  if (slice.lifecycle === 'release-pending') {
    record(errors, slice.certification?.status === 'passed', `${label}: release-pending requires passed certification`);
    record(errors, isNonEmpty(slice.release?.releaseId), `${label}: release-pending requires a releaseId`);
    record(errors, ['pending','approved'].includes(slice.release?.status), `${label}: release-pending requires pending or approved release status`);
  }
  if (['approved','deploying','released'].includes(slice.release?.status) || RELEASE_AUTHORIZED_LIFECYCLES.has(slice.lifecycle)) {
    record(errors, slice.certification?.status === 'passed', `${label}: release requires passed certification`);
    record(errors, approved(slice,'release'), `${label}: release approval is required`);
    record(errors, isNonEmpty(slice.release?.releaseId), `${label}: releaseId is required`);
    if (slice.riskLevel !== 'low') record(errors, slice.rollback?.status === 'ready', `${label}: medium/high-risk release requires rollback readiness`);
  }
  if (['released','observed','validated'].includes(slice.lifecycle)) {
    record(errors, isNonEmpty(slice.postRelease?.expectedOutcome), `${label}: released slices require an expected outcome`);
    record(errors, Array.isArray(slice.postRelease?.metrics) && slice.postRelease.metrics.length > 0, `${label}: released slices require at least one outcome metric`);
    record(errors, isNonEmpty(slice.postRelease?.reviewAt), `${label}: released slices require a post-release review date`);
  }

  warn(warnings, (slice.blockers ?? []).length === 0 || slice.lifecycle === 'blocked', `${label}: blockers exist but lifecycle is not blocked`);
  warn(warnings, slice.riskLevel !== 'low' || (slice.impact?.areas ?? []).length <= 6, `${label}: broad low-risk impact declaration may need a higher risk level`);
}

function validateDecision(item, delivery, errors) {
  const model = delivery.governance;
  const label = `decision ${item?.id ?? '<missing>'}`;
  record(errors, item && typeof item === 'object', `${label}: must be an object`);
  if (!item || typeof item !== 'object') return;
  record(errors, /^DEC-\d+$/.test(item.id ?? ''), `${label}: id must match DEC-<number>`);
  record(errors, SLICE_PATTERN.test(item.sliceId ?? ''), `${label}: sliceId must match VS-<number>`);
  record(errors, isNonEmpty(item.question), `${label}: question is required`);
  record(errors, model.decisionStatuses.includes(item.status), `${label}: invalid status ${item.status}`);
  record(errors, Array.isArray(item.options) && item.options.length > 0, `${label}: options are required`);
  record(errors, Array.isArray(item.blocks), `${label}: blocks must be an array`);
  for (const target of item.blocks ?? []) record(errors, model.decisionBlockTargets.includes(target), `${label}: invalid block target ${target}`);
  if (item.status === 'approved') {
    record(errors, isNonEmpty(item.decision), `${label}: approved decision requires decision`);
    record(errors, isNonEmpty(item.decidedBy), `${label}: approved decision requires decidedBy`);
    record(errors, isNonEmpty(item.decidedAt), `${label}: approved decision requires decidedAt`);
    record(errors, isNonEmpty(item.rationale), `${label}: approved decision requires rationale`);
  }
  if (item.status === 'rejected') {
    record(errors, isNonEmpty(item.rationale), `${label}: rejected decision requires rationale`);
  }
}

function validateRelease(item, delivery, errors) {
  const label = `release ${item?.id ?? '<missing>'}`;
  record(errors, item && typeof item === 'object', `${label}: must be an object`);
  if (!item || typeof item !== 'object') return;
  record(errors, /^REL-\d+$/.test(item.id ?? ''), `${label}: id must match REL-<number>`);
  record(errors, Array.isArray(item.sliceIds) && item.sliceIds.length > 0, `${label}: sliceIds are required`);
  record(errors, delivery.governance.releaseStatuses.includes(item.status), `${label}: invalid status ${item.status}`);
  record(errors, SHA_PATTERN.test(item.commitSha ?? ''), `${label}: exact commit SHA is required`);
  record(errors, Array.isArray(item.migrations), `${label}: migrations must be an array`);
  record(errors, Array.isArray(item.configurationChanges), `${label}: configurationChanges must be an array`);
  record(errors, Array.isArray(item.featureFlags), `${label}: featureFlags must be an array`);
  record(errors, Array.isArray(item.smokeTests), `${label}: smokeTests must be an array`);
  record(errors, item.rollbackStrategy && typeof item.rollbackStrategy === 'object', `${label}: rollbackStrategy is required`);
  if (['approved','deploying','released'].includes(item.status)) {
    record(errors, isNonEmpty(item.approvedBy), `${label}: approved release requires approvedBy`);
    record(errors, isNonEmpty(item.approvedAt), `${label}: approved release requires approvedAt`);
    record(errors, item.smokeTests.length > 0, `${label}: approved release requires smoke tests`);
    record(errors, isNonEmpty(item.rollbackStrategy?.summary), `${label}: approved release requires a rollback or forward-recovery strategy`);
  }
  if (item.status === 'released') {
    record(errors, item.productionVerification?.status === 'passed', `${label}: released status requires passed production verification`);
  }
}

function validateRollback(item, delivery, errors) {
  const label = `rollback ${item?.id ?? '<missing>'}`;
  record(errors, item && typeof item === 'object', `${label}: must be an object`);
  if (!item || typeof item !== 'object') return;
  record(errors, /^RB-\d+$/.test(item.id ?? ''), `${label}: id must match RB-<number>`);
  record(errors, isNonEmpty(item.releaseId), `${label}: releaseId is required`);
  record(errors, delivery.governance.rollbackStatuses.includes(item.status), `${label}: invalid status ${item.status}`);
  record(errors, isNonEmpty(item.reason), `${label}: reason is required`);
  if (['initiated','completed','failed'].includes(item.status)) {
    record(errors, isNonEmpty(item.initiatedBy), `${label}: initiated rollback requires initiatedBy`);
    record(errors, isNonEmpty(item.initiatedAt), `${label}: initiated rollback requires initiatedAt`);
  }
  if (item.status === 'completed') record(errors, Array.isArray(item.verification) && item.verification.length > 0, `${label}: completed rollback requires verification evidence`);
}

export function validateDelivery(delivery = loadDelivery()) {
  const errors = [];
  const warnings = [];
  const model = delivery.governance;
  record(errors, model.schemaVersion === 1, 'delivery/governance.json: schemaVersion must be 1');
  for (const key of ['lifecycleStates','approvalTypes','approvalStatuses','decisionStatuses','implementationModes','riskLevels','impactAreas','decisionBlockTargets','certificationStatuses','releaseStatuses','rollbackStatuses','postReleaseStatuses']) {
    record(errors, Array.isArray(model[key]) && model[key].length > 0, `delivery/governance.json: ${key} must be a non-empty array`);
  }
  for (const [from,targets] of Object.entries(model.transitions ?? {})) {
    record(errors, model.lifecycleStates.includes(from), `delivery/governance.json: transition source ${from} is not a lifecycle state`);
    record(errors, Array.isArray(targets), `delivery/governance.json: transitions.${from} must be an array`);
    for (const target of targets ?? []) record(errors, model.lifecycleStates.includes(target), `delivery/governance.json: transition target ${target} is not a lifecycle state`);
  }

  if (delivery.current.sliceId) validateSlice(delivery.current,delivery,`slice ${delivery.current.sliceId}`,errors,warnings);
  else {
    record(errors, delivery.current.schemaVersion === 2, 'delivery/current-slice.json: schemaVersion must be 2');
    record(errors, delivery.current.status === 'inactive', 'delivery/current-slice.json: null sliceId must be inactive');
  }

  const sliceIds = new Set();
  for (const [index,slice] of (delivery.backlog.slices ?? []).entries()) {
    validateSlice(slice,delivery,`backlog slice ${index + 1}`,errors,warnings);
    if (sliceIds.has(slice.sliceId)) errors.push(`duplicate sliceId ${slice.sliceId}`);
    sliceIds.add(slice.sliceId);
  }
  if (delivery.current.sliceId) {
    if (sliceIds.has(delivery.current.sliceId)) errors.push(`duplicate sliceId ${delivery.current.sliceId}`);
    sliceIds.add(delivery.current.sliceId);
  }
  for (const [index,slice] of (delivery.completed.slices ?? []).entries()) {
    validateSlice(slice,delivery,`completed slice ${index + 1}`,errors,warnings);
    if (sliceIds.has(slice.sliceId)) errors.push(`duplicate sliceId ${slice.sliceId}`);
    sliceIds.add(slice.sliceId);
  }

  const decisionIds = new Set();
  for (const item of delivery.decisions.decisions ?? []) {
    validateDecision(item,delivery,errors);
    if (decisionIds.has(item.id)) errors.push(`duplicate decision id ${item.id}`);
    decisionIds.add(item.id);
  }
  const releaseIds = new Set();
  for (const item of delivery.releases.releases ?? []) {
    validateRelease(item,delivery,errors);
    if (releaseIds.has(item.id)) errors.push(`duplicate release id ${item.id}`);
    releaseIds.add(item.id);
  }
  const rollbackIds = new Set();
  for (const item of delivery.rollbacks.rollbacks ?? []) {
    validateRollback(item,delivery,errors);
    if (rollbackIds.has(item.id)) errors.push(`duplicate rollback id ${item.id}`);
    rollbackIds.add(item.id);
  }

  return {errors,warnings};
}

export function calculateSliceProgress(slice) {
  const values = Object.values(slice.progress ?? {}).filter(Number.isFinite);
  if (!values.length) return 0;
  return Math.round(values.reduce((sum,value) => sum + value,0) / values.length);
}

export function buildNotifications(delivery = loadDelivery()) {
  const notifications = [];
  const decisions = decisionMap(delivery);
  for (const slice of delivery.slices) {
    const label = `${slice.sliceId} ${slice.title}`;
    for (const item of slice.approvals ?? []) {
      if (item.status === 'pending' && ['scope','implementation','certification','release','production-enable'].includes(item.type)) {
        notifications.push({
          id: `${slice.sliceId}-approval-${item.type}`,
          severity: ['release','production-enable'].includes(item.type) ? 'high' : 'medium',
          type: 'approval-required',
          sliceId: slice.sliceId,
          title: `${item.type} approval required`,
          message: `${label} is waiting for ${item.type} approval.`,
          action: slice.links?.implementationPr ?? slice.links?.specification ?? null
        });
      }
      if (['rejected','changes-requested','revoked'].includes(item.status)) {
        notifications.push({
          id: `${slice.sliceId}-approval-${item.type}-${item.status}`,
          severity: 'high',
          type: 'approval-blocked',
          sliceId: slice.sliceId,
          title: `${item.type} approval ${item.status}`,
          message: `${label} cannot advance until the approval state is resolved.`,
          action: slice.links?.specification ?? null
        });
      }
    }
    for (const id of slice.decisionIds ?? []) {
      const item = decisions.get(id);
      if (item && ['pending','changes-requested'].includes(item.status)) {
        notifications.push({
          id: `${slice.sliceId}-decision-${id}`,
          severity: item.blocks?.includes('production-enable') || item.blocks?.includes('release') ? 'high' : 'medium',
          type: 'decision-pending',
          sliceId: slice.sliceId,
          title: `${id} decision ${item.status}`,
          message: item.question,
          action: slice.links?.specification ?? null
        });
      }
    }
    if ((slice.blockers ?? []).length > 0) {
      notifications.push({
        id: `${slice.sliceId}-blockers`,
        severity: 'high',
        type: 'slice-blocked',
        sliceId: slice.sliceId,
        title: `${slice.blockers.length} blocker${slice.blockers.length === 1 ? '' : 's'}`,
        message: slice.blockers.join(' · '),
        action: slice.links?.implementationPr ?? slice.links?.specification ?? null
      });
    }
    if (['failed','stale'].includes(slice.certification?.status)) {
      notifications.push({
        id: `${slice.sliceId}-certification-${slice.certification.status}`,
        severity: 'high',
        type: 'certification-attention',
        sliceId: slice.sliceId,
        title: `Certification ${slice.certification.status}`,
        message: `${label} requires new exact-head certification evidence.`,
        action: slice.links?.implementationPr ?? null
      });
    }
    if (slice.postRelease?.reviewAt && slice.postRelease.status === 'not-started') {
      notifications.push({
        id: `${slice.sliceId}-post-release-review`,
        severity: 'low',
        type: 'post-release-review',
        sliceId: slice.sliceId,
        title: 'Post-release review scheduled',
        message: `${label} outcome review is due ${slice.postRelease.reviewAt}.`,
        action: slice.links?.evidence?.[0] ?? null
      });
    }
  }
  const order = {high:0,medium:1,low:2};
  return notifications.sort((a,b) => order[a.severity] - order[b.severity] || a.sliceId.localeCompare(b.sliceId));
}

export function buildDashboardData(delivery = loadDelivery()) {
  const slices = delivery.slices.map(slice => ({
    ...slice,
    overallProgress: calculateSliceProgress(slice),
    decisions: (slice.decisionIds ?? []).map(id => (delivery.decisions.decisions ?? []).find(item => item.id === id)).filter(Boolean)
  }));
  const lifecycleCounts = Object.fromEntries(delivery.governance.lifecycleStates.map(state => [state,0]));
  for (const slice of slices) lifecycleCounts[slice.lifecycle] = (lifecycleCounts[slice.lifecycle] ?? 0) + 1;
  const completed = slices.filter(slice => ['validated','released','observed','certified'].includes(slice.lifecycle)).length;
  const progress = slices.length ? Math.round(slices.reduce((sum,slice) => sum + slice.overallProgress,0) / slices.length) : 0;
  return {
    generatedAt: new Date().toISOString(),
    schemaVersion: 1,
    summary: {
      slices: slices.length,
      completed,
      active: slices.filter(slice => !delivery.governance.terminalStates.includes(slice.lifecycle) && !['proposed','deferred'].includes(slice.lifecycle)).length,
      blocked: slices.filter(slice => slice.lifecycle === 'blocked' || (slice.blockers ?? []).length > 0).length,
      pendingDecisions: (delivery.decisions.decisions ?? []).filter(item => ['pending','changes-requested'].includes(item.status)).length,
      pendingApprovals: slices.flatMap(slice => slice.approvals ?? []).filter(item => item.status === 'pending').length,
      rolledBack: slices.filter(slice => slice.lifecycle === 'rolled-back' || slice.rollback?.status === 'completed').length,
      progress
    },
    lifecycleCounts,
    slices,
    decisions: delivery.decisions.decisions ?? [],
    releases: delivery.releases.releases ?? [],
    rollbacks: delivery.rollbacks.rollbacks ?? [],
    notifications: buildNotifications(delivery)
  };
}

export function writeDashboardData(data, outputPath = 'dashboard/data.json') {
  const target = path.join(root,outputPath);
  fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.writeFileSync(target,JSON.stringify(data,null,2)+'\n');
}

export function dashboardDataMatches(data, outputPath = 'dashboard/data.json') {
  const target = path.join(root,outputPath);
  if (!fs.existsSync(target)) return false;
  const existing = JSON.parse(fs.readFileSync(target,'utf8'));
  const stable = value => JSON.stringify({...value,generatedAt:'<ignored>'});
  return stable(existing) === stable(data);
}
