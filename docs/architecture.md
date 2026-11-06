# Architecture notes

## Domain boundaries

OpsTrace is split into four Django apps:

- `accounts`: authentication identity and registration.
- `workspaces`: tenant boundary, memberships, active-workspace middleware, and role checks.
- `operations`: recurring routines, generated work items, evidence records, audit events, and lifecycle services.
- `core`: cross-cutting dashboard and health endpoint.

`config` contains runtime configuration and URL composition. Templates are server-rendered; no JavaScript framework or frontend build tool is required.

## Tenant boundary

Each request passes through `AuthenticationMiddleware`, followed by `WorkspaceMiddleware`. The middleware reads the selected workspace ID from the session, then resolves an active membership for the authenticated user. A session value without a matching active database membership is ignored.

Every workspace-owned query in user-facing views is filtered by `request.workspace`. Members see only items assigned to them. Reviewers, administrators, and owners can see all work items in their current workspace. The active workspace is never accepted from a query parameter for data access.

The same rule must be applied to any future API, background job, export, notification, or storage integration. A background worker must use the workspace foreign key from its database record and must not infer tenant identity from untrusted input.

## Lifecycle and transaction boundaries

`apps.operations.services` owns the write-side business rules:

- `start_work_item`
- `add_evidence`
- `submit_work_item`
- `review_work_item`

Each service opens an atomic transaction, locks the work item using `select_for_update`, validates authorization and the expected prior state, persists the new state, and writes an `AuditEvent`.

The audit event model refuses regular updates and deletes. Admin views are read-only. The database is still managed by the application owner; stronger tamper resistance for regulated environments requires database permissions, external append-only log storage, or cryptographic log chaining.

## Scheduling and idempotency

Each `Routine` stores its next due date. The `generate_work_items` command:

1. Finds active routines whose `next_due_date` is on or before the requested horizon.
2. Locks each routine row in a transaction.
3. Generates all missing occurrences up to the horizon.
4. Uses a unique constraint on `(routine, scheduled_for)` as the final duplicate-prevention boundary.
5. Advances `next_due_date` to the next occurrence after the horizon.

Monthly and yearly recurrence clamp invalid dates to the final day of the target month (for example, a monthly occurrence on January 31 becomes February 28 or 29). The following month is calculated from that clamped date. If a business requires an explicit “last calendar day” or fixed-day anchor policy, add a separate schedule rule instead of changing this implicit behavior.

## Evidence storage

Evidence records use random storage keys, preserve the original filename as metadata, enforce a 10 MB size limit, allow a constrained extension list, and store a SHA-256 digest. Files are downloaded only through an authenticated view that checks workspace membership and work-item visibility.

The default filesystem storage is suitable for local evaluation. Production should use private object storage with authorization at download time, malware scanning, content inspection, backup, and retention controls.

## Database and runtime

SQLite is a convenience for local development. PostgreSQL is used by Docker Compose and recommended for deployment because the scheduler uses row-level locking and the application expects transactional behavior across workflow transitions.

The web process runs via Gunicorn. WhiteNoise serves collected static assets. A separate scheduler process runs the management command hourly. The command is safe to rerun and can also be invoked by an external scheduler.
