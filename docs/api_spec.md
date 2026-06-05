# 📖 AI Money Mentor API Specification

This document details the backend REST API endpoints exposed by the Flask application, including their expected JSON payloads, response shapes, and validation rules.

---

## 🤖 Chat Endpoint
- **URL**: `/chat`
- **Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "message": "What is tax exemption under Section 80C?"
  }
  ```
- **Response Shape**:
  ```json
  {
    "reply": "Section 80C allows deductions up to ₹1.5L for specific investments like ELSS, PPF, and EPF..."
  }
  ```

---

## 📈 SIP Calculator Endpoint
- **URL**: `/sip`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "monthly": 10000.0,
    "rate": 12.0,
    "years": 10,
    "inflation": 6.0
  }
  ```
- **Response Shape**:
  ```json
  {
    "future_value": 2323390.8,
    "nominal_value": 2323390.8,
    "inflation_adjusted_value": 1297380.5,
    "inflation_applied": 6.0
  }
  ```

---

## 💸 Tax Planner Endpoint
- **URL**: `/tax`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "income": 1200000.0,
    "deduction_80c": 150000.0,
    "deduction_80d": 25000.0,
    "deduction_hra": 50000.0
  }
  ```
- **Response Shape**:
  ```json
  {
    "tax": {
      "gross_income": 1200000.0,
      "deductions_applied": {
        "80c": 150000.0,
        "80d": 25000.0,
        "hra": 50000.0,
        "total": 275000.0
      },
      "new_regime": {
        "standard_deduction": 75000,
        "taxable_income": 1125000.0,
        "base_tax": 78750.0,
        "cess": 3150.0,
        "total_tax": 81900.0
      },
      "old_regime": {
        "standard_deduction": 50000,
        "taxable_income": 925000.0,
        "base_tax": 97500.0,
        "cess": 3900.0,
        "total_tax": 101400.0
      },
      "recommended": "New Regime",
      "savings": 19500.0
    }
  }
  ```

---

## 📄 PDF Parser Upload Endpoint
- **URL**: `/upload`
- **Method**: `POST`
- **Request Headers**: `Content-Type: multipart/form-data`
- **Form Data**:
  - `file`: (Binary File - PDF format)
- **Response Shape (Groq LLM Mode)**:
  ```json
  {
    "data": {
      "document_type": "Form 16",
      "employer_organization": "Example Corp Ltd",
      "gross_income": 1500000.0,
      "tax_deducted_tds": 65000.0,
      "confidence_score": 0.98
    }
  }
  ```
