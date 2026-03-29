import pdfplumber

def extract_income(file):
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""

    if "Salary" in text:
        return "Salary details detected"
    
    return "Could not extract structured data"