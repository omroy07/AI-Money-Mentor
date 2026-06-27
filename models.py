"""Database models and persistence layer for AI-Money-Mentor.

Replaces the previous module-level in-memory lists (expense_data,
assets_data, liabilities_data) with SQLite-backed storage via
Flask-SQLAlchemy, so data survives server restarts.
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin


db = SQLAlchemy()

class RecurringExpense(db.Model):
    """Model for recurring expenses"""
    __tablename__ = 'recurring_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, default=1)  # For now, single user
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    merchant = db.Column(db.String(100))
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, quarterly, yearly
    start_date = db.Column(db.Date, nullable=False)
    next_due_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    auto_add = db.Column(db.Boolean, default=True)  # Auto-add vs Ask before adding
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_processed = db.Column(db.Date, nullable=True)
    is_subscription = db.Column(db.Boolean, default=False)  # New field to flag subscription
    last_price = db.Column(db.Float, nullable=True)      # Store last known price for alerts
    status = db.Column(db.String(20), default='active') # active, canceled, paused
    
    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'category': self.category,
            'merchant': self.merchant,
            'frequency': self.frequency,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'auto_add': self.auto_add,
            'is_active': self.is_active
        }


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )


class Portfolio(db.Model):
    __tablename__ = "portfolio"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="portfolio")
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    buy_date = db.Column(db.String(40), nullable=False)
    investment_type = db.Column(db.String(20), default="stock")
    notes = db.Column(db.String(200), nullable=True)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self, current_price=None):
        current_price = current_price or self.buy_price
        current_value = self.quantity * current_price
        invested_value = self.quantity * self.buy_price
        pnl = current_value - invested_value
        pnl_percent = (pnl / invested_value * 100) if invested_value > 0 else 0
        
        return {
            "user_id": self.user_id,
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "quantity": self.quantity,
            "buy_price": self.buy_price,
            "currency": self.currency,
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
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="price_alerts")
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(20), default="above")
    operator_type = db.Column(db.String(20), default="above")
    cooldown_days = db.Column(db.Integer, default=0)
    duration_days = db.Column(db.Integer, default=0)
    last_checked_price = db.Column(db.Float, nullable=True)
    consecutive_polls_met = db.Column(db.Integer, default=0)
    is_triggered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Diagnostics + UI info
    last_check_error = db.Column(db.String(500), nullable=True)
    last_triggered_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "id": self.id,
            "symbol": self.symbol,
            "target_price": self.target_price,
            "condition": self.condition,
            "operator_type": self.operator_type,
            "cooldown_days": self.cooldown_days,
            "duration_days": self.duration_days,
            "is_triggered": self.is_triggered,
            "last_check_error": self.last_check_error,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
        }


class PriceAlertEvent(db.Model):
    __tablename__ = "price_alert_events"
    id = db.Column(db.Integer, primary_key=True)

    alert_id = db.Column(db.Integer, nullable=False, index=True)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Price snapshot at the moment of trigger
    price = db.Column(db.Float, nullable=False)
    prev_price = db.Column(db.Float, nullable=True)
    reason = db.Column(db.String(250), nullable=True)

    # Store condition + symbol for easier querying/debugging
    condition = db.Column(db.String(20), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "price": self.price,
            "prev_price": self.prev_price,
            "reason": self.reason,
            "condition": self.condition,
            "symbol": self.symbol,
        }


class Expense(db.Model):

# New model for shared subscriptions between couple users
class CoupleSubscription(db.Model):
    __tablename__ = 'couple_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Owner
    partner_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Partner
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # monthly, yearly, etc.
    next_due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, canceled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    partner = db.relationship('User', foreign_keys=[partner_user_id])
    __tablename__ = "expenses"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="expenses")
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
    currency = db.Column(db.String(10), default='INR', nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "amount": self.amount,
            "currency": self.currency,
            "date": self.date,
            "ai_confidence": self.ai_confidence,
            "user_corrected": self.user_corrected,
            "is_subscription": self.is_subscription,
            "is_recurring": self.is_recurring,
            "is_anomaly": self.is_anomaly,
            "user_id": self.user_id
        }


class Asset(db.Model):
    __tablename__ = "assets"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="assets")
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    date = db.Column(db.String(40), nullable=False, default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))

    def to_dict(self):
        # Returns the real database primary key so /delete-item can look up the
        # row by stable PK rather than by positional list index. Using a
        # positional index was the root cause of the negative-index silent
        # deletion and out-of-range IndexError bugs (issue #125).
        return {"id": self.id, "name": self.name, "amount": self.amount, "currency": self.currency, "user_id": self.user_id, "date": self.date}


class Liability(db.Model):
    __tablename__ = "liabilities"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="liabilities")
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    date = db.Column(db.String(40), nullable=False, default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))

    def to_dict(self):
        # Same fix as Asset.to_dict -- returns the real PK, not a list index.
        return {"id": self.id, "name": self.name, "amount": self.amount, "currency": self.currency, "user_id": self.user_id, "date": self.date}


class BudgetLimit(db.Model):
    __tablename__ = "budget_limits"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="budget_limits")
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)
    limit_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "limit_amount": self.limit_amount,
            "currency": self.currency,
            "user_id": self.user_id
        }


class BudgetAlert(db.Model):
    __tablename__ = "budget_alerts"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="budget_alerts")
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)
    year_month = db.Column(db.String(7), nullable=False)  # e.g., "2026-06"
    threshold = db.Column(db.Integer, nullable=False)    # 80, 90, or 100
    currency = db.Column(db.String(10), default='INR', nullable=False)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "year_month": self.year_month,
            "threshold": self.threshold,
            "triggered_at": self.triggered_at.isoformat(),
            "currency": self.currency,
            "user_id": self.user_id
        }


class FinancialGoal(db.Model):
    __tablename__ = "financial_goals"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    target_date = db.Column(db.String(10), nullable=False)  # YYYY-MM

    # Optional AI-generated plan/tactics
    ai_milestone_tactics = db.Column(db.Text, nullable=True)  # plain text, 3-5 bullet points
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref="financial_goals")

    def to_dict(self):
        progress_percent = (self.current_amount / self.target_amount * 100) if self.target_amount > 0 else 0
        return {
            "id": self.id,
            "name": self.name,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "currency": self.currency,
            "progress_percent": round(progress_percent, 2),
            "target_date": self.target_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_id": self.user_id
        }



# ---------------- WEEKLY DIGEST (Scheduled AI) ----------------
class DigestPreference(db.Model):
    """Single-row preference store (no user table in current app)."""
    __tablename__ = "digest_preferences"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=True)
    enable_weekly_digest = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WeeklyDigestLog(db.Model):
    __tablename__ = "weekly_digest_logs"
    id = db.Column(db.Integer, primary_key=True)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)

    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="scheduled")  # scheduled|sent|failed|done
    digest_text = db.Column(db.Text, nullable=True)
    ai_used = db.Column(db.Boolean, default=False)

    snapshot_net_worth_start = db.Column(db.Float, nullable=True)
    snapshot_net_worth_end = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('period_start', 'period_end', name='uq_weekly_digest_period'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
            "digest_text": self.digest_text,
            "ai_used": self.ai_used,
            "snapshot_net_worth_start": self.snapshot_net_worth_start,
            "snapshot_net_worth_end": self.snapshot_net_worth_end,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class FxRateCache(db.Model):
    __tablename__ = "fx_rate_cache"
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(10), nullable=False)
    to_currency = db.Column(db.String(10), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FinancialGoalMilestone(db.Model):
    __tablename__ = "financial_goal_milestones"
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("financial_goals.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # e.g., "2026-06"
    target_amount_for_month = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="planned")  # planned, completed

class RecurringIncome(db.Model):
    __tablename__ = 'recurring_incomes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Salary, Rent, Freelance, Other
    source = db.Column(db.String(100), nullable=False)    # Employer/Source Name
    frequency = db.Column(db.String(20), nullable=False)   # daily, weekly, monthly, quarterly, yearly
    start_date = db.Column(db.Date, nullable=False)
    next_due_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_processed = db.Column(db.Date, nullable=True)

    user = db.relationship("User", backref="recurring_incomes")

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'category': self.category,
            'source': self.source,
            'frequency': self.frequency,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active,
            'currency': self.currency
        }

class IncomeOccurrence(db.Model):
    __tablename__ = 'income_occurrences'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recurring_income_id = db.Column(db.Integer, db.ForeignKey('recurring_incomes.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="income_occurrences")

    def to_dict(self):
        return {
            'id': self.id,
            'recurring_income_id': self.recurring_income_id,
            'amount': self.amount,
            'category': self.category,
            'source': self.source,
            'date': self.date.isoformat() if self.date else None,
            'currency': self.currency
        }

# ============================================
# LEDGER SYSTEM MODELS
# ============================================



class Account(db.Model):
    """Bank Account Model"""
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ✅ FIXED
    account_type = db.Column(db.String(50), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Numeric(15, 2), default=0.00)
    currency = db.Column(db.String(10), default='INR')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ✅ ADD THIS
    user = db.relationship("User", backref="accounts")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_type': self.account_type,
            'account_name': self.account_name,
            'balance': float(self.balance),
            'currency': self.currency,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def credit(self, amount):
        self.balance = float(self.balance) + amount
        return self
    
    def debit(self, amount):
        if float(self.balance) < amount:
            raise ValueError(f"Insufficient balance. Available: {self.balance}, Required: {amount}")
        self.balance = float(self.balance) - amount
        return self


class Transaction(db.Model):
    """Transaction Model - Atomic unit"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ✅ FIXED
    transaction_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='PENDING')
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # ✅ ADD THIS
    user = db.relationship("User", backref="transactions")
    entries = db.relationship('LedgerEntry', backref='transaction', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'reference_id': self.reference_id,
            'transaction_type': self.transaction_type,
            'status': self.status,
            'total_amount': float(self.total_amount),
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'entries': [e.to_dict() for e in self.entries]
        }


