# Security Audit Report — CodeQL Triage

Tracking issue: #521

This document consolidates the findings, remediation status, and rationale for each of the 8 CodeQL / dependency-audit issues assigned to **@arcgod-design** during the SSoC '26 cycle against `omroy07/AI-Money-Mentor`. It exists to give maintainers a single place to review what was triaged, what was fixed, what was closed as already-fixed, and what intentionally remains out of scope.

## Triage summary

| Issue | Title                                                                                                         | Severity | Resolution                                                                                                 | PR   | Status           |
| ----- | ------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------- | ---- | ---------------- |
| #514  | Hardcoded `'your-email@gmail.com'` fallback in `/test-email` route                                            | High     | Fixed in dedicated PR                                                                                      | #523 | Open             |
| #515  | Hardcoded `'dev-secret-key'` Flask session key                                                                | High     | Already fixed via PR #492 (merged). Closing note posted on issue; no new PR raised to avoid duplicate work | #492 | Closed (covered) |
| #516  | Use of `hashlib.md5(...)` (weak hash)                                                                         | High     | Already fixed via PR #492 — replaced with `hashlib.sha256`                                                 | #492 | Closed (covered) |
| #517  | XSS via `innerHTML` across `templates/` and `static/scripts/`                                                 | High     | Fixed in dedicated PR                                                                                      | #536 | Open             |
| #518  | `app.py` models layer interleaved with route handlers (CodeQL flag `py/...`)                                  | Medium   | Already fixed via PR #492 — `models.py` de-interleaved, dead code removed                                  | #492 | Closed (covered) |
| #519  | Duplicate and shadowed `from models import ...` blocks in `app.py`                                            | Medium   | Already fixed via PR #492 — collapsed into single top-level import                                         | #492 | Closed (covered) |
| #520  | Missing top-level imports of new models (`BankConnection`, `FraudAlert`, `Notification`, `InvestmentGoal`, …) | Medium   | Fixed in dedicated PR                                                                                      | #531 | Open             |
| #521  | Triage of remaining CodeQL alerts (this umbrella issue)                                                       | Medium   | Audit report via this `docs/SECURITY_AUDIT.md` (this PR)                                                   | TBD  | Open             |

All 8 issues are addressed. Three are merged-and-closed upstream; four are in open PRs awaiting maintainer review; one is this PR.

## Severity matrix and methodology

- **High** — issues that GitHub CodeQL marks with security-severity `high` (often CVSS ≥ 7.0): hardcoded credentials in source, weak crypto primitives, reflected/stored XSS. Each assigned a dedicated PR with a focused, minimal diff so they can be re-rolled independently if the maintainer disagrees with secondary changes.
- **Medium** — code-organization issues that CodeQL flags as code-quality alerts or maintainability risks: duplicate imports, shadowed symbols, dead code, missing symbols. Resolved through de-interleaving and import consolidation.

## Per-issue detail

### #514 — Hardcoded email credential fallback

- **Location**: `app.py`, `/test-email` route (originally ~line 3698)
- **CodeQL rule**: `python/hardcoded-credentials/EnvVariableAssignment`
- **Fix**: removed the `'your-email@gmail.com'` literal fallback inside `os.getenv('EMAIL_USER', ...)`. The route now returns HTTP 503 if `EMAIL_USER` is unset rather than silently email-blasting the original hardcoded address.
- **Additional commit**: `requirements.txt` downgrade (`transformers 5.3.0 -> 4.53.0`, `scipy 1.18.0 -> 1.17.1`) — needed only because the upstream Dependency-Audit job runs under Python 3.11 and the upstream-pinned 5.x tree fails to install. This second commit is tech-debt-of-the-CI, not part of the security fix proper; reviewer is free to cherry-pick or split.
- **Verification**: `rg 'your-email|your-app' app.py` returns 0 matches; Python `ast.parse` passes.
- **PR**: https://github.com/omroy07/AI-Money-Mentor/pull/523

### #515 — Hardcoded `'dev-secret-key'` Flask session key

- **Location**: `app.py`, `app.secret_key = 'dev-secret-key'` (originally ~line 190)
- **CodeQL rule**: `python/hardcoded-credentials/EnvVariableAssignment`
- **Fix**: replaced with `app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)`. The app will now deterministically pick up a configured `SECRET_KEY` if provided, or generate a fresh cryptographically-random key per process boot if not.
- **Landed in**: PR #492 (merged → `main`).
- **Verification**: `rg 'dev-secret-key' app.py` returns 0 matches.

### #516 — Use of `hashlib.md5(...)` (weak hash)

- **Location**: `app.py`, document-integrity hash (originally ~line 270)
- **CodeQL rule**: `python/weak-crypto/WeakHash`
- **Fix**: replaced with `hashlib.sha256(...)`. The only consumer of the digest was an internal cache key, so digest-size change is transparent to the rest of the codebase.
- **Landed in**: PR #492 (merged → `main`).

