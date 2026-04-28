# Changelog

All notable changes to this project should be recorded in this file.

## [1.2.52] - 2026-04-28

### Added

- Release metadata regression test that keeps package version, runtime version, changelog entry, and release notes indexes aligned
- Manual dependency and GitHub Actions update review checklist for maintainer-authored upgrades instead of direct Dependabot merges
- Security issue intake and response flow covering private disclosure, maintainer triage, fix/release handling, and public disclosure

### Changed

- Package version is now `1.2.52`
- README, support policy, and support lifecycle docs now link to the security reporting and response process

## [1.2.51] - 2026-04-28

### Added

- Maintainer dependency update policy that treats Dependabot PRs as upgrade notifications instead of directly mergeable commits

### Changed

- Package version is now `1.2.51`
- Maintainer bootstrap docs now describe the human-authored review branch flow for dependency and GitHub Actions upgrades

## [1.2.50] - 2026-04-28

### Added

- Release asset verification docs now include a copy-pasteable flow for downloading wheel, source archive, checksums, and SBOM assets
- Post-release smoke checklist covering tag validation, GitHub Release assets, workflow status, clean installs, and milestone closeout
- Release notes index pages in English and Simplified Chinese for easier discovery of recent releases and maintainer release docs

### Changed

- Package version is now `1.2.50`
- Release checklist now points maintainers to the fuller release artifact verification flow
- README, roadmap, and support lifecycle docs now cross-link roadmap, support policy, and release notes entry points more directly
- Roadmap status now reflects `v1.2.50` maintenance work while keeping PyPI trusted publishing explicitly deferred

## [1.2.49] - 2026-04-27

### Added

- Support lifecycle docs that define active support, maintenance support, unsupported releases, and the `v1.x` deprecation policy
- Chinese roadmap translation plus a refreshed roadmap that separates current release priorities from completed governance work
- Markdown relative-link regression test coverage for repository docs, `docs/`, and `.github/` Markdown files

### Changed

- Package version is now `1.2.49`
- README community-baseline links now include the community triage and support lifecycle docs in both English and Simplified Chinese
- Issue-template roadmap contact links now point contributors to current maintainer priorities in English and Simplified Chinese
- GitHub Pages and release supply-chain workflow actions were refreshed to their newer major versions

### Deferred

- PyPI trusted publishing remains deferred in the `Deferred: PyPI` milestone until the PyPI project and trusted publisher are configured

## [1.2.48] - 2026-04-15

### Added

- Community triage guidance that defines when contributors should use GitHub Issues versus GitHub Discussions
- Maintainer bootstrap docs for first-time GitHub Pages and PyPI trusted publishing setup

### Changed

- Package version is now `1.2.48`
- README, deployment, release checklist, support policy, and issue templates now point maintainers and contributors to the new release-operations and discussion-routing docs

### Fixed

- Release checksum files now use downloaded asset filenames so `sha256sum -c sha256sums.txt` works directly from the release download directory
- Release artifact smoke verification now checks checksums from the downloaded asset directory instead of assuming a `dist/` prefix

## [1.2.47] - 2026-04-15

### Added

- Versioned digest history, rollback routes, and publish-target preview support for stored snapshots
- Governance metadata and contributor-facing architecture docs through `GOVERNANCE.md`, `MAINTAINERS.md`, `CITATION.cff`, and `docs/architecture.md`

### Changed

- Package version is now `1.2.47`
- Package author and maintainer metadata now point to `X-PG13 <2720174336@qq.com>`
- Publication history now records the digest snapshot version used for each publish attempt and surfaces when a digest changed after publish

### Fixed

- Duplicate clustering for replayed or historical feeds now uses article publish time instead of the wall clock
- Qualified publication history queries so digest version history no longer fails with `ambiguous column name: id`
- Added service and API regression coverage for digest history, rollback, and publish preview flows

## [1.2.46] - 2026-04-11

### Added

- Frozen digest snapshot support with editable `manual_rank`, `section_override`, `publish_title_override`, and `publish_summary_override` fields
- New admin routes `POST /admin/digests/snapshot` and `PATCH /admin/digests/{digest_id}/editor` for saving and revising publishable digest drafts

### Changed

- Package version is now `1.2.46`
- Publish flows now prefer a stored digest snapshot when `digest_id` is supplied, so outbound content matches the reviewed editor state instead of a live recompute
- The admin dashboard now includes a dedicated pre-publish digest editor panel for freezing, revising, and reviewing publish-time decisions

### Fixed

- Preserved editor snapshot state through stored digest payload reloads so previously archived digests can still be edited and republished safely
- Kept digest compatibility docs and bilingual README guidance aligned with the new preview-to-snapshot publishing workflow

## [1.2.45] - 2026-04-10

### Added

- Digest editor controls now include `suppress` and digest preview routes so operators can inspect `selected`, `suppressed`, `duplicate_secondary`, and `ranked_out` decisions before publishing

### Changed

- Package version is now `1.2.45`
- Cross-source digest selection now exposes `selection_decisions`, `selection_summary`, and duplicate-cluster primary switching through the admin preview flow
- The admin dashboard now surfaces suppressed articles and a dedicated editorial preview panel for digest candidate review