class LedgerEntry(db.Model):
    """Ledger Entry - Double-entry accounting"""
    __tablename__ = 'ledger_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    entry_type = db.Column(db.String(10), nullable=False)  # DEBIT or CREDIT
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    account = db.relationship('Account', backref='entries', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'account_id': self.account_id,
            'account_name': self.account.account_name if self.account else None,
            'entry_type': self.entry_type,
            'amount': float(self.amount),
            'description': self.description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None


        }

        # ============================================
# COUPLE FINANCE MODELS
# ============================================

class Couple(db.Model):
    """Couple Relationship Model"""
    __tablename__ = 'couples'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, ACTIVE, DECLINED, UNLINKED
    invitation_token = db.Column(db.String(100), unique=True, nullable=True)
    invitation_expires = db.Column(db.DateTime, nullable=True)
    linked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user1 = db.relationship("User", foreign_keys=[user1_id], backref="couple_user1")
    user2 = db.relationship("User", foreign_keys=[user2_id], backref="couple_user2")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'status': self.status,
            'linked_at': self.linked_at.isoformat() if self.linked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SharedGoal(db.Model):
    """Shared Goals for Couples"""
    __tablename__ = 'shared_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    target_amount = db.Column(db.Numeric(15, 2), nullable=False)
    current_amount = db.Column(db.Numeric(15, 2), default=0.00)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE, COMPLETED, CANCELLED
    priority = db.Column(db.String(20), default='MEDIUM')  # LOW, MEDIUM, HIGH
    icon = db.Column(db.String(50), default='🎯')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    couple = db.relationship("Couple", backref="shared_goals")
    contributions = db.relationship("GoalContribution", backref="goal", lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'name': self.name,
            'description': self.description,
            'target_amount': float(self.target_amount),
            'current_amount': float(self.current_amount),
            'progress': round(float(self.current_amount) / float(self.target_amount) * 100, 2) if float(self.target_amount) > 0 else 0,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'status': self.status,
            'priority': self.priority,
            'icon': self.icon,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'contributions': [c.to_dict() for c in self.contributions]
        }


