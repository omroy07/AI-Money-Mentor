import json
import pytest
from app import app, db
from models import BudgetLimit, BudgetAlert, Expense

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            from models import User
            user = User.query.filter_by(email="test@example.com").first()
            if not user:
                user = User(username="testuser", email="test@example.com", password_hash="pbkdf2:sha256:260000$test")
                db.session.add(user)
                db.session.commit()
            user_id = user.id
            
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
            
        yield client
        
        with app.app_context():
            db.drop_all()

def test_set_and_get_budget_limits(client):
    # Set limit
    res = client.post("/budget/limits", json={
        "category": "Food",
        "limit_amount": 5000.0
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"

    # Get limits
    res = client.get("/budget/limits")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert len(data) == 1
    assert data[0]["category"] == "Food"
    assert data[0]["limit_amount"] == 5000.0

def test_budget_status_calculation(client):
    # Set limit for Food
    client.post("/budget/limits", json={"category": "Food", "limit_amount": 1000.0})
    
    # Add expenses
    client.post("/add_expense", json={"category": "Food", "amount": 300.0, "date": "2026-06-01"})
    client.post("/add_expense", json={"category": "Food", "amount": 400.0, "date": "2026-06-02"})
    client.post("/add_expense", json={"category": "Travel", "amount": 150.0, "date": "2026-06-03"})

    # Get status
    res = client.get("/budget/status?month=2026-06")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["month"] == "2026-06"
    assert data["total_budgeted"] == 1000.0
    assert data["total_spent"] == 850.0
    
    # Food category detailed check
    food_cat = next(c for c in data["categories"] if c["category"] == "Food")
    assert food_cat["spent"] == 700.0
    assert food_cat["percentage"] == 70.0

def test_realtime_threshold_alerts(client):
    # Set limit for Food = 1000
    client.post("/budget/limits", json={"category": "Food", "limit_amount": 1000.0})

    # Add expense = 750 (75% - no alert)
    client.post("/add_expense", json={"category": "Food", "amount": 750.0, "date": "2026-06-01"})
    alerts = json.loads(client.get("/budget/alerts").data)
    assert len(alerts) == 0

    # Add expense = 100 (85% total - triggers 80% alert)
    client.post("/add_expense", json={"category": "Food", "amount": 100.0, "date": "2026-06-02"})
    alerts = json.loads(client.get("/budget/alerts").data)
    assert len(alerts) == 1
    assert alerts[0]["category"] == "Food"
    assert alerts[0]["threshold"] == 80

    # Add expense = 100 (95% total - triggers 90% alert)
    client.post("/add_expense", json={"category": "Food", "amount": 100.0, "date": "2026-06-03"})
    alerts = json.loads(client.get("/budget/alerts").data)
    # Order by triggered_at desc, so index 0 is threshold 90
    assert len(alerts) == 2
    assert alerts[0]["threshold"] == 90


def test_delete_budget_limit(client):
    """DELETE /budget/limits/<id> removes the limit and returns its category."""
    # Create a limit first
    client.post("/budget/limits", json={"category": "Shopping", "limit_amount": 2000.0})
    limits = json.loads(client.get("/budget/limits").data)
    assert len(limits) == 1
    limit_id = limits[0]["id"]

    # Delete it
    res = client.delete(f"/budget/limits/{limit_id}")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert data["deleted_category"] == "Shopping"

    # Confirm it's gone
    limits = json.loads(client.get("/budget/limits").data)
    assert len(limits) == 0


def test_delete_budget_limit_cascades_alerts(client):
    """Deleting a limit also removes any BudgetAlert rows for that category."""
    # Set limit and add 85% spend → fires the 80% alert only (85% < 90%)
    client.post("/budget/limits", json={"category": "Food", "limit_amount": 100.0})
    client.post("/add_expense", json={"category": "Food", "amount": 85.0, "date": "2026-06-01"})
    alerts_before = json.loads(client.get("/budget/alerts").data)
    assert len(alerts_before) == 1

    limits = json.loads(client.get("/budget/limits").data)
    limit_id = limits[0]["id"]

    # Delete the limit — its alert should be cleaned up too
    client.delete(f"/budget/limits/{limit_id}")
    alerts_after = json.loads(client.get("/budget/alerts").data)
    assert len(alerts_after) == 0


def test_delete_budget_limit_not_found(client):
    """DELETE /budget/limits/<id> returns 404 for a non-existent ID."""
    res = client.delete("/budget/limits/9999")
    assert res.status_code == 404
    data = json.loads(res.data)
    assert "not found" in data["error"].lower()


def test_configurable_thresholds(client):
    """Budgets and thresholds are configurable via POST /budget/limits."""
    # 1. Configure with list of thresholds [80, 100]
    res = client.post("/budget/limits", json={
        "category": "Travel",
        "limit_amount": 2000.0,
        "currency": "INR",
        "thresholds": [80, 100]
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert data["limit"]["thresholds"] == [80, 100]

    # Verify GET /budget/limits returns configured thresholds
    res = client.get("/budget/limits")
    assert res.status_code == 200
    limits = json.loads(res.data)
    travel_limit = next(l for l in limits if l["category"] == "Travel")
    assert travel_limit["thresholds"] == [80, 100]

    # 2. Configure with string of comma-separated thresholds "50, 80, 100"
    res = client.post("/budget/limits", json={
        "category": "Shopping",
        "limit_amount": 1500.0,
        "currency": "INR",
        "thresholds": "50, 80, 100"
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["limit"]["thresholds"] == [50, 80, 100]

    # 3. Verify GET /budget/status reflects configured thresholds per category
    res = client.get("/budget/status?month=2026-06")
    assert res.status_code == 200
    status_data = json.loads(res.data)
    shop_status = next(c for c in status_data["categories"] if c["category"] == "Shopping")
    assert shop_status["thresholds"] == [50, 80, 100]


def test_alert_triggered_once_per_threshold_per_period(client):
    """Alerts must trigger exactly once per threshold per period (month)."""
    # Configure budget for Food with thresholds [80, 100]
    client.post("/budget/limits", json={
        "category": "Groceries",
        "limit_amount": 1000.0,
        "thresholds": [80, 100]
    })

    # Period 1: 2026-06
    # 70% spend (700) -> no alert
    client.post("/add_expense", json={"category": "Groceries", "amount": 700.0, "date": "2026-06-01"})
    alerts = json.loads(client.get("/budget/alerts").data)
    assert len(alerts) == 0

    # 85% spend total (add 150 -> 850 total) -> triggers 80% alert
    client.post("/add_expense", json={"category": "Groceries", "amount": 150.0, "date": "2026-06-05"})
    alerts = json.loads(client.get("/budget/alerts").data)
    assert len(alerts) == 1
    assert alerts[0]["threshold"] == 80
    assert alerts[0]["year_month"] == "2026-06"

    # Additional spend in same month staying below 100% (add 50 -> 900 total)
    # 80% was already triggered this period, 90% is NOT a configured threshold -> no new alert
    client.post("/add_expense", json={"category": "Groceries", "amount": 50.0, "date": "2026-06-10"})
    alerts = json.loads(client.get("/budget/alerts").data)
    assert len(alerts) == 1

    # Cross 100% (add 150 -> 1050 total, 105%) -> triggers 100% alert
    client.post("/add_expense", json={"category": "Groceries", "amount": 150.0, "date": "2026-06-15"})
    alerts = json.loads(client.get("/budget/alerts").data)
    assert len(alerts) == 2
    thresholds = [a["threshold"] for a in alerts]
    assert 80 in thresholds
    assert 100 in thresholds

    # Further spend in same month (add 200 -> 1250 total, 125%)
    # Neither 80% nor 100% should re-trigger for 2026-06
    client.post("/add_expense", json={"category": "Groceries", "amount": 200.0, "date": "2026-06-20"})
    alerts = json.loads(client.get("/budget/alerts").data)
    assert len(alerts) == 2

    # Period 2: 2026-07 (new month)
    # Spending 850 in new month triggers 80% alert for 2026-07
    client.post("/add_expense", json={"category": "Groceries", "amount": 850.0, "date": "2026-07-02"})
    alerts = json.loads(client.get("/budget/alerts").data)
    assert len(alerts) == 3
    new_month_alert = next(a for a in alerts if a["year_month"] == "2026-07")
    assert new_month_alert["threshold"] == 80


def test_in_app_notification_created_on_alert(client):
    """When a threshold is crossed, an in-app notification is created."""
    from models import Notification

    client.post("/budget/limits", json={
        "category": "Dining",
        "limit_amount": 500.0,
        "thresholds": [80, 100]
    })

    # Cross 80% (420 / 500 = 84%)
    client.post("/add_expense", json={"category": "Dining", "amount": 420.0, "date": "2026-06-01"})

    with app.app_context():
        notifs = Notification.query.filter_by(type="budget_alert").all()
        assert len(notifs) >= 1
        notif_80 = next(n for n in notifs if "80%" in n.title)
        assert notif_80.category == "budget"
        assert notif_80.severity == "medium"
        assert "Dining" in notif_80.message
        assert notif_80.action_url == "/budget"

    # Cross 100% (add 100 -> 520 / 500 = 104%)
    client.post("/add_expense", json={"category": "Dining", "amount": 100.0, "date": "2026-06-02"})

    with app.app_context():
        notifs = Notification.query.filter_by(type="budget_alert").all()
        notif_100 = next(n for n in notifs if "100%" in n.title)
        assert notif_100.severity == "high"


def test_email_sent_on_threshold_and_opt_out(client, monkeypatch):
    """Email is sent when threshold is crossed; users can opt out of emails."""
    sent_emails = []

    def mock_send(msg):
        sent_emails.append(msg)

    monkeypatch.setattr("app.mail.send", mock_send)

    # 1. Set budget limit
    client.post("/budget/limits", json={
        "category": "Entertainment",
        "limit_amount": 1000.0,
        "thresholds": [80, 100]
    })

    # Cross 80% (850) -> User is not opted out, so email should be sent
    client.post("/add_expense", json={"category": "Entertainment", "amount": 850.0, "date": "2026-08-01"})
    assert len(sent_emails) == 1
    assert "80%" in sent_emails[0].subject
    assert "Entertainment" in sent_emails[0].subject
    assert "test@example.com" in sent_emails[0].recipients

    # 2. User opts out of budget emails
    res = client.post("/budget/email-settings", json={"budget_email_enabled": False})
    assert res.status_code == 200
    assert json.loads(res.data)["budget_email_enabled"] is False

    # Check GET /budget/email-settings confirms opted out
    res = client.get("/budget/email-settings")
    assert json.loads(res.data)["budget_email_enabled"] is False

    # Cross 100% (add 200 -> 1050) -> In-app alert created, but NO email sent!
    client.post("/add_expense", json={"category": "Entertainment", "amount": 200.0, "date": "2026-08-02"})
    assert len(sent_emails) == 1  # Still 1, no new email sent!

    alerts = json.loads(client.get("/budget/alerts").data)
    assert any(a["threshold"] == 100 and a["category"] == "Entertainment" for a in alerts)

    # 3. User opts back in
    client.post("/budget/email-settings", json={"budget_email_enabled": True})
    res = client.get("/budget/email-settings")
    assert json.loads(res.data)["budget_email_enabled"] is True


def test_unsubscribe_endpoints(client):
    """Dedicated unsubscribe endpoint opts the user out of budget alert emails."""
    # Test POST /api/budget/unsubscribe
    res = client.post("/api/budget/unsubscribe", json={"email": "test@example.com"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"

    # Verify user is now opted out
    res = client.get("/budget/email-settings")
    assert json.loads(res.data)["budget_email_enabled"] is False

    # Test GET /budget/unsubscribe HTML response
    res = client.get("/budget/unsubscribe?email=test@example.com")
    assert res.status_code == 200
    assert b"Unsubscribed Successfully" in res.data