### Fixed

- Ensured digest preview payloads persist `selection_decisions` all the way through the API response, stored payload fallback, and dashboard rendering path
- Prevented editor-suppressed articles from re-entering enrichment work and digest candidate lists unless operators explicitly clear the suppression flag

## [1.2.44] - 2026-04-10

### Added

- Override-approval-replay-note, continuity-revalidation-waiver-checklist, and audit-replay-waiver-escalation-faq extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.44`
- International extraction coverage now includes override-approval-replay-note, continuity-revalidation-waiver-checklist, and audit-replay-waiver-escalation-faq layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, audit-waiver-checklist layouts, rollover-waiver-matrix layouts, continuity-handoff-checklist layouts, audit-recovery-faq layouts, recovery-exception-matrix layouts, continuity-waiver-faq layouts, audit-restoration-checklist layouts, recovery-override-matrix layouts, continuity-exception-checklist layouts, audit-replay-faq layouts, recovery-override-faq layouts, continuity-revalidation-matrix layouts, audit-replay-checklist layouts, override-escalation-checklist layouts, continuity-revalidation-faq layouts, audit-replay-exception-matrix layouts, override-approval-matrix layouts, continuity-revalidation-checklist layouts, audit-replay-waiver-faq layouts, override-approval-faq layouts, continuity-revalidation-exception-matrix layouts, audit-replay-waiver-checklist layouts, override-approval-incident-note layouts, continuity-revalidation-waiver-faq layouts, and audit-replay-waiver-exception-matrix layouts

### Fixed

- Reduced override approval replay summaries, continuity revalidation waiver checklist summaries, audit replay waiver escalation summaries, audit replay matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of override-approval-replay-note, continuity-revalidation-waiver-checklist, and audit-replay-waiver-escalation-faq layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.43] - 2026-04-10

### Added

- Override-approval-incident-note, continuity-revalidation-waiver-faq, and audit-replay-waiver-exception-matrix extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.43`
- International extraction coverage now includes override-approval-incident-note, continuity-revalidation-waiver-faq, and audit-replay-waiver-exception-matrix layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, audit-waiver-checklist layouts, rollover-waiver-matrix layouts, continuity-handoff-checklist layouts, audit-recovery-faq layouts, recovery-exception-matrix layouts, continuity-waiver-faq layouts, audit-restoration-checklist layouts, recovery-override-matrix layouts, continuity-exception-checklist layouts, audit-replay-faq layouts, recovery-override-faq layouts, continuity-revalidation-matrix layouts, audit-replay-checklist layouts, override-escalation-checklist layouts, continuity-revalidation-faq layouts, audit-replay-exception-matrix layouts, override-approval-matrix layouts, continuity-revalidation-checklist layouts, audit-replay-waiver-faq layouts, override-approval-faq layouts, continuity-revalidation-exception-matrix layouts, and audit-replay-waiver-checklist layouts

### Fixed

- Reduced override approval incident summaries, continuity revalidation waiver summaries, audit replay waiver exception summaries, audit replay matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of override-approval-incident-note, continuity-revalidation-waiver-faq, and audit-replay-waiver-exception-matrix layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.42] - 2026-04-10

### Added

- Override-approval-faq, continuity-revalidation-exception-matrix, and audit-replay-waiver-checklist extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.42`
- International extraction coverage now includes override-approval-faq, continuity-revalidation-exception-matrix, and audit-replay-waiver-checklist layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, audit-waiver-checklist layouts, rollover-waiver-matrix layouts, continuity-handoff-checklist layouts, audit-recovery-faq layouts, recovery-exception-matrix layouts, continuity-waiver-faq layouts, audit-restoration-checklist layouts, recovery-override-matrix layouts, continuity-exception-checklist layouts, audit-replay-faq layouts, recovery-override-faq layouts, continuity-revalidation-matrix layouts, audit-replay-checklist layouts, override-escalation-checklist layouts, continuity-revalidation-faq layouts, audit-replay-exception-matrix layouts, override-approval-matrix layouts, continuity-revalidation-checklist layouts, and audit-replay-waiver-faq layouts

### Fixed

- Reduced override approval FAQ summaries, continuity revalidation exception summaries, audit replay waiver checklist summaries, audit replay matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of override-approval-faq, continuity-revalidation-exception-matrix, and audit-replay-waiver-checklist layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.41] - 2026-04-10

### Added

- Override-approval-matrix, continuity-revalidation-checklist, and audit-replay-waiver-faq extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.41`
- International extraction coverage now includes override-approval-matrix, continuity-revalidation-checklist, and audit-replay-waiver-faq layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, audit-waiver-checklist layouts, rollover-waiver-matrix layouts, continuity-handoff-checklist layouts, audit-recovery-faq layouts, recovery-exception-matrix layouts, continuity-waiver-faq layouts, audit-restoration-checklist layouts, recovery-override-matrix layouts, continuity-exception-checklist layouts, audit-replay-faq layouts, recovery-override-faq layouts, continuity-revalidation-matrix layouts, audit-replay-checklist layouts, override-escalation-checklist layouts, continuity-revalidation-faq layouts, and audit-replay-exception-matrix layouts