class GoalContribution(db.Model):
    """Individual Contributions to Shared Goals"""
    __tablename__ = 'goal_contributions'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('shared_goals.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    note = db.Column(db.String(200))
    contributed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", backref="goal_contributions")
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'note': self.note,
            'contributed_at': self.contributed_at.isoformat() if self.contributed_at else None
        }


class SplitExpense(db.Model):
    """Split Expenses for Couples"""
    __tablename__ = 'split_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='Other')
    payer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    split_type = db.Column(db.String(20), default='EQUAL')  # EQUAL, PERCENTAGE, CUSTOM
    user1_share = db.Column(db.Numeric(15, 2), nullable=True)
    user2_share = db.Column(db.Numeric(15, 2), nullable=True)
    settled = db.Column(db.Boolean, default=False)
    expense_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    settled_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    couple = db.relationship("Couple", backref="split_expenses")
    payer = db.relationship("User", backref="paid_expenses")
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'total_amount': float(self.total_amount),
            'description': self.description,
            'category': self.category,
            'payer_id': self.payer_id,
            'split_type': self.split_type,
            'user1_share': float(self.user1_share) if self.user1_share else None,
            'user2_share': float(self.user2_share) if self.user2_share else None,
            'settled': self.settled,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'settled_at': self.settled_at.isoformat() if self.settled_at else None
        }


