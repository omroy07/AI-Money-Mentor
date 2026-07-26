# Setup Guide

## Prerequisites

- Python 3.10+
- Node.js 18+ (for commit hooks only)
- Groq API key (free tier available at https://console.groq.com)

## Quick Start

```shell
# 1. Clone and enter the project
git clone https://github.com/omroy07/AI-Money-Mentor.git
cd AI-Money-Mentor

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY=<your_key>

# 5. Run the app
python app.py
# Server starts at http://localhost:5000
```

## Development Setup

```shell
# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Install git hooks
npm install

# Run tests
pytest tests/ -v

# Run a single test file
pytest tests/test_tax.py -v
```

## Configuration

All configuration is in `.env`:

| Variable        | Required | Default                   | Description          |
| --------------- | -------- | ------------------------- | -------------------- |
| `GROQ_API_KEY`  | Yes      | —                         | API key for Groq LLM |
| `SECRET_KEY`    | No       | auto-generated            | Flask session key    |
| `DATABASE_URL`  | No       | sqlite:///money_mentor.db | Primary database     |
| `MAIL_SERVER`   | No       | localhost                 | SMTP server          |
| `MAIL_PORT`     | No       | 587                       | SMTP port            |
| `MAIL_USE_TLS`  | No       | True                      | SMTP TLS             |
| `MAIL_USERNAME` | No       | —                         | SMTP user            |
| `MAIL_PASSWORD` | No       | —                         | SMTP password        |

## Production Deployment

The app uses Flask's built-in development server. For production,
use a WSGI server like Gunicorn or Waitress:

```shell
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or with eventlet for WebSocket support:

```shell
pip install eventlet
python app.py --production
```

> **Note**: SQLite is not suitable for production workloads.
> Consider migrating to PostgreSQL by setting `DATABASE_URL`.

## Troubleshooting

| Symptom               | Likely Cause           | Fix                                               |
| --------------------- | ---------------------- | ------------------------------------------------- |
| App exits immediately | Missing `GROQ_API_KEY` | Set it in `.env`                                  |
| Stock data fails      | Unknown ticker         | The app auto-tries `.NS` suffix for Indian stocks |
| Login not working     | Secret key changed     | Delete the `.env` `SECRET_KEY` line to regenerate |
| Tests fail            | Missing test deps      | Run `pip install -r requirements-dev.txt`         |
| CSS not loading       | Static files cached    | Hard refresh (Ctrl+Shift+R)                       |
