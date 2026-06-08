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
