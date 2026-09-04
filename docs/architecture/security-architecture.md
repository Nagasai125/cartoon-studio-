# Security Architecture

## Purpose

This document defines identity, trust boundaries, secrets, source ingestion,
media access, publishing isolation, audit, and incident controls.

## Security Objectives

- Only the owner can access private production data or issue commands.
- Public static files disclose no secret or private asset.
- Retrieved content cannot control agents or infrastructure.
- Generation workers cannot publish.
- A video cannot be published unless its exact hash was approved.
- Compromise of one provider credential does not expose all credentials.
- Security-relevant actions are auditable.
- The platform collects no child personal information.

## Trust Boundaries

```text
  UNTRUSTED PUBLIC ZONE
  +--------------------------------------------------------------+
  | Browser | GitHub Pages files | Internet sources | Providers  |
  +-------------------------------+------------------------------+
                                  |
                          authenticated/validated
                                  |
  TRUSTED CONTROL ZONE            v
  +--------------------------------------------------------------+
  | API | workflow rules | callback verifier | publisher         |
  +-------------------------------+------------------------------+
                                  |
                           service identity
                                  |
  PRIVATE DATA ZONE               v
  +--------------------------------------------------------------+
  | PostgreSQL | object storage | secret storage | audit records |
  +--------------------------------------------------------------+
```

No content becomes trusted merely because an AI provider returned it.

## Authentication

Initial authentication uses GitHub OAuth through Supabase Auth.

Requirements:

- Authorization Code with PKCE.
- Exact allowlist of the owner's immutable GitHub numeric ID.
- Short-lived access token.
- Token issuer, audience, expiry, and signature validation by the API.
- Authentication failures do not reveal whether an account is allowlisted.
- Logout revokes the local session and clears owner data from the UI.

## Authorization

Even with one user, enforce named capabilities:

```text
  production.read
  production.control
  library.read
  library.manage
  settings.manage
  episode.approve
  episode.publish
```

This avoids redesigning authorization if a read-only reviewer is added later.
The frontend never provides authoritative permission checks.

## Public Frontend Rules

- No provider keys, database service keys, or YouTube tokens.
- No private source documents or media in the build artifact.
- Only public configuration such as API origin is embedded.
- No arbitrary third-party scripts.
- Source maps are not published publicly unless explicitly accepted.
- Dependency updates and bundle changes pass CI security checks.
- The site communicates only with allowlisted API and authentication origins.

## API Controls

- HTTPS only.
- Exact CORS origins.
- Authorization on every non-health endpoint.
- Request size and rate limits.
- Idempotency keys for state-changing commands.
- Schema validation for every request.
- Safe error responses with correlation IDs.
- Database parameterization through the ORM.
- Security audit event for approval, settings, credentials, and publishing.

## Webhook Controls

Provider callbacks must include or be wrapped with:

- Provider signature verification
- Timestamp freshness window
- Replay nonce or event ID
- Expected provider account
- Internal job and provider job match
- Idempotent completion behavior
- Response size limits
- Artifact download validation

If a provider lacks signed callbacks, use authenticated polling instead of an
unguarded callback endpoint.

## Source Ingestion Threats

| Threat | Control |
| --- | --- |
| SSRF | Resolve and block private/metadata IP ranges; recheck redirects |
| Oversized file | Header and streaming size limits |
| Malicious document | Type detection, scanning, sandboxed parser |
| Prompt injection | Treat content as quoted data; isolate instructions |
| Stale guidance | Effective dates and refresh policy |
| False authority | Trust tiers and domain policy |
| Copyright misuse | Rights state required before production eligibility |
| Hidden redirects | Canonical URL and full redirect audit |

## Prompt and Agent Security

- System policy is stored separately from retrieved content.
- Retrieved text is clearly delimited as untrusted evidence.
- Tools use allowlisted operations and validated arguments.
- Agents cannot directly execute shell, SQL, or arbitrary network requests.
- Model output is parsed into strict schemas.
- Policy failures cannot be overruled by another model response.
- Sensitive credentials are never placed in prompts.
- Prompt and policy versions are recorded for audit.

## Secrets

| Secret | Accessible by API | Accessible by worker | Accessible by frontend |
| --- | --- | --- | --- |
| Database service credential | Yes | Limited if required | No |
| Object storage service credential | Yes | Yes | No |
| AI provider key | No or limited | Yes | No |
| OAuth configuration secret | Yes | No | No |
| YouTube refresh token | Publisher path only | No | No |
| Callback verification secret | Yes | Limited adapter | No |

Secrets reside in Secret Manager, are accessed through service identity, and
are rotated without rebuilding the frontend.

## Media Security

- Buckets are private by default.
- Media is accessed through short-lived signed URLs.
- Signed URLs are scoped to one object and HTTP method.
- Uploaded files are type-checked and hashed.
- Original assets are immutable.
- Preview proxies reduce exposure of production originals.
- Temporary worker files are deleted after use.
- Untrusted media is processed in constrained worker environments.

## Publishing Isolation

```text
  Generation worker
       |
       | no publishing credential
       v
  final artifact + QA result
       |
       v
  Owner approval records exact SHA-256
       |
       v
  Publisher loads artifact and recomputes SHA-256
       |
    +--+--+
    |     |
  match mismatch
    |     |
    v     v
 upload  block + alert
```

The publisher also verifies current episode version, current QA report,
approval revocation, intended channel, and made-for-kids metadata.

## Supply Chain

- Lock all package versions.
- Pin GitHub Actions by full commit SHA.
- Enable Dependabot and vulnerability alerts.
- Run CodeQL and dependency review.
- Scan container images.
- Generate an SBOM.
- Sign production images using keyless OIDC.
- Deploy by immutable image digest.
- Do not execute untrusted pull-request code with production secrets.

## Logging and Privacy

Logs may include identifiers, state, duration, provider, model, status, and safe
failure classification.

Logs must not include:

- Access or refresh tokens
- Provider credentials
- Signed URL query strings
- Complete authorization headers
- Unnecessary raw provider payloads
- Child personal information

The system operates on aggregate YouTube analytics and does not build profiles
of individual children.

## Incident Response

Initial incident classes:

- Unauthorized dashboard access
- Credential exposure
- Malicious source ingestion
- Unapproved publication attempt
- Incorrect or unsafe published content
- Database or storage compromise
- Provider supply-chain incident

Every runbook must define containment, credential rotation, evidence retention,
owner notification, recovery, and post-incident corrective action.

An unsafe published episode is immediately made private before investigation.
