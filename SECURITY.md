# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in AI Money Mentor, please report it
privately rather than opening a public issue. Open a
[GitHub security advisory](https://github.com/omroy07/AI-Money-Mentor/security/advisories/new)
or contact the maintainers directly. Please include steps to reproduce and the
potential impact. We aim to acknowledge reports within a few days.

## Session & CSRF Hardening

The app authenticates with **session cookies** (Flask-Login). To reduce the
risk of Cross-Site Request Forgery (CSRF) and cookie theft, the following
cookie attributes are configured in `app.py`:

| Setting                   | Value                | Why                                                                                                                |
| ------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `SESSION_COOKIE_SAMESITE` | `Lax`                | Prevents the session cookie from being sent on cross-site POST requests — the primary CSRF vector for cookie auth. |
| `SESSION_COOKIE_HTTPONLY` | `True`               | Keeps the cookie inaccessible to JavaScript, mitigating theft via XSS.                                             |
| `SESSION_COOKIE_SECURE`   | `True` in production | Restricts the cookie to HTTPS so it can't leak over plaintext. Enabled when `FLASK_ENV=production`.                |

### Token-based CSRF (follow-up)

`SameSite=Lax` blocks the common CSRF cases for the current JSON/`fetch` API.
For defense-in-depth on form-based POST routes, [Flask-WTF](https://flask-wtf.readthedocs.io/)
`CSRFProtect` can be added. Note this requires the frontend to send a CSRF
token with each state-changing request, so it should be rolled out together
with the corresponding client-side changes; enabling it globally without that
would reject the existing JSON POST endpoints.

## Secrets & Environment

- `SECRET_KEY` **must** be set to a strong random value in production — it
  signs session cookies, so a known/default value lets attackers forge
  sessions. See `.env.example`.
- Never commit a real `.env` file; it is gitignored.
- `FLASK_DEBUG` must never be enabled in production.

## CodeQL Audit Report

See [`docs/SECURITY_AUDIT.md`](docs/SECURITY_AUDIT.md) for the consolidated
CodeQL / dependency-audit triage report (issue #521). It lists every CodeQL
flag raised against the current `main`, the resolution path for each
(hardcoded-credential removal, weak-hash replacement, XSS-via-`innerHTML`
guarding, model-import deinterleaving, top-level import restoration) and
the corresponding PR number.