### Fixed

- Reduced override approval summaries, continuity revalidation checklist summaries, audit replay waiver summaries, audit replay matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of override-approval, continuity-revalidation-checklist, and audit-replay-waiver layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.40] - 2026-04-10

### Added

- Override-escalation-checklist, continuity-revalidation-faq, and audit-replay-exception-matrix extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.40`
- International extraction coverage now includes override-escalation-checklist, continuity-revalidation-faq, and audit-replay-exception-matrix layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, audit-waiver-checklist layouts, rollover-waiver-matrix layouts, continuity-handoff-checklist layouts, audit-recovery-faq layouts, recovery-exception-matrix layouts, continuity-waiver-faq layouts, audit-restoration-checklist layouts, recovery-override-matrix layouts, continuity-exception-checklist layouts, audit-replay-faq layouts, recovery-override-faq layouts, continuity-revalidation-matrix layouts, and audit-replay-checklist layouts

### Fixed

- Reduced override escalation summaries, continuity revalidation FAQ summaries, audit replay exception summaries, audit replay matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of override-escalation, continuity-revalidation-faq, and audit-replay-exception layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.39] - 2026-04-10

### Added

- Recovery-override-faq, continuity-revalidation-matrix, and audit-replay-checklist extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.39`
- International extraction coverage now includes recovery-override-faq, continuity-revalidation-matrix, and audit-replay-checklist layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, audit-waiver-checklist layouts, rollover-waiver-matrix layouts, continuity-handoff-checklist layouts, audit-recovery-faq layouts, recovery-exception-matrix layouts, continuity-waiver-faq layouts, audit-restoration-checklist layouts, recovery-override-matrix layouts, continuity-exception-checklist layouts, and audit-replay-faq layouts

### Fixed

- Reduced recovery override FAQ summaries, continuity revalidation summaries, audit replay checklist summaries, audit replay matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of recovery-override-faq, continuity-revalidation, and audit-replay-checklist layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.38] - 2026-04-10

### Added

- Recovery-override-matrix, continuity-exception-checklist, and audit-replay-faq extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.38`
- International extraction coverage now includes recovery-override-matrix, continuity-exception-checklist, and audit-replay-faq layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, audit-waiver-checklist layouts, rollover-waiver-matrix layouts, continuity-handoff-checklist layouts, audit-recovery-faq layouts, recovery-exception-matrix layouts, continuity-waiver-faq layouts, and audit-restoration-checklist layouts

### Fixed

- Reduced recovery override summaries, continuity exception summaries, audit replay summaries, audit replay matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of recovery-override, continuity-exception, and audit-replay layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.37] - 2026-04-10

### Added

- Recovery-exception-matrix, continuity-waiver-faq, and audit-restoration-checklist extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.37`
- International extraction coverage now includes recovery-exception-matrix, continuity-waiver-faq, and audit-restoration-checklist layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, audit-waiver-checklist layouts, rollover-waiver-matrix layouts, continuity-handoff-checklist layouts, and audit-recovery-faq layouts

### Fixed

- Reduced recovery exception summaries, continuity waiver summaries, audit restoration summaries, audit restoration matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of recovery-exception, continuity-waiver, and audit-restoration layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.36] - 2026-04-10

### Added

- Rollover-waiver-matrix, continuity-handoff-checklist, and audit-recovery-faq extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.36`
- International extraction coverage now includes rollover-waiver-matrix, continuity-handoff-checklist, and audit-recovery-faq layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, audit-exception-faq layouts, eligibility-rollover-matrix layouts, approval-continuity-faq layouts, and audit-waiver-checklist layouts

### Fixed

- Reduced rollover waiver summaries, continuity handoff summaries, audit recovery summaries, audit recovery matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of rollover-waiver, continuity-handoff, and audit-recovery layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.35] - 2026-04-10

### Added

- Eligibility-rollover-matrix, approval-continuity-faq, and audit-waiver-checklist extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.35`
- International extraction coverage now includes eligibility-rollover-matrix, approval-continuity-faq, and audit-waiver-checklist layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, rollover-audit-checklist layouts, exception-eligibility-matrix layouts, handoff-escalation-checklist layouts, and audit-exception-faq layouts

### Fixed

- Reduced eligibility rollover summaries, approval continuity summaries, audit waiver summaries, audit waiver matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of eligibility-rollover, approval-continuity, and audit-waiver layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.34] - 2026-04-10

### Added