class CoupleBudget(db.Model):
    """Joint Budget for Couples"""
    __tablename__ = 'couple_budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    combined_limit = db.Column(db.Numeric(15, 2), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    couple = db.relationship("Couple", backref="budgets")
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'category': self.category,
            'combined_limit': float(self.combined_limit),
            'month': self.month,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CoupleTaxPlan(db.Model):
    """Tax Optimization for Couples"""
    __tablename__ = 'couple_tax_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    user1_income = db.Column(db.Numeric(15, 2), nullable=False)
    user2_income = db.Column(db.Numeric(15, 2), nullable=False)
    regime = db.Column(db.String(20), default='NEW')  # NEW, OLD
    total_tax = db.Column(db.Numeric(15, 2), nullable=True)
    total_savings = db.Column(db.Numeric(15, 2), nullable=True)
    suggestions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'user1_income': float(self.user1_income),
            'user2_income': float(self.user2_income),
            'regime': self.regime,
            'total_tax': float(self.total_tax) if self.total_tax else None,
            'total_savings': float(self.total_savings) if self.total_savings else None,
            'suggestions': self.suggestions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CoupleAlert(db.Model):
    """Alerts for Couple Activities"""
    __tablename__ = 'couple_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # INVITATION, GOAL, EXPENSE, BUDGET
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    couple = db.relationship("Couple", backref="alerts")
    user = db.relationship("User", backref="couple_alerts")
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None


        }


        # ============================================
# COUPLE FINANCE MODELS
# ============================================

class Couple(db.Model):
    """Couple Relationship Model"""
    __tablename__ = 'couples'
    
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, ACTIVE, DECLINED, UNLINKED
    invitation_token = db.Column(db.String(100), unique=True, nullable=True)
    invitation_expires = db.Column(db.DateTime, nullable=True)
    linked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user1 = db.relationship("User", foreign_keys=[user1_id], backref="couple_user1")
    user2 = db.relationship("User", foreign_keys=[user2_id], backref="couple_user2")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'status': self.status,
            'linked_at': self.linked_at.isoformat() if self.linked_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SharedGoal(db.Model):
    """Shared Goals for Couples"""
    __tablename__ = 'shared_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    target_amount = db.Column(db.Numeric(15, 2), nullable=False)
    current_amount = db.Column(db.Numeric(15, 2), default=0.00)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE, COMPLETED, CANCELLED
    priority = db.Column(db.String(20), default='MEDIUM')  # LOW, MEDIUM, HIGH
    icon = db.Column(db.String(50), default='🎯')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    couple = db.relationship("Couple", backref="shared_goals")
    contributions = db.relationship("GoalContribution", backref="goal", lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'name': self.name,
            'description': self.description,
            'target_amount': float(self.target_amount),
            'current_amount': float(self.current_amount),
            'progress': round(float(self.current_amount) / float(self.target_amount) * 100, 2) if float(self.target_amount) > 0 else 0,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'status': self.status,
            'priority': self.priority,
            'icon': self.icon,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'contributions': [c.to_dict() for c in self.contributions]
        }


class GoalContribution(db.Model):
    """Individual Contributions to Shared Goals"""
    __tablename__ = 'goal_contributions'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('shared_goals.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    note = db.Column(db.String(200))
    contributed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", backref="goal_contributions")
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'note': self.note,
            'contributed_at': self.contributed_at.isoformat() if self.contributed_at else None
        }


class SplitExpense(db.Model):
    """Split Expenses for Couples"""
    __tablename__ = 'split_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='Other')
    payer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    split_type = db.Column(db.String(20), default='EQUAL')  # EQUAL, PERCENTAGE, CUSTOM
    user1_share = db.Column(db.Numeric(15, 2), nullable=True)
    user2_share = db.Column(db.Numeric(15, 2), nullable=True)
    settled = db.Column(db.Boolean, default=False)
    expense_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    settled_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    couple = db.relationship("Couple", backref="split_expenses")
    payer = db.relationship("User", backref="paid_expenses")
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'total_amount': float(self.total_amount),
            'description': self.description,
            'category': self.category,
            'payer_id': self.payer_id,
            'split_type': self.split_type,
            'user1_share': float(self.user1_share) if self.user1_share else None,
            'user2_share': float(self.user2_share) if self.user2_share else None,
            'settled': self.settled,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'settled_at': self.settled_at.isoformat() if self.settled_at else None
        }


