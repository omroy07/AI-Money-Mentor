"""
Multi-Agent Financial Advisor System
Specialized agents for different financial domains with smart routing
"""

from typing import Dict, List, Tuple
from urllib import response
from groq import Groq
import re

# Import local mathematical calculators
from utils.sip import calculate_sip
from utils.tax import calculate_tax
from utils.stock import get_stock_price
from utils.money_score import calculate_money_score_details

class FinancialAgent:
    """Base class for specialized financial agents"""
    
    def __init__(self, name: str, specialization: str, system_prompt: str, keywords: List[str]):
        self.name = name
        self.specialization = specialization
        self.system_prompt = system_prompt
        self.keywords = keywords  # Keywords that trigger this agent
        self.queries_handled = 0
        self.total_response_time = 0
    
    def process_query(self, query: str, client: Groq, context: str = "") -> Dict:
        """Process query and return response"""
        import time
        start = time.time()
        
        full_prompt = f"""{self.system_prompt}

Previous context from other agents: {context if context else 'None'}

User Query: {query}

Provide expert, actionable advice based on your specialization. Be specific and practical."""

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            elapsed = time.time() - start
            self.queries_handled += 1
            self.total_response_time += elapsed
            
            return {
                "agent": self.name,
                "specialization": self.specialization,
                "response": response.choices[0].message.content,
                "confidence": 0.85,
                "response_time": round(elapsed, 2)
            }
        except Exception as e:
            return {
                "agent": self.name,
                "specialization": self.specialization,
                "response": f"I apologize, but I encountered an error. Let me try to help differently.",
                "confidence": 0.3,
                "error": str(e)
            }
    
    def get_avg_response_time(self):
        if self.queries_handled == 0:
            return 0
        return round(self.total_response_time / self.queries_handled, 2)

# Agent Definitions with specialized prompts and keywords

TAX_AGENT = FinancialAgent(
    name="Tax Advisor",
    specialization="Tax Planning & Optimization",
    system_prompt="""You are a specialized Tax Advisor for Indian taxation system.

Your expertise includes:
- Income Tax calculation (Old vs New Regime)
- Tax deductions under 80C, 80D, 80E
- HRA exemption calculation
- Capital gains tax
- GST for businesses
- TDS/TCS provisions
- Tax saving investments (ELSS, PPF, NPS, etc.)
- ITR filing guidance

Guidelines:
1. Always mention applicable sections when suggesting deductions
2. Compare Old vs New Regime when relevant
3. Suggest specific tax-saving investments with amounts
4. Be practical and consider user's income level
5. Mention deadlines for tax-saving investments (March 31st)

Remember: You are a tax expert - provide accurate, actionable tax advice.""",
    keywords=["tax", "itr", "income tax", "deduction", "80c", "80d", "hra", "capital gains", "gst", "tds", "tax saving", "elss", "ppf", "nps", "it refund", "tax filing"]
)

INVESTMENT_AGENT = FinancialAgent(
    name="Investment Advisor",
    specialization="Investment & Portfolio Management",
    system_prompt="""You are a specialized Investment Advisor.

Your expertise includes:
- Stock market investments (equity, derivatives)
- Mutual funds (large cap, mid cap, small cap, ELSS)
- Fixed income (FD, bonds, debentures)
- Portfolio allocation strategies
- Risk assessment and management
- Goal-based investing (retirement, child education, etc.)
- SIP planning and optimization
- Asset allocation based on age and risk profile

Guidelines:
1. Always mention risk levels when suggesting investments
2. Recommend specific mutual funds or stocks when possible
3. Consider investment horizon (short/medium/long term)
4. Suggest diversification strategies
5. Include expected returns range (not guaranteed)

Remember: You are an investment expert - provide balanced, risk-aware advice.""",
    keywords=["invest", "stock", "mutual fund", "sip", "portfolio", "equity", "bond", "fd", "fixed deposit", "share market", "nifty", "sensex", "returns", "dividend", "asset allocation", "risk profile"]
)

DEBT_AGENT = FinancialAgent(
    name="Debt Management Expert",
    specialization="Debt & Credit Management",
    system_prompt="""You are a specialized Debt Management Expert.

Your expertise includes:
- Loan management (home, car, personal, education)
- Credit score improvement (CIBIL)
- Debt consolidation strategies
- EMI calculation and restructuring
- Credit card management
- Loan prepayment strategies
- Bankruptcy alternatives
- Interest rate negotiation

Guidelines:
1. Prioritize high-interest debt repayment
2. Suggest specific debt reduction strategies (snowball/avalanche)
3. Provide EMI calculations when relevant
4. Explain credit score factors and improvement tips
5. Be empathetic but practical about debt situations

Remember: You are a debt expert - focus on reducing financial burden and improving credit health.""",
    keywords=["debt", "loan", "emi", "credit card", "cibil", "credit score", "borrow", "interest rate", "personal loan", "home loan", "car loan", "education loan", "debt consolidation", "bankruptcy", "overdue"]
)

