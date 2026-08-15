# Pre-Bid Intelligence MVP Progress

Last updated: 2026-08-15

This tracker records only behavior that is reachable and validated. A checked item is not a production claim; production readiness additionally requires the listed security, operations, and test gates.

## Validated Now

- [x] Tenant and project-scoped manual Pre-Bid workflow.
- [x] PDF MIME/signature/size/page validation, SHA-256 identity, project deduplication, and page-text extraction.
- [x] Document version metadata, project-scoped document families, immutable addendum/supersession relationships, and evidence-based re-review impact identification.
- [x] Manual evidence spans linked to source pages.
- [x] Atomic proposed requirements with controlled taxonomy and stable keys.
- [x] Additive structured requirement fields and explicit evidence extraction provenance; manual source text is labelled `human_transcription` and remains subject to human verification.
- [x] Evidence verification, requirement verification/rejection, optimistic version checking, and audit events.
- [x] Deterministic Pre-Bid source coverage report and verified-requirement CSV export.
- [x] Design Basis domain validation, draft versioning, and approval API/UI.
- [x] Procurement project modes/archetypes and expanded versioned Design Basis inputs for project, operating profile, performance, degradation/augmentation, and commercial evaluation assumptions.
- [x] Deterministic starter completeness rules for long-life capacity retention and frequency-regulation response time.
- [x] Persisted, auditable deterministic findings with idempotent rule runs and human reasoned terminal resolution, exposed through the Findings workbench UI.
- [x] Project-scoped clarification records and immutable baseline snapshots with reproducibility hashes, readiness gates, approval records, audit events, and workspace controls.
- [x] Formula Lab fixed-template configuration versions with optional source clause provenance, approval metadata fields, and retained project-scoped RTE-adjusted calculation history. Arbitrary expressions are not accepted.
- [x] Live Pre-Bid Assurance Report API and workspace panel with project, Design Basis, document, requirement, finding, clarification, baseline, and limitation summaries plus browser print support.
- [x] Initial Bid Intelligence project mode with bidder legal-entity profiles and project-scoped human compliance mapping API, plus workflow-mode and bidder-profile workspace controls.
- [x] Local session bootstrap/login/logout/revocation API and empty-database migration validation.
- [x] Same-origin Next.js API proxy for local/Codespaces development.

## Ready for Manual Validation

1. Create workspace and project.
2. Save then approve Design Basis.
3. Upload one or more PDFs.
4. Inspect pages, create source evidence, and create a proposed requirement.
5. Verify/reject the requirement.
6. View the coverage report and export verified requirements as CSV.
7. Call `GET /projects/{project_id}/completeness-findings` after Design Basis approval to inspect deterministic missing-requirement findings.

## Checkpoint Checklist

### Checkpoint 1: Architecture and Security Foundation

- [x] Session persistence, password hashing, expiry metadata, and logout revocation.
- [x] Local development bootstrap.
- [x] Tenant membership check and cross-tenant regression coverage.
- [x] Disposable-database Alembic validation.
- [ ] Browser sign-in/logout and authenticated project selection UI.
- [ ] Role-permission matrix enforced for author, reviewer, approver, and auditor.
- [ ] Disable development identity headers outside explicit local configuration.
- [ ] IDOR/cross-project/expired-session security suite.

### Checkpoint 2: Design Basis

- [x] Core BESS design inputs and deterministic validation.
- [x] Project-scoped draft versions and approval transition.
- [x] API and UI form.
- [ ] Reviewer comments and role-based approval.
- [x] Complete core Design Basis fields: site/jurisdiction, COD, currency/timezone, operating window, annual throughput, retention trajectory, augmentation, performance boundary, and commercial assumptions. Environmental conditions remain deferred.
- [ ] Version comparison and immutable approval gate.

### Checkpoint 3: Document Platform

