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
        "\n[ERROR] GROQ_API_KEY is not configured.\n"
        "  1. Copy .env.example to .env\n"
        "  2. Set your GROQ_API_KEY in .env\n"
        "  Obtain a free key at: https://console.groq.com/\n",
        file=sys.stderr,
    )
    sys.exit(1)
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
from models import db, Expense, Asset, Liability

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///money_mentor.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- INIT GROQ ----------------
client = Groq(api_key=GROQ_API_KEY)

# ── Dev-mode startup message ─────────────────────────────────
if os.getenv("FLASK_ENV", "development") != "production":
    print("[OK] Groq client initialised successfully.")
# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


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
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        msg = data.get("message")
        history = data.get("history", [])

        # Build messages: system prompt + last 10 history turns + current message
        messages = [{"role": "system", "content": "You are a financial advisor for India."}]
        messages += history[-10:]
        messages.append({"role": "user", "content": msg})

        res = client.chat.completions.create(

    model="llama-3.1-8b-instant",
    messages=[
        {
            "role": "system",
            "content": """
You are an expert AI financial advisor for Indian users.

            model="llama-3.1-8b-instant",
            messages=messages
        )


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
- Friendly, practical, and easy to understand
"""
        },
        {"role": "user", "content": msg}
    ]
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
@app.route("/sip", methods=["POST"])
def sip():
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
@app.route("/tax", methods=["POST"])
def tax():
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
        query = request.json["query"]
        response = run_multi_agent(client, query)
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- 💰 MONEY SCORE ----------------
@app.route("/money-score", methods=["POST"])
def money_score():
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
    assets_data = [a.to_dict(i) for i, a in enumerate(assets)]
    liabilities_data = [l.to_dict(i) for i, l in enumerate(liabilities)]
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
        item_type = data["type"] # 'asset' or 'liability'
        item_id = int(data["id"]) # positional index from the frontend

        if item_type == 'asset':
            rows = Asset.query.order_by(Asset.id).all()
            db.session.delete(rows[item_id])
        else:
            rows = Liability.query.order_by(Liability.id).all()
            db.session.delete(rows[item_id])

        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- RUN ----------------
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    app.run(debug=debug_mode)
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

    app.run(debug=debug_mode)

