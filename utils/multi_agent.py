# utils/multi_agent.py

from groq import Groq
import os
import re

from .sip import calculate_sip
from .tax import calculate_tax
from .stock import get_stock_price
from .money_score import calculate_money_score

# ✅ CORRECT WAY
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- 🔍 ROUTER ----------------
def route_query(query):
    query = query.lower()

    if any(word in query for word in ["sip", "mutual fund", "investment"]):
        return "SIP"

    elif any(word in query for word in ["tax", "income tax", "itr"]):
        return "TAX"

    elif any(word in query for word in ["stock", "share", "price"]):
        return "STOCK"

    elif any(word in query for word in ["score", "financial health", "money score"]):
        return "SCORE"

    else:
        return "AI"


# ---------------- 🤖 AI AGENT ----------------
def ai_agent(query):
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a smart financial advisor for India."},
                {"role": "user", "content": query}
            ]
        )
        return res.choices[0].message.content
    except Exception as e:
        print("AI ERROR:", e)
        return "AI service error ❌"


# ---------------- 📈 SIP ----------------
def sip_agent(query):
    try:
        nums = list(map(float, re.findall(r"\d+", query)))

        if len(nums) >= 3:
            monthly, rate, years = nums[0], nums[1], int(nums[2])
            result = calculate_sip(monthly, rate, years)
            return f"SIP Future Value: ₹ {round(result, 2)}"

        return "Provide: SIP amount, rate, years"

    except Exception as e:
        print("SIP ERROR:", e)
        return "SIP error ❌"


# ---------------- 💸 TAX ----------------
def tax_agent(query):
    try:
        income = float(re.findall(r"\d+", query)[0])
        tax = calculate_tax(income)
        return f"Estimated Tax: ₹ {tax}"

    except Exception as e:
        print("TAX ERROR:", e)
        return "Provide valid income"


# ---------------- 📊 STOCK ----------------
def stock_agent(query):
    try:
        symbol = query.split()[-1].upper()
        price = get_stock_price(symbol)

        if price:
            return f"{symbol} Price: ₹ {price}"

        return "Invalid stock symbol"

    except Exception as e:
        print("STOCK ERROR:", e)
        return "Stock error ❌"


# ---------------- 💰 SCORE ----------------
def score_agent(query):
    try:
        nums = list(map(float, re.findall(r"\d+", query)))

        if len(nums) >= 6:
            score = calculate_money_score(*nums[:6])

            if score >= 80:
                status = "Excellent 💚"
            elif score >= 60:
                status = "Good 👍"
            elif score >= 40:
                status = "Average ⚠️"
            else:
                status = "Needs Improvement ❌"

            return f"Money Score: {score} | {status}"

        return "Provide 6 values (income, expenses, savings, investments, debt, emergency)"

    except Exception as e:
        print("SCORE ERROR:", e)
        return "Score error ❌"


# ---------------- 🧠 MAIN ----------------
def run_multi_agent(query):
    task = route_query(query)

    print("ROUTED TO:", task)   # ✅ DEBUG

    if task == "SIP":
        return sip_agent(query)

    elif task == "TAX":
        return tax_agent(query)

    elif task == "STOCK":
        return stock_agent(query)

    elif task == "SCORE":
        return score_agent(query)

    else:
        return ai_agent(query)