- Exception-eligibility-matrix, handoff-escalation-checklist, and audit-exception-faq extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.34`
- International extraction coverage now includes exception-eligibility-matrix, handoff-escalation-checklist, and audit-exception-faq layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, exception-rollover-checklist layouts, grace-window-exception-matrix layouts, approval-handoff-faq layouts, and rollover-audit-checklist layouts

### Fixed

- Reduced exception eligibility summaries, handoff escalation summaries, audit exception summaries, audit exception matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of exception-eligibility, handoff-escalation, and audit-exception layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.33] - 2026-04-10

### Added

- Grace-window-exception-matrix, approval-handoff-faq, and rollover-audit-checklist extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.33`
- International extraction coverage now includes grace-window-exception-matrix, approval-handoff-faq, and rollover-audit-checklist layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, eligibility-exception-faq layouts, grace-window-faq layouts, approval-escalation-note layouts, and exception-rollover-checklist layouts

### Fixed

- Reduced grace-window exception summaries, approval handoff summaries, rollover audit summaries, rollover audit matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of grace-window exception, approval handoff, and rollover audit layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.32] - 2026-04-10

### Added

- Grace-window-faq, approval-escalation-note, and exception-rollover-checklist extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.32`
- International extraction coverage now includes grace-window-faq, approval-escalation-note, and exception-rollover-checklist layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, eligibility-edge-case-advisory layouts, recovery-grace-period-note layouts, rollback-approval-matrix layouts, and eligibility-exception-faq layouts

### Fixed

- Reduced grace-window summaries, approval escalation summaries, exception rollover summaries, exception rollover matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of grace-window, approval-escalation, and exception-rollover layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.31] - 2026-04-10

### Added

- Recovery-grace-period-note, rollback-approval-matrix, and eligibility-exception-faq extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.31`
- International extraction coverage now includes recovery-grace-period-note, rollback-approval-matrix, and eligibility-exception-faq layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, rollover-eligibility-guide layouts, burst-credit-recovery-faq layouts, rollback-exception-note layouts, and eligibility-edge-case-advisory layouts

### Fixed

- Reduced recovery grace summaries, rollback approval matrix summaries, eligibility exception summaries, eligibility exception matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of recovery-grace, rollback-approval, and eligibility-exception layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.30] - 2026-04-10

### Added

- Burst-credit-recovery-faq, rollback-exception-note, and eligibility-edge-case-advisory extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.30`
- International extraction coverage now includes burst-credit-recovery-faq, rollback-exception-note, and eligibility-edge-case-advisory layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, rollover-exception-policy layouts, burst-credit-recovery-note layouts, escalation-rollback-checklist layouts, and rollover-eligibility-guide layouts

### Fixed

- Reduced burst-credit recovery FAQ summaries, rollback exception summaries, eligibility edge-case summaries, eligibility edge-case matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of burst-credit recovery FAQ, rollback exception, and eligibility edge-case layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.29] - 2026-04-10

### Added

- Burst-credit-recovery-note, escalation-rollback-checklist, and rollover-eligibility-guide extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.29`
- International extraction coverage now includes burst-credit-recovery-note, escalation-rollback-checklist, and rollover-eligibility-guide layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, reservation-rollover-policy layouts, burst-credit-faq layouts, priority-escalation-guide layouts, and rollover-exception-policy layouts

### Fixed

- Reduced burst-credit recovery summaries, rollback checklist summaries, rollover eligibility summaries, rollover eligibility matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of burst-credit recovery, escalation rollback, and rollover eligibility layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.28] - 2026-04-10

### Added

- Burst-credit-faq, priority-escalation-guide, and rollover-exception-policy extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.28`
- International extraction coverage now includes burst-credit-faq, priority-escalation-guide, and rollover-exception-policy layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, capacity-reservation-note layouts, burst-credit-notice layouts, queue-priority-update layouts, and reservation-rollover-policy layouts

### Fixed

- Reduced burst-credit FAQ summaries, priority escalation summaries, rollover exception summaries, rollover exception matrices, and related-guide recirculation noise on developer policy pages
- Locked another class of burst-credit, priority-escalation, and rollover-exception layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.27] - 2026-04-10

### Added

- Burst-credit-notice, queue-priority-update, and reservation-rollover-policy extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.27`
- International extraction coverage now includes burst-credit-notice, queue-priority-update, and reservation-rollover-policy layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, throughput-exception-policy layouts, temporary-overage-notice layouts, fairness-policy-update layouts, and capacity-reservation-note layouts

### Fixed

- Reduced burst-credit summaries, priority summaries, rollover summaries, rollover matrices, and related-guide recirculation noise on developer limit and reservation-rollover pages
- Locked another class of burst-credit, queue-priority, and reservation-rollover layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.26] - 2026-04-10

### Added

- Temporary-overage-notice, fairness-policy-update, and capacity-reservation-note extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.26`
- International extraction coverage now includes temporary-overage-notice, fairness-policy-update, and capacity-reservation-note layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, regional-quota-advisory layouts, soft-limit-warning layouts, grace-period-notice layouts, and throughput-exception-policy layouts

### Fixed

- Reduced overage summaries, fairness summaries, reservation summaries, reservation matrices, and related-guide recirculation noise on developer limit and reservation-policy pages
- Locked another class of overage, fairness, and capacity-reservation layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.25] - 2026-04-09

### Added

- Soft-limit-warning, grace-period-notice, and throughput-exception-policy extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.25`
- International extraction coverage now includes soft-limit-warning, grace-period-notice, and throughput-exception-policy layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, quota-policy layouts, burst-cap-notice layouts, concurrency-cap-update layouts, and regional-quota-advisory layouts