- [x] Private local source storage, SHA-256, page extraction, idempotent duplicate upload.
- [x] Document inventory metadata: type, volume, revision, issue/effective date, tender/addendum/corrigendum numbers, parser version, page count, review status, and controlling status.
- [x] Addendum/supersession model and re-review impact API. It identifies requirements cited to the amended source; human review remains required to resolve the impact.
- [ ] MinIO/S3 adapter with byte-identical authorized download.
- [ ] Celery/Redis asynchronous processing, idempotent runs, retry state, job visibility.
- [ ] OCR fallback, parser/OCR version metadata, and quality-review path.
- [ ] Malware-scanner adapter and encrypted/malformed PDF handling.

### Checkpoint 4: Evidence and Requirements UX

- [x] Page text review, manual evidence creation, evidence-backed requirements, reviewer decisions.
- [x] Requirement detail register with page provenance.
- [ ] Rendered PDF page/region viewer, selection coordinates, highlights, and scanned-page support.
- [ ] Structured requirement fields, automatic keys, versions, duplicates, and immutable verified history. Additive engineering/evaluation fields and evidence provenance are persisted; automatic keys, duplicate detection, and immutable verified-history snapshots remain outstanding.
- [ ] Persistent project context, search/filter/sort/pagination, bulk-safe review.

### Checkpoint 5: AI Candidate Extraction

- [ ] Provider-neutral port, no-external-LLM mode, deterministic fake provider.
- [ ] Schema-constrained candidate extraction with citations and confidence.
- [ ] Candidate isolation, accept/edit/reject/defer workflow.
- [ ] Evaluation dataset, fixtures, metrics, and release gates.

### Checkpoint 6: Intelligence Engines

- [x] Starter deterministic completeness API rules.
- [x] Formula Lab supports the fixed RTE-adjusted capacity-charge template, persisted configuration versions, and reproducible internal scenario history.
- [ ] Full versioned rule catalogue and persisted, resolvable findings. The initial catalogue has persisted `missing_requirement` findings for capacity retention and frequency response; broader BESS, commercial, qualification, warranty, and addendum rules remain outstanding.
- [ ] Ambiguity detection and reviewer-controlled improved wording.
- [ ] Cross-document conflict and addendum impact analysis.
- [ ] Standards register and reviewer-approved applicability.
- [ ] Clarification workflow and register.

### Checkpoint 7: Baseline and Reports

- [x] CSV verified requirement register.
- [ ] Full immutable RFP baseline aggregate, readiness gates, version/hash, and approvals. The initial freeze workflow requires an approved Design Basis, source documents, verified/resolved requirements, no open high/critical findings, an authorized local approver role, and a written approval reason; required multi-discipline approvals and controlling-document review gates remain outstanding.
- [ ] XLSX workbook and full printable Pre-Bid Assurance Report with provenance. The current live API/UI report summarizes project records and supports browser printing; XLSX and a complete formal report layout remain outstanding.
- [ ] Full audit/version report sections.

### Checkpoint 8: Product Hardening

- [x] Ruff, mypy, pytest, frontend production build, npm audit, Docker images, and basic CI workflow.
- [ ] PostgreSQL/MinIO/Redis integration tests and Testcontainers.
- [ ] Playwright E2E, frontend unit tests, API contract checks, secret/container scanning.
- [ ] Structured logs, correlation IDs, metrics, tracing, backup/restore, security and operations runbooks.
- [ ] Production Compose/Nginx, secret injection, CSP/rate-limiting, retention/deletion controls.

## Current Evidence

Latest verified commands:

```bash
ruff check apps packages tests alembic
mypy apps packages
pytest -q
alembic -x db_url=sqlite:////tmp/fluxera-design-basis.db upgrade head
cd apps/web && npm audit --audit-level=high && npm run build
```

Latest observed results: Ruff and mypy passed; 16 pytest tests passed; migrations applied through `0006_design_basis_versions`; npm audit found zero high-severity vulnerabilities; Next.js production build passed.

## Current Risks

- Local runtime data is stored in `fluxera.local.db` and `private-storage/`; it is not production object storage.
- The web UI still uses the explicit local development identity path, not interactive production sign-in.
- Parsing remains synchronous and can block on large/complex PDFs.
- Completeness findings are calculated but not yet persisted or resolvable.
- No automatic requirement extraction or procurement conclusion is permitted until candidate/evaluation controls are implemented.
