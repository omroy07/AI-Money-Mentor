import pytest
from flask import jsonify
from werkzeug.exceptions import Conflict

from app import app as flask_app

SECRET = "sqlite3.OperationalError: no such table: users at /srv/app/secret/path.py"

REQUIRED_KEYS = {"success", "error", "code"}


@pytest.fixture
def api():
    flask_app.config["TESTING"] = True
    # TESTING makes Flask re-raise unhandled errors; the handlers should deal with them.
    flask_app.config["PROPAGATE_EXCEPTIONS"] = False
    return flask_app.test_client()


# Registered at import time: Flask refuses new routes once the app has served a request.
@flask_app.route("/_test_boom")
def _test_boom():
    raise RuntimeError(SECRET)


@flask_app.route("/_test_caught")
def _test_caught():
    return jsonify({"success": False, "error": SECRET}), 500


@flask_app.route("/_test_conflict")
def _test_conflict():
    raise Conflict("already exists")


def _assert_shape(resp, status):
    data = resp.get_json()
    assert resp.status_code == status
    assert REQUIRED_KEYS <= set(data)
    assert data["success"] is False
    assert data["code"] == status
    assert data["request_id"]


def test_unexpected_exception_hides_details(api):
    resp = api.get("/_test_boom", headers={"Accept": "application/json"})
    _assert_shape(resp, 500)
    assert SECRET not in resp.get_data(as_text=True)
    assert "RuntimeError" not in resp.get_data(as_text=True)


def test_route_returning_str_e_is_sanitized(api):
    resp = api.get("/_test_caught", headers={"Accept": "application/json"})
    _assert_shape(resp, 500)
    assert SECRET not in resp.get_data(as_text=True)


def test_404_shape(api):
    resp = api.get("/definitely-not-a-route", headers={"Accept": "application/json"})
    _assert_shape(resp, 404)


def test_405_shape(api):
    resp = api.post("/_test_boom", headers={"Accept": "application/json"})
    _assert_shape(resp, 405)


def test_other_http_errors_use_same_shape(api):
    resp = api.get("/_test_conflict", headers={"Accept": "application/json"})
    _assert_shape(resp, 409)


def test_html_clients_still_get_error_page(api):
    resp = api.get("/definitely-not-a-route", headers={"Accept": "text/html"})
    assert resp.status_code == 404
    assert resp.mimetype == "text/html"