### Fixed

- Reduced soft-limit summaries, grace-period summaries, exception-threshold panels, and related-guide recirculation noise on developer limit and exception-policy pages
- Locked another class of soft-limit, grace-period, and throughput-exception layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.24] - 2026-04-09

### Added

- Burst-cap-notice, concurrency-cap-update, and regional-quota-advisory extraction fixtures for `platform.openai.com`, `docs.anthropic.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.24`
- International extraction coverage now includes burst-cap-notice, concurrency-cap-update, and regional-quota-advisory layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, SKU-change layouts, usage-limit-notice layouts, rate-limit-update layouts, and quota-policy layouts

### Fixed

- Reduced burst-cap summaries, concurrency summaries, regional quota summaries, region matrices, and related-guide recirculation noise on developer limit and quota advisory pages
- Locked another class of burst, concurrency, and regional quota layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.23] - 2026-04-09

### Added

- Usage-limit-notice, rate-limit-update, and quota-policy extraction fixtures for `docs.anthropic.com`, `platform.openai.com`, and `docs.together.ai`

### Changed

- Package version is now `1.2.23`
- International extraction coverage now includes usage-limit-notice, rate-limit-update, and quota-policy layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, compliance-update layouts, pricing-update layouts, service-tier-notice layouts, and SKU-change layouts

### Fixed

- Reduced rate-limit sidebars, tier summaries, limit summaries, quota summaries, and related-guide recirculation noise on developer quota and usage-policy pages
- Locked another class of quota-policy and rate-limit layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.22] - 2026-04-09

### Added

- Pricing-update, service-tier-notice, and SKU-change extraction fixtures for `openai.com`, `anthropic.com`, and `together.ai`

### Changed

- Package version is now `1.2.22`
- International extraction coverage now includes pricing-update, service-tier-notice, and SKU-change layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, outage-RCA layouts, security-bulletin layouts, trust-center-advisory layouts, and compliance-update layouts

### Fixed

- Reduced pricing sidebars, service-tier grids, plan-comparison modules, and related-update recirculation noise on product pricing and commercial notice pages
- Locked another class of pricing and commercial-notice layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.21] - 2026-04-09

### Added

- Security-bulletin, trust-center-advisory, and compliance-update extraction fixtures for `trust.openai.com`, `docs.anthropic.com`, and `cloud.google.com`

### Changed

- Package version is now `1.2.21`
- International extraction coverage now includes security-bulletin, trust-center-advisory, and compliance-update layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, release-channel-note layouts, incident-update layouts, postmortem layouts, and outage-RCA layouts

### Fixed

- Reduced severity banners, trust-center sidebars, compliance navigation, and related-advisory recirculation noise on security and trust vendor pages
- Locked another class of security and compliance layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.20] - 2026-04-09

### Added

- Incident-update, postmortem, and outage-RCA extraction fixtures for `status.openai.com`, `status.pinecone.io`, and `status.together.ai`

### Changed

- Package version is now `1.2.20`
- International extraction coverage now includes incident-update, postmortem, and outage-RCA layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, versioned-doc-notice layouts, support-policy layouts, compatibility-matrix layouts, and release-channel-note layouts

### Fixed

- Reduced affected-component sidebars, status banners, incident navigation, and related-incident recirculation noise on vendor status and outage-notice pages
- Locked another class of incident and postmortem layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.19] - 2026-04-09

### Added

- Support-policy, compatibility-matrix, and release-channel-note extraction fixtures for `docs.llamaindex.ai`, `docs.together.ai`, and `docs.fireworks.ai`

### Changed

- Package version is now `1.2.19`
- International extraction coverage now includes support-policy, compatibility-matrix, and release-channel-note layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, migration/deprecation layouts, and versioned-doc-notice layouts

### Fixed

- Reduced compatibility sidebars, support-policy banners, release-channel navigation, and related-doc recirculation noise on AI developer-documentation pages
- Locked another class of support-policy and compatibility layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.18] - 2026-04-09

### Added

- Deprecation FAQ, migration checklist, and versioned-doc notice extraction fixtures for `platform.openai.com`, `docs.pinecone.io`, and `docs.vllm.ai`

### Changed

- Package version is now `1.2.18`
- International extraction coverage now includes deprecation-FAQ, migration-checklist, and versioned-doc-notice layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, API-reference/changelog layouts, and migration/deprecation layouts

### Fixed

- Reduced deprecation sidebars, checklist navigation, version banners, and related-doc recirculation noise on AI developer-documentation pages
- Locked another class of deprecation and versioned-doc layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.17] - 2026-04-09

### Added

- Migration guide, deprecation notice, and upgrade guide extraction fixtures for `docs.langchain.com`, `developer.atlassian.com`, and `supabase.com`

### Changed

