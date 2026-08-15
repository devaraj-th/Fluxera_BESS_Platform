# Pre-Bid Intelligence MVP Progress

Last updated: 2026-08-15

This tracker records only behavior that is reachable and validated. A checked item is not a production claim; production readiness additionally requires the listed security, operations, and test gates.

## Validated Now

- [x] Tenant and project-scoped manual Pre-Bid workflow.
- [x] PDF MIME/signature/size/page validation, SHA-256 identity, project deduplication, and page-text extraction.
- [x] Manual evidence spans linked to source pages.
- [x] Atomic proposed requirements with controlled taxonomy and stable keys.
- [x] Evidence verification, requirement verification/rejection, optimistic version checking, and audit events.
- [x] Deterministic Pre-Bid source coverage report and verified-requirement CSV export.
- [x] Design Basis domain validation, draft versioning, and approval API/UI.
- [x] Deterministic starter completeness rules for long-life capacity retention and frequency-regulation response time.
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
- [ ] Complete Design Basis fields: jurisdiction/site, environmental conditions, augmentation, COD, currency, timezone, operating window, annual throughput, and retention milestones.
- [ ] Version comparison and immutable approval gate.

### Checkpoint 3: Document Platform

- [x] Private local source storage, SHA-256, page extraction, idempotent duplicate upload.
- [ ] Document inventory metadata: type, volume, revision, issue/effective date, addendum number, review status.
- [ ] Addendum/supersession model and re-review impact.
- [ ] MinIO/S3 adapter with byte-identical authorized download.
- [ ] Celery/Redis asynchronous processing, idempotent runs, retry state, job visibility.
- [ ] OCR fallback, parser/OCR version metadata, and quality-review path.
- [ ] Malware-scanner adapter and encrypted/malformed PDF handling.

### Checkpoint 4: Evidence and Requirements UX

- [x] Page text review, manual evidence creation, evidence-backed requirements, reviewer decisions.
- [x] Requirement detail register with page provenance.
- [ ] Rendered PDF page/region viewer, selection coordinates, highlights, and scanned-page support.
- [ ] Structured requirement fields, automatic keys, versions, duplicates, and immutable verified history.
- [ ] Persistent project context, search/filter/sort/pagination, bulk-safe review.

### Checkpoint 5: AI Candidate Extraction

- [ ] Provider-neutral port, no-external-LLM mode, deterministic fake provider.
- [ ] Schema-constrained candidate extraction with citations and confidence.
- [ ] Candidate isolation, accept/edit/reject/defer workflow.
- [ ] Evaluation dataset, fixtures, metrics, and release gates.

### Checkpoint 6: Intelligence Engines

- [x] Starter deterministic completeness API rules.
- [ ] Versioned rule catalogue and persisted, resolvable findings.
- [ ] Ambiguity detection and reviewer-controlled improved wording.
- [ ] Cross-document conflict and addendum impact analysis.
- [ ] Standards register and reviewer-approved applicability.
- [ ] Clarification workflow and register.

### Checkpoint 7: Baseline and Reports

- [x] CSV verified requirement register.
- [ ] Immutable RFP baseline aggregate, readiness gates, version/hash, and approvals.
- [ ] XLSX workbook and printable Pre-Bid Assurance Report with provenance.
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
