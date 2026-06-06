from flask import Flask, request, jsonify, render_template
import yfinance as yf
import os
import sys
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# ── Startup validation ───────────────────────────────────────
# Fail fast and clearly if the required API key is missing.
# Copy .env.example → .env and set your GROQ_API_KEY.
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
# ---------------- IMPORT UTILS ----------------
from utils.sip import calculate_sip
from utils.tax import calculate_tax
from utils.pdf_parser import extract_income
from utils.money_score import calculate_money_score
from utils.multi_agent import run_multi_agent
from utils.stock import get_stock_price
from utils.expense_track import calculate_expense, insights

app = Flask(__name__)

# ---------------- INIT DATABASE ----------------
from models import db, Expense, Asset, Liability, BudgetLimit, BudgetAlert

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///money_mentor.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- INIT GROQ ----------------
# client is initialized in the startup validation block above

# ── Dev-mode startup message ─────────────────────────────────
if os.getenv("FLASK_ENV", "development") != "production":
    if client:
        print("[OK] Groq client initialised successfully.")
    else:
        print("[WARNING] Groq client is running in offline mode.")
# ---------------- HOME / PAGES ----------------
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


# ---------------- HEALTH CHECK ----------------
@app.route("/health", methods=["GET"])
def health_check():
    """Lightweight liveness probe for deployment environments (Docker, Railway, etc.)."""
    return jsonify({"status": "ok", "service": "AI Money Mentor"}), 200


# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad Request",
        "message": str(error),
        "status_code": 400
    }), 400


@app.errorhandler(404)
def not_found(error):
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


# ---------------- 🤖 AI CHAT ----------------
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return render_template("chat.html", active_page="chat")
    try:
        if client is None:
            return jsonify({
                "reply": "AI Money Mentor is offline because GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your env/config files."
            })

        data = request.json
        msg = data.get("message")
        history = data.get("history", [])

        # Build messages: system prompt + last 10 history turns + current message
        system_content = """You are an expert AI financial advisor for Indian users.

Your job:
- Help users manage money smartly
- Teach budgeting, saving, and investing
- Give simple, practical, real-life advice

Response rules:
- Always use structured format:

Income / Situation Summary:
- ...

Budget Breakdown (if applicable):
- Needs: 50%
- Wants: 30%
- Savings: 20%

Advice:
- Give clear steps
- Keep it simple and actionable

Tone:
- Friendly, practical, and easy to understand"""

        messages = [{"role": "system", "content": system_content}]
        for h in history[-10:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": msg})

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages
        )
        return jsonify({
            "reply": res.choices[0].message.content
        })

    except Exception as e:
        app.logger.error(f"Groq API Error: {str(e)}")

        return jsonify({
            "reply": "Unable to generate a response at the moment. Please try again later."
        }), 500


# ---------------- 💸 SIP ----------------
@app.route("/sip", methods=["GET", "POST"])
def sip():
    if request.method == "GET":
        return render_template("sip.html", active_page="sip")
    try:
        data = request.json
        result = calculate_sip(
            float(data["monthly"]),
            float(data["rate"]),
            int(data["years"]),
            float(data.get("inflation", 0.0))
        )
        return jsonify({
            "future_value": result["nominal_value"],
            "nominal_value": result["nominal_value"],
            "inflation_adjusted_value": result["inflation_adjusted_value"],
            "inflation_applied": result["inflation_applied"]
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- 📊 STOCK ----------------
@app.route("/portfolio", methods=["POST"])
def portfolio():
    try:
        stock = request.json["stock"].upper()
        result = get_stock_price(stock)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})
    
# ---------------- 💸 TAX ----------------
@app.route("/tax", methods=["GET", "POST"])
def tax():
    if request.method == "GET":
        return render_template("tax.html", active_page="tax")
    try:
        data = request.json
        income = float(data["income"])
        deduction_80c = float(data.get("deduction_80c", 0.0))
        deduction_80d = float(data.get("deduction_80d", 0.0))
        deduction_hra = float(data.get("deduction_hra", 0.0))
        
        result = calculate_tax(
            income,
            deduction_80c=deduction_80c,
            deduction_80d=deduction_80d,
            deduction_hra=deduction_hra
        )
        return jsonify({"tax": result})

    except Exception as e:
        return jsonify({"error": str(e)})


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
    try:
        if client is None:
            return jsonify({
                "error": "AI Multi-Agent is offline because GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your env/config files."
            })
        query = request.json["query"]
        response = run_multi_agent(client, query)
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- 💰 MONEY SCORE ----------------
@app.route("/money-score", methods=["GET", "POST"])
def money_score():
    if request.method == "GET":
        return render_template("score.html", active_page="score")
    try:
        data = request.json

        score = calculate_money_score(
            float(data["income"]),
            float(data["expenses"]),
            float(data["savings"]),
            float(data["investments"]),
            float(data["debt"]),
            float(data["emergency"])
        )

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

    except Exception as e:
        return jsonify({"error": str(e)})