- Package version is now `1.2.17`
- International extraction coverage now includes migration-guide, deprecation-notice, and upgrade-guide layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, vendor documentation layouts, and API-reference/changelog layouts

### Fixed

- Reduced migration menus, deprecation banners, upgrade CTAs, and related-doc recirculation noise on developer-doc and change-management pages
- Locked another class of migration and deprecation layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.16] - 2026-04-09

### Added

- API reference, developer guide, and changelog-style extraction fixtures for `docs.cohere.com`, `developer.nvidia.com`, and `vercel.com`

### Changed

- Package version is now `1.2.16`
- International extraction coverage now includes API-reference, developer-guide, and changelog-update layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, conference recap layouts, and vendor documentation layouts

### Fixed

- Reduced navigation menus, endpoint sidebars, checklist modules, and changelog recirculation noise on documentation- and update-heavy vendor pages
- Locked another class of API reference and product-update layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.15] - 2026-04-09

### Added

- Vendor FAQ, troubleshooting, and best-practices extraction fixtures for `aws.amazon.com`, `docs.anthropic.com`, and `learn.microsoft.com`

### Changed

- Package version is now `1.2.15`
- International extraction coverage now includes vendor FAQ, troubleshooting, and best-practices guide layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, vendor benchmark layouts, and conference recap layouts

### Fixed

- Reduced resource sidebars, help navigation, feedback modules, and checklist noise on documentation-heavy vendor pages
- Locked another class of documentation-style operational pages into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.14] - 2026-04-09

### Added

- Conference recap, event takeaways, and transcript-summary extraction fixtures for `techpolicy.press`, `a16z.com`, and `ted.com`

### Changed

- Package version is now `1.2.14`
- International extraction coverage now includes conference-recap, event-takeaways, and transcript-summary hybrid layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, policy-feature layouts, and vendor benchmark layouts

### Fixed

- Reduced event metadata, session promos, transcript navigation, and related-content noise on recap-heavy publisher pages
- Locked another class of conference and session-summary layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.13] - 2026-04-09

### Added

- Whitepaper, vendor benchmark, and enterprise case-study extraction fixtures for `mckinsey.com`, `cloud.google.com`, and `databricks.com`

### Changed

- Package version is now `1.2.13`
- International extraction coverage now includes whitepaper, benchmark, and case-study publisher layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, longform analysis layouts, and policy-feature layouts

### Fixed

- Reduced methodology blurbs, download prompts, video modules, and related-resource noise on benchmark- and case-study-heavy pages
- Locked another class of vendor and research content-marketing layouts into deterministic fixture coverage so extraction regressions are caught in CI

## [1.2.12] - 2026-04-09

### Added

- Policy memo, research note, and magazine-feature extraction fixtures for `brookings.edu`, `rand.org`, and `restofworld.org`

### Changed

- Package version is now `1.2.12`
- International extraction coverage now includes policy-memo, research-note, and feature-with-pull-quote newsroom layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, interview/transcript layouts, and longform analysis layouts

### Fixed

- Reduced pull-quote bleed-through, briefing modules, audio prompts, and related-content noise on policy- and feature-heavy longform pages
- Locked another class of fragmented longform layouts into deterministic fixture coverage so cleanup regressions are caught in CI

## [1.2.11] - 2026-04-09

### Added

- Longform analysis and essay extraction fixtures for `theatlantic.com`, `foreignpolicy.com`, and `newstatesman.com`

### Changed

- Package version is now `1.2.11`
- International extraction coverage now includes analysis-, essay-, and longform-feature-style newsroom layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, roundup/what-to-know layouts, and interview/transcript layouts

### Fixed

- Reduced audio prompts, recirculation modules, and subscription or newsletter noise on longform publisher pages
- Locked another class of essay-heavy newsroom layouts into deterministic fixture coverage so longform cleanup regressions are caught in CI

## [1.2.10] - 2026-04-09

### Added

- Interview, transcript, and Q&A extraction fixtures for `fastcompany.com`, `businessinsider.com`, and `spectrum.ieee.org`

### Changed

- Package version is now `1.2.10`
- International extraction coverage now includes interview-, transcript-, and Q&A-style newsroom layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, explainer/guide layouts, and roundup/what-to-know layouts

### Fixed

- Reduced inline audio prompts, author/promo modules, and read-next noise on interview-style publisher pages
- Locked another class of speaker-label-heavy newsroom layouts into deterministic fixture coverage so transcript cleanup regressions are caught in CI

## [1.2.9] - 2026-04-09

### Added

- Roundup and what-to-know extraction fixtures for `vox.com`, `time.com`, and `nbcnews.com`

### Changed

- Package version is now `1.2.9`
- International extraction coverage now includes roundup-, list-, and what-to-know-style newsroom layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, paywall-heavy layouts, and explainer/guide layouts

### Fixed

- Reduced newsletter cards, read-next recirculation, video prompts, and related-coverage noise on roundup-style publisher pages
- Locked another class of list-heavy newsroom layouts into deterministic fixture coverage so roundup cleanup regressions are caught in CI

