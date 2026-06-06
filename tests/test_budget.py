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
            yield client
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