RETIREMENT_AGENT = FinancialAgent(
    name="Retirement Planner",
    specialization="Retirement & Pension Planning",
    system_prompt="""You are a specialized Retirement Planner.

Your expertise includes:
- Retirement corpus calculation
- NPS (National Pension System)
- PPF (Public Provident Fund)
- Senior citizen savings schemes
- Pension planning strategies
- Withdrawal strategies post-retirement
- Inflation-adjusted retirement planning
- Reverse mortgage options

Guidelines:
1. Use 4% withdrawal rule as reference
2. Account for inflation (typically 6-7%)
3. Suggest specific retirement products with current rates
4. Calculate required corpus based on current expenses
5. Consider life expectancy (85+ years)

Remember: You are a retirement expert - help users plan for a comfortable post-retirement life.""",
    keywords=["retirement", "pension", "nps", "ppf", "senior citizen", "retire", "post retirement", "old age", "pension scheme", "retirement corpus", "annuity"]
)

INSURANCE_AGENT = FinancialAgent(
    name="Insurance Advisor",
    specialization="Insurance Planning",
    system_prompt="""You are a specialized Insurance Advisor.

Your expertise includes:
- Life insurance (term, whole life, ULIP)
- Health insurance (individual, family floater)
- Critical illness coverage
- Accident insurance
- Home and vehicle insurance
- Claim process guidance
- Coverage gap analysis
- Premium optimization

Guidelines:
1. Recommend term insurance with adequate coverage (10-15x annual income)
2. Suggest health insurance with sufficient sum insured (min ₹5-10 lakhs)
3. Explain waiting periods and exclusions clearly
4. Compare different plan types when relevant
5. Emphasize buying pure term insurance over investment-linked plans

Remember: You are an insurance expert - prioritize adequate coverage over returns.""",
    keywords=["insurance", "health insurance", "life insurance", "term plan", "medical insurance", "claim", "premium", "coverage", "critical illness", "family floater", "accident insurance"]
)

GENERAL_AGENT = FinancialAgent(
    name="General Financial Advisor",
    specialization="General Financial Guidance",
    system_prompt="""You are a General Financial Advisor - a fallback for topics not covered by specialized agents.

Your expertise includes:
- Basic financial literacy
- Budgeting and saving tips
- Emergency fund planning
- General money management
- Financial goal setting
- Expense tracking advice
- Basic financial calculations

Guidelines:
1. Keep advice practical and actionable
2. Explain financial concepts in simple terms
3. Suggest specific percentages (e.g., 50/30/20 rule)
4. When specialized knowledge is needed, acknowledge it
5. Encourage users to ask specialized questions

Remember: You're the generalist - help with basic finance but defer to specialists when needed.""",
    keywords=["money", "finance", "budget", "save", "emergency fund", "financial goal", "spending", "expense", "salary", "income", "monthly budget", "financial planning", "wealth", "saving money"]
)


# ---------------- 🔢 ROBUST FINANCIAL NUMBER PARSER & TOOL CALLERS ----------------
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


