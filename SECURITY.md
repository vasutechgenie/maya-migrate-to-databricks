# Security Policy

## Scope

MAYA is an offline code-generation and planning tool. It reads exported source
metadata and emits SQL, contracts, and reports; it does not connect to your
production systems on its own. The most relevant "security" concerns are therefore:

- Accidentally committing real schemas, credentials, hostnames, or customer names
  into a repo (the CI scrub check helps prevent this).
- Trusting generated SQL without review before running it against your data.

Always review generated artifacts before executing them, and run them with
least-privilege credentials.

## Reporting a Vulnerability

If you discover a security issue in the tool itself (for example, a code path that
could execute untrusted input, or a dependency vulnerability), please report it
privately:

- Use GitHub's **Report a vulnerability** (Security Advisories) on the repository, or
- Open a minimal issue asking a maintainer to contact you, without disclosing details.

Please do not open a public issue with exploit details until a fix is available.
We aim to acknowledge reports within a few days.

## Supported Versions

This project is pre-1.0; security fixes are applied to the latest `main`.
