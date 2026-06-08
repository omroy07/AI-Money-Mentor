"""
Regression tests for issue #125: /delete-item used a positional list index
instead of the real database primary key, causing:
  - id = -1  -> silently deleted the LAST record (Python negative indexing)
  - id >= len -> unhandled IndexError returned as generic 400

Fix: Asset.to_dict() and Liability.to_dict() now return self.id (real PK);
     /delete-item uses db.session.get() + 404 instead of rows[item_id];
     the frontend sends item.id (real PK) instead of the forEach array index.
"""
import json
import pathlib
import pytest

# ---- Minimal Flask app using only the models/routes we are testing ----
# We wire up a bare Flask app with just the net-worth routes so the test
# does not require groq, yfinance, or any other optional dependency.

from flask import Flask, request, jsonify
from models import db, Asset, Liability

def create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    @app.route("/net-worth")
    def net_worth():
        assets = Asset.query.order_by(Asset.id).all()
        liabilities = Liability.query.order_by(Liability.id).all()
        assets_data = [a.to_dict() for a in assets]
        liabilities_data = [l.to_dict() for l in liabilities]
        return jsonify({
            "assets": assets_data,
            "liabilities": liabilities_data,
            "total_assets": sum(i["amount"] for i in assets_data),
            "total_liabilities": sum(i["amount"] for i in liabilities_data),
        })

    @app.route("/add-asset", methods=["POST"])
    def add_asset():
        data = request.json
        a = Asset(name=data["name"], amount=float(data["amount"]))
        db.session.add(a)
        db.session.commit()
        return jsonify({"status": "success"})

    @app.route("/add-liability", methods=["POST"])
    def add_liability():
        data = request.json
        l = Liability(name=data["name"], amount=float(data["amount"]))
        db.session.add(l)
        db.session.commit()
        return jsonify({"status": "success"})

    @app.route("/delete-item", methods=["POST"])
    def delete_item():
        try:
            data = request.json
            item_type = data["type"]
            item_id = int(data["id"])
            item = db.session.get(Asset, item_id) if item_type == "asset" \
                else db.session.get(Liability, item_id)
            if item is None:
                return jsonify({"error": "Item not found"}), 404
            db.session.delete(item)
            db.session.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    return app


@pytest.fixture
def client():
    app = create_test_app()
    with app.test_client() as c:
        with app.app_context():
            db.create_all()
            yield c
            db.drop_all()


# ---- to_dict returns real PK ----

def test_asset_to_dict_returns_real_pk(client):
    """to_dict() must return the real DB primary key, not a positional index."""
    client.post("/add-asset", json={"name": "Gold", "amount": 50000})
    client.post("/add-asset", json={"name": "FD", "amount": 100000})
    res = client.get("/net-worth")
    data = json.loads(res.data)
    ids = [a["id"] for a in data["assets"]]
    # Real PKs are assigned by the DB (1-based autoincrement), never 0-based
    assert all(i >= 1 for i in ids), f"Expected real PKs >= 1, got {ids}"
    # IDs must be unique and stable (not reset to 0 and 1 each time)
    assert len(set(ids)) == 2


def test_liability_to_dict_returns_real_pk(client):
    """Liability.to_dict() must return self.id, not a list position."""
    client.post("/add-liability", json={"name": "Home Loan", "amount": 500000})
    client.post("/add-liability", json={"name": "Car Loan", "amount": 200000})
    res = client.get("/net-worth")
    data = json.loads(res.data)
    ids = [l["id"] for l in data["liabilities"]]
    assert all(i >= 1 for i in ids), f"Expected real PKs >= 1, got {ids}"
    assert len(set(ids)) == 2


# ---- /delete-item deletes the correct record ----