class CoupleBudget(db.Model):
    """Joint Budget for Couples"""
    __tablename__ = 'couple_budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    combined_limit = db.Column(db.Numeric(15, 2), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    couple = db.relationship("Couple", backref="budgets")
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'category': self.category,
            'combined_limit': float(self.combined_limit),
            'month': self.month,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CoupleTaxPlan(db.Model):
    """Tax Optimization for Couples"""
    __tablename__ = 'couple_tax_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    user1_income = db.Column(db.Numeric(15, 2), nullable=False)
    user2_income = db.Column(db.Numeric(15, 2), nullable=False)
    regime = db.Column(db.String(20), default='NEW')  # NEW, OLD
    total_tax = db.Column(db.Numeric(15, 2), nullable=True)
    total_savings = db.Column(db.Numeric(15, 2), nullable=True)
    suggestions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'user1_income': float(self.user1_income),
            'user2_income': float(self.user2_income),
            'regime': self.regime,
            'total_tax': float(self.total_tax) if self.total_tax else None,
            'total_savings': float(self.total_savings) if self.total_savings else None,
            'suggestions': self.suggestions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CoupleAlert(db.Model):
    """Alerts for Couple Activities"""
    __tablename__ = 'couple_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    couple_id = db.Column(db.Integer, db.ForeignKey('couples.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # INVITATION, GOAL, EXPENSE, BUDGET
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    couple = db.relationship("Couple", backref="alerts")
    user = db.relationship("User", backref="couple_alerts")
    
    def to_dict(self):
        return {
            'id': self.id,
            'couple_id': self.couple_id,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None

        }


   # ============================================
# BANK INTEGRATION MODELS
# ============================================

class BankConnection(db.Model):
    """Bank Connection Model"""
    __tablename__ = 'bank_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # upi, netbanking, card
    account_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=True)
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship("User", backref="bank_connections")
    
    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider,
            'account_name': self.account_name,
            'account_number': self.account_number[-4:] if self.account_number else None,
            'is_active': self.is_active,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BankTransaction(db.Model):
    """Bank Transaction Model"""
    __tablename__ = 'bank_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    connection_id = db.Column(db.Integer, db.ForeignKey('bank_connections.id'), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(10), default='INR')
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=True)
    merchant = db.Column(db.String(100), nullable=True)
    transaction_date = db.Column(db.DateTime, nullable=False)
    posted_date = db.Column(db.DateTime, nullable=True)
    is_anomaly = db.Column(db.Boolean, default=False)
    anomaly_reason = db.Column(db.String(200), nullable=True)
    is_flagged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="bank_transactions")
    connection = db.relationship("BankConnection", backref="transactions")
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'description': self.description,
            'category': self.category,
            'merchant': self.merchant,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'is_anomaly': self.is_anomaly,
            'anomaly_reason': self.anomaly_reason,
            'is_flagged': self.is_flagged
        }


class FraudAlert(db.Model):
    """Fraud Alert Model"""
    __tablename__ = 'fraud_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('bank_transactions.id'), nullable=True)
    alert_type = db.Column(db.String(50), nullable=False)  # high_amount, unusual_category, suspicious_pattern, etc.
    severity = db.Column(db.String(20), default='medium')  # low, medium, high
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship("User", backref="fraud_alerts")
    transaction = db.relationship("BankTransaction", backref="alerts")
    
    def to_dict(self):
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'is_read': self.is_read,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at.isoformat() if self.created_at else None

        }   

# ============================================
# GOAL-BASED INVESTMENT PLANNER MODELS
# ============================================