## [1.2.8] - 2026-04-09

### Added

- Explainer and guide-style extraction fixtures for `cnn.com`, `nytimes.com`, and `washingtonpost.com`

### Changed

- Package version is now `1.2.8`
- International extraction coverage now includes FAQ-, explainer-, and guide-style newsroom layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, opinion/column layouts, and paywall-heavy layouts

### Fixed

- Reduced listen/audio prompts, newsletter modules, gift offers, and related-coverage noise on explainer-style publisher pages
- Locked another class of newsroom Q&A and guide layouts into deterministic fixture coverage so explainer cleanup regressions are caught in CI

## [1.2.7] - 2026-04-09

### Added

- Paywall-heavy extraction fixtures for `bloomberg.com`, `wsj.com`, and `economist.com`

### Changed

- Package version is now `1.2.7`
- International extraction coverage now includes paywall- and subscriber-prompt-heavy newsroom layouts in addition to standard articles, live updates, briefing pages, multimedia-heavy pages, and opinion/column layouts

### Fixed

- Reduced subscription prompts, audio/listen modules, and recirculation noise on paywall-heavy publisher pages
- Locked another class of premium-news publisher layouts into deterministic fixture coverage so paywall cleanup regressions are caught in CI

## [1.2.6] - 2026-04-09

### Added

- Opinion and column-style extraction fixtures for `newyorker.com`, `fortune.com`, and `inc.com`

### Changed

- Package version is now `1.2.6`
- International extraction coverage now includes opinion, column, and author-driven publisher layouts in addition to standard articles, live updates, briefing pages, and multimedia-heavy pages

### Fixed

- Reduced author bio, premium upsell, newsletter, and most-popular noise on opinion-style publisher pages
- Locked another class of commentary-heavy media layouts into deterministic fixture coverage so column cleanup regressions are caught in CI

## [1.2.5] - 2026-04-09

### Added

- Multimedia-heavy extraction fixtures for `engadget.com`, `forbes.com`, and `zdnet.com`

### Changed

- Package version is now `1.2.5`
- International extraction coverage now includes video, podcast, and audio-summary-heavy publisher layouts in addition to standard articles, live updates, and briefing pages

### Fixed

- Reduced video player, podcast module, audio summary, and embed CTA noise on multimedia-heavy publisher pages
- Locked another class of media layouts into deterministic fixture coverage so multimedia cleanup regressions are caught in CI

## [1.2.4] - 2026-04-09

### Added

- Briefing and newsletter-style extraction fixtures for `semafor.com`, `morningbrew.com`, and `theinformation.com`

### Changed

- Package version is now `1.2.4`
- International extraction coverage now includes briefing, digest, and subscriber-prompt-heavy newsroom layouts in addition to standard articles and live updates

### Fixed

- Reduced newsletter CTA, subscriber prompt, and related-coverage noise on briefing-style publisher pages
- Locked another class of digest-style international media layouts into deterministic fixture coverage so content cleanup regressions are caught in CI

## [1.2.3] - 2026-04-09

### Added

- Live and timeline-style extraction fixtures for `apnews.com`, `bbc.com`, and `theguardian.com`

### Changed

- Package version is now `1.2.3`
- International content extraction coverage now includes live update and timeline layouts in addition to standard article pages

### Fixed

- Reduced timestamp, live-feed label, share, and recirculation noise on liveblog-style publisher pages
- Locked another class of noisy newsroom layouts into deterministic fixture coverage so timeline formatting regressions are caught in CI

## [1.2.2] - 2026-04-09

### Added

- New fixture-driven extraction coverage for `technologyreview.com` and `axios.com`, extending the international media regression set with additional newsletter-heavy article layouts

### Changed

- Package version is now `1.2.2`
- `make check` now runs the full local engineering gate: `lint`, `coverage`, `build`, and `smoke`

### Fixed

- Improved source-specific cleanup for Axios article pages so newsletter prompts, share tools, and recirculation blocks are excluded from extracted body text
- Reduced regression risk on MIT Technology Review and Axios layouts by locking both shapes into deterministic fixture coverage

## [1.2.1] - 2026-04-09

### Added

- Multi-source feed fixtures for `Jiqizhixin`, `Ars Technica`, `Substack`, and `Yahoo` syndication pages in the pipeline end-to-end suite
- A deterministic partial-error pipeline regression that keeps extraction timeout handling covered without depending on live network behavior

### Changed

- Package version is now `1.2.1`
- Fixture-driven pipeline coverage now spans domestic media, international media, newsletter/blog layouts, and syndication targets in one CI-safe bundle

### Fixed

- Closed issue `#8` by expanding pipeline fixture coverage across more sources while keeping the regression suite deterministic

## [1.2.0] - 2026-04-09

### Added

- A one-screen `Operations` dashboard panel that aggregates `/health`, metrics, recent pipeline runs, source cooldown hotspots, source alerts, and publication failures
- A richer `/admin/operations` payload with runtime summaries for operators and demo assets for the new operations surface
- New source-specific extraction regression fixtures for `Jiqizhixin`, `Ars Technica`, `Substack`, and `Yahoo` syndication targets

