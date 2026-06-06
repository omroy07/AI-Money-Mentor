import os
from groq import Groq, GroqError  # Imported GroqError for explicit API exception catching


def calculate_expense(expenses):
    if not expenses:
        return {"Total": 0, "Average": 0, "By Category": {}}

    total = sum([e["amount"] for e in expenses])
    average = total / len(expenses)
    by_category = {}

    for e in expenses:
        by_category[e["category"]] = (
            by_category.get(e["category"], 0) + e["amount"]
        )

    return {"Total": total, "Average": average, "By Category": by_category}


def insights(client, expenses):
    totals = calculate_expense(expenses)

    if client is None:
        return {
            "insights": """
                <div class="insight-card">
                    <h3>Insights Offline</h3>
                    <p>AI Money Mentor is offline because GROQ_API_KEY is not configured.</p>
                </div>
            """,
            "summary": totals,
        }

    if not expenses:
        return {
            "insights": "Add some expenses to generate AI insights.",
            "summary": {},
        }

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

    # Wrapped the API call inside a try-except block to gracefully handle network/service failures
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are AI-Money Mentor who helps to analyze the expense given by the user and provide the personalized insights",
                },
                {"role": "user", "content": prompt},
            ],
        )
        insights_text = response.choices[0].message.content

    except GroqError as e:
        # Handles API-specific issues (Rate limits, Invalid API Key, Server Down)
        print(f"Groq API Error encountered: {e}")
        insights_text = """
            <div class="insight-card">
                <h3>Insights Temporarily Unavailable</h3>
                <p>We encountered an issue communicating with the AI mentor. Please check back shortly.</p>
            </div>
        """
    except Exception as e:
        # Fallback catch for unexpected connection drops or generic Python code failures
        print(f"Unexpected error while generating insights: {e}")
        insights_text = """
            <div class="insight-card">
                <h3>System Error</h3>
                <p>An unexpected error occurred while analyzing your details. Please try again later.</p>
            </div>
        """

    return {"insights": insights_text, "summary": totals}