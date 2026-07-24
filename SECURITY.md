# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive findings.

Email **hello@adamsimms.xyz** with:

- A description of the vulnerability
- Steps to reproduce
- Impact assessment
- Any suggested fix, if you have one

You may also use GitHub private vulnerability reporting on this repository when available.

We will acknowledge receipt and work on a fix as soon as practical.

## In scope

- Accidental secrets in the repo (tokens, keys, private contacts that should stay private)
- Future firmware / controller code and GitHub Actions if added
- Abuse of open workflows that could harm fabricators, landowners, or the artist

## Out of scope

- Third-party shops, platforms, or grant portals themselves
- Physical security of a future installation site
- Social engineering

## Secrets

Never commit `.env`, API keys, private landowner contacts meant to stay private, or unpublished funding strategy that should remain confidential. Prefer issues that describe *process* without dumping private data.
