# AGENTS.md — AI Money Mentor

## Entry point

- `python app.py` starts Flask dev server on port 5000
- Must set `GROQ_API_KEY` in `.env` (from `.env.example`) — without it the app exits via `sys.exit(1)` (dead `client = None` follows on line 38)

## Database quirks

- **Two SQLite files**: `money_mentor.db` (Flask-SQLAlchemy ORM via `models.py`) + `database.db` (raw `sqlite3` for email settings table only)
- Schema created via `db.create_all()` at app startup — no migration system
- Both files are in `.gitignore`

## AI / LLM

- Model: `llama-3.1-8b-instant` via Groq
- Two separate agent systems: `utils/multi_agent.py` (routed from `/agent` endpoint) and `agents.py` (standalone CLI)
- `app.py` uses keyword-based routing (`utils/multi_agent.route_query`) — not LLM-based
- Fallback messages shown when `GROQ_API_KEY` is missing (routes still work)

## Stock data

- Uses `yfinance` with automatic `.NS` suffix for Indian stocks when bare symbol fails
- 10-minute in-memory cache (`STOCK_CACHE` dict in `utils/stock.py`)

## Commands

```shell
pip install -r requirements.txt
pip install -r requirements.txt -r requirements-dev.txt  # for dev + tests
pytest tests/ -v                                          # full suite
pytest tests/test_tax.py -v                               # single file
```

## Testing quirks

- No CI test runner — workflows only cover security audit, stale cleanup, PR labeling
- `tests/test_validation.py` mocks `yfinance`, `groq`, `apscheduler`, `flask_sqlalchemy` at **module level** before importing `app`
- `tests/test_offline_fallback.py` and `tests/test_chat_context.py` use pytest fixtures that override `app_module.client = None` / `mock_client` to simulate offline/online
- `tests/test_price_alerts.py` uses `:memory:` SQLite + `db.create_all()` per fixture
- Tests touching LLM features (`/insights`, `/chat`, `/agent`) need a mocked `client` — they never call a real API

## Commit convention

- Conventional Commits enforced via `husky` + `commitlint` (`@commitlint/config-conventional`)
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`

## Installed skills

| Skill                             | Use in this repo                                                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `conventional-commit`             | Generate `feat`/`fix`/`chore` commit messages that pass the existing `husky` + `commitlint` hook                                     |
| `python-observability`            | Add structured logging and correlation IDs to Flask request handlers and the multi-agent pipeline in `utils/multi_agent.py`          |
| `python-design-patterns`          | Refactor `app.py` keyword-routing logic and `agents.py` into focused, testable layers with clear separation of concerns              |
| `python-testing-patterns`         | Extend `tests/` with proper pytest fixtures, mocking of `groq`/`yfinance`, and patterns for the dual-SQLite setup                    |
| `python-performance-optimization` | Profile stock-cache hit rates in `utils/stock.py`, LLM call latency, and SQLAlchemy query costs                                      |
| `api-security-best-practices`     | Harden Flask endpoints: input validation, sanitized error messages, rate limiting on `/chat` and `/agent`                            |
| `groq-api`                        | Reference for Groq Python SDK usage, model selection, streaming, tool use, and error handling in `app.py` and `utils/multi_agent.py` |
| `modern-css`                      | Modernize styles in `static/` with container queries, `oklch` colors, and scroll-driven animations                                   |
| `modern-javascript-patterns`      | Refactor frontend JS in `static/` to async/await, optional chaining, and ES modules                                                  |
| `github-actions-docs`             | Author or troubleshoot the existing security-audit, stale-cleanup, and PR-labeling workflows in `.github/workflows/`                 |

## Stale CONTRIBUTING.md warnings

- References `pyproject.toml` (does not exist), `pre-commit` (not installed — uses `husky`), and `flake8` (not in deps)
- Don't trust file listings there; trust the actual files
