import json
import pytest
from unittest.mock import patch
from app import app, db, check_stock_alerts_job
from models import PriceAlert

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_create_and_get_price_alerts(client):
    # 1. Create alert
    res = client.post("/api/alerts", json={
        "symbol": "AAPL",
        "target_price": 150.5,
        "condition": "above"
    })
    assert res.status_code == 201
    data = json.loads(res.data)
    assert data["symbol"] == "AAPL"
    assert data["target_price"] == 150.5
    assert data["condition"] == "above"
    assert data["is_triggered"] is False

    # 2. Get alerts
    res = client.get("/api/alerts")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert len(data) == 1
    assert data[0]["symbol"] == "AAPL"

def test_delete_price_alert(client):
    # Create
    res = client.post("/api/alerts", json={
        "symbol": "TCS",
        "target_price": 3000.0,
        "condition": "below"
    })
    alert_id = json.loads(res.data)["id"]

    # Delete
    res = client.delete(f"/api/alerts/{alert_id}")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"

    # Get should be empty
    res = client.get("/api/alerts")
    assert len(json.loads(res.data)) == 0

def test_check_stock_alerts_job(client):
    # Create two alerts:
    # 1. AAPL above 150 (triggers if price >= 150)
    # 2. TCS below 3000 (does not trigger if price > 3000)
    client.post("/api/alerts", json={"symbol": "AAPL", "target_price": 150.0, "condition": "above"})
    client.post("/api/alerts", json={"symbol": "TCS", "target_price": 3000.0, "condition": "below"})

    def mock_get_stock_price(symbol):
        if symbol == "AAPL":
            return {"price": 155.0}
        elif symbol == "TCS":
            return {"price": 3100.0}
        return {"error": "not found"}

    with patch("app.get_stock_price", side_effect=mock_get_stock_price):
        check_stock_alerts_job()

    # Verify triggering status in db
    with app.app_context():
        aapl_alert = PriceAlert.query.filter_by(symbol="AAPL").first()
        tcs_alert = PriceAlert.query.filter_by(symbol="TCS").first()
        assert aapl_alert.is_triggered is True
        assert tcs_alert.is_triggered is False
