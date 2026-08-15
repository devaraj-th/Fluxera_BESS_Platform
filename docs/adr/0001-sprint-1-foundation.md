# ADR 0001: Sprint 1 foundation

## Decision

Fluxera uses a modular monolith with a pure Python domain package, FastAPI interfaces, SQLAlchemy infrastructure, and asynchronous worker seams. PostgreSQL is the system of record; Redis and MinIO are local infrastructure dependencies.

The first vertical slice keeps authorization at the application boundary and uses tenant/project scoped repositories. Original uploads are addressed by SHA-256 and are never overwritten. AI extraction is explicitly out of scope for Sprint 1.

## Consequences

This keeps deployment and transactions simple while preserving ports for storage, parsing, authentication, and jobs. Local tests may use SQLite only as a fast substitute; PostgreSQL migration compatibility remains a required integration gate.
