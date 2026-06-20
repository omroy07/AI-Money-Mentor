import re
from flask import Flask, request, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta, date
import sqlite3
import atexit

from flask import Flask, request, jsonify, render_template, make_response

import yfinance as yf
import os
import sys
import csv
import io
from groq import Groq
from fpdf import FPDF
from dotenv import load_dotenv
from flask_login import (
    login_user,
    logout_user,
    current_user,
    login_required
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

# Load environment variables from .env file (if present)
load_dotenv()

# Log a warning to console if API key is missing, enabling offline mode.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY or GROQ_API_KEY.strip() in ("", "your_groq_api_key_here"):
    print(
        "\n[WARNING] GROQ_API_KEY is not configured. AI features will run in offline mode.\n"
        "  1. Copy .env.example to .env\n"
        "  2. Set your GROQ_API_KEY in .env\n"
        "  Obtain a free key at: https://console.groq.com/\n",
        file=sys.stderr,
    )

    sys.exit(1)

    client = None
else:
    client = Groq(api_key=GROQ_API_KEY)

# ---------------- IMPORT UTILS ----------------
from utils.sip import calculate_sip, calculate_goal_sip
from utils.tax import calculate_tax
from utils.pdf_parser import extract_income
from utils.money_score import calculate_money_score
from utils.multi_agent import run_multi_agent
from utils.stock import get_stock_price, get_stock_dividends
from utils.expense_track import calculate_expense, insights
from utils.validation import ValidationError, validate_string, validate_float, validate_int, validate_history
from utils.safety_engine import SafetyEngine

app = Flask(__name__)

# ============================================
# EMAIL CONFIGURATION
# ============================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_USER', 'your-email@gmail.com')

mail = Mail(app)

# ============================================
# DATABASE FUNCTIONS FOR EMAIL SETTINGS
# ============================================
def init_email_db():
    """Create email settings table if not exists"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(120) UNIQUE,
            weekly_email_enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_user_email_settings():
    """Get all users with email enabled"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT email FROM user_settings WHERE weekly_email_enabled = 1')
    users = c.fetchall()
    conn.close()
    return [user[0] for user in users]

# Initialize email database
init_email_db()

# ============================================
# WEEKLY REPORT GENERATOR
# ============================================
def generate_weekly_report(user_email):
    """Generate weekly financial report for a user"""
    return {
        'date': datetime.now().strftime('%B %d, %Y'),
        'total_spend': '₹12,450',
        'spend_change': '+5.2',
        'spend_change_class': 'positive' if 5.2 > 0 else 'negative',
        'net_worth': '₹4,28,500',
        'net_worth_change': '+2.1',
        'budget_health': '85%',
        'budget_health_class': 'positive' if 85 > 70 else 'negative',
        'budget_health_text': 'On Track ✅' if 85 > 70 else 'Over Budget ⚠️',
        'top_category': 'Food',
        'top_category_amount': '₹4,200',
        'top_categories': {
            'Food': '₹4,200',
            'Transport': '₹2,800',
            'Shopping': '₹1,900',
            'Entertainment': '₹1,500'
        },
        'ai_insight': 'You spent 40% more on dining out this week. Try cooking 2 extra meals at home to save ₹600.',
        'dashboard_url': 'http://localhost:5000/dashboard',
        'opt_out_url': 'http://localhost:5000/settings'
    }

def send_weekly_email(user_email):
    """Send weekly report email to a user"""
    try:
        report_data = generate_weekly_report(user_email)

        msg = Message(
            subject=f"📊 Weekly Financial Digest - {datetime.now().strftime('%B %d, %Y')}",
            recipients=[user_email],
            html=render_template('weekly_report.html', **report_data)
        )
        mail.send(msg)
        print(f"✅ Email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {user_email}: {e}")
        return False

def send_weekly_reports():
    """Send weekly reports to all users"""
    print("🔄 Running weekly email job...")
    users = get_user_email_settings()

    if not users:
        print("📭 No users subscribed to weekly emails")
        return

    success = 0
    for user_email in users:
        if send_weekly_email(user_email):
            success += 1

    print(f"✅ Sent {success}/{len(users)} weekly reports")

# ============================================
# RECURRING EXPENSES
# ============================================
def process_recurring_expenses():
    """Process recurring expenses and add them to expense tracker"""
    print("🔄 Processing recurring expenses...")
    today = date.today()

    try:
        from models import RecurringExpense, Expense

        # Get all active recurring expenses due today
        due_expenses = RecurringExpense.query.filter(
            RecurringExpense.is_active == True,
            RecurringExpense.next_due_date <= today
        ).all()

        if not due_expenses:
            print("📭 No recurring expenses due today")
            return

        added_count = 0
        for recurring in due_expenses:
            # Check if already added today (avoid duplicates)
            existing = Expense.query.filter(
                Expense.merchant == recurring.merchant,
                Expense.amount == recurring.amount,
                Expense.date == today,
                Expense.category == recurring.category
            ).first()

            if existing:
                continue

            # Create expense entry
            expense = Expense(
                amount=recurring.amount,
                category=recurring.category,
                merchant=recurring.merchant or 'Recurring',
                date=today
            )
            db.session.add(expense)

            # Update next due date based on frequency
            if recurring.frequency == 'daily':
                next_date = today + timedelta(days=1)
            elif recurring.frequency == 'weekly':
                next_date = today + timedelta(days=7)
            elif recurring.frequency == 'monthly':
                next_date = today + timedelta(days=30)
            elif recurring.frequency == 'quarterly':
                next_date = today + timedelta(days=90)
            elif recurring.frequency == 'yearly':
                next_date = today + timedelta(days=365)
            else:
                next_date = today + timedelta(days=30)

            recurring.next_due_date = next_date
            recurring.last_processed = today
            added_count += 1

        db.session.commit()
        print(f"✅ Added {added_count} recurring expenses")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error processing recurring expenses: {e}")

# ---------------- INIT DATABASE ----------------
from models import db, Expense, Asset, Liability, BudgetLimit, BudgetAlert, PriceAlert, PriceAlertEvent, FinancialGoal, RecurringExpense, Portfolio

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///money_mentor.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "dev-secret-key"
)
from flask_login import LoginManager

login_manager = LoginManager()
login_manager.init_app(app)
db.init_app(app)

from models import User

with app.app_context():
    db.create_all()

# ---------------- INIT SAFETY ENGINE ----------------
safety_engine = SafetyEngine()

# ---------------- INIT GROQ ----------------
# client is initialized in the startup validation block above

# ── Dev-mode startup message ─────────────────────────────────
if os.getenv("FLASK_ENV", "development") != "production":
    if client:
        print("[OK] Groq client initialised successfully.")
    else:
        print("[WARNING] Groq client is running in offline mode.")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ============================================
# SCHEDULER - Runs weekly email and recurring expenses
# ============================================
scheduler = BackgroundScheduler()

# Weekly email job - Every Monday at 9:00 AM
scheduler.add_job(
    func=send_weekly_reports,
    trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
    id='weekly_email_job',
    replace_existing=True
)

# Recurring expenses job - Every day at 9:00 AM
scheduler.add_job(
    func=process_recurring_expenses,
    trigger=CronTrigger(hour=9, minute=0),
    id='recurring_expense_job',
    replace_existing=True
)

scheduler.start()

# Shutdown scheduler on app exit
atexit.register(lambda: scheduler.shutdown())

# ============================================
# ROUTES
# ============================================

# ---------------- HOME ----------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if not username or not password or not email:
        return jsonify({"error": "Username, email, and password are required."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 400

    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"status": "success"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if not username or not password or not email:
        return jsonify({"error": "Username, email, and password are required."}), 400

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({"status": "success"})
    return jsonify({"error": "Invalid username or password."}), 401

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "success"})

@app.route("/")
def home():
    return render_template("dashboard.html", active_page="dashboard")

@app.route("/stock", methods=["GET"])
def stock():
    return render_template("stock.html", active_page="stock")

@app.route("/pdf-parser", methods=["GET"])
def pdf_parser():
    return render_template("pdf.html", active_page="pdf")

