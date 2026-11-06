# Security policy

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, customer data, or private evidence. Contact the repository maintainers through a private security advisory channel once the repository has one configured. Until then, use a private contact method agreed with the project owner.

## Security controls in this codebase

- Django password hashing and built-in password validators.
- CSRF protection and POST-only state-changing endpoints.
- Workspace membership re-check on every authenticated request.
- Role checks for routine management and review operations.
- Workspace-scoped object lookups and private evidence downloads.
- Evidence file extension and size validation; randomized storage names.
- SHA-256 digest stored for evidence records.
- Append-only application-level audit events.
- Secure cookie, HTTPS redirect, HSTS, host, content-type, and frame settings configurable for production.

## Deployment responsibilities

The current baseline does not provide antivirus scanning, content-type/magic-byte verification, rate limiting, email verification, SSO/MFA, external tamper-proof audit storage, or managed object storage. These are important additions before handling sensitive or regulated information.

Operators must keep `DEBUG=False`, use TLS, secure secrets, restrict hostnames and trusted origins, patch dependencies, back up the database and evidence files, monitor logs, and test restoration. Do not expose the Django development server or the PostgreSQL port to the public internet.

## Supported versions

The project targets maintained Python and Django releases. Update dependencies promptly when security releases are published and rerun the full test suite before deployment.