def check_and_run_local_tools(query: str) -> Tuple[str, str]:
    """Check if query is mathematical and run local calculators to provide precise context.
    Returns (tool_name, tool_result_text)
    """
    query_lower = query.lower()
    
    # 1. Tax check
    if any(w in query_lower for w in ["tax", "itr", "income tax"]):
        nums = extract_financial_numbers(query)
        if nums:
            income = nums[0]
            # check if other nums can be deductions
            deductions_80c = nums[1] if len(nums) > 1 else 0.0
            deductions_80d = nums[2] if len(nums) > 2 else 0.0
            hra = nums[3] if len(nums) > 3 else 0.0
            try:
                res = calculate_tax(income, deductions_80c, deductions_80d, hra)
                res_text = (
                    f"Income Tax Calculation Results for Income ₹{income:,}:\n"
                    f"- Recommended Regime: {res['recommended']}\n"
                    f"- Tax Savings: ₹{res['savings']:,}\n"
                    f"- Old Regime Tax Payable: ₹{res['old_regime']['total_tax']:,}\n"
                    f"- New Regime Tax Payable: ₹{res['new_regime']['total_tax']:,}"
                )
                return "Tax Calculator", res_text
            except Exception as e:
                return "Tax Calculator", f"Error calculating tax: {str(e)}"
                
    # 2. SIP check
    if any(w in query_lower for w in ["sip", "mutual fund", "investment returns"]):
        nums = extract_financial_numbers(query)
        if len(nums) >= 3:
            monthly, rate, years = nums[0], nums[1], int(nums[2])
            try:
                fv = calculate_sip(monthly, rate, years)
                total_invested = monthly * years * 12
                wealth_gained = fv - total_invested
                res_text = (
                    f"SIP Growth Calculation Results:\n"
                    f"- Monthly Investment: ₹{monthly:,}\n"
                    f"- Expected Rate: {rate}%\n"
                    f"- Tenure: {years} years\n"
                    f"- Total Invested: ₹{total_invested:,}\n"
                    f"- Estimated Returns: ₹{wealth_gained:,}\n"
                    f"- Future Value: ₹{fv:,}"
                )
                return "SIP Calculator", res_text
            except Exception as e:
                return "SIP Calculator", f"Error calculating SIP: {str(e)}"
                
    # 3. Money Score check
    if any(w in query_lower for w in ["score", "financial health", "money score"]):
        nums = extract_financial_numbers(query)
        if len(nums) >= 6:
            try:
                res = calculate_money_score_details(*nums[:6])
                res_text = (
                    f"Financial Money Score Results:\n"
                    f"- Total Score: {res['score']}/100\n"
                    f"- Savings Rate: {res['savings_rate']}% (Score: {res['savings_score']}/30)\n"
                    f"- Investment Rate: {res['investment_rate']}% (Score: {res['investment_score']}/25)\n"
                    f"- Debt Ratio: {res['debt_ratio']}% (Score: {res['debt_score']}/25)\n"
                    f"- Emergency Fund: {res['months_cover']} months expenses (Score: {res['emergency_score']}/20)"
                )
                return "Money Score Calculator", res_text
            except Exception as e:
                return "Money Score Calculator", f"Error calculating Money Score: {str(e)}"
                
    # 4. Stock check
    if any(w in query_lower for w in ["stock", "share", "price of"]):
        # Extract stock symbol (usually uppercase word)
        words = query.split()
        for w in words:
            w_clean = re.sub(r'[^a-zA-Z\.\-]', '', w).upper()
            if len(w_clean) >= 2 and len(w_clean) <= 10 and not w_clean.isdigit():
                # Avoid general financial terms
                if w_clean not in ["STOCK", "PRICE", "SHARE", "MUTUAL", "FUND", "TAX", "SIP", "CIBIL", "LOAN", "EMI"]:
                    try:
                        res = get_stock_price(w_clean)
                        if res and "error" not in res:
                            res_text = (
                                f"Stock Market Price for {res['symbol']}:\n"
                                f"- Price: ₹{res['price']:.2f}\n"
                                f"- PE Ratio: {res['metrics']['pe_ratio']}\n"
                                f"- Market Cap: {res['metrics']['market_cap']}"
                            )
                            return "Stock Checker", res_text
                    except:
                        pass
                        
    return "", ""


