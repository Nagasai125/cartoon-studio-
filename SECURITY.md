# Security Policy

## Reporting

This repository and its Pages site are public. Security issues should be
reported directly to the repository owner and must not be placed in public
issue content.

## Sensitive Data

Never commit:

- AI provider keys
- Database service credentials
- OAuth client secrets
- YouTube refresh tokens
- Signed media URLs
- Production environment files

Use ignored local environment files during development and GitHub Actions
Secrets for production provider credentials.

Actions logs, caches, artifacts, Pages output, and releases must not contain
prompts, private source material, or unpublished media. Workflow checkpoint
artifacts contain allowlisted public-safe metadata only.

## Publishing Invariant

Generation workers must not receive publishing credentials. Production
publishing must verify an owner approval bound to the exact final media hash.

See [security architecture](docs/architecture/security-architecture.md) for the
complete baseline.
