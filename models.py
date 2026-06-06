"""Database models and persistence layer for AI-Money-Mentor.

Replaces the previous module-level in-memory lists (expense_data,
assets_data, liabilities_data) with SQLite-backed storage via
Flask-SQLAlchemy, so data survives server restarts.
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Portfolio(db.Model):
    __tablename__ = "portfolio"
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    buy_date = db.Column(db.String(40), nullable=False)
    investment_type = db.Column(db.String(20), default="stock")
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self, current_price=None):
        current_price = current_price or self.buy_price
        current_value = self.quantity * current_price
        invested_value = self.quantity * self.buy_price
        pnl = current_value - invested_value
        pnl_percent = (pnl / invested_value * 100) if invested_value > 0 else 0
        
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "quantity": self.quantity,
            "buy_price": self.buy_price,
            "buy_date": self.buy_date,
            "current_price": current_price,
            "current_value": round(current_value, 2),
            "invested_value": round(invested_value, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_percent, 2),
            "investment_type": self.investment_type
        }


class PriceAlert(db.Model):
    __tablename__ = "price_alerts"
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(10), default="above")
    is_triggered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "target_price": self.target_price,
            "condition": self.condition,
            "is_triggered": self.is_triggered
        }


class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(40), nullable=False)
    
    # New AI fields
    ai_confidence = db.Column(db.Float, default=0.0)
    user_corrected = db.Column(db.Boolean, default=False)
    original_ai_category = db.Column(db.String(120), nullable=True)
    is_subscription = db.Column(db.Boolean, default=False)
    is_recurring = db.Column(db.Boolean, default=False)
    is_anomaly = db.Column(db.Boolean, default=False)
    merchant_name = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "amount": self.amount,
            "date": self.date,
            "ai_confidence": self.ai_confidence,
            "user_corrected": self.user_corrected,
            "is_subscription": self.is_subscription,
            "is_recurring": self.is_recurring,
            "is_anomaly": self.is_anomaly
        }


class Asset(db.Model):
    __tablename__ = "assets"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    def to_dict(self, index):
        return {"id": index, "name": self.name, "amount": self.amount}


class Liability(db.Model):
    __tablename__ = "liabilities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    def to_dict(self, index):
        return {"id": index, "name": self.name, "amount": self.amount}


class BudgetLimit(db.Model):
    __tablename__ = "budget_limits"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), unique=True, nullable=False)
    limit_amount = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "limit_amount": self.limit_amount
        }


class BudgetAlert(db.Model):
    __tablename__ = "budget_alerts"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)
    year_month = db.Column(db.String(7), nullable=False)  # e.g., "2026-06"
    threshold = db.Column(db.Integer, nullable=False)    # 80, 90, or 100
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "year_month": self.year_month,
            "threshold": self.threshold,
            "triggered_at": self.triggered_at.isoformat()
        }