class MultiAgentRouter:
    """Routes user queries to the most appropriate specialized agent"""
    
    def __init__(self, client: Groq):
        self.client = client
        self.agents = [
            TAX_AGENT,
            INVESTMENT_AGENT,
            DEBT_AGENT,
            RETIREMENT_AGENT,
            INSURANCE_AGENT,
            GENERAL_AGENT
        ]
        self.conversation_context = []  # Stores last 5 conversations for context
        self.cross_agent_context = {}  # Share insights between agents
    
    def route_query(self, query: str) -> FinancialAgent:
        """Determine which agent should handle the query"""
        query_lower = query.lower()
        
        # Score each agent based on keyword matches
        scores = {}
        for agent in self.agents:
            score = 0
            for keyword in agent.keywords:
                if keyword in query_lower:
                    score += 1
            # Boost score for exact matches at start
            for keyword in agent.keywords:
                if query_lower.startswith(keyword):
                    score += 2
            scores[agent] = score
        
        # Get the agent with highest score
        best_agent = max(scores, key=scores.get)
        
        # If max score is 0, use GENERAL_AGENT
        if scores[best_agent] == 0:
            return GENERAL_AGENT
        
        # If score is low (<2), maybe use general agent
        if scores[best_agent] < 2:
            return GENERAL_AGENT
            
        return best_agent
    
    def get_cross_agent_context(self, current_agent: FinancialAgent) -> str:
        """Get relevant context from other agents for this query"""
        context_parts = []
        
        # Get recent insights from other agents
        for agent_name, context in self.cross_agent_context.items():
            if agent_name != current_agent.name:
                context_parts.append(f"[{agent_name} insight]: {context}")
        
        return " | ".join(context_parts) if context_parts else ""
    
    def process_query(self, query: str, chat_history: List = None) -> Dict:
        """Process query using the best suited agent"""
        try:
            # 1. Run local mathematical tools first to get accurate context
            tool_name, tool_context = check_and_run_local_tools(query)
            
            # Select the right agent
            selected_agent = self.route_query(query)
            
            # 2. If client is offline, return calculated tool results or standard fallback answers
            if not self.client:
                response_text = ""
                if tool_context:
                    response_text = f"Here is the precise calculation from the {tool_name}:\n\n{tool_context}\n\n*(Note: Chatbot is in offline mode due to missing GROQ_API_KEY)*"
                else:
                    # Generic offline fallback response based on agent
                    if selected_agent.name == "Tax Advisor":
                        response_text = "I am in offline mode. Standard deduction is ₹75,000 for New Regime and ₹50,000 for Old Regime. Use the Tax Planner tab to calculate side-by-side comparison with deductions under 80C and 80D."
                    elif selected_agent.name == "Investment Advisor":
                        response_text = "I am in offline mode. For investments: consider starting a SIP (Mutual Funds) for long-term compounding. Fixed Deposits offer safe 6-7% returns. Use the SIP Calculator tab to simulate your returns."
                    elif selected_agent.name == "Debt Management Expert":
                        response_text = "I am in offline mode. To manage debt: list loans by interest rate. Use the Debt Snowball (pay smallest first) or Debt Avalanche (pay highest interest rate first) method. Keep your Credit Score (CIBIL) high by paying EMI on time."
                    elif selected_agent.name == "Retirement Planner":
                        response_text = "I am in offline mode. For retirement: calculate your monthly expenses adjusted for inflation. Invest in NPS, PPF, or equity mutual funds for long-term growth."
                    elif selected_agent.name == "Insurance Advisor":
                        response_text = "I am in offline mode. For protection: buy a pure Term Life Insurance (10-15x annual income) and a Family Health Insurance policy (minimum ₹5-10 lakhs sum insured)."
                    else:
                        response_text = "I am in offline mode. Let's talk about budgeting: use the 50/30/20 rule (50% Needs, 30% Wants, 20% Savings). You can track expenses in the Expense Tracker tab."
                
                return {
                    "agent": selected_agent.name,
                    "specialization": selected_agent.specialization,
                    "response": response_text,
                    "confidence": 1.0,
                    "response_time": 0.0
                }
                
            # Get context from previous conversations
            context = self.get_cross_agent_context(selected_agent)
            
            # 3. Inject mathematical calculation output as context to the LLM agent
            if tool_context:
                context += f" | Precise Tool Calculation Output: {tool_context}" if context else f"Precise Tool Calculation Output: {tool_context}"
            
            # Add chat history context if available
            if chat_history and len(chat_history) > 0:
                last_few = chat_history[-3:]  # Last 3 exchanges
                history_text = " | ".join([f"Q: {h['user']} A: {h.get('assistant', '')[:100]}" for h in last_few])
                context += f" | Recent conversation: {history_text}" if context else f"Recent conversation: {history_text}"
            
            # Process with selected agent
            result = selected_agent.process_query(query, self.client, context)
            
            # Store context for cross-agent learning
            self.cross_agent_context[selected_agent.name] = result['response'][:200]
            
            # Keep conversation history
            self.conversation_context.append({
                "query": query,
                "agent": selected_agent.name,
                "specialization": selected_agent.specialization
            })
            # Keep only last 10
            if len(self.conversation_context) > 10:
                self.conversation_context.pop(0)
            
            # Add routing info to result
            result["routing_reason"] = f"Matched with {selected_agent.specialization} agent"
            result["queried_agent"] = selected_agent.name
            
            return result
            
        except Exception as e:
            return {
                "agent": "Error Handler",
                "specialization": "System",
                "response": "I apologize, but I'm having trouble processing your request. Could you please rephrase your question?",
                "confidence": 0,
                "error": str(e)
            }
    
    def get_performance_stats(self) -> Dict:
        """Get performance metrics for all agents"""
        stats = {}
        for agent in self.agents:
            stats[agent.name] = {
                "queries_handled": agent.queries_handled,
                "avg_response_time": agent.get_avg_response_time(),
                "specialization": agent.specialization
            }
        return stats