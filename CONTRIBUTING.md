# 🤝 Contributing to AI Money Mentor

Thank you for your interest in contributing! This guide walks you through everything you need to set up, develop, and submit a great contribution.

---

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Project Structure](#project-structure)
5. [Branching Strategy](#branching-strategy)
6. [Making Changes](#making-changes)
7. [Running Tests](#running-tests)
8. [Commit Message Convention](#commit-message-convention)
9. [Submitting a Pull Request](#submitting-a-pull-request)
10. [Issue Reporting](#issue-reporting)
11. [Coding Standards](#coding-standards)

---

## Code of Conduct

By participating in this project you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

---

## Getting Started

### Prerequisites

| Tool   | Version |
| ------ | ------- |
| Python | ≥ 3.10  |
| pip    | latest  |
| Git    | ≥ 2.30  |

### Fork & Clone

```bash
# 1. Fork the repo on GitHub (click the Fork button)
# 2. Clone your fork locally
git clone https://github.com/<your-username>/AI-Money-Mentor.git
cd AI-Money-Mentor

# 3. Add upstream remote to keep your fork in sync
git remote add upstream https://github.com/omroy07/AI-Money-Mentor.git
```

---

## Development Setup

```bash
# Create a virtual environment (strongly recommended)
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows PowerShell

# Install all dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# → Open .env and set your GROQ_API_KEY
# → Obtain a free key at https://console.groq.com/

# Verify setup
python app.py
# You should see: [OK] Groq client initialised successfully.
# Open http://127.0.0.1:5000 in your browser
```

> **⚠️ Never commit your `.env` file.** It is already listed in `.gitignore`.

---

## Project Structure

```
AI-Money-Mentor/
├── app.py                  # Flask application entry point
├── agents.py               # Agent definitions
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Pytest configuration
├── .env.example            # Environment variable template
├── templates/
│   └── index.html          # Single-page frontend (HTML/CSS/JS)
├── utils/
│   ├── sip.py              # SIP (mutual fund) calculator
│   ├── tax.py              # Indian income tax calculator
│   ├── money_score.py      # Financial health scoring engine
│   ├── expense_track.py    # Expense aggregation & AI insights
│   ├── stock.py            # yfinance stock data wrapper
│   ├── pdf_parser.py       # LLM + regex PDF financial parser
│   ├── multi_agent.py      # Query router & specialist agents
│   └── persistence.py      # JSON-file data persistence layer
├── tests/
│   ├── test_sip.py
│   ├── test_tax.py
│   ├── test_money_score.py
│   └── test_expense_track.py
└── .github/
    ├── ISSUE_TEMPLATE/     # Bug, Feature, Docs templates
    ├── PULL_REQUEST_TEMPLATE.md
    └── workflows/
        └── ci.yml          # GitHub Actions CI pipeline
```

---

## Branching Strategy

Always create a new branch from a **synced** `main`:

```bash
# 1. Sync your fork with upstream
git fetch upstream
git checkout main
git merge upstream/main

# 2. Create a focused, descriptively named branch
git checkout -b <type>/<short-description>
```

### Branch naming examples

| Type          | Branch Name                        |
| ------------- | ---------------------------------- |
| Bug fix       | `fix/navbar-mobile-overflow`       |
| New feature   | `feat/export-report-pdf`           |
| Documentation | `docs/improve-setup-guide`         |
| CI / Workflow | `ci/add-dependency-audit`          |
| Refactor      | `refactor/extract-chart-component` |
| Accessibility | `accessibility/add-aria-labels`    |

---

## Making Changes

- **One branch = one focused change.** Do not combine unrelated changes.
- Modify only files that are necessary for the problem you are solving.
- Maintain backward compatibility — avoid breaking existing API contracts.
- For frontend changes in `templates/index.html`, test at mobile (≤ 480 px), tablet (≤ 768 px), and desktop widths.
- For backend changes, add or update the relevant test in `tests/`.

---

## Running Tests

```bash
# Run the full test suite
pytest tests/ -v

# Run a single test file
pytest tests/test_sip.py -v

# Run with coverage (optional)
pip install pytest-cov
pytest tests/ --cov=utils --cov-report=term-missing
```

> Tests that require a live Groq API key are intentionally excluded from the automated suite. The CI pipeline injects a placeholder `GROQ_API_KEY` so pure-logic tests pass without real credentials.

---

## Commit Message Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/). Commit linting is enforced via `pre-commit` hooks.

### Setup pre-commit hooks (one-time)

```bash
# Install pre-commit
pip install -r dev-requirements.txt

# Install the git hooks
pre-commit install --hook-type commit-msg
```

After setup, any commit that doesn't follow the convention will be rejected.

### Format

```
<type>: <short imperative description>

[Optional body: explain *why*, not *what*]

[Optional footer: Closes #<issue-number>]
```

**Note:** Body and footer are optional. For simple changes, just the first line is enough.

### Allowed types

| Type       | Use for                                     |
| ---------- | ------------------------------------------- |
| `feat`     | New feature or capability                   |
| `fix`      | Bug fix                                     |
| `docs`     | Documentation only                          |
| `refactor` | Code restructuring without behaviour change |
| `test`     | Adding or updating tests                    |
| `ci`       | CI workflow changes                         |
| `style`    | Formatting / whitespace (no logic change)   |
| `perf`     | Performance improvements                    |
| `chore`    | Dependency updates, housekeeping            |

### ✅ Good examples (all valid)

One-liner (most common):

```
fix: prevent index corruption in delete-item endpoint
feat: add /health liveness probe for deployment environments
docs: add local setup instructions to CONTRIBUTING.md
test: add parametrized edge-case tests for money_score
chore: update groq dependency to 1.5.0
```

With body (for context):

```
fix: prevent index corruption in delete-item endpoint

The delete operation was using array index instead of item ID.
This caused the wrong item to be removed when items were sorted.

Closes #45
```

### ❌ Invalid (will be rejected)

```
fixed stuff
update code
changes made
final commit
WIP
Updated the thing
```

---

## Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin <your-branch-name>
   ```
2. Open a PR from your fork's branch → `omroy07/AI-Money-Mentor:main`.
3. Fill out the **PR template** completely — partial templates will be requested to be completed before review.
4. Link the PR to its issue using `Closes #<issue-number>`.
5. Wait for the CI pipeline to pass (green ✅) before requesting review.
6. Respond to review comments within a reasonable timeframe.

### PR checklist

- [ ] Branch is rebased on the latest `main`
- [ ] CI pipeline is passing
- [ ] All related tests pass locally (`pytest tests/ -v`)
- [ ] No secrets or credentials in any committed file
- [ ] Only files relevant to this change are modified
- [ ] Responsive design verified for frontend changes

---

## Issue Reporting

Before opening an issue, please:

1. Search existing [open and closed issues](https://github.com/omroy07/AI-Money-Mentor/issues) to avoid duplicates.
2. Use the appropriate **issue template** (bug report / feature request / documentation).
3. Provide as much context as possible — stack traces, reproduction steps, OS, Python version.

---

## Coding Standards

### Python

- PEP 8 style (enforced by `flake8` in CI — max line length: 127)
- Type hints encouraged but not mandatory
- Docstrings on all public functions (`"""Short summary.\n\nLonger detail."""`)
- No bare `except:` — always catch specific exception types

### JavaScript / HTML

- Vanilla JS (no jQuery or frameworks in the frontend)
- Use `const` / `let`; avoid `var`
- Keep functions small and single-purpose
- Use semantic HTML5 elements (`<main>`, `<nav>`, `<section>`, etc.)

### Security

- **Never** hardcode credentials, API keys, or tokens in source code
- Always use environment variables (see `.env.example`)
- Sanitize all user inputs before processing

---

_Questions? Open a [Discussion](https://github.com/omroy07/AI-Money-Mentor/discussions) or drop a comment on the relevant issue._ 🙌