### Changed

- Package version is now `1.2.0`
- Content extraction cleanup now covers more Chinese media, English media, blog/newsletter layouts, and syndication-style article pages
- README and public demo assets now show the operator-focused overview and sample operations payload

### Fixed

- Reduced over-cleaning risk on Chinese publisher pages by separating editorial label noise from the first body paragraph
- Improved article body extraction on additional noisy layouts where share widgets, subscribe prompts, and recirculation blocks previously contaminated the output

## [1.1.2] - 2026-04-08

### Changed

- The tag release workflow now explicitly dispatches `Release Artifact Smoke` after publishing the GitHub Release
- Release documentation now reflects that published tags trigger artifact smoke automatically, while manual reruns remain available
- Package version is now `1.1.2`

### Fixed

- Closed the last manual step in the release flow by wiring release publication to post-release artifact validation

## [1.1.1] - 2026-04-08

### Added

- A dedicated `Release Artifact Smoke` workflow that downloads published release assets, verifies checksums, installs both wheel and source archive, and runs minimal CLI plus `/health` smoke checks

### Changed

- Package version is now `1.1.1`
- Release documentation now treats `Release Artifact Smoke` as a mandatory pass gate before a release is considered complete
- PyPI publication is now opt-in by default through `AINEWS_ENABLE_PYPI_PUBLISH=true`, while manual workflow dispatch remains available

### Fixed

- Corrected release artifact checksum verification so the smoke workflow validates the published bundle paths exactly as recorded in `sha256sums.txt`

## [1.1.0] - 2026-04-08

### Added

- Source runtime protections with cooldown state, maintenance mode, alert acknowledgement, snooze controls, and recovery lifecycle automation
- Source operations coverage across API, dashboard, and CLI, including runtime history pruning and cooldown reset commands
- Google News wrapper resolution at ingest time, historical backfill support, and end-to-end coverage for wrapper-to-article extraction flow
- Prometheus-compatible `/metrics` endpoint, monitoring docs, and Docker Compose monitoring profile with Prometheus and Grafana assets
- Scheduled housekeeping workflow for pruning archived source runtime history
- Expanded regression fixtures for Chinese, international, and noise-heavy media pages including TechCrunch, VentureBeat, Reuters, Wired, Google AI Blog, and Google News wrapper samples

### Changed

- Package version is now `1.1.0`
- Smoke workflow now runs on `push` to `main` and on all pull requests so it can be used as a required branch check
- Source extraction retries now classify `throttled`, `blocked`, `temporary_error`, and `permanent_error` states with explicit retry metadata
- `/health`, stats, and runtime views now surface source cooldown and recovery state instead of treating all extraction failures as generic degradation
- Alert delivery now covers degraded health, publication failures, pipeline errors, and source cooldown transitions with deduplication and recovery notices

### Fixed

- Stopped Google News wrapper URLs from polluting deduplication and downstream publication links by resolving canonical targets before ingest
- Prevented repeated extraction pressure on blocked or throttled sources by honoring source cooldowns, maintenance state, and retry windows
- Sanitized API and service error payloads so internal exception details are not exposed to clients
- Reduced false-positive extraction failures by improving source-specific cleanup for blog-style and noisy article layouts

## [1.0.0] - 2026-04-07

### Added

- Stable `v1.x` compatibility contract covering environment variables, CLI flags, HTTP endpoints, export JSON, and migration policy
- Deployment, migration, and troubleshooting docs for local runs, Docker, `systemd`, and GitHub Actions
- Source registry contract test for the default source pack
- Legacy SQLite migration coverage with explicit `schema_version` metadata

### Changed

- Package version is now `1.0.0`
- Exported digest payloads now include a top-level `schema_version`
- `publish` and `run-pipeline --publish` now persist digests before publication so publication history and idempotency are enforced
- Re-publishing the same stored digest to the same target is skipped by default unless `--force-republish` or `force_republish=true` is used
- `/health` now returns the running service version

### Fixed

- Prevented duplicate publication rows and accidental repeat outbound publishes for the same digest and target in the default operator flow

## [0.6.0] - 2026-04-07

### Added

- Open-source project governance files: Code of Conduct, Security Policy, issue templates, and pull request template
- Engineering tooling: `.editorconfig`, `.pre-commit-config.yaml`, `ruff` configuration, package build target, and expanded CI checks
- Docker packaging hygiene with `.dockerignore` and non-root container runtime
- Publication history filtering and WeChat publish-status refresh from the admin API, CLI, and dashboard

### Changed

- CI now runs lint, tests, and package builds on Python 3.9 and 3.12
- Makefile now exposes `lint`, `build`, and `check` targets

## [0.5.0] - 2026-04-07

### Added

- WeChat `freepublish/get` status refresh and publication history UI
- Feishu card fallback, WeChat thumb auto-upload, and publication record persistence

## [0.4.0] - 2026-04-07

### Added

- Content extraction cleanup for `36Kr` and `IT之家`
- Publish targets for Telegram, Feishu, WeChat, and static site export
