# utils/multi_agent.py

from groq import Groq
import os
import re

from .sip import calculate_sip
from .tax import calculate_tax
from .stock import get_stock_price
from .money_score import calculate_money_score

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- ROUTER ----------------
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


# ---------------- AI AGENT ----------------
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
        return f"AI service error: {e}"


# ---------------- SIP ----------------
def sip_agent(query):
    try:
        nums = list(map(float, re.findall(r"\d+\.?\d*", query)))

        if len(nums) >= 3:
            monthly, rate, years = nums[0], nums[1], int(nums[2])
            result = calculate_sip(monthly, rate, years)
            return f"SIP Future Value: ₹ {round(result, 2)}"

        return "Provide: SIP amount, rate, years"

    except Exception as e:
        return f"SIP error: {e}"


# ---------------- TAX ----------------
def tax_agent(query):
    try:
        nums = re.findall(r"\d+\.?\d*", query)
        if not nums:
            return "Provide a valid income amount"
        income = float(nums[0])
        tax = calculate_tax(income)
        return f"Estimated Tax: ₹ {tax}"

    except Exception as e:
        return f"Tax error: {e}"


# ---------------- STOCK ----------------
def stock_agent(query):
    try:
        # Find the last alphabetic word of 2–10 chars as the ticker
        words = query.upper().split()
        symbol = next(
            (w for w in reversed(words) if w.isalpha() and 2 <= len(w) <= 10),
            words[-1]
        )
        price = get_stock_price(symbol)

        if price is not None:
            return f"{symbol} Price: ₹ {price}"
        return "Invalid stock symbol or no data found"

    except Exception as e:
        return f"Stock error: {e}"


# ---------------- SCORE ----------------
def score_agent(query):
    try:
        nums = list(map(float, re.findall(r"\d+\.?\d*", query)))

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
        return f"Score error: {e}"


# ---------------- MAIN ----------------
def run_multi_agent(query):
    task = route_query(query)

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
