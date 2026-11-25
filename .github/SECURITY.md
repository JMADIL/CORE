# Security policy

## Supported code

Security fixes target the latest code on `main`. Older commits and deployments
do not have a separate maintenance policy.

## Reporting a vulnerability

Use the repository's **Security → Advisories → Report a vulnerability** option
when available: <https://github.com/JMADIL/CORE/security/advisories/new>.

If private reporting is unavailable, open an issue requesting a private contact
method without including vulnerability details. Do not post exploits, API keys,
database URLs, browser ownership tokens, or other people's conversations in public.

Include affected components, reproduction steps using synthetic data, expected
impact, and any suggested fix. Response times are not guaranteed.

## Deployment considerations

Core's browser ownership token isolates anonymous sessions; it is not account
authentication. Use an authenticated gateway for private deployments. Keep provider
credentials server-side and separate preview data from production data. Shared
media generation consumes the owner's credits even when a provider call fails.

If a credential is exposed, revoke or rotate it at the provider immediately;
removing it from Git history does not revoke it.
