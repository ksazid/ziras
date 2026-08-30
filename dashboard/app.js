const lifecycleOrder = [
  'discovery',
  'decision-pending',
  'approved',
  'implementing',
  'testing',
  'certification',
  'released',
  'validated'
];
const statusIcons = {
  approved: '✓',
  passed: '✓',
  validated: '✓',
  pending: '⏳',
  'decision-pending': '?',
  'changes-requested': '↻',
  rejected: '✕',
  blocked: '!',
  failed: '!',
  stale: '!',
  'rolled-back': '↶',
  released: '↑',
  default: '•'
};
const severityIcons = {high:'!',medium:'?',low:'i'};
let dashboard = null;

function text(value, fallback = 'Not set') {
  return value === null || value === undefined || value === '' ? fallback : String(value);
}
function formatLabel(value) {
  return text(value).replaceAll('-', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}
function iconFor(value) {
  return statusIcons[value] ?? statusIcons.default;
}
function link(label, href) {
  if (!href) return null;
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.textContent = label;
  anchor.target = '_blank';
  anchor.rel = 'noreferrer';
  return anchor;
}
function badge(value, className = 'record-status') {
  const span = document.createElement('span');
  span.className = className;
  span.textContent = `${iconFor(value)} ${formatLabel(value)}`;
  return span;
}
function emptyRecord(message) {
  const p = document.createElement('p');
  p.className = 'empty-state';
  p.textContent = message;
  return p;
}

function renderSummary() {
  const items = [
    ['Slices',dashboard.summary.slices,'Tracked across backlog, active and completed'],
    ['Active',dashboard.summary.active,'Currently progressing'],
    ['Blocked',dashboard.summary.blocked,'Needs intervention'],
    ['Pending decisions',dashboard.summary.pendingDecisions,'Product or policy choices'],
    ['Pending approvals',dashboard.summary.pendingApprovals,'Human gates'],
    ['Rolled back',dashboard.summary.rolledBack,'Recorded recovery events']
  ];
  const container = document.querySelector('#summary-cards');
  container.replaceChildren();
  const template = document.querySelector('#summary-card-template');
  for (const [label,value,detail] of items) {
    const node = template.content.cloneNode(true);
    node.querySelector('.summary-label').textContent = label;
    node.querySelector('.summary-value').textContent = value;
    node.querySelector('.summary-detail').textContent = detail;
    container.append(node);
  }
  const progress = dashboard.summary.progress;
  document.querySelector('#overall-progress-value').textContent = `${progress}%`;
  const bar = document.querySelector('#overall-progress-bar');
  bar.style.width = `${progress}%`;
  bar.parentElement.setAttribute('aria-valuenow',String(progress));
}

function renderNotifications() {
  const list = document.querySelector('#notification-list');
  list.replaceChildren();
  document.querySelector('#notification-count').textContent = dashboard.notifications.length;
  if (!dashboard.notifications.length) {
    list.append(emptyRecord('No action-required notifications.'));
    return;
  }
  for (const item of dashboard.notifications) {
    const row = document.createElement('article');
    row.className = 'notification-item';
    const icon = document.createElement('span');
    icon.className = 'notification-icon';
    icon.setAttribute('aria-hidden','true');
    icon.textContent = severityIcons[item.severity] ?? '•';
    const copy = document.createElement('div');
    const heading = document.createElement('h3');
    heading.textContent = item.title;
    const message = document.createElement('p');
    message.textContent = item.message;
    copy.append(heading,message);
    row.append(icon,copy);
    const action = link('Open evidence',item.action);
    if (action) row.append(action);
    list.append(row);
  }
}

function currentLifecycleIndex(slice) {
  const aliases = {
    proposed: -1,
    'ready-for-implementation': 2,
    certified: 5,
    'release-pending': 5,
    observed: 6,
    blocked: Math.max(0,lifecycleOrder.indexOf(slice.previousLifecycle ?? 'discovery')),
    deferred: -1,
    rejected: -1,
    superseded: -1,
    'rolled-back': 6
  };
  return lifecycleOrder.includes(slice.lifecycle) ? lifecycleOrder.indexOf(slice.lifecycle) : (aliases[slice.lifecycle] ?? -1);
}
function renderLifecycle(container,slice) {
  const current = currentLifecycleIndex(slice);
  container.replaceChildren();
  lifecycleOrder.forEach((stage,index) => {
    const step = document.createElement('div');
    step.className = `lifecycle-step ${index < current ? 'done' : index === current ? 'current' : ''}`;
    const dot = document.createElement('div');
    dot.className = 'lifecycle-dot';
    const label = document.createElement('span');
    label.className = 'lifecycle-label';
    label.textContent = formatLabel(stage);
    step.title = `${formatLabel(stage)}: ${index < current ? 'complete' : index === current ? 'current' : 'not reached'}`;
    step.append(dot,label);
    container.append(step);
  });
}
function renderGateProgress(container,slice) {
  container.replaceChildren();
  for (const [name,value] of Object.entries(slice.progress ?? {})) {
    const item = document.createElement('div');
    item.className = 'gate-progress';
    const head = document.createElement('div');
    head.className = 'gate-progress-head';
    const label = document.createElement('span');
    label.textContent = formatLabel(name);
    const percent = document.createElement('span');
    percent.textContent = `${value}%`;
    head.append(label,percent);
    const track = document.createElement('div');
    track.className = 'mini-track';
    track.setAttribute('role','progressbar');
    track.setAttribute('aria-label',`${formatLabel(name)} progress`);
    track.setAttribute('aria-valuemin','0');
    track.setAttribute('aria-valuemax','100');
    track.setAttribute('aria-valuenow',String(value));
    const fill = document.createElement('span');
    fill.style.width = `${value}%`;
    track.append(fill);
    item.append(head,track);
    container.append(item);
  }
}
function appendMeta(container,label,value) {
  const chip = document.createElement('span');
  chip.className = 'meta-chip';
  chip.textContent = `${label}: ${formatLabel(value)}`;
  container.append(chip);
}
function renderSliceAlerts(container,slice) {
  container.replaceChildren();
  const pendingApprovals = (slice.approvals ?? []).filter(item => item.status === 'pending');
  const pendingDecisions = (slice.decisions ?? []).filter(item => ['pending','changes-requested'].includes(item.status));
  if ((slice.blockers ?? []).length) {
    const alert = document.createElement('div');
    alert.className = 'alert danger';
    alert.textContent = `Blocked: ${slice.blockers.join(' · ')}`;
    container.append(alert);
  }
  if (pendingDecisions.length) {
    const alert = document.createElement('div');
    alert.className = 'alert warning';
    alert.textContent = `${pendingDecisions.length} decision${pendingDecisions.length === 1 ? '' : 's'} pending: ${pendingDecisions.map(item => item.id).join(', ')}`;
    container.append(alert);
  }
  if (pendingApprovals.length) {
    const alert = document.createElement('div');
    alert.className = 'alert warning';
    alert.textContent = `Approvals pending: ${pendingApprovals.map(item => formatLabel(item.type)).join(', ')}`;
    container.append(alert);
  }
  if (!pendingApprovals.length && !pendingDecisions.length && !(slice.blockers ?? []).length) {
    const alert = document.createElement('div');
    alert.className = 'alert success';
    alert.textContent = 'No recorded blockers, pending decisions or pending approvals.';
    container.append(alert);
  }
}
function renderSliceLinks(container,slice) {
  container.replaceChildren();
  const links = [
    link('Specification',slice.links?.specification),
    link('Implementation PR',slice.links?.implementationPr),
    ...(slice.links?.evidence ?? []).map((href,index) => link(`Evidence ${index + 1}`,href))
  ].filter(Boolean);
  if (!links.length) {
    const span = document.createElement('span');
    span.className = 'summary-detail';
    span.textContent = 'No linked evidence yet.';
    container.append(span);
    return;
  }
  container.append(...links);
}
function renderSlices() {
  const query = document.querySelector('#slice-search').value.trim().toLowerCase();
  const lifecycle = document.querySelector('#lifecycle-filter').value;
  const risk = document.querySelector('#risk-filter').value;
  const matches = dashboard.slices.filter(slice => {
    const searchable = `${slice.sliceId} ${slice.title}`.toLowerCase();
    return (!query || searchable.includes(query)) && (lifecycle === 'all' || slice.lifecycle === lifecycle) && (risk === 'all' || slice.riskLevel === risk);
  });
  const list = document.querySelector('#slice-list');
  list.replaceChildren();
  document.querySelector('#empty-slices').hidden = matches.length > 0;
  const template = document.querySelector('#slice-template');
  for (const slice of matches) {
    const node = template.content.cloneNode(true);
    const card = node.querySelector('.slice-card');
    card.dataset.sliceId = slice.sliceId;
    node.querySelector('.slice-id').textContent = slice.sliceId;
    const status = node.querySelector('.status-badge');
    status.textContent = `${iconFor(slice.lifecycle)} ${formatLabel(slice.lifecycle)}`;
    const riskBadge = node.querySelector('.risk-badge');
    riskBadge.classList.add(slice.riskLevel);
    riskBadge.textContent = `${formatLabel(slice.riskLevel)} risk`;
    node.querySelector('.slice-title').textContent = slice.title;
    node.querySelector('.slice-progress-value').textContent = `${slice.overallProgress}%`;
    renderLifecycle(node.querySelector('.lifecycle-rail'),slice);
    renderGateProgress(node.querySelector('.slice-progress-grid'),slice);
    const meta = node.querySelector('.slice-meta');
    appendMeta(meta,'Mode',slice.implementationMode);
    appendMeta(meta,'Certification',slice.certification?.status);
    appendMeta(meta,'Release',slice.release?.status);
    appendMeta(meta,'Rollback',slice.rollback?.status);
    renderSliceAlerts(node.querySelector('.slice-alerts'),slice);
    renderSliceLinks(node.querySelector('.slice-links'),slice);
    list.append(node);
  }
}

function renderDecisions() {
  const list = document.querySelector('#decision-list');
  list.replaceChildren();
  if (!dashboard.decisions.length) {
    list.append(emptyRecord('No product or policy decisions recorded.'));
    return;
  }
  for (const item of dashboard.decisions) {
    const row = document.createElement('article');
    row.className = 'record-item';
    const head = document.createElement('div');
    head.className = 'record-head';
    const heading = document.createElement('h3');
    heading.textContent = `${item.id} · ${item.sliceId}`;
    head.append(heading,badge(item.status));
    const question = document.createElement('p');
    question.textContent = item.question;
    const meta = document.createElement('div');
    meta.className = 'record-meta';
    for (const target of item.blocks ?? []) appendMeta(meta,'Blocks',target);
    row.append(head,question,meta);
    list.append(row);
  }
}
function renderReleases() {
  const list = document.querySelector('#release-list');
  list.replaceChildren();
  const records = [
    ...dashboard.releases.map(item => ({kind:'Release',...item})),
    ...dashboard.rollbacks.map(item => ({kind:'Rollback',...item}))
  ];
  if (!records.length) {
    list.append(emptyRecord('No releases or rollback events recorded.'));
    return;
  }
  for (const item of records) {
    const row = document.createElement('article');
    row.className = 'record-item';
    const head = document.createElement('div');
    head.className = 'record-head';
    const heading = document.createElement('h3');
    heading.textContent = `${item.kind} ${item.id}`;
    head.append(heading,badge(item.status));
    const message = document.createElement('p');
    message.textContent = item.kind === 'Release' ? `Slices: ${(item.sliceIds ?? []).join(', ')}` : `Release: ${item.releaseId} · ${item.reason}`;
    row.append(head,message);
    list.append(row);
  }
}
function populateFilters() {
  const select = document.querySelector('#lifecycle-filter');
  const states = [...new Set(dashboard.slices.map(slice => slice.lifecycle))].sort();
  for (const state of states) {
    const option = document.createElement('option');
    option.value = state;
    option.textContent = formatLabel(state);
    select.append(option);
  }
}
function wireInteractions() {
  for (const id of ['slice-search','lifecycle-filter','risk-filter']) document.querySelector(`#${id}`).addEventListener('input',renderSlices);
  const panel = document.querySelector('#notifications');
  const button = document.querySelector('#notification-button');
  const setOpen = open => {
    panel.hidden = !open;
    button.setAttribute('aria-expanded',String(open));
    if (open) panel.scrollIntoView({behavior:'smooth',block:'start'});
  };
  button.addEventListener('click',() => setOpen(panel.hidden));
  document.querySelector('#close-notifications').addEventListener('click',() => setOpen(false));
}

async function start() {
  try {
    const response = await fetch('./data.json',{cache:'no-store'});
    if (!response.ok) throw new Error(`Dashboard data request failed: ${response.status}`);
    dashboard = await response.json();
    document.querySelector('#generated-at').textContent = `Generated ${new Date(dashboard.generatedAt).toLocaleString()}`;
    populateFilters();
    renderSummary();
    renderNotifications();
    renderSlices();
    renderDecisions();
    renderReleases();
    wireInteractions();
  } catch (error) {
    document.querySelector('#generated-at').textContent = 'Dashboard unavailable';
    const message = document.createElement('p');
    message.className = 'empty-state';
    message.textContent = `${error.message}. Run npm run dashboard:build and serve the dashboard directory over HTTP.`;
    document.querySelector('#main').prepend(message);
  }
}
start();
