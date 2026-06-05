# utils/multi_agent.py

from groq import Groq
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from .sip import calculate_sip
from .tax import calculate_tax
from .stock import get_stock_price
from .money_score import calculate_money_score

# Groq client — key is validated at startup in app.py; conditional initialization here
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None
if GROQ_API_KEY and GROQ_API_KEY.strip() not in ("", "your_groq_api_key_here"):
    client = Groq(api_key=GROQ_API_KEY)

# ---------------- 🔢 ROBUST FINANCIAL NUMBER PARSER ----------------
def extract_financial_numbers(query):
    query_clean = query.lower()
    # Matches numbers with optional commas/decimals and optional financial scale suffixes
    pattern = r"(\d[\d,]*\.?\d*)\s*(lakh[s]?|l|crore[s]?|cr|k|thousand[s]?|m|million[s]?)?"
    matches = re.finditer(pattern, query_clean)
    
    nums = []
    for match in matches:
        num_str = match.group(1).replace(",", "")
        if not num_str or num_str == ".":
            continue
        try:
            val = float(num_str)
            suffix = match.group(2)
            if suffix:
                if "lakh" in suffix or suffix == "l":
                    val *= 100000
                elif "crore" in suffix or suffix == "cr":
                    val *= 10000000
                elif "thousand" in suffix or suffix == "k":
                    val *= 1000
                elif "million" in suffix or suffix == "m":
                    val *= 1000000
            nums.append(val)
        except ValueError:
            continue
    return nums

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
def ai_agent(client, query): # add the Groq client here since we mentioned it in app.py
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
        nums = extract_financial_numbers(query)

        if len(nums) >= 3:
            monthly, rate, years = nums[0], nums[1], int(nums[2])
            result = calculate_sip(monthly, rate, years)
            return f"SIP Future Value: ₹ {round(result['nominal_value'], 2)}"

        return "Provide: SIP amount, rate, years"

    except Exception as e:
        print("SIP ERROR:", e)
        return "SIP error ❌"


# ---------------- 💸 TAX ----------------
def tax_agent(query):
    try:
        income = extract_financial_numbers(query)[0]
        tax_res = calculate_tax(income)
        new_tax = tax_res["new_regime"]["total_tax"]
        old_tax = tax_res["old_regime"]["total_tax"]
        rec = tax_res["recommended"]
        sav = tax_res["savings"]
        
        reply = f"For gross income of ₹{income:,}:\n"
        reply += f"- Tax under New Regime: ₹{new_tax:,}\n"
        reply += f"- Tax under Old Regime: ₹{old_tax:,}\n"
        reply += f"Recommendation: Go with the **{rec}** (saves ₹{sav:,})."
        return reply

    except Exception as e:
        print("TAX ERROR:", e)
        return "Provide valid income"


# ---------------- 📊 STOCK ----------------
def stock_agent(query):
    try:
        symbol = query.split()[-1].upper()
        res = get_stock_price(symbol)

        if isinstance(res, dict) and "error" in res:
            return f"Error: {res['error']}"

        if isinstance(res, dict) and "price" in res:
            price = res["price"]
            actual_symbol = res["symbol"]
            pe = res["metrics"]["pe_ratio"]
            return f"{actual_symbol} current price is ₹{price:.2f}. PE Ratio: {pe}."

        return "Invalid stock symbol"

    except Exception as e:
        print("STOCK ERROR:", e)
        return "Stock error ❌"


# ---------------- 💰 SCORE ----------------
def score_agent(query):
    try:
        nums = extract_financial_numbers(query)

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
def run_multi_agent(client, query):
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
        return ai_agent(client, query)