# Authentication and Authorization

## Separation of concerns

Authentication answers: **Who is making this request?**

Authorization answers: **What may that identity do in the selected organization?**

The application does not treat a role carried in a browser or JWT as
authoritative. Each protected request loads the current user, membership, and
organization state from PostgreSQL.

## Identity and membership model

- A normalized, case-insensitive email identifies one user account globally.
- A user may have memberships in multiple organizations.
- Each membership has one role: `owner`, `admin`, or `member`.
- Users, memberships, and organizations can each be deactivated.
- A request is authorized only when all three are active.
- Existing `users.company_id` and `users.role` columns remain temporarily for
  compatibility; authorization no longer reads them.

If a user has more than one active membership, login requires
`organization_slug`. This prevents the server from silently selecting the wrong
tenant.

## Access tokens

Access tokens are signed JWTs containing:

- `sub`: internal user identifier
- `mid`: membership identifier
- `type`: `access`
- issuer and audience
- issued-at, not-before, and expiry timestamps
- unique token identifier

Access tokens are short-lived. They do not contain an authoritative role or
organization permission. The backend resolves `sub` and `mid` to the current
database membership for every protected request.

Changing a membership role or deactivating it therefore affects subsequent API
requests without waiting for the access token to expire.

## Refresh sessions

Refresh tokens are opaque random secrets, not JWTs.

- Only a SHA-256 digest is stored in `refresh_sessions`.
- Tokens expire after the configured number of days.
- Every refresh rotates the token and revokes its predecessor in one
  transaction.
- Reusing a rotated or revoked token fails.
- Logout revokes the submitted refresh session.

An already issued access token remains usable until its short expiration unless
the user, membership, or organization is deactivated. This is an explicit
tradeoff; a per-request access-token denylist is not implemented.

## Passwords

- Passwords are hashed with Argon2 through Passlib.
- The complete password is hashed; the previous bcrypt-oriented 72-byte
  truncation has been removed.
- API schemas cap password input at 256 characters to bound request processing.
- Passwords and hashes are never returned by API schemas.

## Role permissions

| Capability | Owner | Admin | Member |
|---|:---:|:---:|:---:|
| Read authorized documents and ask questions | Yes | Yes | Yes |
| Manage own conversations | Yes | Yes | Yes |
| Upload and deactivate documents | Yes | Yes | No |
| View organization members | Yes | Yes | No |
| Invite members | Yes | Yes | No |
| Invite admins or owners | Yes | No | No |
| Change roles or deactivate memberships | Yes | No | No |
| Execute legacy workflow actions | Yes | Yes | No |

The final active owner cannot be demoted or deactivated.

Frontend route checks are usability controls only. FastAPI dependencies and
tenant-scoped database queries enforce permissions server-side.

## Invitation security

- Invitation secrets are generated with a cryptographically secure random
  generator.
- PostgreSQL stores only a SHA-256 digest.
- Invitations expire and are single-use.
- Creating an invitation returns the raw secret once to the authorized caller.
- Pending-invitation lists never return a secret.
- Reissuing an invitation replaces the previous secret.
- An existing user accepting an invitation must provide the account password;
  invitation possession alone cannot reset that account.

Email delivery is not implemented yet. Returning the secret once supports a
manual portfolio demonstration but should be replaced by an email delivery
boundary before public deployment.

## Tenant context

`get_current_user` performs these checks:

1. Require a bearer credential.
2. Validate JWT signature, algorithm, issuer, audience, type, and time claims.
3. Parse the user and membership identifiers.
4. Load the matching user and membership from PostgreSQL.
5. Confirm the user, membership, and organization are active.
6. Return the database role and organization ID to downstream authorization.

Endpoint code must use the returned `company_id`; it must not accept tenant
ownership from request bodies.

## Configuration

Required:

- `SECRET_KEY`: at least 32 characters, supplied outside version control
- `DATABASE_URL`
- `GROQ_API_KEY`

Relevant optional settings:

- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `JWT_ISSUER`
- `JWT_AUDIENCE`
- `ALGORITHM` (currently HS256)

Docker Compose refuses to start the API when `SECRET_KEY` is absent.

## Known limitations

- Database connection pooling is deferred to the backend engineering phase.
- Refresh tokens are returned in JSON until the frontend session transport is
  implemented. The intended browser design uses a Secure, HttpOnly, SameSite
  cookie for refresh state.
- No password reset or email verification flow exists.
- No account-level MFA, SSO, or SCIM exists.
- Rate limiting is not yet enforced.
- Row-level security is deferred until transaction-scoped tenant context is
  available.
- Legacy identity columns remain until all call sites and data are migrated.

These limitations should be stated directly rather than describing the current
system as completely secure.
