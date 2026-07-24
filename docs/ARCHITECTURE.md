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
