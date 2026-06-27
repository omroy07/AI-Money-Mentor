import re
from flask import Flask, request, jsonify, render_template, make_response
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta, date
import sqlite3
import atexit
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
    login_required,
    LoginManager
)




from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


from flask_mail import Mail, Message



from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


from models import db, Expense, Asset, Liability, BudgetLimit, BudgetAlert, PriceAlert, PriceAlertEvent, FinancialGoal, RecurringExpense, Portfolio, Account, Transaction, LedgerEntry, FxRateCache, FinancialGoalMilestone, RecurringIncome, IncomeOccurrence, MilestoneNotification, SipSchedule


from models import db, Expense, Asset, Liability, BudgetLimit, BudgetAlert, PriceAlert, PriceAlertEvent, FinancialGoal, RecurringExpense, Portfolio, Account, Transaction, LedgerEntry


from utils.portfolio_optimizer import PortfolioOptimizer

from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit, join_room, leave_room

# Load environment variables from .env file (if present)
load_dotenv()

# ---------------- INIT APP ----------------
app = Flask(__name__)

# ---------------- INIT SOCKETIO ----------------
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- IMPORT MODELS ----------------
from models import (
    db, Expense, Asset, Liability, BudgetLimit, BudgetAlert, 
    PriceAlert, PriceAlertEvent, FinancialGoal, RecurringExpense, 
    Portfolio, Account, Transaction, LedgerEntry,
    BankConnection, BankTransaction, FraudAlert, Notification,
    NotificationPreference, InvestmentGoal, GoalAllocation,
    GoalContribution, GoalRecommendation, Couple
)

# ---------------- IMPORT UTILS ----------------
from utils.sip import calculate_sip, calculate_goal_sip, calculate_stepup_sip
from utils.tax import calculate_tax, tax_optimization_module
from utils.pdf_parser import extract_income
from utils.money_score import calculate_money_score
from utils.multi_agent import run_multi_agent
from utils.stock import get_stock_price, get_stock_dividends
from utils.expense_track import calculate_expense, insights
from utils.validation import ValidationError, validate_string, validate_float, validate_int, validate_history
from utils.safety_engine import SafetyEngine
from utils.portfolio_optimizer import PortfolioOptimizer
from utils.voice_assistant import MultiLanguageVoiceAssistant
from utils.couple_finance import CoupleFinanceManager
from utils.financial_predictor import FinancialPredictor
from utils.auto_rebalancer import AutoRebalancer
from utils.fire_planner import FIREPlanner
from utils.bank_integration import BankIntegration
from utils.scenario_planner import get_user_snapshot, job_change, new_loan, add_child, project_snapshot
from utils.ledger import LedgerSystem
from utils.notification_system import NotificationSystem


# ---------------- GROQ CLIENT ----------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY or GROQ_API_KEY.strip() in ("", "your_groq_api_key_here"):
    print(
        "\n[WARNING] GROQ_API_KEY is not configured. AI features will run in offline mode.\n"
        "  1. Copy .env.example to .env\n"
        "  2. Set your GROQ_API_KEY in .env\n"
        "  Obtain a free key at: https://console.groq.com/\n",
        file=sys.stderr,
    )
    client = None
else:
    client = Groq(api_key=GROQ_API_KEY)

from utils.rag_system import RAGSystem
from utils.fx import convert_to_base, get_rate

app = Flask(__name__)


# ---------------- EMAIL CONFIG ----------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_USER', 'your-email@gmail.com')

mail = Mail(app)

# ---------------- DATABASE ----------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///money_mentor.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

login_manager = LoginManager()
login_manager.init_app(app)
db.init_app(app)

from models import User

with app.app_context():
    db.create_all()

# ---------------- INIT UTILITIES ----------------
safety_engine = SafetyEngine()
notification_system = NotificationSystem(socketio)
voice_assistant = MultiLanguageVoiceAssistant(client)
couple_manager = CoupleFinanceManager(client)
predictor = FinancialPredictor()
bank_integration = BankIntegration()

# ---------------- USER LOADER ----------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ---------------- EMAIL DB ----------------
def init_email_db():
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
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT email FROM user_settings WHERE weekly_email_enabled = 1')
    users = c.fetchall()
    conn.close()
    return [user[0] for user in users]

init_email_db()

# ---------------- WEEKLY EMAIL ----------------
def generate_weekly_report(user_email):
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

# ---------------- RECURRING EXPENSES ----------------
def process_recurring_expenses():
    # Run subscription detection before processing existing recurring expenses
    try:
        from utils.subscription_detector import run_detection
        run_detection()
    except Exception as e:
        print(f"⚠️ Subscription detection error: {e}")
    print("🔄 Processing recurring expenses...")
    today = date.today()
    try:


        from models import db, Expense, Asset, Liability, BudgetLimit, BudgetAlert, PriceAlert, PriceAlertEvent, FinancialGoal, RecurringExpense, Portfolio, Account, Transaction, LedgerEntry, FxRateCache, FinancialGoalMilestone, RecurringIncome, IncomeOccurrence

        
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
            existing = Expense.query.filter(
                Expense.merchant == recurring.merchant,
                Expense.amount == recurring.amount,
                Expense.date == today,
                Expense.category == recurring.category
            ).first()
            if existing:
                continue
            expense = Expense(
                amount=recurring.amount,
                category=recurring.category,
                merchant=recurring.merchant or 'Recurring',
                date=today
            )
            db.session.add(expense)
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


# ---------------- SCHEDULER ----------------
scheduler = BackgroundScheduler()
scheduler.add_job(send_weekly_reports, trigger=CronTrigger(day_of_week='mon', hour=9, minute=0), id='weekly_email_job', replace_existing=True)
scheduler.add_job(process_recurring_expenses, trigger=CronTrigger(hour=9, minute=0), id='recurring_expense_job', replace_existing=True)
# Add scheduler for subscription detection if separate frequency needed (currently bundled with recurring expense processing)

def process_recurring_incomes():
    """Process recurring incomes and add them to income occurrences"""
    print("🔄 Processing recurring incomes...")
    today = date.today()
    
    try:
        from models import db, RecurringIncome, IncomeOccurrence
        
        # Get all active recurring incomes due today
        due_incomes = RecurringIncome.query.filter(
            RecurringIncome.is_active == True,
            RecurringIncome.next_due_date <= today
        ).all()
        
        if not due_incomes:
            print("📭 No recurring incomes due today")
            return
        
        added_count = 0
        for recurring in due_incomes:
            # Check if already added today (avoid duplicates)
            existing = IncomeOccurrence.query.filter(
                IncomeOccurrence.recurring_income_id == recurring.id,
                IncomeOccurrence.date == today
            ).first()
            
            if existing:
                continue
            
            # Create income occurrence entry
            occurrence = IncomeOccurrence(
                user_id=recurring.user_id,
                recurring_income_id=recurring.id,
                amount=recurring.amount,
                category=recurring.category,
                source=recurring.source,
                date=today,
                currency=recurring.currency
            )
            db.session.add(occurrence)
            
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
        print(f"✅ Added {added_count} recurring incomes")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error processing recurring incomes: {e}")

# ---------------- INIT DATABASE ----------------
from models import db, Expense, Asset, Liability, BudgetLimit, BudgetAlert, PriceAlert, PriceAlertEvent, FinancialGoal, RecurringExpense, Portfolio, FxRateCache, FinancialGoalMilestone, RecurringIncome, IncomeOccurrence, MilestoneNotification, SipSchedule

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

@app.before_request
def auto_login():
    # Only in development: Auto-login a default user if not logged in
    from flask_login import current_user
    if not current_user.is_authenticated and request.endpoint != 'static':
        user = User.query.first()
        if not user:
            user = User(username="admin", email="admin@example.com", password_hash="pbkdf2:sha256:260000$test")
            db.session.add(user)
            db.session.commit()
        login_user(user)

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

# Recurring incomes job - Every day at 9:00 AM
scheduler.add_job(
    func=process_recurring_incomes,
    trigger=CronTrigger(hour=9, minute=0),
    id='recurring_income_job',
    replace_existing=True
)




scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# ============================================
# ROUTES
# ============================================

# ---------------- RAG SYSTEM ----------------
from utils.rag_system import RAGSystem

# Initialize RAG system
rag_system = RAGSystem()
rag_system.set_client(client)

@app.route('/rag-assistant')
@login_required
def rag_assistant_page():
    """RAG Assistant Page"""
    return render_template('rag_assistant.html', active_page='rag_assistant')

@app.route('/api/rag/upload', methods=['POST'])
@login_required
def rag_upload():
    """Upload and process a document"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Save file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        doc_name = request.form.get('doc_name', file.filename)
        
        # Process document
        result = rag_system.process_document(
            tmp_path,
            metadata={'doc_name': doc_name, 'user_id': current_user.id}
        )
        
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rag/query', methods=['POST'])
@login_required
def rag_query():
    """Query the RAG system"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'}), 400
        
        if not client:
            return jsonify({
                'success': False,
                'answer': 'AI client not configured. Please set up Groq API key.',
                'sources': []
            }), 503
        
        result = rag_system.query(question)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rag/documents', methods=['GET'])
