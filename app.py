from flask import Flask, request, jsonify, render_template
import yfinance as yf
import os
import logging
from groq import Groq

# ---------------- 🔐 SET API KEY ----------------
# Set GROQ API key via environment variable (recommended for production)
os.environ.setdefault("GROQ_API_KEY", "YOUR_API_KEY")

# ---------------- IMPORT UTILS ----------------
from utils.sip import calculate_sip
from utils.tax import calculate_tax
from utils.pdf_parser import extract_income
from utils.money_score import calculate_money_score
from utils.multi_agent import run_multi_agent

app = Flask(__name__)

# ---------------- INIT GROQ ----------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- 🤖 AI CHAT ----------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        msg = request.json.get("message")

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a financial advisor for India."},
                {"role": "user", "content": msg}
            ]
        )

        return jsonify({"reply": res.choices[0].message.content})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})


# ---------------- 💸 SIP ----------------
@app.route("/sip", methods=["POST"])
def sip():
    try:
        data = request.json

        # ✅ Validation (safe check)
        if (
            "monthly" not in data or
            "rate" not in data or
            "years" not in data
        ):
            return jsonify({"error": "Missing input values"})

        if data["monthly"] <= 0 or data["rate"] <= 0 or data["years"] <= 0:
            return jsonify({"error": "Invalid SIP input values"})

        result = calculate_sip(
            float(data["monthly"]),
            float(data["rate"]),
            int(data["years"])
        )

        return jsonify({"future_value": result})

    except Exception as e:
        return jsonify({"error": str(e)})

# ---------------- 📊 STOCK ----------------
@app.route("/portfolio", methods=["POST"])
def portfolio():
    try:
        stock = request.json["stock"].strip().upper()

        # Add .NS for Indian stocks (important!)
        if not stock.endswith(".NS"):
            stock = stock + ".NS"

        data = yf.Ticker(stock)
        hist = data.history(period="5d")

        if hist.empty:
            return jsonify({"error": "Invalid stock symbol"})

        price = hist["Close"].iloc[-1]

        return jsonify({"price": round(price, 2)})

    except Exception as e:
    print("Error:", e)
    return jsonify({"error": "Internal server error"})
    
# ---------------- 💸 TAX ----------------
@app.route("/tax", methods=["POST"])
def tax():
    try:
        income = float(request.json["income"])
        return jsonify({"tax": calculate_tax(income)})

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
        response = run_multi_agent(query)
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
        
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
