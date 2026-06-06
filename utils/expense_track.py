from groq import Groq
import os


BUDGET_LIMITS = {
    "Food": 5000.0,
    "Shopping": 10000.0,
    "Entertainment": 3000.0,
    "Utilities": 6000.0,
    "Other": 4000.0
}

def calculate_expense(expenses):
    if not expenses:
        return {"Total": 0, "Average": 0, "By Category": {}, "Budget Limits": BUDGET_LIMITS, "Status": {}}

    total = sum([e["amount"]  for e in expenses])
    average = total / len(expenses) 
    by_category = {}

    for e in expenses:
        by_category[e["category"]] = (by_category.get(e["category"],0) + e["amount"])
    
    status = {}
    for cat, spent in by_category.items():
        limit = BUDGET_LIMITS.get(cat, 5000.0) # Default limit if custom category
        status[cat] = {
            "spent": spent,
            "limit": limit,
            "exceeded": spent > limit,
            "percentage": round((spent / limit) * 100, 2) if limit > 0 else 100.0
        }
        
    return {
        "Total": total,
        "Average": average,
        "By Category": by_category,
        "Budget Limits": BUDGET_LIMITS,
        "Status": status
    }
    
def insights(client, expenses):

    if not expenses:
        return {
            "insights": "Add some expenses to generate AI insights.",
            "summary": {}
        }


    totals = calculate_expense(expenses)
    
    # User Prompt for AI
    prompt = f"""
        You are AI-Money Mentor. You will analyze the expense data of the user and 
        generate 3 important insights:
            Analyze the user's spending data and provide:
                1. Top spending category
                2. Spending warning (if applicable)
                3. One practical saving suggestion

                Use this format:

                <div class="insight-card">
                    <h3>Top Spending Category</h3>
                    <p>...</p>
                </div>

                <div class="insight-card">
                    <h3>Spending Warning</h3>
                    <p>...</p>
                </div>

                <div class="insight-card">
                    <h3>Saving Suggestion</h3>
                    <p>...</p>
                </div>

                Do not use markdown tables.
                Do not use code blocks.
                Return HTML only.

        Use the below data for insights generation
        Total spend: ₹{totals['Total']}
        Average expense: ₹{totals['Average']}
        Breakdown: {totals['By Category']}
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages= [
            {'role':'user', 'content':prompt},
            {'role':'system', 'content': "You are AI-Money Mentor who helps to analyze the expense given by the user and provide the personalized insights"}
        ]
    )

    insights_text = response.choices[0].message.content

    return {"insights": insights_text, "summary": totals}