@login_required
def rag_documents():
    """Get list of uploaded documents"""
    try:
        docs = rag_system.get_documents()
        return jsonify({
            'success': True,
            'documents': docs
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rag/delete', methods=['POST'])
@login_required
def rag_delete():
    """Delete a document"""
    try:
        data = request.json
        doc_id = data.get('doc_id')
        
        if not doc_id:
            return jsonify({'success': False, 'error': 'Document ID required'}), 400
        
        success = rag_system.delete_document(doc_id)
        return jsonify({'success': success})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rag/clear', methods=['POST'])
@login_required
def rag_clear():
    """Clear all documents"""
    try:
        success = rag_system.clear_all()
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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


# ---------------- DOCUMENT PARSER ----------------
from utils.document_parser import DocumentParser

document_parser = DocumentParser()

@app.route('/document-parser')
@login_required
def document_parser_page():
    """Document Parser Page"""
    return render_template('document_parser.html', active_page='document_parser')

@app.route('/api/parser/parse', methods=['POST'])
@login_required
def parse_document():
    """Parse uploaded document"""
    try:
        if 'document' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['document']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Save file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        # Parse based on file type
        if file_ext in ['.png', '.jpg', '.jpeg']:
            result = document_parser.extract_from_image(tmp_path)
        elif file_ext == '.pdf':
            result = document_parser.extract_from_pdf(tmp_path)
        else:
            result = {'success': False, 'error': f'Unsupported file type: {file_ext}'}
        
        # Clean up
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/parser/export', methods=['POST'])
@login_required
def export_parsed_expenses():
    """Export parsed transactions to expense tracker"""
    try:
        data = request.json
        parsed_data = data.get('data', {})
        
        expenses = document_parser.export_to_expense(parsed_data)
        
        if not expenses:
            return jsonify({'success': False, 'error': 'No transactions to export'}), 400
        
        # Save to expense tracker
        from models import Expense
        count = 0
        for exp in expenses:
            expense = Expense(
                user_id=current_user.id,
                category=exp['category'],
                amount=exp['amount'],
                date=exp['date'],
                merchant=exp['merchant'],
                description=exp.get('description', 'Imported')
            )
            db.session.add(expense)
            count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'count': count,
            'message': f'Successfully exported {count} transactions'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
        
# ---------------- RETIREMENT ----------------
@app.route('/retirement')
def retirement():
    """Retirement & Inflation Simulator Page"""
    return render_template('retirement.html')

# ---------------- PORTFOLIO OPTIMIZER ----------------
@app.route('/portfolio-optimizer')
@login_required
def portfolio_optimizer_page():
    """Portfolio Optimizer Page"""
    return render_template('portfolio_optimizer.html', active_page='portfolio_optimizer')


@app.route('/api/portfolio/analyze', methods=['POST'])
@login_required
def analyze_portfolio():
    try:
        data = request.json
        holdings = data.get('holdings', [])
        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400
        optimizer = PortfolioOptimizer(holdings)
        optimizer.fetch_historical_data()
        summary = optimizer.get_portfolio_summary()
        frontier = optimizer.calculate_efficient_frontier()
        rebalancing = optimizer.get_rebalancing_suggestions()
        correlation = optimizer.calculate_correlation_matrix()
        return jsonify({
            'success': True,
            'summary': summary,
            'efficient_frontier': frontier['frontier'],
            'max_sharpe': {
                'return': frontier['max_sharpe']['expected_return'] * 100,
                'volatility': frontier['max_sharpe']['volatility'] * 100,
                'sharpe': frontier['max_sharpe']['sharpe_ratio']
            },
            'rebalancing': rebalancing,
            'correlation_matrix': correlation.to_dict(),
            'symbols': optimizer.symbols
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------- MULTI-LANGUAGE VOICE ASSISTANT ----------------
from utils.voice_assistant import MultiLanguageVoiceAssistant


@app.route('/api/portfolio/stress-test', methods=['POST'])
@login_required
def stress_test_portfolio():
    try:
        data = request.json
        holdings = data.get('holdings', [])
        scenario = data.get('scenario', 'mild_crash')
        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400
        optimizer = PortfolioOptimizer(holdings)
        optimizer.fetch_historical_data()
        result = optimizer.stress_test(scenario)
        return jsonify({'success': True, 'stress_test': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------- MULTI-LANGUAGE VOICE ASSISTANT ----------------
@app.route('/voice-assistant')
@login_required
def voice_assistant_page():
    return render_template('voice_assistant.html', active_page='voice_assistant')

@app.route('/api/voice/transcribe', methods=['POST'])
@login_required
def transcribe_voice():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name
        result = voice_assistant.transcribe_voice(tmp_path)
        try:
            os.unlink(tmp_path)
        except:
            pass
        if result['success']:
            parsed = voice_assistant.parse_command(result['text'], result['language'])
            result['parsed'] = parsed
            execution = voice_assistant.execute_command(parsed)
            result['execution'] = execution
            audio_response = voice_assistant.synthesize_voice(
                execution.get('response', ''),
                result['language']
            )
            result['audio_response'] = audio_response
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/test', methods=['GET'])
@login_required
def voice_test():
    return jsonify({
        'status': 'ok',
        'languages': voice_assistant.languages,
        'sample_commands': [
            'Transfer 500 to savings',
            'What is my balance?',
            'Show my spending this month',
            'Add expense 200 for food',
            'What is my net worth?'
        ]
    })



# ---------------- COUPLE FINANCE PLANNER ----------------



  # ---------------- COUPLE FINANCE PLANNER ----------------
from utils.couple_finance import CoupleFinanceManager

couple_manager = CoupleFinanceManager(client)


@app.route('/couple-planner')
@login_required
def couple_planner_page():
    return render_template('couple_planner.html', active_page='couple_planner')

@app.route('/api/couple/status', methods=['GET'])
@login_required
def couple_status():
    try:
        result = couple_manager.get_couple_status(current_user.id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/invite', methods=['POST'])
@login_required
def couple_invite():
    try:
        data = request.json
        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        result = couple_manager.create_invitation(current_user.id, email)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/accept', methods=['POST'])
@login_required
def couple_accept():
    try:
        data = request.json
        token = data.get('token')
        if not token:
            return jsonify({'error': 'Token is required'}), 400
        result = couple_manager.accept_invitation(current_user.id, token)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/unlink', methods=['POST'])
@login_required
def couple_unlink():
    try:
        result = couple_manager.unlink_couple(current_user.id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/goals', methods=['GET'])
@login_required

def get_goals():
    """Get shared goals"""
    try:
        status = couple_manager.get_couple_status(current_user.id)
        if not status.get('has_couple'):
            return jsonify({'error': 'No couple found'}), 400
        goals = couple_manager.get_shared_goals(status['couple_id'])
        return jsonify({'success': True, 'goals': goals})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/goals', methods=['POST'])
@login_required
def create_goal():
    try:
        data = request.json
        status = couple_manager.get_couple_status(current_user.id)
        if not status.get('has_couple'):
            return jsonify({'error': 'No couple found'}), 400
        result = couple_manager.create_shared_goal(status['couple_id'], data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/goals/contribute', methods=['POST'])
@login_required
def contribute_goal():
    try:
        data = request.json
        goal_id = data.get('goal_id')
        amount = data.get('amount')
        note = data.get('note', '')
        if not goal_id or not amount:
            return jsonify({'error': 'Goal ID and amount required'}), 400
        result = couple_manager.add_goal_contribution(current_user.id, goal_id, amount, note)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/expenses', methods=['GET'])
@login_required
def get_split_expenses():
    try:
        status = couple_manager.get_couple_status(current_user.id)
        if not status.get('has_couple'):
            return jsonify({'error': 'No couple found'}), 400
        settled = request.args.get('settled')
        if settled is not None:
            settled = settled.lower() == 'true'
        expenses = couple_manager.get_split_expenses(status['couple_id'], settled)
        summary = couple_manager.get_expense_summary(status['couple_id'])
        return jsonify({'success': True, 'expenses': expenses, 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/expenses', methods=['POST'])
@login_required
def create_split_expense():
    try:
        data = request.json
        status = couple_manager.get_couple_status(current_user.id)
        if not status.get('has_couple'):
            return jsonify({'error': 'No couple found'}), 400
        data['payer_id'] = current_user.id
        result = couple_manager.create_split_expense(status['couple_id'], data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/expenses/settle/<int:expense_id>', methods=['POST'])
@login_required
def settle_split_expense(expense_id):
    try:
        result = couple_manager.settle_expense(expense_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/budget', methods=['GET'])
@login_required
def get_couple_budget():
    try:
        status = couple_manager.get_couple_status(current_user.id)
        if not status.get('has_couple'):
            return jsonify({'error': 'No couple found'}), 400
        month = request.args.get('month')
        result = couple_manager.get_budget_status(status['couple_id'], month)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/budget', methods=['POST'])
@login_required
def create_couple_budget():
    try:
        data = request.json
        status = couple_manager.get_couple_status(current_user.id)
        if not status.get('has_couple'):
            return jsonify({'error': 'No couple found'}), 400
        result = couple_manager.create_couple_budget(status['couple_id'], data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/tax', methods=['GET'])
@login_required
def get_couple_tax():
    try:
        status = couple_manager.get_couple_status(current_user.id)
        if not status.get('has_couple'):
            return jsonify({'error': 'No couple found'}), 400
        user1_income = request.args.get('user1_income', type=float)
        user2_income = request.args.get('user2_income', type=float)
        if not user1_income or not user2_income:
            return jsonify({'error': 'Both incomes required'}), 400
        result = couple_manager.get_tax_optimization(status['couple_id'], user1_income, user2_income)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/couple/dashboard', methods=['GET'])
@login_required
def couple_dashboard():
    try:
        result = couple_manager.get_couple_dashboard(current_user.id)
        return jsonify(result)
    except Exception as e:

        return jsonify({'error': str(e)}), 500

# ---------------- NOTIFICATION SYSTEM ----------------
@app.route('/notifications')

@login_required
def notifications_page():
    return render_template('notifications.html', active_page='notifications')

@login_required
def notifications_page():
    return render_template('notifications.html', active_page='notifications')

@app.route('/api/notifications/list', methods=['GET'])
@login_required
def list_notifications():
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        filter_type = request.args.get('filter', 'all')
        result = notification_system.get_notifications(current_user.id, limit=limit, offset=offset, only_unread=(filter_type == 'unread'))
        if filter_type in ['high', 'medium', 'low']:
            result['notifications'] = [n for n in result['notifications'] if n.get('severity') == filter_type]
            result['total'] = len(result['notifications'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    try:
        data = request.json
        notification_id = data.get('notification_id')
        all_notifications = data.get('all', False)
        if all_notifications:
            result = notification_system.mark_read(current_user.id)
        else:
            result = notification_system.mark_read(current_user.id, notification_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/dismiss', methods=['POST'])
@login_required
def dismiss_notification():
    try:
        data = request.json
        notification_id = data.get('notification_id')
        if not notification_id:
            return jsonify({'error': 'Notification ID required'}), 400
        result = notification_system.dismiss_notification(current_user.id, notification_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    try:
        result = notification_system.get_unread_count(current_user.id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    try:
        if request.method == 'GET':
            result = notification_system.get_preferences(current_user.id)
            return jsonify(result)
        else:
            data = request.json
            result = notification_system.setup_preferences(current_user.id, data)
            return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------- PREDICTIVE FINANCIAL MODELS ----------------
@app.route('/predictive-alerts')
@login_required
def predictive_alerts_page():
    return render_template('predictive_alerts.html', active_page='predictive_alerts')


@app.route('/api/notifications/list', methods=['GET'])
@login_required

def list_notifications():
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        filter_type = request.args.get('filter', 'all')
        result = notification_system.get_notifications(current_user.id, limit=limit, offset=offset, only_unread=(filter_type == 'unread'))
        if filter_type in ['high', 'medium', 'low']:
            result['notifications'] = [n for n in result['notifications'] if n.get('severity') == filter_type]
            result['total'] = len(result['notifications'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    try:
        data = request.json
        notification_id = data.get('notification_id')
        all_notifications = data.get('all', False)
        if all_notifications:
            result = notification_system.mark_read(current_user.id)
        else:
            result = notification_system.mark_read(current_user.id, notification_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/dismiss', methods=['POST'])
@login_required
def dismiss_notification():
    try:
        data = request.json
        notification_id = data.get('notification_id')
        if not notification_id:
            return jsonify({'error': 'Notification ID required'}), 400
        result = notification_system.dismiss_notification(current_user.id, notification_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    try:
        result = notification_system.get_unread_count(current_user.id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    try:
        if request.method == 'GET':
            result = notification_system.get_preferences(current_user.id)
            return jsonify(result)
        else:
            data = request.json
            result = notification_system.setup_preferences(current_user.id, data)
            return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------- PREDICTIVE FINANCIAL MODELS ----------------
@app.route('/predictive-alerts')
@login_required
def predictive_alerts_page():
    return render_template('predictive_alerts.html', active_page='predictive_alerts')

@app.route('/api/predict/train', methods=['POST'])
@login_required
def train_predictor():
    try:

def train_predictor():
    try:

        expenses = Expense.query.filter_by(user_id=current_user.id).all()
        transactions = [{'date': e.date, 'amount': e.amount, 'category': e.category} for e in expenses]
        if len(transactions) < 30:
            return jsonify({'success': False, 'error': f'Need at least 30 transactions. You have {len(transactions)}.'})
        result = predictor.train_models(transactions)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/balance', methods=['POST'])
@login_required
def predict_balance():
    try:
        data = request.json
        income = data.get('income', 0)
        balance = data.get('balance', 0)
        days = data.get('days', 30)
        expenses = Expense.query.filter_by(user_id=current_user.id).all()
        transactions = [{'date': e.date, 'amount': e.amount, 'category': e.category} for e in expenses]
        if len(transactions) < 10:
            return jsonify({'success': False, 'error': f'Need at least 10 transactions. You have {len(transactions)}.'})
        result = predictor.predict_balance(income, balance, transactions, days)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/seasonal', methods=['GET'])
@login_required
def analyze_seasonal():
    try:
        expenses = Expense.query.filter_by(user_id=current_user.id).all()
        transactions = [{'date': e.date, 'amount': e.amount, 'category': e.category} for e in expenses]
        if len(transactions) < 30:
            return jsonify({'success': False, 'error': f'Need at least 30 transactions. You have {len(transactions)}.'})
        result = predictor.analyze_seasonal_patterns(transactions)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/recommendations', methods=['GET'])
@login_required
def get_recommendations():
    try:
        expenses = Expense.query.filter_by(user_id=current_user.id).all()
        transactions = [{'date': e.date, 'amount': e.amount, 'category': e.category} for e in expenses]
        if len(transactions) < 10:
            return jsonify({'success': False, 'error': f'Need at least 10 transactions. You have {len(transactions)}.'})
        income = 50000
        result = predictor.get_savings_recommendations(transactions, income)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/anomalies', methods=['GET'])
@login_required
def detect_anomalies():
    try:
        expenses = Expense.query.filter_by(user_id=current_user.id).all()
        transactions = [{'date': e.date, 'amount': e.amount, 'category': e.category} for e in expenses]
        if len(transactions) < 10:
            return jsonify({'success': True, 'anomalies': [], 'message': f'Need more transactions. You have {len(transactions)}.'})
        anomalies = predictor.detect_anomalies(transactions)
        return jsonify({'success': True, 'anomalies': anomalies})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict/status', methods=['GET'])
@login_required
def predictor_status():

    return jsonify({'is_trained': predictor.is_trained, 'model_dir': predictor.model_dir})

    """Get predictor status"""
    return jsonify({
        'is_trained': predictor.is_trained,
        'model_dir': predictor.model_dir

    })   



# ---------------- AUTO REBALANCER ----------------
from utils.auto_rebalancer import AutoRebalancer

@app.route('/rebalancer')
@login_required
def rebalancer_page():
    """Portfolio Rebalancer Page"""
    return render_template('rebalancer.html', active_page='rebalancer')

@app.route('/api/rebalance/analyze', methods=['POST'])
@login_required
def analyze_rebalance():
    """Analyze portfolio and generate rebalancing recommendations"""
    try:
        data = request.json
        holdings = data.get('holdings', [])
        target = data.get('target', {})
        
        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400
        
        # Create rebalancer
        rebalancer = AutoRebalancer(holdings, target)
        
        # Get current allocation
        current_allocation = rebalancer.get_current_allocation()
        
        # Check if rebalance needed
        rebalance = rebalancer.generate_rebalance_trades()
        
        # Get market signals
        market_signals = {}
        for h in holdings:
            signal = rebalancer.get_market_signal(h['symbol'])
            market_signals[h['symbol']] = signal
        
        # Get tax harvesting opportunities
        tax_harvesting = rebalancer.get_tax_harvesting_opportunities()
        
        return jsonify({
            'success': True,
            'current_allocation': current_allocation,
            'rebalance': rebalance,
            'market_signals': market_signals,
            'tax_harvesting': tax_harvesting
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    # ---------------- FIRE PLANNER ----------------
from utils.fire_planner import FIREPlanner


# ---------------- AUTO REBALANCER ----------------
@app.route('/rebalancer')
@login_required
def rebalancer_page():
    return render_template('rebalancer.html', active_page='rebalancer')

@app.route('/api/rebalance/analyze', methods=['POST'])
@login_required
def analyze_rebalance():
    try:
        data = request.json
        holdings = data.get('holdings', [])
        target = data.get('target', {})
        if not holdings:
            return jsonify({'error': 'No holdings provided'}), 400
        rebalancer = AutoRebalancer(holdings, target)
        current_allocation = rebalancer.get_current_allocation()
        rebalance = rebalancer.generate_rebalance_trades()
        market_signals = {}
        for h in holdings:
            signal = rebalancer.get_market_signal(h['symbol'])
            market_signals[h['symbol']] = signal
        tax_harvesting = rebalancer.get_tax_harvesting_opportunities()
        return jsonify({
            'success': True,
            'current_allocation': current_allocation,
            'rebalance': rebalance,
            'market_signals': market_signals,
            'tax_harvesting': tax_harvesting
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------- FIRE PLANNER ----------------
@app.route('/fire-planner')
@login_required
def fire_planner_page():
    return render_template('fire_planner.html', active_page='fire_planner')

@app.route('/api/fire/plan', methods=['POST'])
@login_required
def fire_plan():
    try:
        data = request.json
        planner = FIREPlanner(
            current_age=data.get('current_age', 30),
            retirement_age=data.get('retirement_age', 45),
            annual_expenses=data.get('annual_expenses', 500000),
            current_corpus=data.get('current_corpus', 1000000),
            monthly_savings=data.get('monthly_savings', 30000),
            return_mean=data.get('return_mean', 0.10),
            return_std=data.get('return_std', 0.15),
            inflation_rate=data.get('inflation_rate', 0.06)
        )
        plan = planner.get_plan_summary()
        return jsonify({'success': True, 'data': plan, 'visualization': planner.get_visualization_data()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fire/quick', methods=['POST'])
@login_required
def fire_quick():
    try:
        data = request.json
        planner = FIREPlanner(
            current_age=data.get('current_age', 30),
            retirement_age=data.get('retirement_age', 45),
            annual_expenses=data.get('annual_expenses', 500000),
            current_corpus=data.get('current_corpus', 1000000),
            monthly_savings=data.get('monthly_savings', 30000),
            return_mean=data.get('return_mean', 0.10),
            return_std=data.get('return_std', 0.15),
            inflation_rate=data.get('inflation_rate', 0.06)
        )
        mc_results = planner.run_monte_carlo(iterations=200)
        return jsonify({
            'success': True,
            'success_probability': mc_results['success']['probability'],
            'median_corpus': mc_results['corpus']['median'],
            'target_corpus': planner.target_corpus
        })
    except Exception as e:

        return jsonify({'error': str(e)}), 500




        return jsonify({'error': str(e)}), 500


        return jsonify({'error': str(e)}), 500 

      ]


        # ---------------- SCENARIO PLANNER ----------------
        @app.route('/scenarios')
        @login_required
        def scenarios_page():
            return render_template('scenarios.html', active_page='scenarios')

        @app.route('/api/scenario/base', methods=['GET'])
        @login_required
        def get_base_snapshot():
            snapshot = get_user_snapshot(current_user.id)
            return jsonify({'success': True, 'snapshot': snapshot})

        @app.route('/api/scenario/job_change', methods=['POST'])
        @login_required
        def scenario_job_change():
            data = request.json
            percent = data.get('salary_delta', 0)
            snapshot = get_user_snapshot(current_user.id)
            updated = job_change(snapshot, percent)
            projection = project_snapshot(updated)
            return jsonify({'success': True, 'snapshot': updated, 'projection': projection})

        @app.route('/api/scenario/new_loan', methods=['POST'])
        @login_required
        def scenario_new_loan():
            data = request.json
            amount = float(data.get('amount', 0))
            interest = float(data.get('interest', 0.07))
            tenure = int(data.get('tenure_years', 15))
            snapshot = get_user_snapshot(current_user.id)
            updated = new_loan(snapshot, amount, interest, tenure)
            projection = project_snapshot(updated)
            return jsonify({'success': True, 'snapshot': updated, 'projection': projection})

        @app.route('/api/scenario/add_child', methods=['POST'])
        @login_required
        def scenario_add_child():
            data = request.json
            annual_cost = float(data.get('annual_cost', 0))
            snapshot = get_user_snapshot(current_user.id)
            updated = add_child(snapshot, annual_cost)
            projection = project_snapshot(updated)
            return jsonify({'success': True, 'snapshot': updated, 'projection': projection})

        # ---------------- BANK INTEGRATION ----------------
from utils.bank_integration import BankIntegration

bank_integration = BankIntegration()



# ---------------- BANK INTEGRATION ----------------
@app.route('/bank-integration')
@login_required
def bank_integration_page():
    return render_template('bank_integration.html', active_page='bank_integration')

@app.route('/api/bank/connect', methods=['POST'])
@login_required
def connect_bank():
    try:
        data = request.json
        provider = data.get('provider')
        account_name = data.get('account_name')
        account_number = data.get('account_number')
        if not provider or not account_name:
            return jsonify({'error': 'Provider and account name are required'}), 400
        credentials = {'account_name': account_name, 'account_number': account_number}
        result = bank_integration.connect_bank(current_user.id, provider, credentials)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/sync', methods=['POST'])
@login_required
def sync_transactions():
    try:
        data = request.json or {}
        connection_id = data.get('connection_id')
        result = bank_integration.sync_transactions(current_user.id, connection_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/connections', methods=['GET'])
@login_required
def get_connections():
    try:
        connections = BankConnection.query.filter_by(user_id=current_user.id, is_active=True).all()
        return jsonify({'success': True, 'connections': [c.to_dict() for c in connections]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/transactions', methods=['GET'])
@login_required
def get_bank_transactions():
    try:
        limit = request.args.get('limit', 50, type=int)
        connection_id = request.args.get('connection_id', type=int)
        query = BankTransaction.query.filter_by(user_id=current_user.id)
        if connection_id:
            query = query.filter_by(connection_id=connection_id)
        transactions = query.order_by(BankTransaction.transaction_date.desc()).limit(limit).all()
        return jsonify({'success': True, 'transactions': [t.to_dict() for t in transactions]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/anomalies', methods=['GET'])
@login_required
def get_anomalies():
    try:
        limit = request.args.get('limit', 50, type=int)
        anomalies = bank_integration.get_anomalies(current_user.id, limit)
        return jsonify({'success': True, 'anomalies': anomalies})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/anomalies/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_anomaly(alert_id):
    try:
        result = bank_integration.resolve_alert(alert_id, current_user.id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/sync-status', methods=['GET'])
@login_required
def get_sync_status():
    try:
        result = bank_integration.get_sync_status(current_user.id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


        return jsonify({'error': str(e)}), 500  


    })    

    return jsonify({'error': str(e)}), 500  


  ]


# ---------------- PORTFOLIO OPTIMIZER ----------------


# ---------------- LEDGER SYSTEM ----------------
@app.route('/ledger')
@login_required
def ledger_page():
    return render_template('ledger.html', active_page='ledger')


@app.route('/api/ledger/accounts', methods=['GET'])
@login_required
def get_accounts():
    try:
        accounts = LedgerSystem.get_user_accounts(current_user.id)
        summary = LedgerSystem.get_account_summary(current_user.id)
        return jsonify({'success': True, 'accounts': [a.to_dict() for a in accounts], 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/account', methods=['POST'])
@login_required
def create_account():
    try:
        data = request.json
        account_type = data.get('account_type')
        account_name = data.get('account_name')
        initial_balance = data.get('initial_balance', 0.0)
        if not account_type or not account_name:
            return jsonify({'error': 'Account type and name are required'}), 400
        account = LedgerSystem.create_account(current_user.id, account_type, account_name, initial_balance)
        return jsonify({'success': True, 'account': account.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/transfer', methods=['POST'])
@login_required
def transfer():
    try:
        data = request.json
        from_account_id = data.get('from_account_id')
        to_account_id = data.get('to_account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not all([from_account_id, to_account_id, amount]):
            return jsonify({'error': 'Missing required fields'}), 400
        result = LedgerSystem.transfer(from_account_id, to_account_id, float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ledger/deposit', methods=['POST'])
@login_required
def deposit():
    try:
        data = request.json
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not account_id or not amount:
            return jsonify({'error': 'Account ID and amount are required'}), 400
        result = LedgerSystem.deposit(int(account_id), float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------- SETTINGS ----------------
@app.route('/settings')
def settings():
    """User settings page"""
    return render_template('settings.html')


@app.route('/api/ledger/withdraw', methods=['POST'])
@login_required
def withdraw():
    try:
        data = request.json
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not account_id or not amount:
            return jsonify({'error': 'Account ID and amount are required'}), 400
        result = LedgerSystem.withdraw(int(account_id), float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ledger/transactions/<int:account_id>', methods=['GET'])
@login_required
def get_transactions(account_id):
    try:
        limit = request.args.get('limit', 50, type=int)
        history = LedgerSystem.get_transaction_history(account_id, limit)
        return jsonify({'success': True, 'transactions': history, 'count': len(history)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/balance/<int:account_id>', methods=['GET'])
@login_required
def get_balance(account_id):
    try:
        balance = LedgerSystem.get_balance(account_id)
        return jsonify({'success': True, 'account_id': account_id, 'balance': balance})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/reconcile/<int:account_id>', methods=['POST'])
@login_required
def reconcile(account_id):
    try:
        result = LedgerSystem.reconcile_account(account_id)
        return jsonify({'success': True, 'reconciliation': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/summary', methods=['GET'])
@login_required
def get_ledger_summary():
    try:
        summary = LedgerSystem.get_account_summary(current_user.id)
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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



@app.route('/api/ledger/accounts', methods=['GET'])
@login_required
def get_accounts():
    try:
        accounts = LedgerSystem.get_user_accounts(current_user.id)
        summary = LedgerSystem.get_account_summary(current_user.id)
        return jsonify({'success': True, 'accounts': [a.to_dict() for a in accounts], 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/account', methods=['POST'])
@login_required
def create_account():
    try:
        data = request.json
        account_type = data.get('account_type')
        account_name = data.get('account_name')
        initial_balance = data.get('initial_balance', 0.0)
        if not account_type or not account_name:
            return jsonify({'error': 'Account type and name are required'}), 400
        account = LedgerSystem.create_account(current_user.id, account_type, account_name, initial_balance)
        return jsonify({'success': True, 'account': account.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/transfer', methods=['POST'])
@login_required
def transfer():
    try:
        data = request.json
        from_account_id = data.get('from_account_id')
        to_account_id = data.get('to_account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not all([from_account_id, to_account_id, amount]):
            return jsonify({'error': 'Missing required fields'}), 400
        result = LedgerSystem.transfer(from_account_id, to_account_id, float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/ledger/accounts', methods=['GET'])
@login_required
def get_accounts():
    try:
        accounts = LedgerSystem.get_user_accounts(current_user.id)
        summary = LedgerSystem.get_account_summary(current_user.id)
        return jsonify({'success': True, 'accounts': [a.to_dict() for a in accounts], 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/account', methods=['POST'])
@login_required
def create_account():
    try:
        data = request.json
        account_type = data.get('account_type')
        account_name = data.get('account_name')
        initial_balance = data.get('initial_balance', 0.0)
        if not account_type or not account_name:
            return jsonify({'error': 'Account type and name are required'}), 400
        account = LedgerSystem.create_account(current_user.id, account_type, account_name, initial_balance)
        return jsonify({'success': True, 'account': account.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/transfer', methods=['POST'])
@login_required
def transfer():
    try:
        data = request.json
        from_account_id = data.get('from_account_id')
        to_account_id = data.get('to_account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not all([from_account_id, to_account_id, amount]):
            return jsonify({'error': 'Missing required fields'}), 400
        result = LedgerSystem.transfer(from_account_id, to_account_id, float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

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


# ---------------- SETTINGS ----------------
@app.route('/settings')
def settings():
    """User settings page"""
    return render_template('settings.html')


@app.route('/api/ledger/deposit', methods=['POST'])
@login_required
def deposit():
    try:
        data = request.json
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not account_id or not amount:
            return jsonify({'error': 'Account ID and amount are required'}), 400
        result = LedgerSystem.deposit(int(account_id), float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ledger/withdraw', methods=['POST'])
@login_required
def withdraw():
    try:
        data = request.json
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not account_id or not amount:
            return jsonify({'error': 'Account ID and amount are required'}), 400
        result = LedgerSystem.withdraw(int(account_id), float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ledger/transactions/<int:account_id>', methods=['GET'])
@login_required
def get_transactions(account_id):
    try:
        limit = request.args.get('limit', 50, type=int)
        history = LedgerSystem.get_transaction_history(account_id, limit)
        return jsonify({'success': True, 'transactions': history, 'count': len(history)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/balance/<int:account_id>', methods=['GET'])
@login_required
def get_balance(account_id):
    try:
        balance = LedgerSystem.get_balance(account_id)
        return jsonify({'success': True, 'account_id': account_id, 'balance': balance})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/reconcile/<int:account_id>', methods=['POST'])
@login_required
def reconcile(account_id):
    try:
        result = LedgerSystem.reconcile_account(account_id)
        return jsonify({'success': True, 'reconciliation': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/summary', methods=['GET'])
@login_required
def get_ledger_summary():
    try:
        summary = LedgerSystem.get_account_summary(current_user.id)
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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



# ---------------- SETTINGS ----------------
@app.route('/settings')
def settings():
    """User settings page"""
    return render_template('settings.html')


@app.route('/api/ledger/deposit', methods=['POST'])
@login_required
def deposit():
    try:
        data = request.json
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not account_id or not amount:
            return jsonify({'error': 'Account ID and amount are required'}), 400
        result = LedgerSystem.deposit(int(account_id), float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ledger/withdraw', methods=['POST'])
@login_required
def withdraw():
    try:
        data = request.json
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description', '')
        if not account_id or not amount:
            return jsonify({'error': 'Account ID and amount are required'}), 400
        result = LedgerSystem.withdraw(int(account_id), float(amount), description)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ledger/transactions/<int:account_id>', methods=['GET'])
@login_required
def get_transactions(account_id):
    try:
        limit = request.args.get('limit', 50, type=int)
        history = LedgerSystem.get_transaction_history(account_id, limit)
        return jsonify({'success': True, 'transactions': history, 'count': len(history)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/balance/<int:account_id>', methods=['GET'])
@login_required
def get_balance(account_id):
    try:
        balance = LedgerSystem.get_balance(account_id)
        return jsonify({'success': True, 'account_id': account_id, 'balance': balance})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/reconcile/<int:account_id>', methods=['POST'])
@login_required
def reconcile(account_id):
    try:
        result = LedgerSystem.reconcile_account(account_id)
        return jsonify({'success': True, 'reconciliation': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/ledger/summary', methods=['GET'])
@login_required
def get_ledger_summary():
    try:
        summary = LedgerSystem.get_account_summary(current_user.id)
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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



# ---------------- SETTINGS ----------------
@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/api/update-email', methods=['POST'])
def update_email():
    data = request.json
    email = data.get('email')
    enabled = data.get('enabled', True)
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO user_settings (email, weekly_email_enabled) VALUES (?, ?)', (email, 1 if enabled else 0))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Settings updated successfully'})

@app.route('/api/unsubscribe', methods=['POST'])
def unsubscribe():
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
    email = os.getenv('EMAIL_USER', 'your-email@gmail.com')
    send_weekly_email(email)
    return "Test email sent! Check your inbox."

@app.route('/force-weekly')
def force_weekly():
    send_weekly_reports()
    return "Weekly reports sent manually!"

# ---------------- RECURRING EXPENSES ROUTES ----------------
@app.route('/recurring')
def recurring_page():
    return render_template('recurring.html')

@app.route('/subscriptions')
def subscriptions_page():
    return render_template('subscriptions.html')

# API: List subscriptions
@app.route('/api/subscriptions', methods=['GET'])
def list_subscriptions():
    from models import CoupleSubscription, User
    user_id = 1  # placeholder for current user auth
    subs = CoupleSubscription.query.filter(
        (CoupleSubscription.user_id == user_id) | (CoupleSubscription.partner_user_id == user_id)
    ).all()
    return jsonify({'success': True, 'subscriptions': [s.to_dict() for s in subs]})

# API: Add subscription (manual)
@app.route('/api/subscriptions/add', methods=['POST'])
def add_subscription():
    data = request.json
    required = ['title', 'amount', 'frequency', 'next_due_date', 'partner_user_id']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
    sub = CoupleSubscription(
        user_id=1,  # placeholder current user
        partner_user_id=data['partner_user_id'],
        title=data['title'],
        amount=data['amount'],
        frequency=data['frequency'],
        next_due_date=datetime.strptime(data['next_due_date'], "%Y-%m-%d").date(),
        status='active'
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify({'success': True, 'subscription': sub.to_dict()})

# API: Update subscription
@app.route('/api/subscriptions/update', methods=['POST'])
def update_subscription():
    data = request.json
    sub_id = data.get('id')
    if not sub_id:
        return jsonify({'success': False, 'error': 'Missing subscription id'}), 400
    sub = CoupleSubscription.query.get(sub_id)
    if not sub:
        return jsonify({'success': False, 'error': 'Subscription not found'}), 404
    for field in ['title', 'amount', 'frequency', 'next_due_date', 'status']:
        if field in data:
            setattr(sub, field, data[field] if field != 'next_due_date' else datetime.strptime(data[field], "%Y-%m-%d").date())
    db.session.commit()
    return jsonify({'success': True, 'subscription': sub.to_dict()})

# API: Cancel subscription (set status)
@app.route('/api/subscriptions/cancel', methods=['POST'])
def cancel_subscription():
    data = request.json
    sub_id = data.get('id')
    sub = CoupleSubscription.query.get(sub_id)
    if not sub:
        return jsonify({'success': False, 'error': 'Subscription not found'}), 404
    sub.status = 'canceled'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Subscription canceled'})


@app.route('/api/recurring/detect', methods=['GET'])
def detect_recurring_expenses():
    try:
        cutoff_date = date.today() - timedelta(days=60)
        expenses = Expense.query.filter(Expense.date >= cutoff_date).order_by(Expense.date.desc()).all()
        if not expenses:
            return jsonify({'success': True, 'detected': [], 'message': 'No expenses found in last 60 days'})
        patterns = {}
        for exp in expenses:
            key = f"{exp.merchant or 'Unknown'}_{exp.category}"
            if key not in patterns:
                patterns[key] = {'merchant': exp.merchant or 'Unknown', 'category': exp.category, 'amounts': [], 'dates': []}
            patterns[key]['amounts'].append(exp.amount)
            patterns[key]['dates'].append(exp.date)
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
        return jsonify({'success': True, 'detected': detected, 'count': len(detected)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/add', methods=['POST'])
def add_recurring_expense():
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
        return jsonify({'success': True, 'message': 'Recurring expense added successfully', 'id': recurring.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/list', methods=['GET'])
def get_recurring_expenses():
    try:
        recurring = RecurringExpense.query.filter_by(is_active=True).all()
        return jsonify({'success': True, 'recurring': [r.to_dict() for r in recurring]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/delete/<int:id>', methods=['DELETE'])
def delete_recurring_expense(id):
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
    try:
        recurring = RecurringExpense.query.get(id)
        if not recurring:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        recurring.is_active = not recurring.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': recurring.is_active, 'message': 'Status updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recurring/process-now', methods=['POST'])
def process_recurring_now():
    process_recurring_expenses()
    return jsonify({'success': True, 'message': 'Recurring expenses processed'})

# ---------------- RECURRING INCOME ENDPOINTS ----------------

@app.route('/recurring-income-page')
@login_required
def recurring_income_page():
    return render_template('recurring_income.html', active_page='recurring_income')

@app.route('/recurring-income', methods=['GET', 'POST'])
@login_required
def handle_recurring_income():
    if request.method == 'POST':
        try:
            data = request.json or {}
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")
            
            amount = validate_float(data.get("amount"), "amount", min_val=0.01)
            category = validate_string(data.get("category"), "category").strip()
            source = validate_string(data.get("source"), "source").strip()
            frequency = validate_string(data.get("frequency"), "frequency").strip()
            if frequency not in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
                raise ValidationError("Invalid frequency")
            
            start_date_str = validate_string(data.get("start_date"), "start_date")
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError("start_date must be in YYYY-MM-DD format")
            
            next_due_date_str = data.get("next_due_date")
            if next_due_date_str:
                next_due_date_str = validate_string(next_due_date_str, "next_due_date")
                try:
                    next_due_date = datetime.strptime(next_due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    raise ValidationError("next_due_date must be in YYYY-MM-DD format")
            else:
                next_due_date = start_date

            end_date_str = data.get("end_date")
            end_date = None
            if end_date_str:
                end_date_str = validate_string(end_date_str, "end_date")
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    raise ValidationError("end_date must be in YYYY-MM-DD format")

            currency = validate_string(data.get("currency", "INR"), "currency").strip().upper()
            
            rec_income = RecurringIncome(
                user_id=current_user.id,
                amount=amount,
                category=category,
                source=source,
                frequency=frequency,
                start_date=start_date,
                next_due_date=next_due_date,
                end_date=end_date,
                currency=currency,
                is_active=True
            )
            db.session.add(rec_income)
            db.session.commit()
            return jsonify({"success": True, "message": "Recurring income added successfully", "id": rec_income.id})
        except ValidationError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
            
    # GET method
    try:
        incomes = RecurringIncome.query.filter_by(user_id=current_user.id, is_active=True).all()
        return jsonify({
            "success": True,
            "incomes": [inc.to_dict() for inc in incomes]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/recurring-income/<int:id>', methods=['DELETE'])
@login_required
def delete_recurring_income(id):
    try:
        inc = RecurringIncome.query.filter_by(id=id, user_id=current_user.id).first()
        if not inc:
            return jsonify({"success": False, "error": "Not found"}), 404
        
        inc.is_active = False
        db.session.commit()
        return jsonify({"success": True, "message": "Recurring income disabled successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# ---------------- CASHFLOW FORECAST API ----------------

@app.route('/cashflow', methods=['GET'])
@login_required
def get_cashflow_forecast():
    import calendar
    try:
        n_months = validate_int(request.args.get("months", "6"), "months", min_val=1, max_val=24)
    except ValidationError:
        n_months = 6
        
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    month_keys = []
    for i in range(n_months):
        m = current_month + i
        y = current_year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        month_keys.append(f"{y:04d}-{m:02d}")
        
    # Get projection end date
    last_month_parts = month_keys[-1].split("-")
    last_year = int(last_month_parts[0])
    last_month = int(last_month_parts[1])
    _, last_day = calendar.monthrange(last_year, last_month)
    projection_end_date = date(last_year, last_month, last_day)
    
    # Helper to advance date
    def advance_date(curr_d, freq):
        if freq == 'daily':
            return curr_d + timedelta(days=1)
        elif freq == 'weekly':
            return curr_d + timedelta(days=7)
        elif freq == 'monthly':
            m = curr_d.month + 1
            y = curr_d.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            try:
                return date(y, m, curr_d.day)
            except ValueError:
                _, last_d = calendar.monthrange(y, m)
                return date(y, m, last_d)
        elif freq == 'quarterly':
            m = curr_d.month + 3
            y = curr_d.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            try:
                return date(y, m, curr_d.day)
            except ValueError:
                _, last_d = calendar.monthrange(y, m)
                return date(y, m, last_d)
        elif freq == 'yearly':
            y = curr_d.year + 1
            try:
                return date(y, curr_d.month, curr_d.day)
            except ValueError:
                return date(y, 2, 28)
        else:
            return curr_d + timedelta(days=30)
            
    # Project Incomes
    projected_income = {m: 0.0 for m in month_keys}
    incomes = RecurringIncome.query.filter_by(user_id=current_user.id, is_active=True).all()
    for inc in incomes:
        curr_d = inc.next_due_date
        if curr_d < inc.start_date:
            curr_d = inc.start_date
        while curr_d <= projection_end_date:
            if inc.end_date and curr_d > inc.end_date:
                break
            m_key = curr_d.strftime("%Y-%m")
            if m_key in projected_income:
                projected_income[m_key] += convert_to_base(inc.amount, inc.currency)
            curr_d = advance_date(curr_d, inc.frequency)
            
    # Project Recurring Expenses
    projected_rec_expenses = {m: 0.0 for m in month_keys}
    expenses = RecurringExpense.query.filter_by(user_id=current_user.id, is_active=True).all()
    for exp in expenses:
        curr_d = exp.next_due_date
        if curr_d < exp.start_date:
            curr_d = exp.start_date
        while curr_d <= projection_end_date:
            if exp.end_date and curr_d > exp.end_date:
                break
            m_key = curr_d.strftime("%Y-%m")
            if m_key in projected_rec_expenses:
                projected_rec_expenses[m_key] += convert_to_base(exp.amount, getattr(exp, 'currency', 'INR'))
            curr_d = advance_date(curr_d, exp.frequency)
            
    # Calculate historical manual expense monthly average
    cutoff_3m = date.today() - timedelta(days=90)
    manual_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= cutoff_3m.strftime("%Y-%m-%d"),
        Expense.is_recurring == False
    ).all()
    total_manual_inr = sum(convert_to_base(e.amount, e.currency) for e in manual_expenses)
    avg_monthly_manual_expense = total_manual_inr / 3.0
    
    # Current net worth
    assets = Asset.query.filter_by(user_id=current_user.id).all()
    liabilities = Liability.query.filter_by(user_id=current_user.id).all()
    net_worth = sum(convert_to_base(a.amount, a.currency) for a in assets) - sum(convert_to_base(l.amount, l.currency) for l in liabilities)
    
    balance = net_worth
    projected_months = []
    runway_months = None
    
    for idx, m_key in enumerate(month_keys):
        inc_val = projected_income[m_key]
        exp_val = projected_rec_expenses[m_key] + avg_monthly_manual_expense
        net_val = inc_val - exp_val
        balance += net_val
        
        if balance < 0 and runway_months is None:
            runway_months = idx + 1
            
        projected_months.append({
            "month": m_key,
            "projected_income": round(inc_val, 2),
            "projected_expense": round(exp_val, 2),
            "net_cashflow": round(net_val, 2),
            "cumulative_balance": round(balance, 2)
        })
        
    if runway_months is None:
        runway_status = "Healthy"
        runway_msg = "No projected cash shortfalls."
    else:
        runway_status = "Critical"
        runway_msg = f"Warning: Projected runway is {runway_months} month(s). Balance drops below zero in {runway_months} month(s)."
        
    return jsonify({
        "success": True,
        "forecast": projected_months,
        "current_net_worth": round(net_worth, 2),
        "runway_months": runway_months,
        "runway_status": runway_status,
        "runway_message": runway_msg
    })

# ---------------- HEALTH CHECK ----------------
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "AI Money Mentor"}), 200



# ---------------- AI STATUS ----------------
@app.route("/api/status", methods=["GET"])
def ai_status():
    if client is not None:
        return jsonify({"ai_online": True, "message": "AI Money Mentor is online and ready."})
    return jsonify({"ai_online": False, "message": "AI features are unavailable — GROQ_API_KEY is not configured."})


@app.route("/api/achievements", methods=["GET"])
@login_required
def get_achievements():
    """Calculate and return gamification achievements for the user."""
    achievements = []
    
    # Check for Expense Tracker Badge
    expenses = Expense.query.filter_by(user_id=current_user.id).count()
    if expenses > 0:
        achievements.append({
            "icon": "💸", "title": "First Step", "desc": "Logged your first expense"
        })
    if expenses >= 10:
        achievements.append({
            "icon": "📝", "title": "Diligent Tracker", "desc": "Logged 10+ expenses"
        })
        
    # Check for Goal Setter Badge
    goals = FinancialGoal.query.filter_by(user_id=current_user.id).count()
    if goals > 0:
        achievements.append({
            "icon": "🎯", "title": "Goal Setter", "desc": "Created a financial goal"
        })
        
    # Check for Portfolio Badge
    investments = Portfolio.query.filter_by(user_id=current_user.id).count()
    if investments > 0:
        achievements.append({
            "icon": "💼", "title": "Investor", "desc": "Added to your portfolio"
        })
        
    # Check Net Worth Badge
    assets = sum(a.amount for a in Asset.query.filter_by(user_id=current_user.id).all())
    liabilities = sum(l.amount for l in Liability.query.filter_by(user_id=current_user.id).all())
    net_worth = assets - liabilities
    if net_worth > 100000:
        achievements.append({
            "icon": "💎", "title": "Wealth Builder", "desc": "Net worth over ₹1L"
        })
        
    if not achievements:
        achievements.append({
            "icon": "🌱", "title": "The Beginning", "desc": "Started your financial journey"
        })
        
    return jsonify({"achievements": achievements}), 200

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
    if client is not None:
        return jsonify({"ai_online": True, "message": "AI Money Mentor is online and ready."})
    return jsonify({"ai_online": False, "message": "AI features are unavailable — GROQ_API_KEY is not configured."})


# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({"error": "Bad Request", "message": str(error), "status_code": 400}), 400

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad Request", "message": str(error), "status_code": 400}), 400

@app.errorhandler(404)
def not_found(error):
    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
        return render_template("404.html", active_page=None), 404
    return jsonify({"error": "Not Found", "message": "The requested endpoint does not exist.", "status_code": 404}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method Not Allowed", "message": str(error), "status_code": 405}), 405

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred. Please try again later.", "status_code": 500}), 500


# ---------------- AI CHAT WITH SAFETY ENGINE ----------------
@app.route("/chat", methods=["POST"])

# ---------------- 🤖 AI CHAT WITH SAFETY ENGINE ----------------
@app.route("/chat", methods=["GET", "POST"])

def chat():
    if request.method == "GET":
        return render_template("chat.html", active_page="chat")
    try:
        data = request.json
        msg = data.get("message")
        history = data.get("history", [])
        user_context = {}
        if current_user.is_authenticated:
            expenses = Expense.query.filter_by(user_id=current_user.id).all()
            assets = Asset.query.filter_by(user_id=current_user.id).all()
            user_context = {
                'income': 80000,
                'expenses': sum(e.amount for e in expenses) if expenses else 0,
                'savings': sum(a.amount for a in assets) if assets else 0,
                'investments': 500000,
                'debt': 100000,
                'emergency': 240000
            }
        system_prompt = """You are a professional financial advisor for Indian users.

CRITICAL RULES - YOU MUST FOLLOW:
1. NEVER invent numbers, amounts, or financial data about the user.
2. If you don't know the user's income, savings, or expenses, ASK for that information.
3. If the user asks for advice without providing data, give general methodology only.
4. Always be honest about what you don't know.
5. Provide practical, actionable advice based ONLY on information the user has shared.

CHART GENERATION:
If the user asks for a chart or visualization (e.g. "show me a pie chart of my expenses"), you MUST output a raw JSON block at the very end of your response, wrapped exactly like this:
[CHART_DATA: {"type": "pie", "data": {"labels": ["Rent", "Food"], "datasets": [{"data": [2000, 500]}]}}]
You can generate "pie", "bar", or "doughnut" charts.

Be friendly, supportive, and encouraging."""
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages += history[-10:]
        messages.append({"role": "user", "content": msg})

        res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.7, max_tokens=500)


        if client is None:
            return jsonify({
                "reply": "I'm currently in offline mode. Please configure the GROQ_API_KEY environment variable to enable AI chat.",
                "safety": {
                    "passed": True,
                    "confidence_score": 1.0,
                    "confidence_level": "High",
                    "flagged_topics": [],
                    "filtered_sentences": []
                }
            })

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )


        reply = res.choices[0].message.content
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
        return jsonify({"reply": "⚠️ I'm having trouble connecting. Please try again in a moment."}), 500

# ---------------- SIP ----------------
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
        nominal_fv = result["nominal_value"]
        inflation_adjusted_value = result["inflation_adjusted_value"]

        # Sensitivity calculations
        rate_p1 = calculate_sip(monthly, rate + 1.0, years, inflation)
        rate_m1 = calculate_sip(monthly, max(0.0, rate - 1.0), years, inflation)
        inf_p1 = calculate_sip(monthly, rate, years, inflation + 1.0)
        inf_m1 = calculate_sip(monthly, rate, years, max(0.0, inflation - 1.0))

        explainability = {
            "inputs": {
                "monthly_investment": monthly,
                "expected_return_rate": rate,
                "duration_years": years,
                "inflation_rate": inflation
            },
            "formulas": {
                "nominal_future_value": "FV = P * (((1 + r)^n - 1) / r) * (1 + r) where P is monthly investment, r is monthly rate (R / 12 / 100), and n is total months (Years * 12).",
                "inflation_adjusted_value": "FV_adjusted = FV / (1 + i)^n where i is monthly inflation rate (Inflation / 12 / 100) and n is total months."
            },
            "sensitivity": {
                "rate_plus_1_percent": {
                    "rate": rate + 1.0,
                    "nominal_value": rate_p1["nominal_value"],
                    "difference": round(rate_p1["nominal_value"] - nominal_fv, 2)
                },
                "rate_minus_1_percent": {
                    "rate": round(max(0.0, rate - 1.0), 2),
                    "nominal_value": rate_m1["nominal_value"],
                    "difference": round(rate_m1["nominal_value"] - nominal_fv, 2)
                },
                "inflation_plus_1_percent": {
                    "inflation": inflation + 1.0,
                    "inflation_adjusted_value": inf_p1["inflation_adjusted_value"],
                    "difference": round(inf_p1["inflation_adjusted_value"] - inflation_adjusted_value, 2)
                },
                "inflation_minus_1_percent": {
                    "inflation": round(max(0.0, inflation - 1.0), 2),
                    "inflation_adjusted_value": inf_m1["inflation_adjusted_value"],
                    "difference": round(inf_m1["inflation_adjusted_value"] - inflation_adjusted_value, 2)
                }
            }
        }

        return jsonify({
            "future_value": nominal_fv,
            "nominal_value": nominal_fv,
            "inflation_adjusted_value": inflation_adjusted_value,
            "inflation_applied": result["inflation_applied"],
            "explainability": explainability
        })
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route("/sip-stepup", methods=["POST"])
def sip_stepup():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        monthly = validate_float(data.get("monthly"), "monthly", min_val=0.0)
        rate = validate_float(data.get("rate"), "rate", min_val=0.0)
        years = validate_int(data.get("years"), "years", min_val=1)
        stepup_type = validate_string(data.get("stepup_type"), "stepup_type")
        if stepup_type not in ("percentage", "amount"):
            raise ValidationError("'stepup_type' must be 'percentage' or 'amount'")
        stepup_value = validate_float(data.get("stepup_value"), "stepup_value", min_val=0.0)
        inflation = validate_float(data.get("inflation", 0.0), "inflation", min_val=0.0)

        result = calculate_stepup_sip(monthly, rate, years, stepup_type, stepup_value, inflation)
        return jsonify(result)

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- GOAL-BASED SAVINGS PLANNER ----------------
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

        monthly_sip = result["monthly_sip"]

        # Sensitivity calculations
        rate_p1 = calculate_goal_sip(goal, rate + 1.0, years)
        rate_m1 = calculate_goal_sip(goal, max(0.0, rate - 1.0), years)
        dur_p1 = calculate_goal_sip(goal, rate, years + 1)
        dur_m1 = calculate_goal_sip(goal, rate, max(1, years - 1))

        explainability = {
            "inputs": {
                "target_goal": goal,
                "expected_return_rate": rate,
                "duration_years": years
            },
            "formulas": {
                "required_monthly_sip": "Monthly SIP = Goal * r / (((1 + r)^n - 1) * (1 + r)) where r is monthly rate (R / 12 / 100) and n is total months (Years * 12)."
            },
            "sensitivity": {
                "rate_plus_1_percent": {
                    "rate": rate + 1.0,
                    "monthly_sip": rate_p1["monthly_sip"],
                    "difference": round(rate_p1["monthly_sip"] - monthly_sip, 2)
                },
                "rate_minus_1_percent": {
                    "rate": round(max(0.0, rate - 1.0), 2),
                    "monthly_sip": rate_m1["monthly_sip"],
                    "difference": round(rate_m1["monthly_sip"] - monthly_sip, 2)
                },
                "duration_plus_1_year": {
                    "years": years + 1,
                    "monthly_sip": dur_p1["monthly_sip"],
                    "difference": round(dur_p1["monthly_sip"] - monthly_sip, 2)
                },
                "duration_minus_1_year": {
                    "years": max(1, years - 1),
                    "monthly_sip": dur_m1["monthly_sip"],
                    "difference": round(dur_m1["monthly_sip"] - monthly_sip, 2)
                }
            }
        }

        response_data = {
            "monthly_sip": monthly_sip,
            "total_invested": result["total_invested"],
            "returns": result["returns"],
            "explainability": explainability
        }
        return jsonify(response_data)


    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- STOCK ----------------
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


# ---------------- TAX ----------------

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
        operator_type = data.get("operator_type", data.get("condition", "above")).strip().lower()

        if operator_type not in ("above", "below", "cross", "cross_above", "cross_below"):
            return jsonify({"error": "Invalid operator_type value"}), 400
            
        cooldown_days = int(data.get("cooldown_days", 0))
        duration_days = int(data.get("duration_days", 0))

        if cooldown_days < 0 or duration_days < 0:
            return jsonify({"error": "Cooldown and duration must be non-negative"}), 400
            
        alert = PriceAlert(
            symbol=symbol,
            target_price=target_price,
            condition=operator_type, # keep condition for backward compatibility
            operator_type=operator_type,
            cooldown_days=cooldown_days,
            duration_days=duration_days,
            user_id=current_user.id
        )
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

        
        # Offline explainability fallback
        offline_explainability = {
            "assumptions": [
                "Standard deduction of ₹75,000 for New Regime, ₹50,000 for Old Regime.",
                "Section 80C deductions are capped at ₹1,50,000.",
                "Section 80D deductions are capped at ₹25,000.",
                "HRA exemption is calculated based on rent paid, basic salary, and metro city status."
            ],
            "top_drivers": [
                {"driver": "Section 80C", "delta": f"Reduces taxable income by up to ₹{min(150000.0, float(deduction_80c)):,}.", "reason": "ELSS, PPF, EPF contributions."},
                {"driver": "Section 80D", "delta": f"Reduces taxable income by up to ₹{min(25000.0, float(deduction_80d)):,}.", "reason": "Health insurance premiums."},
                {"driver": "Section 10(13A) HRA", "delta": f"Reduces taxable income by HRA exemption of ₹{float(tax_details['deductions_applied']['hra']):,}.", "reason": "Rent paid compared to Basic salary."}
            ],
            "recommendations": [
                "Maximize Section 80C options (PPF, ELSS) if you file under the Old Tax Regime.",
                "Utilize Section 80D medical insurance deduction to protect family and save tax.",
                "Compare both Old and New tax regimes; the New regime is preferred unless you have total deductions exceeding ₹3.75 Lakhs."
            ]
        }

        # Compute exact lever contributions under Old Regime (Base tax vs deduction applied)
        tax_no_ded = calculate_tax(income, deduction_80c=0, deduction_80d=0, deduction_hra=0)
        old_tax_no_ded = tax_no_ded["old_regime"]["total_tax"]

        tax_80c_only = calculate_tax(income, deduction_80c=deduction_80c, deduction_80d=0, deduction_hra=0)
        saving_80c = max(0.0, old_tax_no_ded - tax_80c_only["old_regime"]["total_tax"])

        tax_80d_only = calculate_tax(income, deduction_80c=0, deduction_80d=deduction_80d, deduction_hra=0)
        saving_80d = max(0.0, old_tax_no_ded - tax_80d_only["old_regime"]["total_tax"])

        tax_hra_only = calculate_tax(income, deduction_80c=0, deduction_80d=0, deduction_hra=deduction_hra, hra_inputs=hra_inputs)
        saving_hra = max(0.0, old_tax_no_ded - tax_hra_only["old_regime"]["total_tax"])

        lever_contributions = {
            "80c": round(saving_80c, 2),
            "80d": round(saving_80d, 2),
            "hra": round(saving_hra, 2)
        }

        recommended_regime = tax_details.get("recommended", "New Regime")
        regime_key = "new_regime" if recommended_regime == "New Regime" else "old_regime"
        total_tax = tax_details.get(regime_key, {}).get("total_tax", 0.0)
        
        ai_explainability = None
        if total_tax > 0.0 and client:
            prompt = (
                f"A user in India has a gross annual income of ₹{income:,} and has a total tax liability of ₹{total_tax:,} "
                f"under the recommended {recommended_regime}. Generate structured tax-saving recommendations.\n\n"
                f"Your response must be a single JSON object with no markdown surrounding it. It must strictly follow this JSON schema:\n"
                f"{{\n"
                f"  \"assumptions\": [\"string\"],\n"
                f"  \"top_drivers\": [\n"
                f"     {{\"driver\": \"string\", \"delta\": \"string\", \"reason\": \"string\"}}\n"
                f"  ],\n"
                f"  \"recommendations\": [\"string\"]\n"
                f"}}\n"

            )            try:

            )

            try:

                ai_res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a professional Indian tax consultant. Answer ONLY with the requested JSON schema and no conversational filler."},
                        {"role": "user", "content": prompt}
                    ]
                )
                import json
                content = ai_res.choices[0].message.content.strip()
                if content.startswith("```"):
                    if content.startswith("```json"):
                        content = content[7:]
                    else:
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                ai_explainability = json.loads(content.strip())
            except Exception as ai_err:
                app.logger.error(f"Tax AI Recommendation Error: {str(ai_err)}")

                recommendations = "AI Tax recommendations are currently unavailable. Consider investing in ELSS or NPS to reduce your tax."
        elif total_tax > 0.0:
            recommendations = "AI Tax recommendations are currently offline (no GROQ_API_KEY configured). Consider investing in ELSS or NPS to reduce your tax."
        tax_details["ai_recommendations"] = recommendations


        if not ai_explainability or not isinstance(ai_explainability, dict):
            ai_explainability = offline_explainability

        explainability = {
            "assumptions": ai_explainability.get("assumptions", offline_explainability["assumptions"]),
            "top_drivers": ai_explainability.get("top_drivers", offline_explainability["top_drivers"]),
            "recommendations": ai_explainability.get("recommendations", offline_explainability["recommendations"]),
            "lever_contributions": lever_contributions
        }
        
        tax_details["explainability"] = explainability
        tax_details["ai_recommendations"] = "\n".join(f"- {r}" for r in explainability["recommendations"])

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


        # Compute exact lever contributions under Old Regime for Scenario A and Scenario B (savings vs standard deduction only)
        a_tax_no_ded = calculate_tax(income, deduction_80c=0, deduction_80d=0, deduction_hra=0)
        a_old_tax_no_ded = a_tax_no_ded["old_regime"]["total_tax"]

        a_tax_80c = calculate_tax(income, deduction_80c=scenario_a_d80c, deduction_80d=0, deduction_hra=0)
        a_saving_80c = max(0.0, a_old_tax_no_ded - a_tax_80c["old_regime"]["total_tax"])

        a_tax_80d = calculate_tax(income, deduction_80c=0, deduction_80d=scenario_a_d80d, deduction_hra=0)
        a_saving_80d = max(0.0, a_old_tax_no_ded - a_tax_80d["old_regime"]["total_tax"])

        a_tax_hra = calculate_tax(income, deduction_80c=0, deduction_80d=0, deduction_hra=scenario_a_hra, hra_inputs=scenario_a_hra_inputs)
        a_saving_hra = max(0.0, a_old_tax_no_ded - a_tax_hra["old_regime"]["total_tax"])

        b_tax_80c = calculate_tax(income, deduction_80c=scenario_b_d80c, deduction_80d=0, deduction_hra=0)
        b_saving_80c = max(0.0, a_old_tax_no_ded - b_tax_80c["old_regime"]["total_tax"])

        b_tax_80d = calculate_tax(income, deduction_80c=0, deduction_80d=scenario_b_d80d, deduction_hra=0)
        b_saving_80d = max(0.0, a_old_tax_no_ded - b_tax_80d["old_regime"]["total_tax"])

        b_tax_hra = calculate_tax(income, deduction_80c=0, deduction_80d=0, deduction_hra=scenario_b_hra, hra_inputs=scenario_b_hra_inputs)
        b_saving_hra = max(0.0, a_old_tax_no_ded - b_tax_hra["old_regime"]["total_tax"])

        lever_contributions = {
            "scenario_a": {
                "80c": round(a_saving_80c, 2),
                "80d": round(a_saving_80d, 2),
                "hra": round(a_saving_hra, 2)
            },
            "scenario_b": {
                "80c": round(b_saving_80c, 2),
                "80d": round(b_saving_80d, 2),
                "hra": round(b_saving_hra, 2)
            }
        }

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


        # Build sensitivity ranking list as drivers
        drivers = []
        for rank in lever_ranking:
            drivers.append({
                "driver": f"Lever {rank['lever']}",
                "delta": f"Saves ₹{abs(rank['delta_per_1']):.2f} tax per ₹1 contribution.",
                "reason": f"Sensitivity analysis for Scenario B recommended regime {best_regime_b}."
            })

        result["explainability"] = {
            "assumptions": [
                "Standard deduction of ₹75,000 for New Regime, ₹50,000 for Old Regime.",
                "Section 80C deductions are capped at ₹1,50,000.",
                "Section 80D deductions are capped at ₹25,000.",
                "Tax rebates under Section 87A apply."
            ],
            "top_drivers": drivers,
            "lever_contributions": lever_contributions
        }


        return jsonify({"result": result})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- PDF ----------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files["file"]
        result = extract_income(file)
        return jsonify({"data": result})
    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------- MULTI AGENT ----------------
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

# ---------------- MONEY SCORE ----------------
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
        return jsonify({"score": score, "status": status})
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
            advice.append("Reduce credit utilization below 30%.")
        if dti > 40:
            advice.append("Lower your debt-to-income ratio.")
        if payment < 90:
            advice.append("Maintain timely payments to improve credit history.")
        if score >= 750:
            advice.append("Excellent credit profile. Maintain your habits.")
        if not advice:
            advice.append("Keep monitoring your credit health regularly.")
        return jsonify({"message": " ".join(advice)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
@app.route("/expense", methods=["GET"])
def expense_page():
    return render_template("expense.html", active_page="expense")

@app.route("/add_expense", methods=["POST"])
@login_required
def add_expense():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object.")
        category = validate_string(data.get("category"), "category")

        amount = validate_float(data.get("amount"), "amount", min_val=0.01)
        date = validate_string(data.get("date"), "date")

        amount   = validate_float(data.get("amount"),   "amount",   min_val=0.01)
        date     = validate_string(data.get("date"),    "date")
        currency = validate_string(data.get("currency", "INR"), "currency")


        expense = Expense(
            category=category,
            amount=amount,
            currency=currency,
            date=date,
            merchant_name=data.get("merchant", ""),
            user_id=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        ym = date[:7] if len(date) >= 7 else None
        run_threshold_checks(current_user.id, category, ym)
        return jsonify({"status": "success", "id": expense.id})
    except ValidationError as e:
        raise e
    except Exception as e:
        app.logger.error(f"[add_expense] {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/expense/<int:expense_id>", methods=["PUT", "DELETE"])
@login_required
def expense_detail(expense_id):
    try:
        expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
        if not expense:
            return jsonify({"error": f"Expense {expense_id} not found."}), 404
        if request.method == "DELETE":
            db.session.delete(expense)
            db.session.commit()
            return jsonify({"status": "success"})
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object.")
        if "category" in data:
            expense.category = validate_string(data["category"], "category")
        if "amount" in data:
            expense.amount = validate_float(data["amount"], "amount", min_val=0.01)
        if "date" in data:
            expense.date = validate_string(data["date"], "date")

        if "currency" in data:
            expense.currency = validate_string(data["currency"], "currency")
            
        expense.user_corrected = True
 

        db.session.commit()
        return jsonify({"status": "success", "expense": expense.to_dict()})
    except ValidationError as e:
        raise e
    except Exception as e:
        app.logger.error(f"[expense_detail] {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/calculate", methods=["GET"])
@login_required
def calculate():

    try:
        expense_rows = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id.desc()).all()

    """
    GET /calculate
    Returns total, average, by-category breakdown, and full expense list
    for the current user.
    """
    try:
        expense_rows = (
            Expense.query
            .filter_by(user_id=current_user.id)
            .order_by(Expense.id.desc())
            .all()
        )
        converted_expense_data = []
        for e in expense_rows:
            converted_amount = convert_to_base(e.amount, e.currency)
            converted_expense_data.append({
                "category": e.category,
                "amount": converted_amount
            })
            

        expense_data = [e.to_dict() for e in expense_rows]
        result = calculate_expense(converted_expense_data)
        result["expenses"] = expense_data
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"[calculate] {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/insights", methods=["GET"])
@login_required
def expense_insights():

    try:
        expense_rows = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id.desc()).all()
        expense_data = [e.to_dict() for e in expense_rows]
        result = insights(client, expense_data)

    """
    GET /insights
    Returns AI-generated HTML insight cards for the current user's expenses.
    Falls back gracefully when GROQ_API_KEY is not set.
    """
    try:
        expense_rows = (
            Expense.query
            .filter_by(user_id=current_user.id)
            .order_by(Expense.id.desc())
            .all()
        )
        converted_expense_data = []
        for e in expense_rows:
            converted_amount = convert_to_base(e.amount, e.currency)
            converted_expense_data.append({
                "category": e.category,
                "amount": converted_amount
            })
 
        # client is None when GROQ_API_KEY is missing —
        # insights() handles this and returns an offline message
        result = insights(client, converted_expense_data)


        return jsonify(result)

     return jsonify(result)

    except Exception as e:
        app.logger.error(f"[expense_insights] {e}")
        return jsonify({
            "insights": '<div class="insight-card"><h3>Server Error</h3><p>Could not generate insights right now.</p></div>'
        }), 500




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

def create_recurring_expense():
    """
    Create a recurring expense template.
    """
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        category = validate_string(data.get("category"), "category")
        amount = validate_float(data.get("amount"), "amount", min_val=0.01)
        start_date = validate_string(data.get("start_date"), "start_date")  # YYYY-MM-DD
        frequency = _validate_frequency(data.get("frequency"))

        active = data.get("active", True)
        if not isinstance(active, bool):
            raise ValidationError("active must be a boolean")

        end_date = data.get("end_date", None)
        if end_date is not None:
            end_date = validate_string(end_date, "end_date")  # YYYY-MM-DD

        # Validate date format (YYYY-MM-DD)
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
    """
    Disable a recurring expense template.
    """
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


@app.route("/net-worth", methods=["GET", "POST"])
@login_required
def get_net_worth():
    assets = Asset.query.filter_by(user_id=current_user.id).order_by(Asset.id).all()
    liabilities = Liability.query.filter_by(user_id=current_user.id).order_by(Liability.id).all()
    assets_data = [a.to_dict() for a in assets]
    liabilities_data = [l.to_dict() for l in liabilities]
    total_assets = sum(convert_to_base(item['amount'], item.get('currency', 'INR')) for item in assets_data)
    total_liabilities = sum(convert_to_base(item['amount'], item.get('currency', 'INR')) for item in liabilities_data)
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
        currency = validate_string(data.get("currency", "INR"), "currency")
        date = data.get("date")
        if date:
            date = validate_string(date, "date")

        asset = Asset(name=name, amount=amount, user_id=current_user.id)

        
        asset = Asset(name=name, amount=amount, currency=currency, user_id=current_user.id)

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
        currency = validate_string(data.get("currency", "INR"), "currency")
        date = data.get("date")
        if date:
            date = validate_string(date, "date")

        liability = Liability(name=name, amount=amount, user_id=current_user.id)


        liability = Liability(name=name, amount=amount, currency=currency, user_id=current_user.id)

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
    try:
        data = request.json
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400


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


        result_text = response.choices[0].message.content.strip()

        

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

    
    total_spent = sum(convert_to_base(e.amount, e.currency) for e in expenses)
    limit_amount_inr = convert_to_base(limit.limit_amount, limit.currency)
    pct = total_spent / limit_amount_inr if limit_amount_inr > 0 else 0.0


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
                    currency=limit.currency,
                    user_id=user_id
                )
                db.session.add(alert)
                triggered.append(threshold)
                print(f"\n[EMAIL ALERT] Budget Alert: {category} spending reached {threshold}%\n", file=sys.stderr)

                # Add milestone notification
                title = f"Budget Alert: {threshold}% Limit Crossed"
                message = f"Your spending in category '{category}' has reached {threshold}% of your limit (₹{total_spent:,.2f} of ₹{limit_amount_inr:,.2f})."
                notification = MilestoneNotification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    category="budget",
                    ref_id=limit.id,
                    milestone_value=float(threshold)
                )
                db.session.add(notification)
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

            currency = validate_string(data.get("currency", "INR"), "currency")


            limit = BudgetLimit.query.filter_by(user_id=current_user.id, category=category).first()
            if limit:
                limit.limit_amount = limit_amount
                limit.currency = currency
            else:
                limit = BudgetLimit(user_id=current_user.id, category=category, limit_amount=limit_amount, currency=currency)
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

    limits_map = {l.category: (l.limit_amount, l.currency) for l in limits}
    
    expenses = Expense.query.filter(Expense.user_id == current_user.id, Expense.date.like(f"{year_month}%")).all()
    
    spent_by_category_inr = {}
    for e in expenses:
        spent_by_category_inr[e.category] = spent_by_category_inr.get(e.category, 0.0) + convert_to_base(e.amount, e.currency)
        
    status_list = []
    all_categories = set(limits_map.keys()) | set(spent_by_category_inr.keys())
    
    total_budgeted_inr = 0.0
    total_spent_inr = sum(spent_by_category_inr.values())


    for cat in sorted(all_categories):
        lim_orig, lim_curr = limits_map.get(cat, (0.0, 'INR'))
        lim_inr = convert_to_base(lim_orig, lim_curr)
        total_budgeted_inr += lim_inr
        
        spent_inr = spent_by_category_inr.get(cat, 0.0)
        pct = (spent_inr / lim_inr * 100) if lim_inr > 0 else 0.0
        status_list.append({
            "category": cat,
            "limit_amount": lim_orig,
            "currency": lim_curr,
            "spent": spent_inr,
            "percentage": round(pct, 2)
        })
    return jsonify({
        "month": year_month,
        "categories": status_list,
        "total_budgeted": total_budgeted_inr,
        "total_spent": total_spent_inr
    })

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
            milestones.append({"month": f"{y:04d}-{m:02d}", "target_amount_for_month": 0.0, "status": "completed"})
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
        milestones.append({"month": f"{y:04d}-{m:02d}", "target_amount_for_month": float(amounts[i]), "status": "planned"})
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


def check_goal_milestones(goal):
    if goal.target_amount <= 0:
        return
    pct = (goal.current_amount / goal.target_amount) * 100.0
    for threshold in [25.0, 50.0, 75.0, 100.0]:
        if pct >= threshold:
            exists = MilestoneNotification.query.filter_by(
                user_id=goal.user_id,
                category="goal",
                ref_id=goal.id,
                milestone_value=threshold
            ).first()
            if not exists:
                title = f"Goal Milestone Reached: {int(threshold)}%"
                message = f"Incredible! You have reached {int(threshold)}% of your target for your goal '{goal.name}' (₹{goal.current_amount:,.2f} of ₹{goal.target_amount:,.2f})."
                notification = MilestoneNotification(
                    user_id=goal.user_id,
                    title=title,
                    message=message,
                    category="goal",
                    ref_id=goal.id,
                    milestone_value=threshold
                )
                db.session.add(notification)
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
        currency = validate_string(data.get("currency", "INR"), "currency")
        target_date = validate_string(data.get("target_date"), "target_date")
        goal = FinancialGoal(
            user_id=current_user.id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            currency=currency,
            target_date=target_date
        )
        db.session.add(goal)
        db.session.commit()
        milestones = compute_monthly_milestones(goal)
        persist_goal_milestones(goal, milestones)

        check_goal_milestones(goal)


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
        else:
            data = request.json or {}
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")
            if "name" in data:
                goal.name = validate_string(data["name"], "name")
            if "target_amount" in data:
                goal.target_amount = validate_float(data["target_amount"], "target_amount", min_val=0.01)
            if "current_amount" in data:
                goal.current_amount = validate_float(data["current_amount"], "current_amount", min_val=0.0)
            if "currency" in data:
                goal.currency = validate_string(data["currency"], "currency")
            if "target_date" in data:
                goal.target_date = validate_string(data["target_date"], "target_date")
            db.session.commit()
            milestones = compute_monthly_milestones(goal)
            persist_goal_milestones(goal, milestones)

            check_goal_milestones(goal)


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


# ---------------- PERSONAL FINANCE MILESTONES & SIP ----------------
def check_sip_due_reminders():
    with app.app_context():
        import datetime
        today = datetime.date.today()
        day = today.day
        year_month_as_int = today.year * 100 + today.month

        schedules = SipSchedule.query.filter_by(is_active=True, day_of_month=day).all()

        for sip in schedules:
            if sip.last_notified_at:
                ln = sip.last_notified_at.date()
                if ln.year == today.year and ln.month == today.month:
                    continue

            title = f"SIP Payment Due: {sip.name}"
            message = f"Your monthly SIP payment of {sip.currency} {sip.amount:,.2f} for '{sip.name}' is due today."
            notification = MilestoneNotification(
                user_id=sip.user_id,
                title=title,
                message=message,
                category="sip",
                ref_id=sip.id,
                milestone_value=float(year_month_as_int)
            )
            db.session.add(notification)
            sip.last_notified_at = datetime.datetime.utcnow()

        db.session.commit()

@app.route("/milestones")
@login_required
def milestones_page():
    return render_template("milestones.html", active_page="milestones")

@app.route("/api/milestones", methods=["GET"])
@login_required
def get_milestone_notifications():
    try:
        unread_only = request.args.get("unread_only", "false").lower() == "true"
        query = MilestoneNotification.query.filter_by(user_id=current_user.id)
        if unread_only:
            query = query.filter_by(is_read=False)
        notifications = query.order_by(MilestoneNotification.triggered_at.desc()).all()
        return jsonify([n.to_dict() for n in notifications])
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/milestones/read", methods=["POST"])
@login_required
def mark_milestones_read():
    try:
        data = request.json or {}
        notif_id = data.get("id")
        if notif_id:
            notification = MilestoneNotification.query.filter_by(id=notif_id, user_id=current_user.id).first()
            if notification:
                notification.is_read = True
        else:
            MilestoneNotification.query.filter_by(user_id=current_user.id).update({"is_read": True})
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/sip/schedules", methods=["GET"])
@login_required
def get_sip_schedules():
    try:
        schedules = SipSchedule.query.filter_by(user_id=current_user.id).all()
        return jsonify([s.to_dict() for s in schedules])
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/sip/schedules", methods=["POST"])
@login_required
def create_sip_schedule():
    try:
        data = request.json or {}
        if not data or "name" not in data or "amount" not in data or "day_of_month" not in data:
            return jsonify({"error": "Missing required fields"}), 400
        name = validate_string(data["name"], "name")
        amount = validate_float(data["amount"], "amount", min_val=0.01)
        day_of_month = validate_int(data["day_of_month"], "day_of_month", min_val=1, max_val=28)
        currency = validate_string(data.get("currency", "INR"), "currency")

        schedule = SipSchedule(
            user_id=current_user.id,
            name=name,
            amount=amount,
            day_of_month=day_of_month,
            currency=currency,
            is_active=True
        )
        db.session.add(schedule)
        db.session.commit()
        return jsonify(schedule.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/sip/schedules/<int:schedule_id>", methods=["DELETE"])
@login_required
def delete_sip_schedule(schedule_id):
    try:
        schedule = SipSchedule.query.filter_by(id=schedule_id, user_id=current_user.id).first()
        if not schedule:
            return jsonify({"error": "SIP schedule not found"}), 404
        db.session.delete(schedule)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/sip/schedules/<int:schedule_id>/pay", methods=["POST"])
@login_required
def pay_sip_installment(schedule_id):
    try:
        schedule = SipSchedule.query.filter_by(id=schedule_id, user_id=current_user.id).first()
        if not schedule:
            return jsonify({"error": "SIP schedule not found"}), 404
        
        old_total = schedule.total_invested
        schedule.total_invested += schedule.amount
        
        # Check compounding milestones (10k, 50k, 100k, 500k, 1m)
        for milestone in [10000.0, 50000.0, 100000.0, 500000.0, 1000000.0]:
            if old_total < milestone <= schedule.total_invested:
                title = f"SIP Milestone Reached: {schedule.currency} {milestone:,.0f}"
                message = f"Amazing! Your total investments in SIP '{schedule.name}' have reached {schedule.currency} {schedule.total_invested:,.2f}."
                notification = MilestoneNotification(
                    user_id=current_user.id,
                    title=title,
                    message=message,
                    category="sip",
                    ref_id=schedule.id,
                    milestone_value=float(milestone)
                )
                db.session.add(notification)
        
        db.session.commit()
        return jsonify({"status": "success", "schedule": schedule.to_dict()})
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

        # Get all alerts since we want to check even those where is_triggered is True if cooldown_days is set
        alerts = PriceAlert.query.all()


        max_retries = 3
        base_delay_sec = 1.0
        for alert in alerts:
            # Skip if triggered and cooldown is not enabled
            if alert.is_triggered and (alert.cooldown_days is None or alert.cooldown_days == 0):
                continue

            # Check cooldown condition
            from datetime import datetime as _dt, timedelta
            now = _dt.utcnow()
            if alert.last_triggered_at and alert.cooldown_days and alert.cooldown_days > 0:
                cooldown_until = alert.last_triggered_at + timedelta(days=alert.cooldown_days)
                if now < cooldown_until:
                    # Still in cooldown, skip checking
                    continue

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

                prev_price = alert.last_checked_price
                operator = alert.operator_type or alert.condition or "above"

                condition_met = False
                if operator == "above":
                    condition_met = (current_price >= alert.target_price)
                elif operator == "below":
                    condition_met = (current_price <= alert.target_price)
                elif operator == "cross":
                    if prev_price is not None:
                        condition_met = (prev_price < alert.target_price and current_price >= alert.target_price) or \
                                        (prev_price > alert.target_price and current_price <= alert.target_price)
                elif operator == "cross_above":
                    if prev_price is not None:
                        condition_met = (prev_price < alert.target_price and current_price >= alert.target_price)
                elif operator == "cross_below":
                    if prev_price is not None:
                        condition_met = (prev_price > alert.target_price and current_price <= alert.target_price)

                # Store current price as last checked for next comparison
                alert.last_checked_price = current_price

                if condition_met:
                    # Increment consecutive meets
                    alert.consecutive_polls_met += 1
                    
                    required_consecutive = alert.duration_days or 0
                    trigger_confirmed = False
                    if required_consecutive == 0:
                        trigger_confirmed = True
                    elif alert.consecutive_polls_met >= required_consecutive:
                        trigger_confirmed = True

                    if trigger_confirmed:
                        alert.is_triggered = True
                        alert.last_triggered_at = now
                        alert.consecutive_polls_met = 0

                        reason_str = f"Condition '{operator}' met at {current_price}."
                        if prev_price is not None:
                            reason_str += f" (Previous: {prev_price})"
                        if required_consecutive > 0:
                            reason_str += f" Confirmed over {required_consecutive} consecutive checks."

                        event = PriceAlertEvent(
                            alert_id=alert.id,
                            triggered_at=now,
                            price=current_price,
                            prev_price=prev_price,
                            reason=reason_str,
                            condition=alert.condition,
                            symbol=alert.symbol,
                        )
                        db.session.add(event)

                        print(f"\n[STOCK ALERT] Triggered for {alert.symbol}: {reason_str}\n", file=sys.stderr)
                else:
                    # Reset counter if condition is not met
                    alert.consecutive_polls_met = 0


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

# ---------------- ADDITIONAL SCHEDULERS ----------------
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_budgets_job, 'interval', days=1)
    scheduler.add_job(check_all_recurring_expenses_job, 'interval', days=1)
    scheduler.add_job(check_stock_alerts_job, 'interval', minutes=10)
    scheduler.start()


# ---------------- WEB SOCKET EVENTS ----------------
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        room = f'user_{current_user.id}'
        join_room(room)
        emit('connected', {'status': 'connected', 'user_id': current_user.id})

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        room = f'user_{current_user.id}'
        leave_room(room)

# ---------------- TAX OPTIMIZATION ----------------
@app.route("/tax-optimize", methods=["POST"])
def tax_optimize():
    data = request.get_json()
    income = data.get("income", 0)
    expenses = data.get("expenses", {})
    investments = data.get("investments", {})
    if not income or income <= 0:
        return jsonify({"error": "Please provide a valid income."}), 400
    result = tax_optimization_module(income, expenses, investments)
    return jsonify(result)


# ---------------- LEDGER SYSTEM ----------------
from utils.ledger import LedgerSystem




# ---------------- DASHBOARD DATA ----------------
@app.route("/dashboard-data")
@login_required
def dashboard_data():
    try:
        net_worth = sum(a.amount for a in Asset.query.filter_by(user_id=current_user.id).all()) - sum(l.amount for l in Liability.query.filter_by(user_id=current_user.id).all())
        monthly_expenses = [e.to_dict() for e in Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id.desc()).limit(10).all()]
        budget_alert_count = len([b for b in BudgetAlert.query.filter_by(user_id=current_user.id).all()])
        goal_count = len([g for g in FinancialGoal.query.filter_by(user_id=current_user.id).all()])
        portfolio_items = Portfolio.query.filter_by(user_id=current_user.id).all()
        allocation = {}
        for item in portfolio_items:
            value = item.quantity * item.buy_price
            allocation[item.investment_type] = allocation.get(item.investment_type, 0) + value
        total = sum(allocation.values())
        allocation_percentages = {k: round(v * 100 / total, 2) for k, v in allocation.items()} if total > 0 else {}
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
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id.desc()).limit(5).all()
    for e in expenses:
        activities.append({"type": "expense", "message": f"Added expense: {e.category} ₹{e.amount}", "date": e.date})
    assets = Asset.query.filter_by(user_id=current_user.id).order_by(Asset.id.desc()).limit(5).all()
    for a in assets:
        activities.append({"type": "asset", "message": f"Added asset: {a.name} ₹{a.amount}", "date": a.date})
    goals = FinancialGoal.query.filter_by(user_id=current_user.id).order_by(FinancialGoal.created_at.desc()).limit(5).all()
    for g in goals:
        activities.append({"type": "goal", "message": f"Created goal: {g.name}", "date": g.created_at.isoformat()})
    activities = sorted(activities, key=lambda x: x["date"], reverse=True)
    return jsonify(activities[:10])

# ---------------- API ALERTS ----------------
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


# ---------------- DASHBOARD DATA ----------------
@app.route("/dashboard-data")
@login_required
def dashboard_data():
    try:
        net_worth = sum(a.amount for a in Asset.query.filter_by(user_id=current_user.id).all()) - sum(l.amount for l in Liability.query.filter_by(user_id=current_user.id).all())
        monthly_expenses = [e.to_dict() for e in Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id.desc()).limit(10).all()]
        budget_alert_count = len([b for b in BudgetAlert.query.filter_by(user_id=current_user.id).all()])
        goal_count = len([g for g in FinancialGoal.query.filter_by(user_id=current_user.id).all()])
        portfolio_items = Portfolio.query.filter_by(user_id=current_user.id).all()
        allocation = {}
        for item in portfolio_items:
            value = item.quantity * item.buy_price
            allocation[item.investment_type] = allocation.get(item.investment_type, 0) + value
        total = sum(allocation.values())
        allocation_percentages = {k: round(v * 100 / total, 2) for k, v in allocation.items()} if total > 0 else {}
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
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.id.desc()).limit(5).all()
    for e in expenses:
        activities.append({"type": "expense", "message": f"Added expense: {e.category} ₹{e.amount}", "date": e.date})
    assets = Asset.query.filter_by(user_id=current_user.id).order_by(Asset.id.desc()).limit(5).all()
    for a in assets:
        activities.append({"type": "asset", "message": f"Added asset: {a.name} ₹{a.amount}", "date": a.date})
    goals = FinancialGoal.query.filter_by(user_id=current_user.id).order_by(FinancialGoal.created_at.desc()).limit(5).all()
    for g in goals:
        activities.append({"type": "goal", "message": f"Created goal: {g.name}", "date": g.created_at.isoformat()})
    activities = sorted(activities, key=lambda x: x["date"], reverse=True)
    return jsonify(activities[:10])

# ---------------- FINANCIAL RATIO ANALYZER ----------------
from utils.financial_ratio_analyzer import FinancialRatioAnalyzer

@app.route('/ratio-analyzer')
@login_required
def ratio_analyzer_page():
    """Financial Ratio Analysis Dashboard"""
    return render_template('ratio_analyzer.html', active_page='ratio_analyzer')

@app.route('/api/ratios/analyze', methods=['POST'])
@login_required
def analyze_ratios():
    """Analyze financial ratios"""
    try:
        data = request.json
        financial_data = data.get('financial_data', {})
        industry = data.get('industry', 'general')
        
        # Create analyzer
        analyzer = FinancialRatioAnalyzer(financial_data)
        
        # Generate report
        report = analyzer.generate_report(industry)
        
        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


        # ---------------- DASHBOARD WIDGETS ----------------
from utils.dashboard_widgets import DashboardWidgetManager

@app.route('/dashboard-new')
@login_required
def dashboard_new():
    """Customizable Dashboard"""
    return render_template('dashboard_new.html', active_page='dashboard_new')

@app.route('/api/dashboard/layouts', methods=['POST'])
@login_required
def save_dashboard_layout():
    try:
        data = request.json
        layout_id = data.get('layout_id', 'default')
        widgets = data.get('widgets', [])
        
        manager = DashboardWidgetManager(current_user.id)
        result = manager.save_layout(layout_id, widgets)
        
        return jsonify({
            'success': True,
            'layout': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/layouts', methods=['GET'])
@login_required
def get_dashboard_layouts():
    try:
        manager = DashboardWidgetManager(current_user.id)
        return jsonify({
            'success': True,
            'layouts': manager.get_layouts()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/widget/<widget_id>', methods=['GET'])
@login_required
def get_widget_data(widget_id):
    try:
        # Fetch user data from database
        # For demo, return sample data
        sample_data = {
            'net_worth': {
                'total_assets': 1500000,
                'total_liabilities': 400000,
                'net_worth': 1100000,
                'change': 12.5
            },
            'spending_trend': {
                'current_month': 45000,
                'previous_month': 52000,
                'trend': [12000, 11000, 9500, 8000, 4500],
                'change_percent': -13.5
            },
            'budget_health': {
                'total_budget': 60000,
                'total_spent': 45000,
                'remaining': 15000,
                'health_percent': 75,
                'categories': [
                    {'name': 'Food', 'spent': 12000, 'budget': 15000},
                    {'name': 'Transport', 'spent': 8000, 'budget': 10000},
                    {'name': 'Shopping', 'spent': 5000, 'budget': 8000}
                ]
            },
            'recent_transactions': {
                'transactions': [
                    {'category': 'Food', 'date': '2026-06-24', 'amount': -450},
                    {'category': 'Rent', 'date': '2026-06-23', 'amount': -12000},
                    {'category': 'Salary', 'date': '2026-06-22', 'amount': 50000},
                    {'category': 'Transport', 'date': '2026-06-21', 'amount': -300}
                ]
            },
            'portfolio_summary': {
                'total_value': 500000,
                'returns': 8.5,
                'holdings': [
                    {'symbol': 'AAPL', 'value': 150000, 'percent': 30},
                    {'symbol': 'GOOGL', 'value': 120000, 'percent': 24},
                    {'symbol': 'TSLA', 'value': 100000, 'percent': 20}
                ]
            },
            'goals_progress': {
                'goals': [
                    {'name': 'Vacation', 'target': 200000, 'current': 120000, 'progress': 60},
                    {'name': 'Emergency Fund', 'target': 300000, 'current': 200000, 'progress': 67},
                    {'name': 'Car', 'target': 500000, 'current': 250000, 'progress': 50}
                ]
            },
            'cash_flow': {
                'income': 80000,
                'expenses': 45000,
                'net': 35000
            }
        }
        
        data = sample_data.get(widget_id, {'message': 'No data available'})
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# ---------------- API ALERTS ----------------
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

\\
        return jsonify({'error': str(e)}), 400
        

# ---------------- PORTFOLIO TRACKER ----------------
@app.route("/portfolio-page")
@login_required
def portfolio_page():
    return render_template("portfolio.html", active_page="portfolio")



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
                "currency": h.currency,
                "current_price": current_price,
                "invested_value": round(invested_val, 2),
                "current_value": round(current_val, 2),
                "pnl": round(pnl, 2),
                "pnl_percent": round(pnl_percent, 2),
                "dividends_received": round(divs_received, 2),
                "annual_dividend_per_share": round(annual_div_per_share, 2),
                "yoc": round(yoc, 2)
            })
            
            total_invested += convert_to_base(invested_val, h.currency)
            total_current += convert_to_base(current_val, h.currency)
            total_dividends_received += convert_to_base(divs_received, h.currency)
            total_annual_dividends_value += convert_to_base(annual_div_per_share * h.quantity, h.currency)
            
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
                                "amount": convert_to_base(d["amount"] * h.quantity, h.currency),
                                "currency": h.currency
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

@app.route("/api/alerts/reset", methods=["POST"])
@login_required
def alerts_reset():
    try:

        PriceAlert.query.filter_by(user_id=current_user.id).update({"is_triggered": False, "last_triggered_at": None, "last_check_error": None})
        user_alert_ids = [a.id for a in PriceAlert.query.filter_by(user_id=current_user.id).all()]
        if user_alert_ids:
            PriceAlertEvent.query.filter(PriceAlertEvent.alert_id.in_(user_alert_ids)).delete(synchronize_session=False)


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

        currency = validate_string(data.get("currency", "INR"), "currency").strip().upper()

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
            currency=currency,
            notes=notes
        )
        db.session.add(holding)

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


# Tax Optimization Module
@app.route("/tax-optimize", methods=["POST"])
def tax_optimize():
    data = request.get_json()
    income = data.get("income", 0)
    expenses = data.get("expenses", {})
    investments = data.get("investments", {})
    if not income or income <= 0:
        return jsonify({"error": "Please provide a valid income."}), 400
    result = tax_optimization_module(income, expenses, investments)
    return jsonify(result)



# ---------------- ADDITIONAL SCHEDULERS ----------------
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_budgets_job, 'interval', days=1)
    scheduler.add_job(check_all_recurring_expenses_job, 'interval', days=1)
    scheduler.add_job(check_stock_alerts_job, 'interval', minutes=10)
    scheduler.add_job(check_sip_due_reminders, 'interval', days=1)
    scheduler.start()


# ---------------- RUN ----------------
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    socketio.run(app, debug=debug_mode, host="0.0.0.0", port=5000)