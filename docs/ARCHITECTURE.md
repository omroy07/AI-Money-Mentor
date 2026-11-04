# Architecture Overview

## High-Level Design

AI Money Mentor is a monolithic Flask application with embedded AI orchestration,
serving both a server-rendered web UI and a REST API.

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                            │
│  Jinja2 templates  ←───  static/ (CSS, JS)             │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────────────┐
│                    Flask (app.py)                        │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Blueprints / Route Groups                        │ │
│  │  Auth · Dashboard · Stocks · Budget · Tax         │ │
│  │  Chat · Agent · Insights · Reports · Settings     │ │
│  │  Notifications · Rebalancer · FIRE Planner        │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  AI Layer                                         │ │
│  │  utils/multi_agent.py  ←─  keyword-based routing  │ │
│  │  agents.py             ←─  standalone CLI          │ │
│  │  Groq API (llama-3.1-8b-instant)                  │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Utilities                                        │ │
│  │  stock.py · tax.py · budget.py · alerts.py · ... │ │
│  └────────────────────────────────────────────────────┘ │
└──────────┬────────────────────────────────────────┬─────┘
           │ SQLAlchemy ORM                      │ APScheduler
┌──────────▼──────────┐              ┌───────────▼──────────┐
│   money_mentor.db   │              │  Background Jobs     │
│   (Flask-SQLAlchemy)│              │  Price alerts        │
│   tables: users,    │              │  Notifications       │
│   transactions,     │              │  Auto-rebalancing    │
│   budgets, alerts,  │              └──────────────────────┘
│   portfolios...     │
└─────────────────────┘
           │ raw sqlite3
┌──────────▼──────────┐
│   database.db       │
│   email_settings    │
└─────────────────────┘
```

## Database

Two SQLite files coexist:

| File              | ORM                          | Purpose              |
| ----------------- | ---------------------------- | -------------------- |
| `money_mentor.db` | Flask-SQLAlchemy (models.py) | All application data |
| `database.db`     | raw sqlite3 module           | Email settings only  |

Schema is created via `db.create_all()` at startup. No migration system exists.

## AI Agent System

Two separate agent pipelines:

1. **Web** (`utils/multi_agent.py`): Invoked from `/agent` endpoint. Uses keyword-based
   routing (`utils/multi_agent.route_query`) to dispatch to topic-specific agents.
2. **CLI** (`agents.py`): Standalone command-line interface with its own Groq client.

Both use Groq's `llama-3.1-8b-instant` model.

## Stock Data Pipeline

`utils/stock.py` provides real-time and historical data via yfinance:

- Automatic `.NS` suffix for Indian stocks when bare symbol lookup fails
- 10-minute in-memory cache (`STOCK_CACHE` dict)
- Separate cache for historical data

## Scheduling

APScheduler handles background tasks:

- Price alert checks
- Notification delivery
- Auto-rebalancing triggers

## Key Design Decisions

- **Monolithic architecture**: Single Flask app for simplicity
- **Dual SQLite files**: Legacy design; email settings isolated in separate file
- **Keyword routing not LLM routing**: `/agent` endpoint uses regex/pattern matching,
  not an LLM, to decide which agent handles a query — faster and cheaper
- **In-memory caching**: Stock data cached in process memory for 10 minutes (no Redis)
- **No migration framework**: Schema resets on deploy unless data is manually preserved

## Modular Feature Blueprints

To incrementally decouple `app.py` (~7000 lines) and reduce merge conflicts, self-contained functional areas are organized into Flask Blueprints under `src/features/`.

### Directory Convention

```
src/features/<feature_name>/
├── __init__.py       # Exports the feature blueprint (e.g. fire_planner_bp)
└── routes.py         # Blueprint instance, route decorators, and view logic
```

### Feature Blueprints Inventory

| Blueprint Name | Module | Prefix / Routes | Description |
| -------------- | ------ | --------------- | ----------- |
| `fire_planner` | `src.features.fire_planner` | `/fire-planner`, `/api/fire/plan`, `/api/fire/quick` | Interactive FIRE retirement path calculator & Monte Carlo simulation |

### Blueprint Extraction Pattern (How to repeat for next areas)

1. **Create Package**:
   - Add directory `src/features/<feature_name>/`.
   - In `routes.py`, define `<feature_name>_bp = Blueprint('<feature_name>', __name__)` and transfer the route handlers.
   - In `__init__.py`, export the blueprint: `from .routes import <feature_name>_bp`.

2. **Register in `app.py`**:
   - Import `<feature_name>_bp` and register via `app.register_blueprint(<feature_name>_bp)`.
   - Optionally re-export handler functions in `app.py` if legacy code or tests import them directly.

3. **Verify Compatibility**:
   - Ensure all route URLs, methods, and JSON response shapes remain 100% unchanged.
   - Run tests: `pytest tests/test_<feature_name>.py`.

## Route Inventory

The `app.py` file defines approximately 90+ routes covering:

- Authentication (login, register, logout, profile)
- Dashboard & overview
- Stock tracking & watchlists
- Budget management
- Tax computation & filing
- AI chat & agent
- Portfolio management
- Financial reports (PDF export)
- Transaction ledger
- Notifications & alerts
- Portfolio rebalancing
- FIRE (Financial Independence) planning
- Settings & account management
- Couple finance features
- Bank integration (UPI, statements)
- MFA (multi-factor authentication)
- SIP (Systematic Investment Plan) tracking
