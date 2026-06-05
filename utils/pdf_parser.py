import pdfplumber
import os
import re
import json
from groq import Groq

def extract_income(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        if not text.strip():
            return {"error": "The PDF document seems to be empty or contains no extractable text."}

        # Check if GROQ key is set and valid
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and api_key != "YOUR_API_KEY":
            try:
                client = Groq(api_key=api_key)
                doc_text = text[:8000]  # limit payload size
                
                prompt = f"""
                You are a highly accurate financial document parser. Analyze the following text extracted from a financial document (like Form 16, salary slip, or bank statement) and extract key financial details.
                
                Output your response ONLY as a JSON object. Do not add any conversational text or formatting outside the JSON structure. Use exactly this JSON template:
                {{
                    "document_type": "Form 16",
                    "employer_organization": "Employer or Organization Name",
                    "gross_income": 1200000,
                    "tax_deducted_tds": 45000,
                    "allowances_deductions": {{
                        "80C": 150000,
                        "80D": 25000,
                        "HRA": 60000
                    }},
                    "confidence_score": 0.95,
                    "summary_findings": "Salary Slip for October 2025, gross income detected is ₹1.2L."
                }}
                
                Document Text:
                {doc_text}
                """
                
                res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a helpful, precise JSON-only output assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                
                content = res.choices[0].message.content.strip()
                
                # Clean potential markdown wrappers
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\n", "", content)
                    content = re.sub(r"\n```$", "", content)
                
                parsed_data = json.loads(content)
                return parsed_data
                
            except Exception as llm_err:
                print("LLM parsing error, falling back to regex:", llm_err)
                
        # Regex Fallback
        result = {
            "document_type": "Unknown (Regex Fallback)",
            "employer_organization": "N/A",
            "gross_income": None,
            "tax_deducted_tds": None,
            "allowances_deductions": {},
            "confidence_score": 0.3,
            "summary_findings": "Parsed using basic keyword analysis (LLM offline or key not configured)."
        }
        
        text_lower = text.lower()
        if "form 16" in text_lower or "form no. 16" in text_lower:
            result["document_type"] = "Form 16"
        elif "salary slip" in text_lower or "payslip" in text_lower:
            result["document_type"] = "Salary Slip"
        elif "bank statement" in text_lower or "transaction details" in text_lower:
            result["document_type"] = "Bank Statement"
            
        salary_match = re.search(r"(?:gross|total|net)\s+(?:salary|income|pay|earnings)\D*(\d[\d,]*\d)", text, re.IGNORECASE)
        if salary_match:
            try:
                val = float(salary_match.group(1).replace(",", ""))
                result["gross_income"] = val
            except ValueError:
                pass
                
        tds_match = re.search(r"(?:tds|tax\s+deducted|tax\s+payable)\D*(\d[\d,]*\d)", text, re.IGNORECASE)
        if tds_match:
            try:
                val = float(tds_match.group(1).replace(",", ""))
                result["tax_deducted_tds"] = val
            except ValueError:
                pass
                
        # Fallback extraction for allowances/deductions (80C, 80D, HRA)
        hra_match = re.search(r"(?:hra|house\s+rent\s+allowance)\D*(\d[\d,]*\d)", text, re.IGNORECASE)
        if hra_match:
            try:
                result["allowances_deductions"]["HRA"] = float(hra_match.group(1).replace(",", ""))
            except ValueError:
                pass

        ded_80c_match = re.search(r"(?:80c|section\s+80c)\D*(\d[\d,]*\d)", text, re.IGNORECASE)
        if ded_80c_match:
            try:
                result["allowances_deductions"]["80C"] = float(ded_80c_match.group(1).replace(",", ""))
            except ValueError:
                pass

        ded_80d_match = re.search(r"(?:80d|section\s+80d)\D*(\d[\d,]*\d)", text, re.IGNORECASE)
        if ded_80d_match:
            try:
                result["allowances_deductions"]["80D"] = float(ded_80d_match.group(1).replace(",", ""))
            except ValueError:
                pass
                
        return result

    except Exception as e:
        return {"error": f"Failed to parse PDF: {str(e)}"}