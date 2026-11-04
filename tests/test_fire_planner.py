"""
Unit and integration tests for the FIRE Planner Blueprint and API routes.
"""
import json
import pytest
from app import app, db
from models import User


@pytest.fixture
def auth_client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            user = User.query.filter_by(email="fireuser@example.com").first()
            if not user:
                user = User(
                    username="fireuser",
                    email="fireuser@example.com",
                    password_hash="pbkdf2:sha256:260000$test",
                )
                db.session.add(user)
                db.session.commit()
            user_id = user.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True

        yield client

        with app.app_context():
            db.drop_all()


def test_blueprint_is_registered():
    """Verify fire_planner blueprint is properly registered in Flask application."""
    assert "fire_planner" in app.blueprints
    bp = app.blueprints["fire_planner"]
    assert bp.name == "fire_planner"


def test_fire_planner_views_have_login_required():
    """Verify fire planner view handlers are decorated with login_required."""
    from src.features.fire_planner.routes import fire_planner_page, fire_plan, fire_quick

    # In Python/Flask, functions decorated with @login_required (functools.wraps) have __wrapped__
    assert hasattr(fire_planner_page, "__wrapped__")
    assert hasattr(fire_plan, "__wrapped__")
    assert hasattr(fire_quick, "__wrapped__")


def test_fire_planner_page_authenticated(auth_client):
    """Authenticated users can access /fire-planner and receive HTML template."""
    res = auth_client.get("/fire-planner")
    assert res.status_code == 200
    assert b"FIRE Planner" in res.data or b"fire" in res.data.lower()


def test_fire_plan_endpoint(auth_client):
    """POST /api/fire/plan generates a valid retirement plan and visualization data."""
    payload = {
        "current_age": 28,
        "retirement_age": 45,
        "annual_expenses": 600000,
        "current_corpus": 1500000,
        "monthly_savings": 40000,
        "return_mean": 0.12,
        "return_std": 0.14,
        "inflation_rate": 0.06,
    }
    res = auth_client.post("/api/fire/plan", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert "data" in data
    assert "visualization" in data
    assert "input_summary" in data["data"]
    assert "target_corpus" in data["data"]["input_summary"]
    assert data["data"]["input_summary"]["target_corpus"] > 0


def test_fire_plan_endpoint_defaults(auth_client):
    """POST /api/fire/plan operates with default parameters when payload is empty."""
    res = auth_client.post("/api/fire/plan", json={})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert "data" in data
    assert "input_summary" in data["data"]
    assert "target_corpus" in data["data"]["input_summary"]


def test_fire_quick_endpoint(auth_client):
    """POST /api/fire/quick runs Monte Carlo iterations and returns probability."""
    payload = {
        "current_age": 30,
        "retirement_age": 50,
        "annual_expenses": 500000,
        "current_corpus": 2000000,
        "monthly_savings": 35000,
    }
    res = auth_client.post("/api/fire/quick", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert "success_probability" in data
    assert "median_corpus" in data
    assert "target_corpus" in data
    assert 0.0 <= data["success_probability"] <= 100.0


def test_fire_quick_endpoint_defaults(auth_client):
    """POST /api/fire/quick operates with default parameters when payload is empty."""
    res = auth_client.post("/api/fire/quick", json={})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert "success_probability" in data
