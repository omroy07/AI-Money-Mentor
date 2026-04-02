from groq import Groq

# Initialize Groq client
client = Groq(api_key="YOUR_API_KEY")

# -----------------------
# SIP AGENT
# -----------------------
def sip_agent(query):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",   # fast & free
        messages=[
            {"role": "system", "content": "You are a SIP investment advisor for India."},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content


# -----------------------
# TAX AGENT
# -----------------------
def tax_agent(query):
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are a tax advisor for India."},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content


# -----------------------
# LLM ROUTER (MAIN BRAIN)
# -----------------------
def route_query(query):
    routing_prompt = f"""
    Classify the user's query into one of these categories:
    1. SIP
    2. TAX

    Only return ONE word: SIP or TAX

    Query: {query}
    """

    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": routing_prompt}]
    )

    decision = response.choices[0].message.content.strip().upper()

    return decision


# -----------------------
# MAIN AGENT SYSTEM
# -----------------------
def agent(query):
    decision = route_query(query)

    if "SIP" in decision:
        return sip_agent(query)

    elif "TAX" in decision:
        return tax_agent(query)

    else:
        return "Sorry, I can help with SIP or Tax queries only."


# -----------------------
# TEST
# -----------------------
if __name__ == "__main__":
    while True:
        q = input("Ask: ")
        print(agent(q))