def test_delete_item_removes_correct_asset(client):
    """Deleting item 1 must remove only that item; others must survive."""
    client.post("/add-asset", json={"name": "Gold", "amount": 50000})
    client.post("/add-asset", json={"name": "FD", "amount": 100000})
    client.post("/add-asset", json={"name": "Stocks", "amount": 75000})

    data_before = json.loads(client.get("/net-worth").data)
    first_id = data_before["assets"][0]["id"]

    res = client.post("/delete-item", json={"type": "asset", "id": first_id})
    assert res.status_code == 200

    data_after = json.loads(client.get("/net-worth").data)
    assert len(data_after["assets"]) == 2
    remaining_ids = [a["id"] for a in data_after["assets"]]
    assert first_id not in remaining_ids, "Deleted item still present"


def test_delete_middle_item_leaves_others_intact(client):
    """Deleting a middle record must not affect the first or last."""
    client.post("/add-asset", json={"name": "A", "amount": 10000})
    client.post("/add-asset", json={"name": "B", "amount": 20000})
    client.post("/add-asset", json={"name": "C", "amount": 30000})

    data_before = json.loads(client.get("/net-worth").data)
    ids = [a["id"] for a in data_before["assets"]]
    middle_id = ids[1]

    client.post("/delete-item", json={"type": "asset", "id": middle_id})
    data_after = json.loads(client.get("/net-worth").data)
    remaining_ids = [a["id"] for a in data_after["assets"]]

    assert middle_id not in remaining_ids
    assert ids[0] in remaining_ids, "First item was wrongly deleted"
    assert ids[2] in remaining_ids, "Last item was wrongly deleted"


# ---- old bugs now return 404, not silent wrong deletion ----

def test_negative_id_returns_404_not_silent_deletion(client):
    """id=-1 must return 404; the old code silently deleted the last record."""
    client.post("/add-asset", json={"name": "Gold", "amount": 50000})
    client.post("/add-asset", json={"name": "FD", "amount": 100000})

    res = client.post("/delete-item", json={"type": "asset", "id": -1})
    assert res.status_code == 404, \
        f"id=-1 should return 404 (old code silently deleted last item), got {res.status_code}"

    # Both records must still be present
    data = json.loads(client.get("/net-worth").data)
    assert len(data["assets"]) == 2, "id=-1 should not delete any record"


def test_out_of_range_id_returns_404_not_500(client):
    """An id that does not exist must return 404; the old code raised IndexError."""
    client.post("/add-asset", json={"name": "Gold", "amount": 50000})

    res = client.post("/delete-item", json={"type": "asset", "id": 99999})
    assert res.status_code == 404, \
        f"Non-existent id should return 404, got {res.status_code}"


def test_delete_liability_correct(client):
    """Liability deletion also uses real PK and returns 404 for invalid id."""
    client.post("/add-liability", json={"name": "Home Loan", "amount": 500000})
    data = json.loads(client.get("/net-worth").data)
    real_id = data["liabilities"][0]["id"]

    res = client.post("/delete-item", json={"type": "liability", "id": real_id})
    assert res.status_code == 200

    data_after = json.loads(client.get("/net-worth").data)
    assert len(data_after["liabilities"]) == 0

    # Negative id -> 404
    client.post("/add-liability", json={"name": "Car Loan", "amount": 200000})
    res = client.post("/delete-item", json={"type": "liability", "id": -1})
    assert res.status_code == 404


# ---- structural: frontend sends item.id not array index ----

def test_frontend_uses_item_id_not_array_index():
    """networth.html delete buttons must use ${item.id}, not ${idx}."""
    html = (pathlib.Path(__file__).parents[1] / "templates" / "networth.html").read_text()
    assert "deleteNWItem('asset', ${item.id})" in html, \
        "Asset delete button should send item.id (real PK)"
    assert "deleteNWItem('liability', ${item.id})" in html, \
        "Liability delete button should send item.id (real PK)"
    # The old bug: array index used as the id
    assert "deleteNWItem('asset', ${idx})" not in html, \
        "Asset delete button must not send array index"
    assert "deleteNWItem('liability', ${idx})" not in html, \
        "Liability delete button must not send array index"
