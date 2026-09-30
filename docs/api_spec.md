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

---

## 📊 Portfolio Risk Analysis Endpoint

- **Purpose**: Provides portfolio risk, diversification, and asset concentration insights with optional AI explanation.
- **URL**: `/api/portfolio/risk-analysis`
- **Method**: `POST`
- **Login Requirement**: Requires authentication (`@login_required`)
- **Rate Limit**: 10 per minute
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "holdings": [
      {
        "name": "Reliance",
        "amount": 50000.0,
        "category": "equity"
      }
    ],
    "use_ai": true
  }
  ```
  - `holdings` (list of objects): Each holding must have `name` (string), `amount` (positive float), and `category` (string).
  - `use_ai` (optional boolean, default `true`): Whether to fetch an AI-powered explanation.
- **Accepted Category Aliases**: `stock`, `stocks`, `equity`, `equities`, `mutual fund`, `etf`, `index fund`, `bond`, `bonds`, `debt`, `fixed income`, `fd`, `ppf`, `epf`, `gold`, `sgb`, `gold etf`, `real estate`, `property`, `reit`, `real_estate`, `cash`, `savings`, `liquid`, `crypto`, `cryptocurrency`, `bitcoin`.
- **Success Response (200 OK)**:
  ```json
  {
    "analysis": {
      "total_value": 50000.0,
      "weights": {
        "holdings": [
          {"name": "Reliance", "weight_percent": 100.0}
        ],
        "asset_classes": {
          "equity": 100.0,
          "debt": 0.0,
          "gold": 0.0,
          "real_estate": 0.0,
          "cash": 0.0,
          "crypto": 0.0
        }
      },
      "expected_return_percent": 12.0,
      "volatility_percent": 18.0,
      "sharpe_ratio": 0.33,
      "average_correlation": 0.0,
      "risk_score": 60.0,
      "risk_label": "High",
      "diversification_score": 0.0,
      "concentration_flags": [
        {
          "type": "single_holding",
          "subject": "Reliance",
          "weight_percent": 100.0,
          "threshold_percent": 25.0,
          "message": "High concentration in single holding: Reliance"
        }
      ],
      "scenarios": [
        {
          "name": "equity_crash",
          "portfolio_change_percent": -30.0,
          "portfolio_change_amount": -15000.0,
          "by_class": {"equity": -30.0}
        }
      ],
      "assumptions": {},
      "disclaimer": "Educational analysis based on fixed assumptions. Not financial advice."
    },
    "explanation": {
      "summary": "Your portfolio indicates a High risk profile.",
      "tips": ["Regularly review your asset allocation."],
      "alternatives": ["Increase debt share to lower volatility."],
      "source": "template",
      "disclaimer": "Educational analysis based on fixed assumptions. Not financial advice."
    }
  }
  ```
  - The `analysis` object contains: `total_value`, `weights`, `expected_return_percent`, `volatility_percent`, `sharpe_ratio`, `average_correlation`, `risk_score`, `risk_label`, `diversification_score`, `concentration_flags`, `scenarios`, `assumptions`, and `disclaimer`.
  - The `explanation` object contains: `summary`, `tips`, `alternatives`, `source`, and `disclaimer`.
- **Error Responses**:
  - `400 Bad Request`: Returns `{"error": "<error message>"}` for missing/invalid holdings or categories.
  - `500 Internal Server Error`: Returns `{"error": "Portfolio analysis failed."}` for unexpected failures.
