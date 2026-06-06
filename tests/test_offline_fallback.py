import os
import json
import pytest
from app import app, db
import app as app_module

@pytest.fixture
def offline_client():
    # Force offline mode by setting client to None temporarily
    original_client = app_module.client
    app_module.client = None
    
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()
            
    # Restore original client
    app_module.client = original_client


def test_app_starts_offline_without_key():
    """Verify that the global client in app.py behaves correctly based on key presence."""
    # Since we run tests with a dummy key locally, we check if a real/dummy key exists.
    # If the key is unset, client must be None. Otherwise, it must be initialized.
    has_key = "GROQ_API_KEY" in os.environ and os.environ["GROQ_API_KEY"].strip() not in ("", "your_groq_api_key_here")
    if not has_key:
        assert app_module.client is None
    else:
        assert app_module.client is not None


def test_chat_endpoint_fallback(offline_client):
    """Verify that /chat route returns a friendly offline message when client is None."""
    res = offline_client.post("/chat", json={"message": "hello"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "reply" in data
    assert "offline" in data["reply"].lower()
    assert "groq_api_key" in data["reply"].lower()


def test_agent_endpoint_fallback(offline_client):
    """Verify that /agent route returns a friendly offline error when client is None."""
    res = offline_client.post("/agent", json={"query": "hello"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "error" in data
    assert "offline" in data["error"].lower()
    assert "groq_api_key" in data["error"].lower()


def test_insights_endpoint_fallback(offline_client):
    """Verify that /insights route returns fallback UI card and summary when client is None."""
    res = offline_client.get("/insights")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "insights" in data
    assert "offline" in data["insights"].lower()
    assert "summary" in data