# Expense Tracker Features

@app.route("/add_expense", methods=["POST"])
def add_expense():
    try:
        data = request.json
        expense = Expense(
            category=data["category"],
            amount=float(data["amount"]),
            date=data["date"]
        )
        db.session.add(expense)
        db.session.commit()
        
        # Check thresholds
        ym = expense.date[:7] if len(expense.date) >= 7 else None
        run_threshold_checks(expense.category, ym)
        
        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/calculate", methods=["GET"])
def calculate():
    expense_data = [e.to_dict() for e in Expense.query.order_by(Expense.id).all()]
    result = calculate_expense(expense_data)
    result["expenses"] = expense_data
    return jsonify(result)

@app.route("/insights", methods=["GET"])
def expense_insights():
    expense_data = [e.to_dict() for e in Expense.query.order_by(Expense.id).all()]
    result =insights(client,expense_data)
    return jsonify(result)

# ---------------- NET WORTH TRACKER ----------------
# Net Worth Tracker Features

@app.route("/net-worth", methods=["GET", "POST"])
def get_net_worth():
    assets = Asset.query.order_by(Asset.id).all()
    liabilities = Liability.query.order_by(Liability.id).all()

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
def add_asset():
    try:
        data = request.json
        asset = Asset(name=data["name"], amount=float(data["amount"]))
        db.session.add(asset)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/add-liability", methods=["POST"])
def add_liability():
    try:
        data = request.json
        liability = Liability(name=data["name"], amount=float(data["amount"]))
        db.session.add(liability)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/delete-item", methods=["POST"])
def delete_item():
    try:
        data = request.json
        item_type = data["type"]
        item_id = int(data["id"])

        if item_type == "asset":
            item = Asset.query.get(item_id)
        elif item_type == "liability":
            item = Liability.query.get(item_id)
        else:
            return jsonify({"error": "Invalid item type"}), 400

        if item is None:
            return jsonify({"error": "Item not found"}), 404

        db.session.delete(item)
        db.session.commit()

        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Helper to check budget thresholds
def run_threshold_checks(category, year_month=None):
    if not year_month:
        import datetime
        year_month = datetime.datetime.now().strftime("%Y-%m")
        
    limit = BudgetLimit.query.filter_by(category=category).first()
    if not limit or limit.limit_amount <= 0:
        return []
        
    expenses = Expense.query.filter(
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
                category=category,
                year_month=year_month,
                threshold=threshold
            ).first()
            if not exists:
                alert = BudgetAlert(
                    category=category,
                    year_month=year_month,
                    threshold=threshold
                )
                db.session.add(alert)
                triggered.append(threshold)
                print(
                    f"\n[EMAIL ALERT] To: user@example.com\n"
                    f"Subject: Budget Alert: {category} spending reached {threshold}%\n"
                    f"Body: You have spent ₹{total_spent:.2f} of your ₹{limit.limit_amount:.2f} limit in category '{category}'.\n",
                    file=sys.stderr
                )
    if triggered:
        db.session.commit()
    return triggered


# ---------------- SMART BUDGET ALERTS ----------------

@app.route("/budget/limits", methods=["GET", "POST"])
def budget_limits():
    if request.method == "POST":
        try:
            data = request.json
            category = data["category"]
            limit_amount = float(data["limit_amount"])
            
            limit = BudgetLimit.query.filter_by(category=category).first()
            if limit:
                limit.limit_amount = limit_amount
            else:
                limit = BudgetLimit(category=category, limit_amount=limit_amount)
                db.session.add(limit)
            db.session.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        limits = BudgetLimit.query.order_by(BudgetLimit.category).all()
        return jsonify([l.to_dict() for l in limits])

@app.route("/budget/status", methods=["GET"])
def budget_status():
    import datetime
    year_month = request.args.get("month", datetime.datetime.now().strftime("%Y-%m"))
    
    limits = BudgetLimit.query.all()
    limits_dict = {l.category: l.limit_amount for l in limits}
    
    expenses = Expense.query.filter(Expense.date.like(f"{year_month}%")).all()
    
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

@app.route("/budget/alerts", methods=["GET"])
def budget_alerts():
    alerts = BudgetAlert.query.order_by(BudgetAlert.triggered_at.desc()).limit(10).all()
    return jsonify([a.to_dict() for a in alerts])


# ---------------- SCHEDULER ----------------
from apscheduler.schedulers.background import BackgroundScheduler

def check_all_budgets_job():
    with app.app_context():
        import datetime
        ym = datetime.datetime.now().strftime("%Y-%m")
        limits = BudgetLimit.query.all()
        for limit in limits:
            run_threshold_checks(limit.category, ym)

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_budgets_job, 'interval', days=1)
    scheduler.start()


# ---------------- RUN ----------------
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode)