@app.route("/agent-page", methods=["GET"])
def agent_page():
    return render_template("agent.html", active_page="agent")

@app.route("/expense", methods=["GET"])
def expense():
    return render_template("expense.html", active_page="expense")

@app.route("/networth", methods=["GET"])
def networth():
    return render_template("networth.html", active_page="networth")

@app.route("/budget", methods=["GET"])
def budget():
    return render_template("budget.html", active_page="budget")

# ---------------- RETIREMENT ----------------
@app.route('/retirement')
def retirement():
    """Retirement & Inflation Simulator Page"""
    return render_template('retirement.html')

# ---------------- SETTINGS ----------------
@app.route('/settings')
def settings():
    """User settings page"""
    return render_template('settings.html')

@app.route('/api/update-email', methods=['POST'])
def update_email():
    """Update user email settings"""
    data = request.json
    email = data.get('email')
    enabled = data.get('enabled', True)

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
        INSERT OR REPLACE INTO user_settings (email, weekly_email_enabled)
        VALUES (?, ?)
    ''', (email, 1 if enabled else 0))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Settings updated successfully'})

@app.route('/api/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe from weekly emails"""
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE user_settings SET weekly_email_enabled = 0 WHERE email = ?', (email,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Unsubscribed successfully'})

# ---------------- TEST EMAIL ROUTES ----------------
@app.route('/test-email')
def test_email():
    """Send a test email to verify configuration"""
    email = os.getenv('EMAIL_USER', 'your-email@gmail.com')
    send_weekly_email(email)
    return "Test email sent! Check your inbox."

@app.route('/force-weekly')
def force_weekly():
    """Force send weekly reports (for testing)"""
    send_weekly_reports()
    return "Weekly reports sent manually!"

# ---------------- RECURRING EXPENSES ROUTES ----------------
@app.route('/recurring')
def recurring_page():
    """Recurring Expenses Management Page"""
    return render_template('recurring.html')

@app.route('/api/recurring/detect', methods=['GET'])
def detect_recurring_expenses():
    """Auto-detect recurring expense patterns from last 60 days"""
    try:
        cutoff_date = date.today() - timedelta(days=60)
        expenses = Expense.query.filter(
            Expense.date >= cutoff_date
        ).order_by(Expense.date.desc()).all()

        if not expenses:
            return jsonify({
                'success': True,
                'detected': [],
                'message': 'No expenses found in last 60 days'
            })

        # Group by merchant and category
        patterns = {}
        for exp in expenses:
            key = f"{exp.merchant or 'Unknown'}_{exp.category}"
            if key not in patterns:
                patterns[key] = {
                    'merchant': exp.merchant or 'Unknown',
                    'category': exp.category,
                    'amounts': [],
                    'dates': []
                }
            patterns[key]['amounts'].append(exp.amount)
            patterns[key]['dates'].append(exp.date)

        # Analyze patterns
        detected = []
        for key, data in patterns.items():
            if len(data['amounts']) >= 2:
                avg_amount = sum(data['amounts']) / len(data['amounts'])
                variation = max([abs(a - avg_amount) / avg_amount for a in data['amounts']])

                if variation <= 0.10:
                    sorted_dates = sorted(data['dates'])
                    if len(sorted_dates) >= 2:
                        day_diffs = []
                        for i in range(1, len(sorted_dates)):
                            diff = (sorted_dates[i] - sorted_dates[i-1]).days
                            day_diffs.append(diff)

                        avg_diff = sum(day_diffs) / len(day_diffs)

                        frequency = None
                        if 28 <= avg_diff <= 31:
                            frequency = 'monthly'
                        elif 7 <= avg_diff <= 8:
                            frequency = 'weekly'
                        elif 85 <= avg_diff <= 95:
                            frequency = 'quarterly'
                        elif 355 <= avg_diff <= 370:
                            frequency = 'yearly'

                        if frequency:
                            detected.append({
                                'merchant': data['merchant'],
                                'category': data['category'],
                                'amount': round(avg_amount, 2),
                                'frequency': frequency,
                                'next_due': (sorted_dates[-1] + timedelta(days=round(avg_diff))).isoformat(),
                                'confidence': 'high' if len(data['amounts']) >= 3 else 'medium'
                            })

        return jsonify({
            'success': True,
            'detected': detected,
            'count': len(detected)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/add', methods=['POST'])
def add_recurring_expense():
    """Add a recurring expense manually or from detection"""
    try:
        data = request.json

        required = ['amount', 'category', 'frequency', 'start_date', 'next_due_date']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

        recurring = RecurringExpense(
            amount=float(data['amount']),
            category=data['category'],
            merchant=data.get('merchant', ''),
            frequency=data['frequency'],
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            next_due_date=datetime.strptime(data['next_due_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            auto_add=data.get('auto_add', True),
            is_active=True
        )

        db.session.add(recurring)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Recurring expense added successfully',
            'id': recurring.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/list', methods=['GET'])
def get_recurring_expenses():
    """Get all active recurring expenses"""
    try:
        recurring = RecurringExpense.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'recurring': [r.to_dict() for r in recurring]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/delete/<int:id>', methods=['DELETE'])
def delete_recurring_expense(id):
    """Delete a recurring expense"""
    try:
        recurring = RecurringExpense.query.get(id)
        if not recurring:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        db.session.delete(recurring)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/toggle/<int:id>', methods=['POST'])
def toggle_recurring_expense(id):
    """Toggle active status of recurring expense"""
    try:
        recurring = RecurringExpense.query.get(id)
        if not recurring:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        recurring.is_active = not recurring.is_active
        db.session.commit()

        return jsonify({
            'success': True,
            'is_active': recurring.is_active,
            'message': 'Status updated'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/process-now', methods=['POST'])
def process_recurring_now():
    """Manually trigger recurring expense processing (for testing)"""
    process_recurring_expenses()
    return jsonify({'success': True, 'message': 'Recurring expenses processed'})

# ---------------- HEALTH CHECK ----------------
@app.route("/health", methods=["GET"])
def health_check():
    """Lightweight liveness probe for deployment environments."""
    return jsonify({"status": "ok", "service": "AI Money Mentor"}), 200

@app.route("/dashboard-data")
@login_required
def dashboard_data():
    """API endpoint to fetch all data needed for populating the dashboard in one call."""
    try:
        net_worth = sum(a.amount for a in Asset.query.filter_by(user_id=current_user.id).all()) - sum(l.amount for l in Liability.query.filter_by(user_id=current_user.id).all())
        monthly_expenses = [e.to_dict() for e in Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id.desc()).limit(10).all()]
        budget_alert_count = len([b for b in BudgetAlert.query.filter_by(user_id=current_user.id).all()])
        goal_count = len([g for g in FinancialGoal.query.filter_by(user_id=current_user.id).all()])
        portfolio_items = Portfolio.query.filter_by(user_id=current_user.id).all()

        allocation = {}

        for item in portfolio_items:
            value = item.quantity * item.buy_price

            allocation[item.investment_type] = (
                allocation.get(item.investment_type, 0) + value
            )

        total = sum(allocation.values())

        allocation_percentages = {
            k: round(v * 100 / total, 2)
            for k, v in allocation.items()
        } if total > 0 else {}

        return jsonify({
            "net_worth": net_worth,
            "monthly_expenses": monthly_expenses,
            "budget_alert_count": budget_alert_count,
            "goal_count": goal_count,
            "portfolio_allocation": allocation_percentages,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/dashboard/recent-activity")
@login_required
def recent_activity():
    activities = []

    # Latest expenses
    expenses = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.id.desc())
        .limit(5)
        .all()
    )

    for e in expenses:
        activities.append({
            "type": "expense",
            "message": f"Added expense: {e.category} ₹{e.amount}",
            "date": e.date
        })

    # Latest assets
    assets = (
        Asset.query
        .filter_by(user_id=current_user.id)
        .order_by(Asset.id.desc())
        .limit(5)
        .all()
    )

    for a in assets:
        activities.append({
            "type": "asset",
            "message": f"Added asset: {a.name} ₹{a.amount}",
            "date": a.date
        })

    # Latest goals
    goals = (
        FinancialGoal.query
        .filter_by(user_id=current_user.id)
        .order_by(FinancialGoal.created_at.desc())
        .limit(5)
        .all()
    )

    for g in goals:
        activities.append({
            "type": "goal",
            "message": f"Created goal: {g.name}",
            "date": g.created_at.isoformat()
        })

    activities = sorted(
        activities,
        key=lambda x: x["date"],
        reverse=True
    )

    return jsonify(activities[:10])

# ---------------- AI STATUS ----------------
@app.route("/api/status", methods=["GET"])
def ai_status():
    """Reports whether the Groq AI client is available."""
    if client is not None:
        return jsonify({
            "ai_online": True,
            "message": "AI Money Mentor is online and ready."
        })
    return jsonify({
        "ai_online": False,
        "message": "AI features are unavailable — GROQ_API_KEY is not configured."
    })

# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({
        "error": "Bad Request",
        "message": str(error),
        "status_code": 400
    }), 400

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad Request",
        "message": str(error),
        "status_code": 400
    }), 400

@app.errorhandler(404)
def not_found(error):
    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
        return render_template("404.html", active_page=None), 404
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist.",
        "status_code": 404
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method Not Allowed",
        "message": str(error),
        "status_code": 405
    }), 405

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please try again later.",
        "status_code": 500
    }), 500

# ---------------- 🤖 AI CHAT WITH SAFETY ENGINE ----------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        msg = data.get("message")
        history = data.get("history", [])

        # Get user context from database
        user_context = {}
        if current_user.is_authenticated:
            # Fetch user's financial data
            expenses = Expense.query.filter_by(user_id=current_user.id).all()
            assets = Asset.query.filter_by(user_id=current_user.id).all()

            user_context = {
                'income': 80000,  # TODO: Fetch from user profile
                'expenses': sum(e.amount for e in expenses) if expenses else 0,
                'savings': sum(a.amount for a in assets) if assets else 0,
                'investments': 500000,
                'debt': 100000,
                'emergency': 240000
            }

        # Stronger system prompt to prevent hallucinations
        system_prompt = """You are a professional financial advisor for Indian users.

CRITICAL RULES - YOU MUST FOLLOW:
1. NEVER invent numbers, amounts, or financial data about the user.
2. If you don't know the user's income, savings, or expenses, ASK for that information.
3. If the user asks for advice without providing data, give general methodology only.
4. Always be honest about what you don't know.
5. Provide practical, actionable advice based ONLY on information the user has shared.

Be friendly, supportive, and encouraging."""

        messages = [{"role": "system", "content": system_prompt}]

        if history:
            messages += history[-10:]
        messages.append({"role": "user", "content": msg})

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        reply = res.choices[0].message.content

        # Process through safety engine
        safety_result = safety_engine.process_response(reply, user_context)

        return jsonify({
            "reply": safety_result['safe_response'],
            "safety": {
                "passed": safety_result['passed'],
                "confidence_score": safety_result['confidence_score'],
                "confidence_level": safety_result['confidence_level'],
                "violations": safety_result['violations'],
                "warnings": safety_result['warnings']
            }
        })

    except Exception as e:
        app.logger.error(f"Chat error: {e}")
        return jsonify({
            "reply": "⚠️ I'm having trouble connecting. Please try again in a moment."
        }), 500

# ---------------- 💸 SIP ----------------
@app.route("/sip", methods=["GET", "POST"])
def sip():
    if request.method == "GET":
        return render_template("sip.html", active_page="sip")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        monthly = validate_float(data.get("monthly"), "monthly", min_val=0.0)
        rate = validate_float(data.get("rate"), "rate", min_val=0.0)
        years = validate_int(data.get("years"), "years", min_val=1)
        inflation = validate_float(data.get("inflation", 0.0), "inflation", min_val=0.0)

        result = calculate_sip(monthly, rate, years, inflation)
        return jsonify({
            "future_value": result["nominal_value"],
            "nominal_value": result["nominal_value"],
            "inflation_adjusted_value": result["inflation_adjusted_value"],
            "inflation_applied": result["inflation_applied"]
        })

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- 🎯 GOAL-BASED SAVINGS PLANNER ----------------
@app.route("/goal-planner", methods=["GET", "POST"])
def goal_planner():
    if request.method == "GET":
        return render_template("goal_planner.html", active_page="goal_planner")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        goal = validate_float(data.get("goal"), "goal", min_val=0.01)
        rate = validate_float(data.get("rate"), "rate", min_val=0.0)
        years = validate_int(data.get("years"), "years", min_val=1)

        result = calculate_goal_sip(goal, rate, years)
        return jsonify(result)

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- 📊 STOCK ----------------
@app.route("/portfolio", methods=["POST"])
def portfolio():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        stock = validate_string(data.get("stock"), "stock").upper()
        result = get_stock_price(stock)
        if "error" in result:
            raise ValidationError(result["error"])
        return jsonify(result)

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/alerts", methods=["GET"])
@login_required
def get_alerts():
    try:
        alerts = PriceAlert.query.filter_by(user_id=current_user.id).all()
        return jsonify([a.to_dict() for a in alerts])
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/alerts", methods=["POST"])
@login_required
def create_alert():
    try:
        data = request.json
        if not data or "symbol" not in data or "target_price" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        symbol = data["symbol"].strip().upper()
        target_price = float(data["target_price"])
        condition = data.get("condition", "above").strip().lower()

        if condition not in ("above", "below"):
            return jsonify({"error": "Invalid condition value"}), 400

        alert = PriceAlert(symbol=symbol, target_price=target_price, condition=condition, user_id=current_user.id)
        db.session.add(alert)
        db.session.commit()
        return jsonify(alert.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/alerts/history", methods=["GET"])
@login_required
def alerts_history():
    try:
        user_alert_ids = [a.id for a in PriceAlert.query.filter_by(user_id=current_user.id).all()]
        limit = request.args.get("limit", default=10, type=int)
        if limit < 1:
            limit = 10
        if limit > 100:
            limit = 100

        events = PriceAlertEvent.query.filter(PriceAlertEvent.alert_id.in_(user_alert_ids)).order_by(PriceAlertEvent.triggered_at.desc()).limit(limit).all()
        return jsonify([e.to_dict() for e in events])
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/alerts/reset", methods=["POST"])
@login_required
def alerts_reset():
    try:
        PriceAlert.query.filter_by(user_id=current_user.id).update({"is_triggered": False, "last_triggered_at": None, "last_check_error": None})
        user_alert_ids = [a.id for a in PriceAlert.query.filter_by(user_id=current_user.id).all()]
        if user_alert_ids:
            PriceAlertEvent.query.filter(PriceAlertEvent.alert_id.in_(user_alert_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
@login_required
def delete_alert(alert_id):
    try:
        alert = PriceAlert.query.filter_by(id=alert_id, user_id=current_user.id).first()
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        db.session.delete(alert)
        db.session.commit()
        return jsonify({"status": "success", "message": "Alert deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- 💸 TAX ----------------
@app.route("/tax", methods=["GET", "POST"])
def tax():
    if request.method == "GET":
        return render_template("tax.html", active_page="tax")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        income = validate_float(data.get("income"), "income", min_val=0.0)
        deduction_80c = validate_float(data.get("deduction_80c", 0.0), "deduction_80c", min_val=0.0)
        deduction_80d = validate_float(data.get("deduction_80d", 0.0), "deduction_80d", min_val=0.0)
        deduction_hra = validate_float(data.get("deduction_hra", 0.0), "deduction_hra", min_val=0.0)

        hra_inputs = data.get("hra_inputs")
        if hra_inputs is not None:
            if not isinstance(hra_inputs, dict):
                raise ValidationError("'hra_inputs' must be a dictionary")
            hra_inputs = {
                "basic_salary": validate_float(hra_inputs.get("basic_salary", 0.0), "hra_inputs.basic_salary", min_val=0.0),
                "rent_paid": validate_float(hra_inputs.get("rent_paid", 0.0), "hra_inputs.rent_paid", min_val=0.0),
                "hra_received": validate_float(hra_inputs.get("hra_received", 0.0), "hra_inputs.hra_received", min_val=0.0),
                "is_metro": bool(hra_inputs.get("is_metro", False))
            }

        tax_details = calculate_tax(income, deduction_80c=deduction_80c, deduction_80d=deduction_80d, deduction_hra=deduction_hra, hra_inputs=hra_inputs)

        recommendations = "You are already in the zero-tax bracket! No additional tax-saving investments are required."

        recommended_regime = tax_details.get("recommended", "New Regime")
        regime_key = "new_regime" if recommended_regime == "New Regime" else "old_regime"
        total_tax = tax_details.get(regime_key, {}).get("total_tax", 0.0)

        if total_tax > 0.0 and client:
            prompt = f"A user in India has a gross annual income of ₹{income:,} and has a total tax liability of ₹{total_tax:,} under the recommended {recommended_regime}.\n\nGenerate a customized list of tax-saving investment recommendations for them. Suggest specific options under Section 80C (up to 1.5L, e.g. ELSS, PPF), Section 80CCD(1B) (up to 50k in NPS), and Section 80D (Health Insurance). Be brief and format the response as a bulleted list with clear estimated tax savings."

            try:
                ai_res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a professional Indian tax consultant. Give brief, actionable advice."},
                        {"role": "user", "content": prompt}
                    ]
                )
                recommendations = ai_res.choices[0].message.content.strip()
            except Exception as ai_err:
                app.logger.error(f"Tax AI Recommendation Error: {str(ai_err)}")
                recommendations = "AI Tax recommendations are currently unavailable. Consider investing in ELSS or NPS to reduce your tax."
        elif total_tax > 0.0:
            recommendations = "AI Tax recommendations are currently offline (no GROQ_API_KEY configured). Consider investing in ELSS or NPS to reduce your tax."

        tax_details["ai_recommendations"] = recommendations
        return jsonify({"tax": tax_details})

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/tax/simulate", methods=["POST"])
def tax_simulate():
    try:
        from utils.tax import simulate_tax_scenarios

        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        income = validate_float(data.get("income"), "income", min_val=0.0)

        scenario_a = data.get("scenario_a") or {}
        scenario_b = data.get("scenario_b") or {}

        if not isinstance(scenario_a, dict) or not isinstance(scenario_b, dict):
            raise ValidationError("'scenario_a' and 'scenario_b' must be objects")

        scenario_a_d80c = validate_float(scenario_a.get("deduction_80c", 0.0), "scenario_a.deduction_80c", min_val=0.0)
        scenario_a_d80d = validate_float(scenario_a.get("deduction_80d", 0.0), "scenario_a.deduction_80d", min_val=0.0)
        scenario_a_hra = validate_float(scenario_a.get("deduction_hra", 0.0), "scenario_a.deduction_hra", min_val=0.0)

        scenario_b_d80c = validate_float(scenario_b.get("deduction_80c", 0.0), "scenario_b.deduction_80c", min_val=0.0)
        scenario_b_d80d = validate_float(scenario_b.get("deduction_80d", 0.0), "scenario_b.deduction_80d", min_val=0.0)
        scenario_b_hra = validate_float(scenario_b.get("deduction_hra", 0.0), "scenario_b.deduction_hra", min_val=0.0)

        def validate_hra_inputs(sc_data, sc_name):
            hra_inputs = sc_data.get("hra_inputs")
            if hra_inputs is None:
                return None
            if not isinstance(hra_inputs, dict):
                raise ValidationError(f"'{sc_name}.hra_inputs' must be a dictionary")
            return {
                "basic_salary": validate_float(hra_inputs.get("basic_salary", 0.0), f"{sc_name}.hra_inputs.basic_salary", min_val=0.0),
                "rent_paid": validate_float(hra_inputs.get("rent_paid", 0.0), f"{sc_name}.hra_inputs.rent_paid", min_val=0.0),
                "hra_received": validate_float(hra_inputs.get("hra_received", 0.0), f"{sc_name}.hra_inputs.hra_received", min_val=0.0),
                "is_metro": bool(hra_inputs.get("is_metro", False))
            }

        scenario_a_hra_inputs = validate_hra_inputs(scenario_a, "scenario_a")
        scenario_b_hra_inputs = validate_hra_inputs(scenario_b, "scenario_b")

        result = simulate_tax_scenarios(income, scenario_a={"deduction_80c": scenario_a_d80c, "deduction_80d": scenario_a_d80d, "deduction_hra": scenario_a_hra, "hra_inputs": scenario_a_hra_inputs}, scenario_b={"deduction_80c": scenario_b_d80c, "deduction_80d": scenario_b_d80d, "deduction_hra": scenario_b_hra, "hra_inputs": scenario_b_hra_inputs})

        # Deterministic explanation always available
        best_regime_a = result["comparison"]["best_regime"]["scenario_a"]
        best_regime_b = result["comparison"]["best_regime"]["scenario_b"]
        switch_savings_new = float(result["comparison"]["switch"]["new_regime"]["savings"])
        switch_savings_old = float(result["comparison"]["switch"]["old_regime"]["savings"])

        if switch_savings_new >= switch_savings_old and switch_savings_new > 0:
            regime_for_explanation = "New Regime"
        elif switch_savings_old > 0:
            regime_for_explanation = "Old Regime"
        else:
            regime_for_explanation = result["comparison"]["best_scenario_by_savings_under_recommended_regime"]

        scenario_b_best = best_regime_b
        lever_ranking = result["sensitivity"]["scenario_b"]["lever_ranking_for_best_regime"]

        deterministic_explanation = f"Regime outcome: Scenario A is better under {best_regime_a}, while Scenario B is better under {best_regime_b}. Under {scenario_b_best}, the biggest tax lever tends to be: {lever_ranking[0]['lever']} (≈ {abs(lever_ranking[0]['delta_per_1']):.2f} tax change per ₹1). "

        if client:
            prompt = f"User wants to compare tax scenarios in India.\n\nIncome: ₹{result['income']:.0f}\n\nScenario A recommended regime: {best_regime_a}\nScenario B recommended regime: {best_regime_b}\n\nSwitching A -> B savings:\n- New regime savings: ₹{switch_savings_new:.2f}\n- Old regime savings: ₹{switch_savings_old:.2f}\n\nSensitivity (Scenario B, per ₹1 increase):\n{lever_ranking}\n\nExplain in simple terms why the winning regime is likely to be {best_regime_b} and which levers (80C/80D/HRA) give the biggest savings. Use bullet points and keep it under 8 lines."
            try:
                ai_res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a professional Indian tax consultant. Provide concise, actionable insights."},
                        {"role": "user", "content": prompt},
                    ],
                )
                explanation = ai_res.choices[0].message.content.strip()
            except Exception as ai_err:
                app.logger.error(f"Tax simulate AI error: {str(ai_err)}")
                explanation = deterministic_explanation
        else:
            explanation = deterministic_explanation

        result["explanation"] = explanation
        result["ai_available"] = client is not None

        return jsonify({"result": result})

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- 📄 PDF ----------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files["file"]
        result = extract_income(file)
        return jsonify({"data": result})

    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------- 🧠 MULTI AGENT ----------------
@app.route("/agent", methods=["POST"])
def run_agent_route():
    if not client:
        return jsonify({"error": "AI Agent is offline: GROQ_API_KEY is not configured on the server."})
    try:
        if client is None:
            return jsonify({"error": "AI Multi-Agent is offline because GROQ_API_KEY is not configured."})
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        query = validate_string(data.get("query"), "query")
        response = run_multi_agent(client, query)
        return jsonify({"response": response})

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- 💰 MONEY SCORE ----------------
@app.route("/money-score", methods=["GET", "POST"])
def money_score():
    if request.method == "GET":
        return render_template("score.html", active_page="score")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        income = validate_float(data.get("income"), "income", min_val=0.0)
        expenses = validate_float(data.get("expenses"), "expenses", min_val=0.0)
        savings = validate_float(data.get("savings"), "savings", min_val=0.0)
        investments = validate_float(data.get("investments"), "investments", min_val=0.0)
        debt = validate_float(data.get("debt"), "debt", min_val=0.0)
        emergency = validate_float(data.get("emergency"), "emergency", min_val=0.0)

        score = calculate_money_score(income, expenses, savings, investments, debt, emergency)

        if score >= 80:
            status = "Excellent 💚"
        elif score >= 60:
            status = "Good 👍"
        elif score >= 40:
            status = "Average ⚠️"
        else:
            status = "Needs Improvement ❌"

        return jsonify({
            "score": score,
            "status": status
        })

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------- CREDIT HEALTH FEEDBACK ----------------
@app.route("/credit-feedback", methods=["POST"])
def credit_feedback():

    try:
        data = request.json or {}

        score = data.get("score", 0)
        dti = data.get("dti", 0)
        utilization = data.get("utilization", 0)
        payment = data.get("payment", 0)

        advice = []

        if utilization > 30:
            advice.append(
                "Reduce credit utilization below 30%."
            )

        if dti > 40:
            advice.append(
                "Lower your debt-to-income ratio."
            )

        if payment < 90:
            advice.append(
                "Maintain timely payments to improve credit history."
            )

        if score >= 750:
            advice.append(
                "Excellent credit profile. Maintain your habits."
            )

        if not advice:
            advice.append(
                "Keep monitoring your credit health regularly."
            )

        return jsonify({
            "message": " ".join(advice)
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 400


# ---------------- EXPORT FINANCIAL REPORT ----------------
EXPORT_FIELDS = ["income", "expenses", "savings", "investments", "debt", "emergency", "tax", "money_score", "sip_projection"]
EXPORT_FIELD_LABELS = {"income": "Income", "expenses": "Expenses", "savings": "Savings", "investments": "Investments", "debt": "Debt", "emergency": "Emergency Fund", "tax": "Tax Estimate", "money_score": "Money Score", "sip_projection": "SIP Projection"}

def _pdf_safe(value):
    return str(value).replace("₹", "Rs. ").encode("latin-1", "ignore").decode("latin-1")

@app.route("/export/csv", methods=["POST"])
def export_csv():
    try:
        data = request.json or {}
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerow({field: data.get(field, "N/A") for field in EXPORT_FIELDS})

        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=financial_report.csv"
        response.headers["Content-Type"] = "text/csv"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/export/pdf", methods=["POST"])
def export_pdf():
    try:
        data = request.json or {}

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "AI Money Mentor - Financial Report", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        pdf.set_font("Helvetica", size=12)
        for key in EXPORT_FIELDS:
            value = _pdf_safe(data.get(key, "N/A"))
            pdf.cell(0, 10, f"{EXPORT_FIELD_LABELS[key]}: {value}", new_x="LMARGIN", new_y="NEXT")

        pdf_bytes = bytes(pdf.output())
        response = make_response(pdf_bytes)
        response.headers["Content-Disposition"] = "attachment; filename=financial_report.pdf"
        response.headers["Content-Type"] = "application/pdf"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- EXPENSE TRACKER ----------------
@app.route("/add_expense", methods=["POST"])
@login_required
def add_expense():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        category = validate_string(data.get("category"), "category")
        amount = validate_float(data.get("amount"), "amount", min_val=0.01)
        date = validate_string(data.get("date"), "date")

        expense = Expense(
            category=category,
            amount=amount,
            date=date,
            merchant=data.get("merchant", ""),
            user_id=current_user.id
        )

        db.session.add(expense)
        db.session.commit()

        ym = expense.date[:7] if len(expense.date) >= 7 else None
        run_threshold_checks(expense.user_id, expense.category, ym)

        return jsonify({"status": "success"})

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/expense/<int:expense_id>", methods=["PUT", "DELETE"])
@login_required
def expense_detail(expense_id):
    try:
        expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
        if not expense:
            return jsonify({"error": f"Expense with id {expense_id} not found."}), 404

        if request.method == "DELETE":
            category = expense.category
            ym = expense.date[:7] if len(expense.date) >= 7 else None

            db.session.delete(expense)
            db.session.commit()

            if ym:
                run_threshold_checks(expense.user_id, category, ym)

            return jsonify({"status": "success"})
        else:  # PUT
            data = request.json or {}
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")

            if "category" in data:
                new_cat = validate_string(data["category"], "category")
                if new_cat != expense.category:
                    expense.user_corrected = True
                    if not expense.original_ai_category:
                        expense.original_ai_category = expense.category
                    expense.category = new_cat
            if "amount" in data:
                expense.amount = validate_float(data["amount"], "amount", min_val=0.01)
            if "date" in data:
                expense.date = validate_string(data["date"], "date")

            db.session.commit()

            ym = expense.date[:7] if len(expense.date) >= 7 else None
            if ym:
                run_threshold_checks(expense.user_id, expense.category, ym)

            return jsonify({"status": "success", "expense": expense.to_dict()})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/calculate", methods=["GET"])
@login_required
def calculate():
    expense_data = [e.to_dict() for e in Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id).all()]
    result = calculate_expense(expense_data)
    result["expenses"] = expense_data
    return jsonify(result)

@app.route("/insights", methods=["GET"])
@login_required
def expense_insights():
    expense_data = [e.to_dict() for e in Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id).all()]
    if not client:
        totals = calculate_expense(expense_data)
        return jsonify({
            "insights": "<div class=\"insight-card\"><h3>AI Insights Offline</h3><p>Personalized AI savings suggestions are currently offline because the GROQ_API_KEY is not configured on the server.</p></div>",
            "summary": totals
        })

    result = insights(client, expense_data)
    return jsonify(result)

# ---------------- NET WORTH TRACKER ----------------
@app.route("/net-worth", methods=["GET", "POST"])
@login_required
def get_net_worth():
    assets = Asset.query.filter_by(user_id=current_user.id).order_by(Asset.id).all()
    liabilities = Liability.query.filter_by(user_id=current_user.id).order_by(Liability.id).all()
    assets_data = [a.to_dict() for a in assets]
    liabilities_data = [l.to_dict() for l in liabilities]
    total_assets = sum(item['amount'] for item in assets_data)
    total_liabilities = sum(item['amount'] for item in liabilities_data)
    return jsonify({
        "assets": assets_data,
        "liabilities": liabilities_data,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": total_assets - total_liabilities
    })

@app.route("/add-asset", methods=["POST"])
@login_required
def add_asset():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        name = validate_string(data.get("name"), "name")
        amount = validate_float(data.get("amount"), "amount", min_val=0.0)
        date = data.get("date")
        if date:
            date = validate_string(date, "date")

        asset = Asset(name=name, amount=amount, user_id=current_user.id)
        if date:
            asset.date = date
        db.session.add(asset)
        db.session.commit()
        return jsonify({"status": "success"})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/add-liability", methods=["POST"])
@login_required
def add_liability():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        name = validate_string(data.get("name"), "name")
        amount = validate_float(data.get("amount"), "amount", min_val=0.0)
        date = data.get("date")
        if date:
            date = validate_string(date, "date")

        liability = Liability(name=name, amount=amount, user_id=current_user.id)
        if date:
            liability.date = date
        db.session.add(liability)
        db.session.commit()
        return jsonify({"status": "success"})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/delete-item", methods=["POST", "DELETE"])
@login_required
def delete_item():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        item_type = validate_string(data.get("type"), "type")
        if item_type not in ('asset', 'liability'):
            raise ValidationError("'type' must be either 'asset' or 'liability'")
        item_db_id = validate_int(data.get("id"), "id", min_val=1)

        if item_type == "asset":
            item = Asset.query.filter_by(id=item_db_id, user_id=current_user.id).first()
        else:
            item = Liability.query.filter_by(id=item_db_id, user_id=current_user.id).first()

        if not item:
            return jsonify({"error": f"Item not found (type={item_type}, id={item_db_id})"}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({"status": "success"})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- VOICE EXPENSE PARSER ----------------
@app.route('/api/parse-expense-text', methods=['POST'])
def parse_expense_text():
    """Parse spoken text to extract amount, category, and merchant"""
    try:
        data = request.json
        text = data.get('text', '').strip()

        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400

        prompt = f"""
        You are a financial data extractor. Extract the following details from this spoken text:
        "{text}"

        Return ONLY valid JSON in this exact format:
        {{
            "amount": number or null,
            "category": string or null,
            "merchant": string or null
        }}

        Categories must be one of: Food, Rent, Travel, Shopping, Utilities, Entertainment, Healthcare, Other.

        Examples:
        - "Uber ride to airport 450 rupees" → {{"amount": 450, "category": "Travel", "merchant": "Uber"}}
        - "Bought groceries for 1200 at Big Basket" → {{"amount": 1200, "category": "Food", "merchant": "Big Basket"}}
        - "Paid electricity bill 800 rupees" → {{"amount": 800, "category": "Utilities", "merchant": null}}
        """

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a financial data extractor. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=100
        )

        result_text = response.choices[0].message.content.strip()

        import json
        try:
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = result_text[start:end]
                parsed = json.loads(json_str)

                result = {
                    'success': True,
                    'amount': parsed.get('amount'),
                    'category': parsed.get('category'),
                    'merchant': parsed.get('merchant')
                }

                valid_categories = ['Food', 'Rent', 'Travel', 'Shopping', 'Utilities', 'Entertainment', 'Healthcare', 'Other']
                if result['category'] and result['category'] not in valid_categories:
                    result['category'] = 'Other'

                return jsonify(result)
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            print(f"JSON parse error: {e}")
            return jsonify({'success': False, 'error': 'Failed to parse AI response'}), 500

    except Exception as e:
        print(f"Voice parse error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------------- RECURRING EXPENSES HELPER ----------------
def _validate_frequency(freq: str):
    freq = (freq or "").strip().lower()
    if freq not in ("monthly", "weekly", "yearly"):
        raise ValidationError("frequency must be one of: monthly, weekly, yearly")
    return freq

def _get_period_key(frequency: str, d):
    if frequency == "monthly":
        return d.strftime("%Y-%m")
    if frequency == "weekly":
        iso_year, iso_week, _ = d.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    return d.strftime("%Y")

@app.route("/recurring-expense", methods=["POST"])
@login_required
def create_recurring_expense():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        category = validate_string(data.get("category"), "category")
        amount = validate_float(data.get("amount"), "amount", min_val=0.01)
        start_date = validate_string(data.get("start_date"), "start_date")
        frequency = _validate_frequency(data.get("frequency"))

        active = data.get("active", True)
        if not isinstance(active, bool):
            raise ValidationError("active must be a boolean")

        end_date = data.get("end_date", None)
        if end_date is not None:
            end_date = validate_string(end_date, "end_date")

        import datetime
        try:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        except Exception:
            raise ValidationError("start_date must be in YYYY-MM-DD format")

        if end_date:
            try:
                end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            except Exception:
                raise ValidationError("end_date must be in YYYY-MM-DD format")
            if end_dt < start_dt:
                raise ValidationError("end_date cannot be before start_date")

        rexp = RecurringExpense(
            user_id=current_user.id,
            category=category,
            amount=amount,
            start_date=start_date,
            frequency=frequency,
            active=active,
            end_date=end_date,
        )
        db.session.add(rexp)
        db.session.commit()
        return jsonify(rexp.to_dict()), 201

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/recurring-expense", methods=["GET"])
@login_required
def list_recurring_expenses():
    try:
        items = RecurringExpense.query.filter_by(user_id=current_user.id).order_by(RecurringExpense.id.desc()).all()
        return jsonify([i.to_dict() for i in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/recurring-expense/<int:recurring_id>", methods=["DELETE"])
@login_required
def disable_recurring_expense(recurring_id):
    try:
        item = RecurringExpense.query.filter_by(id=recurring_id, user_id=current_user.id).first()
        if not item:
            return jsonify({"error": "Recurring expense not found"}), 404
        if item.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        item.active = False
        db.session.commit()
        return jsonify({"status": "success", "id": recurring_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- BUDGET THRESHOLD CHECKS ----------------
def run_threshold_checks(user_id, category, year_month=None):
    if not year_month:
        import datetime
        year_month = datetime.datetime.now().strftime("%Y-%m")

    limit = BudgetLimit.query.filter_by(user_id=user_id, category=category).first()
    if not limit or limit.limit_amount <= 0:
        return []

    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.category == category,
        Expense.date.like(f"{year_month}%")
    ).all()

    total_spent = sum(e.amount for e in expenses)
    pct = total_spent / limit.limit_amount

    triggered = []
    for threshold in [100, 90, 80]:
        target = threshold / 100.0
        if pct >= target:
            exists = BudgetAlert.query.filter_by(
                user_id=user_id,
                category=category,
                year_month=year_month,
                threshold=threshold
            ).first()
            if not exists:
                alert = BudgetAlert(
                    category=category,
                    year_month=year_month,
                    threshold=threshold,
                    user_id=user_id
                )
                db.session.add(alert)
                triggered.append(threshold)
                print(f"\n[EMAIL ALERT] Budget Alert: {category} spending reached {threshold}%\n", file=sys.stderr)
    if triggered:
        db.session.commit()
    return triggered

# ---------------- SMART BUDGET ALERTS ----------------
@app.route("/budget/limits", methods=["GET", "POST"])
@login_required
def budget_limits():
    if request.method == "POST":
        try:
            data = request.json or {}
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")
            category = validate_string(data.get("category"), "category")
            limit_amount = validate_float(data.get("limit_amount"), "limit_amount", min_val=0.0)

            limit = BudgetLimit.query.filter_by(user_id=current_user.id, category=category).first()
            if limit:
                limit.limit_amount = limit_amount
            else:
                limit = BudgetLimit(user_id=current_user.id, category=category, limit_amount=limit_amount)
                db.session.add(limit)
            db.session.commit()
            return jsonify({"status": "success"})
        except ValidationError as e:
            raise e
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        limits = BudgetLimit.query.filter_by(user_id=current_user.id).order_by(BudgetLimit.category).all()
        return jsonify([l.to_dict() for l in limits])

@app.route("/budget/status", methods=["GET"])
@login_required
def budget_status():
    import datetime
    year_month = request.args.get("month", datetime.datetime.now().strftime("%Y-%m"))

    limits = BudgetLimit.query.filter_by(user_id=current_user.id).all()
    limits_dict = {l.category: l.limit_amount for l in limits}

    expenses = Expense.query.filter(Expense.user_id == current_user.id, Expense.date.like(f"{year_month}%")).all()

    spent_by_category = {}
    for e in expenses:
        spent_by_category[e.category] = spent_by_category.get(e.category, 0.0) + e.amount

    status_list = []
    all_categories = set(limits_dict.keys()) | set(spent_by_category.keys())

    for cat in sorted(all_categories):
        lim = limits_dict.get(cat, 0.0)
        spent = spent_by_category.get(cat, 0.0)
        pct = (spent / lim * 100) if lim > 0 else 0.0
        status_list.append({
            "category": cat,
            "limit_amount": lim,
            "spent": spent,
            "percentage": round(pct, 2)
        })

    return jsonify({
        "month": year_month,
        "categories": status_list,
        "total_budgeted": sum(limits_dict.values()),
        "total_spent": sum(spent_by_category.values())
    })

@app.route("/budget/rollover", methods=["POST"])
@login_required
def budget_rollover():
    import datetime
    try:
        data = request.json or {}
        category = data.get("category", "").strip()
        month = data.get("month", "")
        action = data.get("action", "")  # "rollover" or "goal"
        goal_id = data.get("goal_id")

        if not category or not month or action not in ("rollover", "goal"):
            return jsonify({"error": "Invalid parameters"}), 400

        # Calculate surplus
        limit = BudgetLimit.query.filter_by(user_id=current_user.id, category=category).first()
        if not limit:
            return jsonify({"error": "No budget limit found for this category"}), 404

        expenses = Expense.query.filter(
            Expense.user_id == current_user.id,
            Expense.date.like(f"{month}%"),
            Expense.category == category
        ).all()
        actual_spent = sum(e.amount for e in expenses)
        surplus = limit.limit_amount - actual_spent

        if surplus <= 0:
            return jsonify({"error": "No surplus available for this category"}), 400

        if action == "rollover":
            # Add surplus to the existing budget limit for next month's use
            limit.limit_amount = limit.limit_amount + surplus
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": f"Rs. {surplus:.2f} rolled over into {category} budget.",
                "new_limit": limit.limit_amount
            })

        elif action == "goal":
            if not goal_id:
                return jsonify({"error": "goal_id is required"}), 400
            goal = FinancialGoal.query.filter_by(id=goal_id, user_id=current_user.id).first()
            if not goal:
                return jsonify({"error": "Goal not found"}), 404
            goal.current_amount = goal.current_amount + surplus
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": f"Rs. {surplus:.2f} added to goal '{goal.name}'.",
                "new_amount": goal.current_amount
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/budget/alerts", methods=["GET"])
@login_required
def budget_alerts():
    alerts = BudgetAlert.query.filter_by(user_id=current_user.id).order_by(BudgetAlert.triggered_at.desc()).limit(10).all()
    return jsonify([a.to_dict() for a in alerts])

@app.route("/budget/limits/<int:limit_id>", methods=["DELETE"])
@login_required
def delete_budget_limit(limit_id):
    try:
        limit = BudgetLimit.query.filter_by(id=limit_id, user_id=current_user.id).first()
        if not limit:
            return jsonify({"error": f"Budget limit with id {limit_id} not found."}), 404
        BudgetAlert.query.filter_by(user_id=current_user.id, category=limit.category).delete(synchronize_session="fetch")
        db.session.delete(limit)
        db.session.commit()
        return jsonify({"status": "success", "deleted_category": limit.category})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- FINANCIAL GOALS TRACKER ----------------
def _months_diff(start_dt, end_dt):
    return (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)

def _ym_add_months(base_dt, months):
    year = base_dt.year + (base_dt.month - 1 + months) // 12
    month = (base_dt.month - 1 + months) % 12 + 1
    return year, month

def compute_monthly_milestones(goal):
    from datetime import datetime

    remaining = float(goal.target_amount) - float(goal.current_amount)
    if remaining <= 0:
        target_dt = datetime.strptime(goal.target_date, "%Y-%m")
        now = datetime.now()
        months_remaining = _months_diff(datetime(now.year, now.month, 1), datetime(target_dt.year, target_dt.month, 1))
        if months_remaining < 0:
            months_remaining = 0
        if months_remaining == 0:
            months_remaining = 1

        milestones = []
        for i in range(months_remaining):
            y, m = _ym_add_months(datetime(now.year, now.month, 1), i)
            milestones.append({
                "month": f"{y:04d}-{m:02d}",
                "target_amount_for_month": 0.0,
                "status": "completed",
            })
        return milestones

    target_dt = datetime.strptime(goal.target_date, "%Y-%m")
    now = datetime.now()

    start = datetime(now.year, now.month, 1)
    end = datetime(target_dt.year, target_dt.month, 1)
    months_remaining = _months_diff(start, end)
    if months_remaining <= 0:
        months_remaining = 1

    base = remaining / months_remaining
    amounts = [round(base, 2) for _ in range(months_remaining)]
    total_alloc = round(sum(amounts), 2)
    diff = round(remaining - total_alloc, 2)
    amounts[-1] = round(amounts[-1] + diff, 2)

    milestones = []
    for i in range(months_remaining):
        y, m = _ym_add_months(start, i)
        milestones.append({
            "month": f"{y:04d}-{m:02d}",
            "target_amount_for_month": float(amounts[i]),
            "status": "planned",
        })

    return milestones

def persist_goal_milestones(goal, milestones):
    FinancialGoalMilestone.query.filter_by(goal_id=goal.id).delete(synchronize_session=False)
    for ms in milestones:
        db.session.add(FinancialGoalMilestone(
            goal_id=goal.id,
            month=ms["month"],
            target_amount_for_month=ms["target_amount_for_month"],
            status=ms["status"],
        ))
    db.session.commit()

@app.route("/goals", methods=["GET", "POST"])
@login_required
def goals():
    if request.method == "GET":
        return render_template("goals.html", active_page="goals")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        name = validate_string(data.get("name"), "name")
        target_amount = validate_float(data.get("target_amount"), "target_amount", min_val=0.01)
        current_amount = validate_float(data.get("current_amount", 0.0), "current_amount", min_val=0.0)
        target_date = validate_string(data.get("target_date"), "target_date")

        goal = FinancialGoal(
            user_id=current_user.id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date
        )
        db.session.add(goal)
        db.session.commit()

        milestones = compute_monthly_milestones(goal)
        persist_goal_milestones(goal, milestones)

        return jsonify({"status": "success", "goal": goal.to_dict()})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/goals/<int:goal_id>", methods=["PUT", "DELETE"])
@login_required
def goal_detail(goal_id):
    try:
        goal = FinancialGoal.query.filter_by(id=goal_id, user_id=current_user.id).first()
        if not goal:
            return jsonify({"error": "Goal not found"}), 404

        if request.method == "DELETE":
            FinancialGoalMilestone.query.filter_by(goal_id=goal.id).delete(synchronize_session=False)
            db.session.delete(goal)
            db.session.commit()
            return jsonify({"status": "success"})
        else:  # PUT
            data = request.json or {}
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")
            if "name" in data:
                goal.name = validate_string(data["name"], "name")
            if "target_amount" in data:
                goal.target_amount = validate_float(data["target_amount"], "target_amount", min_val=0.01)
            if "current_amount" in data:
                goal.current_amount = validate_float(data["current_amount"], "current_amount", min_val=0.0)
            if "target_date" in data:
                goal.target_date = validate_string(data["target_date"], "target_date")
            db.session.commit()

            milestones = compute_monthly_milestones(goal)
            persist_goal_milestones(goal, milestones)

            return jsonify({"status": "success", "goal": goal.to_dict()})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/goals", methods=["GET"])
@login_required
def get_goals():
    try:
        goals = FinancialGoal.query.filter_by(user_id=current_user.id).order_by(FinancialGoal.created_at.desc()).all()
        goals_list = [g.to_dict() for g in goals]

        ai_recommendations = {}
        if client and len(goals_list) > 0:
            for goal in goals_list:
                remaining = goal["target_amount"] - goal["current_amount"]
                if remaining > 0:
                    try:
                        from datetime import datetime
                        target_dt = datetime.strptime(goal["target_date"], "%Y-%m")
                        now = datetime.now()
                        months_remaining = (target_dt.year - now.year) * 12 + (target_dt.month - now.month)
                        if months_remaining <= 0:
                            months_remaining = 1

                        monthly_needed = remaining / months_remaining
                        prompt = (
                            f"Goal: {goal['name']}\n"
                            f"Target amount: ₹{goal['target_amount']:,}\n"
                            f"Current saved: ₹{goal['current_amount']:,}\n"
                            f"Remaining: ₹{remaining:,}\n"
                            f"Months remaining: {months_remaining}\n"
                            f"Required monthly savings: ₹{monthly_needed:,.2f}\n\n"
                            f"Give 3-4 practical, actionable tips to reach this financial goal faster in India. Keep it concise."
                        )
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[
                                {"role": "system", "content": "You are a helpful Indian personal finance advisor."},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        ai_recommendations[goal["id"]] = res.choices[0].message.content.strip()
                    except Exception as ai_err:
                        app.logger.error(f"Goal AI Recommendation Error: {str(ai_err)}")
                        ai_recommendations[goal["id"]] = "AI recommendations unavailable."

        return jsonify({"goals": goals_list, "ai_recommendations": ai_recommendations})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- SCHEDULER ----------------
def check_all_budgets_job():
    with app.app_context():
        import datetime
        ym = datetime.datetime.now().strftime("%Y-%m")
        limits = BudgetLimit.query.all()
        for limit in limits:
            run_threshold_checks(limit.user_id, limit.category, ym)

def check_stock_alerts_job():
    with app.app_context():
        alerts = PriceAlert.query.filter_by(is_triggered=False).all()

        max_retries = 3
        base_delay_sec = 1.0

        for alert in alerts:
            last_err = None
            res = None

            for attempt in range(max_retries):
                try:
                    res = get_stock_price(alert.symbol)
                    if res and isinstance(res, dict) and "price" in res and "error" not in res:
                        last_err = None
                        break
                    if res and isinstance(res, dict) and "error" in res:
                        last_err = res.get("error")
                    else:
                        last_err = "Unexpected response from get_stock_price"
                except Exception as e:
                    last_err = str(e)

                import time as _time
                _time.sleep(base_delay_sec * (2 ** attempt))

            alert.last_check_error = last_err

            if res and isinstance(res, dict) and "price" in res and "error" not in res:
                current_price = res["price"]
                triggered = False
                if alert.condition == "above" and current_price >= alert.target_price:
                    triggered = True
                elif alert.condition == "below" and current_price <= alert.target_price:
                    triggered = True

                if triggered:
                    from datetime import datetime as _dt
                    alert.is_triggered = True
                    alert.last_triggered_at = _dt.utcnow()

                    event = PriceAlertEvent(
                        alert_id=alert.id,
                        triggered_at=alert.last_triggered_at,
                        price=current_price,
                        condition=alert.condition,
                        symbol=alert.symbol,
                    )
                    db.session.add(event)

                    print(f"\n[STOCK ALERT] Triggered for {alert.symbol}\n", file=sys.stderr)

        db.session.commit()

def check_all_recurring_expenses_job():
    with app.app_context():
        import datetime

        today = datetime.date.today()
        active_items = RecurringExpense.query.filter_by(active=True).all()

        for rexp in active_items:
            start_dt = datetime.datetime.strptime(rexp.start_date, "%Y-%m-%d").date()
            if today < start_dt:
                continue

            if rexp.end_date:
                end_dt = datetime.datetime.strptime(rexp.end_date, "%Y-%m-%d").date()
                if today > end_dt:
                    continue

            period_key = _get_period_key(rexp.frequency, today)
            merchant_key = f"recurring_expense:{rexp.id}:{period_key}"

            exists = Expense.query.filter_by(merchant_name=merchant_key).first()
            if exists:
                continue

            occ_date = today.strftime("%Y-%m-%d")
            exp = Expense(
                category=rexp.category,
                amount=rexp.amount,
                date=occ_date,
                is_recurring=True,
                merchant_name=merchant_key,
            )
            db.session.add(exp)

        db.session.commit()

# ---------------- PORTFOLIO TRACKER ----------------
@app.route("/portfolio-page")
@login_required
def portfolio_page():
    return render_template("portfolio.html", active_page="portfolio")

@app.route("/portfolio/list", methods=["GET"])
@login_required
def list_portfolio():
    try:
        holdings = Portfolio.query.filter_by(user_id=current_user.id).all()

        today_dt = datetime.now()
        cutoff_dt = today_dt - timedelta(days=365)

        holdings_list = []
        total_invested = 0.0
        total_current = 0.0
        total_dividends_received = 0.0
        total_annual_dividends_value = 0.0
        timeline = []

        for h in holdings:
            price_data = get_stock_price(h.symbol)
            current_price = price_data.get("price", h.buy_price)

            divs = get_stock_dividends(h.symbol)

            divs_received = 0.0
            for d in divs:
                if d["date"] >= h.buy_date:
                    divs_received += d["amount"] * h.quantity

            annual_div_per_share = 0.0
            for d in divs:
                try:
                    div_date = datetime.strptime(d["date"], "%Y-%m-%d")
                    if cutoff_dt <= div_date <= today_dt:
                        annual_div_per_share += d["amount"]
                except ValueError:
                    continue

            invested_val = h.quantity * h.buy_price
            current_val = h.quantity * current_price
            pnl = current_val - invested_val
            pnl_percent = (pnl / invested_val * 100) if invested_val > 0 else 0.0
            yoc = (annual_div_per_share / h.buy_price * 100) if h.buy_price > 0 else 0.0

            holdings_list.append({
                "id": h.id,
                "symbol": h.symbol,
                "name": h.name,
                "quantity": h.quantity,
                "buy_price": h.buy_price,
                "current_price": current_price,
                "invested_value": round(invested_val, 2),
                "current_value": round(current_val, 2),
                "pnl": round(pnl, 2),
                "pnl_percent": round(pnl_percent, 2),
                "dividends_received": round(divs_received, 2),
                "annual_dividend_per_share": round(annual_div_per_share, 2),
                "yoc": round(yoc, 2)
            })

            total_invested += invested_val
            total_current += current_val
            total_dividends_received += divs_received
            total_annual_dividends_value += annual_div_per_share * h.quantity

            for d in divs:
                try:
                    div_date = datetime.strptime(d["date"], "%Y-%m-%d")
                    if cutoff_dt <= div_date <= today_dt:
                        projected_date = div_date + timedelta(days=365)
                        if projected_date > today_dt:
                            timeline.append({
                                "date": projected_date.strftime("%Y-%m-%d"),
                                "symbol": h.symbol,
                                "amount_per_share": d["amount"],
                                "amount": d["amount"] * h.quantity
                            })
                except ValueError:
                    continue

        total_pnl = total_current - total_invested
        total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
        portfolio_yoc = (total_annual_dividends_value / total_invested * 100) if total_invested > 0 else 0.0

        timeline.sort(key=lambda x: x["date"])

        summary = {
            "total_invested": round(total_invested, 2),
            "total_current": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_percent, 2),
            "total_dividends_received": round(total_dividends_received, 2),
            "portfolio_yoc": round(portfolio_yoc, 2)
        }

        return jsonify({
            "success": True,
            "holdings": holdings_list,
            "summary": summary,
            "timeline": timeline
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/portfolio/add", methods=["POST"])
@login_required
def add_portfolio_holding():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        symbol = validate_string(data.get("symbol"), "symbol").strip().upper()
        if not symbol or not re.match(r"^[A-Z0-9.\-_]+$", symbol):
            raise ValidationError("Invalid symbol format")

        quantity = validate_float(data.get("quantity"), "quantity", min_val=0.0001)
        buy_price = validate_float(data.get("buy_price"), "buy_price", min_val=0.01)
        buy_date = validate_string(data.get("buy_date"), "buy_date")

        try:
            datetime.strptime(buy_date, "%Y-%m-%d")
        except ValueError:
            raise ValidationError("buy_date must be in YYYY-MM-DD format")

        notes = data.get("notes", "")
        if notes:
            notes = validate_string(notes, "notes")

        stock = yf.Ticker(symbol)
        name = symbol
        try:
            info = stock.info
            if info:
                name = info.get("longName") or info.get("shortName") or symbol
        except Exception:
            if "." not in symbol:
                symbol_ns = symbol + ".NS"
                try:
                    stock_ns = yf.Ticker(symbol_ns)
                    info = stock_ns.info
                    if info:
                        name = info.get("longName") or info.get("shortName") or symbol_ns
                        symbol = symbol_ns
                except Exception:
                    pass

        price_data = get_stock_price(symbol)
        if "error" in price_data:
            raise ValidationError(price_data["error"])

        holding = Portfolio(
            user_id=current_user.id,
            symbol=symbol,
            name=name,
            quantity=quantity,
            buy_price=buy_price,
            buy_date=buy_date,
            notes=notes
        )
        db.session.add(holding)
        db.session.commit()
        return jsonify({"success": True, "message": f"Successfully added {symbol} to portfolio"})
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/portfolio/delete/<int:item_id>", methods=["DELETE"])
@login_required
def delete_portfolio_holding(item_id):
    try:
        holding = db.session.get(Portfolio, item_id)
        if not holding or holding.user_id != current_user.id:
            return jsonify({"error": "Holding not found or unauthorized"}), 404
        db.session.delete(holding)
        db.session.commit()
        return jsonify({"success": True, "message": "Successfully deleted holding"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- ADDITIONAL SCHEDULERS ----------------
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_budgets_job, 'interval', days=1)
    scheduler.add_job(check_all_recurring_expenses_job, 'interval', days=1)
    scheduler.add_job(check_stock_alerts_job, 'interval', minutes=10)
    scheduler.start()

# ---------------- RUN ----------------
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    app.run(debug=debug_mode)

    app.run(host="0.0.0.0", port=5000, debug=True)