class InvestmentGoal(db.Model):
    """Investment Goal Model"""
    __tablename__ = 'investment_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(20), nullable=False)  # short_term, medium_term, long_term
    target_amount = db.Column(db.Numeric(15, 2), nullable=False)
    current_amount = db.Column(db.Numeric(15, 2), default=0.00)
    priority = db.Column(db.Integer, default=3)  # 1-5 (1=highest)
    timeframe = db.Column(db.Integer, nullable=False)  # months
    target_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE, COMPLETED, PAUSED
    icon = db.Column(db.String(50), default='🎯')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship("User", backref="investment_goals")
    allocations = db.relationship("GoalAllocation", backref="goal", lazy=True, cascade='all, delete-orphan')
    contributions = db.relationship("GoalContribution", backref="goal", lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        progress = (float(self.current_amount) / float(self.target_amount) * 100) if float(self.target_amount) > 0 else 0
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'target_amount': float(self.target_amount),
            'current_amount': float(self.current_amount),
            'progress': round(progress, 2),
            'priority': self.priority,
            'timeframe': self.timeframe,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'status': self.status,
            'icon': self.icon,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'shortfall': round(float(self.target_amount) - float(self.current_amount), 2),
            'monthly_required': self.calculate_monthly_required()
        }
    
    def calculate_monthly_required(self):
        remaining = float(self.target_amount) - float(self.current_amount)
        if remaining <= 0 or self.timeframe <= 0:
            return 0
        return round(remaining / self.timeframe, 2)


class GoalAllocation(db.Model):
    """Investment Allocation for Goals"""
    __tablename__ = 'goal_allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('investment_goals.id'), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)  # equity, debt, gold, real_estate, cash
    percentage = db.Column(db.Numeric(5, 2), nullable=False)  # Percentage of allocation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'asset_type': self.asset_type,
            'percentage': float(self.percentage)
        }


class GoalContribution(db.Model):
    """Contributions to Goals"""
    __tablename__ = 'goal_contributions'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('investment_goals.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    source = db.Column(db.String(50), default='manual')  # manual, auto, sip
    note = db.Column(db.String(200))
    contributed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'amount': float(self.amount),
            'source': self.source,
            'note': self.note,
            'contributed_at': self.contributed_at.isoformat() if self.contributed_at else None
        }


class GoalRecommendation(db.Model):
    """AI-generated Recommendations for Goals"""
    __tablename__ = 'goal_recommendations'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('investment_goals.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # allocation, contribution, timeline, priority
    message = db.Column(db.Text, nullable=False)
    suggestion = db.Column(db.Text)
    is_applied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'type': self.type,
            'message': self.message,
            'suggestion': self.suggestion,
            'is_applied': self.is_applied,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================
# NOTIFICATION MODELS
# ============================================

class Notification(db.Model):
    """User Notification Model"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # overspend, anomaly, goal_completed, investment_opportunity, etc.
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='medium')  # low, medium, high
    category = db.Column(db.String(50), default='general')  # finance, investment, goal, expense, security
    is_read = db.Column(db.Boolean, default=False)
    is_dismissed = db.Column(db.Boolean, default=False)
    action_url = db.Column(db.String(200), nullable=True)
    action_label = db.Column(db.String(50), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)  # Additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    dismissed_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship("User", backref="notifications")
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'category': self.category,
            'is_read': self.is_read,
            'is_dismissed': self.is_dismissed,
            'action_url': self.action_url,
            'action_label': self.action_label,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'metadata': json.loads(self.metadata_json) if self.metadata_json else None
        }


class NotificationPreference(db.Model):
    """User Notification Preferences"""
    __tablename__ = 'notification_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # notification type
    enabled = db.Column(db.Boolean, default=True)
    email_notification = db.Column(db.Boolean, default=True)
    push_notification = db.Column(db.Boolean, default=True)
    in_app_notification = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship("User", backref="notification_preferences")
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'enabled': self.enabled,
            'email_notification': self.email_notification,
            'push_notification': self.push_notification,
            'in_app_notification': self.in_app_notification,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }





class MilestoneNotification(db.Model):
    __tablename__ = "milestone_notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # goal, budget, sip
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    ref_id = db.Column(db.Integer, nullable=True)
    milestone_value = db.Column(db.Float, nullable=True)

    user = db.relationship("User", backref="milestone_notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "is_read": self.is_read,
            "ref_id": self.ref_id,
            "milestone_value": self.milestone_value
        }


class SipSchedule(db.Model):
    __tablename__ = "sip_schedules"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    day_of_month = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_notified_at = db.Column(db.DateTime, nullable=True)
    total_invested = db.Column(db.Float, default=0.0)

    user = db.relationship("User", backref="sip_schedules")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "amount": self.amount,
            "day_of_month": self.day_of_month,
            "currency": self.currency,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_notified_at": self.last_notified_at.isoformat() if self.last_notified_at else None,
            "total_invested": self.total_invested

        }



        }


