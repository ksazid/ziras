# VS-07 Final Certification — 2026-09-01 through 2026-09-14

## Verdict

**FAIL — the frozen 14-day POC acceptance contract is not satisfied.**

This verdict concerns measurement acceptance, not workflow execution. The ingestion workflow reached Day 14, but VS-07 requires 14 consecutive complete daily evidence records. Production source access remains **OFF**.

## Decisive evidence

- **Day 1 replacement run 33483023566** measured frozen main SHA `745018e2dc5115b65faf3fb363d677fd411dee6a`. Trigger-wrapper SHA `6e51a61c55ff90f7b8330320ef4d1d597d550138` is not the measured SHA. Ingestion was partial: Active Ageing HTTP 403; 315 candidates, 246 ranked, 69 duplicates (21.9%), 0 expired and 11 contributing source keys. POC-04 failed and the audit census was unrecoverable. Day 1 remains unaccepted.
- **Day 2 run 33629134040** remained partial and POC-02 evidence incomplete. It remains unaccepted.
- **Days 3–4** have complete frozen-method audits and were accepted.
- **Days 5–14** have preserved machine artifacts. Reconstruction records retain missing useful/valid-open/relevance audits as PENDING rather than manufacturing observations.
- **Day 6** was partial: `spazju_kreattiv_events` returned `insufficient_candidates`; four source keys contributed.
- **Day 11** was partial: `spazju_kreattiv_events` returned `insufficient_candidates` and `visitmalta_events` had an acquisition error; three source keys contributed.

## Final gate disposition

| Gate | Threshold | Certification status | Basis |
|---|---|---|---|
| POC-01 | >=50 useful/day | **PENDING / not certifiable** | Missing frozen audit evidence on multiple days |
| POC-02 | >=90% valid when opened | **PENDING / not certifiable** | Day 2 and Days 5–14 lack complete frozen validity audits |
| POC-03 | <5% stale/expired | **PASS on available machine evidence** | Observed machine rates remain below threshold |
| POC-04 | <5% duplicates | **FAIL** | Day 1 = 69/315 = 21.9%; failing evidence cannot be discarded |
| POC-05 | >=5 independent source types | **FAIL / incomplete coverage** | Days 6 and 11 have fewer than five contributing source keys; keys are not inflated into independent types |
| POC-06 | >=70% relevance | **PENDING / not certifiable** | Missing frozen full-census audits |
| POC-07 | 0 merchant onboarding | **PASS on recorded evidence** | No merchant onboarding required |

## 14-day completion

- Calendar ingestion window: **14/14 days reached**.
- Complete accepted daily measurement records currently evidenced: **2/14 (Days 3–4)**.
- Requirement for 14 consecutive complete records: **FAIL**.
- Workflow success must not be represented as measurement acceptance.

## Required next action

Do not rewrite this window. Fix evidence retention, source reliability and duplicate handling, then start a **new clean 14-day validation window** under an explicitly approved protocol. Production source access and release/deployment authorization remain OFF until separately approved.
