from flask import Flask, request, jsonify, render_template
import yfinance as yf
import os
import sys
from groq import Groq
from dotenv import load_dotenv

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
        system_prompt = (
            "You are an expert AI financial advisor for Indian users.\n\n"
            "Your job:\n"
            "- Help users manage money smartly\n"
            "- Teach budgeting, saving, and investing\n"
            "- Give simple, practical, real-life advice\n\n"
            "Response rules:\n"
            "- Always use structured format:\n"
            "Income / Situation Summary:\n"
            "- ...\n"
            "Budget Breakdown (if applicable):\n"
            "- Needs: 50%\n"
            "- Wants: 30%\n"
            "- Savings: 20%\n"
            "Advice:\n"
            "- Give clear steps\n"
            "- Keep it simple and actionable\n\n"
            "Tone:\n"
            "- Friendly, practical, and easy to understand"
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages += history[-10:]
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
        
        tax_details = calculate_tax(
            income,
            deduction_80c=deduction_80c,
            deduction_80d=deduction_80d,
            deduction_hra=deduction_hra
        )
        
        # AI Tax-saving advice
        recommendations = "You are already in the zero-tax bracket! No additional tax-saving investments are required."
        
        recommended_regime = tax_details.get("recommended", "New Regime")
        regime_key = "new_regime" if recommended_regime == "New Regime" else "old_regime"
        total_tax = tax_details.get(regime_key, {}).get("total_tax", 0.0)
        
        # Only query AI if there is actual tax payable and client is available
        if total_tax > 0.0 and client:
            prompt = (
                f"A user in India has a gross annual income of ₹{income:,} and has a total tax liability of "
                f"₹{total_tax:,} under the recommended {recommended_regime}.\n\n"
                f"Generate a customized list of tax-saving investment recommendations for them. "
                f"Suggest specific options under Section 80C (up to 1.5L, e.g. ELSS, PPF), Section 80CCD(1B) (up to 50k in NPS), "
                f"and Section 80D (Health Insurance). Be brief and format the response as a bulleted list with clear estimated tax savings."
            )
            
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
    if not client:
        return jsonify({
            "error": "AI Agent is offline: GROQ_API_KEY is not configured on the server."
        })
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
    if not client:
        # Calculate standard expenses metrics but return fallback AI insights content
        totals = calculate_expense(expense_data)
        return jsonify({
            "insights": "<div class=\"insight-card\"><h3>AI Insights Offline</h3><p>Personalized AI savings suggestions are currently offline because the GROQ_API_KEY is not configured on the server. Please configure it to enable insights.</p></div>",
            "summary": totals
        })
    result = insights(client, expense_data)
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
        item_type = data["type"]  # 'asset' or 'liability'
        item_db_id = int(data["id"])  # stable database id from the frontend

        if item_type == "asset":
            item = Asset.query.get(item_db_id)
        else:
            item = Liability.query.get(item_db_id)

        if not item:
            return jsonify({"error": f"Item not found (type={item_type}, id={item_db_id})"}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- RUN ----------------
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode)