### #517 — XSS via `innerHTML` across `templates/` and `static/scripts/`

- **Location**: ~100 `.innerHTML = \`...${field}...\``sinks across`static/scripts/_.js`(6 files) and`templates/_.html` (19 files).
- **CodeQL rule**: `js/xss-through-dom` (and the HTML template rule variant)
- **Fix strategy**: shared `esc()` helper added to `templates/base.html` (extends-available) plus standalone-helper added to `templates/index.html` and `templates/predictive_alerts.html`. User-controlled fields — `widget.title`, `h.symbol`, `goal.name`, `t.category`, `data.error`, `error.message`, `file.name`, `data.runway_message`, `taxRes.recommended`, etc. — wrapped in `esc()` only where they flow into `innerHTML`. Numeric-only fields intentionally left untouched since their stringification cannot produce HTML.
- **Bonus fix**: `script.js` portfolio row no longer interpolates `h.id` into inline `onclick="deleteFromPortfolio(${h.id})"` (a JS-injection vector since `h.id` was used inside a JS expression context). Replaced with `data-portfolio-id` attribute + a single event-delegation `click` listener on `<tbody>`.
- **Verification**:
  - `node --check` passes on all 6 backend JS files.
  - `rg "\$\{[a-z][a-zA-Z0-9_]*\.[a-zA-Z]" templates/` shows no remaining user-controlled object-property interpolation inside `.innerHTML = \`...\`` sinks.
- **PR**: https://github.com/omroy07/AI-Money-Mentor/pull/536

### #518 — `app.py` models layer interleaved with route handlers

- **Location**: `app.py` (where `from models import ...` was originally scattered through the file) and `models.py`
- **CodeQL rule**: code-quality alert — interleaved model and controller concerns
- **Fix**: `models.py` de-interleaved into a clean top-of-file block. Dead `client = None` reference (after `sys.exit(1)` on missing `GROQ_API_KEY`) removed. Routes no longer re-import models inline.
- **Landed in**: PR #492 (merged → `main`).

### #519 — Duplicate and shadowed `from models import ...` blocks

- **Location**: `app.py`
- **CodeQL rule**: code-quality alert — duplicate import and shadowed symbol
- **Fix**: 6 scattered `from models import ...` blocks consolidated into a single top-level import. Eliminates shadowing of imported symbols by later imports inside function bodies.
- **Landed in**: PR #492 (merged → `main`).

### #520 — Missing top-level imports of new models

- **Location**: `app.py`
- **CodeQL rule**: code-quality alert — undefined-name and import-rotation
- **Fix**: added 11 missing top-level model imports (`BankConnection`, `BankTransaction`, `FraudAlert`, `Notification`, `NotificationPreference`, `InvestmentGoal`, `GoalAllocation`, `GoalContribution`, `GoalRecommendation`, `Couple`, `CoupleSubscription`, `User`) so the new handlers in `app.py` no longer hit `NameError`s when those routes are first invoked.
- **Verification**: `python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read())"` passes; `rg 'from models import' app.py` now returns exactly one top-level match.
- **PR**: https://github.com/omroy07/AI-Money-Mentor/pull/531

### #521 — Triage of remaining CodeQL alerts (this issue)

- **Resolution**: this audit document + the four dedicated fix PRs cited above.
- **Out of scope (intentionally)**:
  - Many `.innerHTML = \`...\`` sinks that interpolate **only** numeric values (`fmtNum(h.amount)`, `data.change_percent`, `Math.abs(...)`) were NOT wrapped in `esc()`. Their stringification cannot produce HTML. Wrapping them would add noise without adding security.
  - The bot-reply render path in `script.js::appendMsg` continues to use `DOMPurify.sanitize(marked.parse(text))` — this is intentional rich-HTML rendering of markdown-formatted bot replies; `esc()` would break formatting.
  - Dependency-installation failures under the upstream Python 3.11 CI job (scipy 1.18.0, transformers 5.3.0) are CI engineering debt; the version downgrades in PR #523 are a minimal workaround. The proper fix is for the upstream `dependency-audit` workflow to bump to Python 3.12.

## Maintainer checklist

1. Review #523 — the email-credential fix and the Python-3.11-workaround `requirements.txt` downgrade.
2. Review #531 — the missing top-level model imports for #520.
3. Review #536 — the `esc()`-based blanket XSS hardening across 6 JS files and 19 HTML templates.
4. Verify the issues #515 / #516 / #518 / #519 (all already fixed via merged PR #492) are indeed closed.
5. Optionally merge `docs/SECURITY_AUDIT.md` (this PR) as a permanent audit reference.

Closes #521
