# VS-07 Audit Method V1

Status: Frozen for the 2026-09-01 through 2026-09-14 Malta POC window.

This method is derived from the already approved PRD/VS-07 contract and applies consistently to all 14 POC days, including retrospective completion of Days 1-3. It must not be changed to rescue a failing day. Any later amendment requires an explicit version bump and must not rewrite prior evidence.

## Audit profile

The fixed synthetic pilot profile uses the complete approved MVP interest set from `product/PRD.md`:

- Food & drink
- Fashion/retail
- Events/activities
- New openings

This broad profile is intentionally PRD-derived rather than selected from observed Day 3 output.

## Useful-discovery audit (POC-01)

Audit the full ranked/surfaced set for the day, not a sample. A discovery is useful when all of the following are true:

1. it has a specific, non-generic title rather than navigation/header noise;
2. it has an original permitted source URL;
3. it is not marked expired;
4. its discovery type/source meaning maps to an approved POC/MVP category; and
5. it represents a concrete user-action signal such as a named event/activity, named offer/deal, price/value signal, new opening or similarly actionable local discovery.

Validity of the source at audit time is measured separately by POC-02 and does not silently change the POC-01 label.

## Valid-when-opened audit (POC-02)

Sample size is `ceil(20% of ranked_count)`, with a minimum of 20 and maximum of 30 when the ranked set is at least 20 items. If fewer than 20 items exist, audit the full set.

Sampling is deterministic:

1. score each discovery with `SHA256(measured_sha + "|" + discovery_id)`;
2. include the lowest-scored discovery from every contributing source key first;
3. fill the remaining sample slots by ascending score across the full ranked set, without duplicates.

A sampled discovery is valid only when the original permitted source, or another page on the same official source, confirms that the named event/offer/discovery is currently present and materially matches the surfaced item. A transient auditor transport failure is retried once and may use an official same-domain listing/search page; if the item remains unconfirmable it fails closed as invalid. Third-party mirrors do not establish validity.

## Relevance audit (POC-06)

Audit the full ranked/surfaced set. A discovery is relevant when its source/type/content maps to at least one interest in the frozen synthetic profile above. Generic/noise records are not relevant even when their source category normally maps to an approved interest.

## Merchant-onboarding audit (POC-07)

The count is zero only when the ingestion/audit path required no merchant account, merchant listing creation, merchant upload, merchant login or merchant intervention. Any such requirement increments the count and fails the gate.

## Evidence requirements

Every daily audit record must include:

- measurement date;
- exact measured repository SHA;
- exact ingestion GitHub run ID;
- audit method version;
- useful-discovery count and census size;
- valid-open sample IDs/count and valid count;
- relevance census size and relevant count;
- merchant-onboarding count;
- notes for every invalid/unconfirmable sampled item;
- resulting gate rates/statuses.

Machine-measured ingestion metrics remain separate from these audit metrics. A green workflow is not measurement acceptance. Missing audit evidence fails closed under the existing VS-07 contract.

Production source access remains OFF.