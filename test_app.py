import pytest

import app as inventory
import seed_data


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Flask test client backed by a fresh, seeded temporary database."""
    monkeypatch.setattr(inventory, "DB", str(tmp_path / "test.db"))
    seed_data.seed()
    inventory.app.config["TESTING"] = True
    return inventory.app.test_client()


def login(client):
    return client.post("/", data={"username": "admin", "password": "admin123"})


def test_forecast_and_reorder_formulas():
    # constant demand of 10 units/day -> forecast 10, no variability
    demand, sigma = inventory.forecast_demand([10] * 30)
    assert demand == 10 and sigma == 0
    # exponential smoothing reacts to the latest value: 0.3*20 + 0.7*10 = 13
    assert inventory.forecast_demand([10, 20])[0] == 13
    product = {"id": 1, "sku": "T1", "name": "Test", "stock": 50, "lead_time": 4,
               "unit_price": 100, "supplier": "S"}
    plan = inventory.reorder_plan(product, [10] * 30)
    assert plan["safety"] == 0
    assert plan["rop"] == 40                       # d x L + safety stock
    assert plan["eoq"] == 428                      # ceil(sqrt(2 * 3650 * 500 / 20)) = ceil(427.2)
    assert plan["status"] == "Low"                 # 40 < 50 <= 60
    assert inventory.reorder_plan({**product, "stock": 40}, [10] * 30)["status"] == "Reorder Now"
    assert inventory.reorder_plan({**product, "stock": 0}, [10] * 30)["status"] == "Out of Stock"


def test_login_success_and_failure(client):
    bad = client.post("/", data={"username": "admin", "password": "wrong"})
    assert b"Invalid username or password" in bad.data
    ok = login(client)
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/dashboard")
    assert client.get("/dashboard").status_code == 200


def test_protected_page_redirects(client):
    for page in ("/dashboard", "/products", "/transactions", "/reorder", "/analysis"):
        response = client.get(page)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")


def test_stock_in_and_out_updates_stock(client):
    login(client)

    def stock():
        conn = inventory.get_db()
        value = conn.execute("SELECT stock FROM products WHERE sku='P001'").fetchone()["stock"]
        conn.close()
        return value

    assert stock() == 42
    client.post("/transactions", data={"product_id": 1, "txn_type": "PURCHASE", "quantity": 10,
                                       "txn_date": "2026-10-07"})
    assert stock() == 52
    client.post("/transactions", data={"product_id": 1, "txn_type": "SALE", "quantity": 12,
                                       "txn_date": "2026-10-07"})
    assert stock() == 40
    # a sale larger than the available stock is rejected and stock is unchanged
    rejected = client.post("/transactions", data={"product_id": 1, "txn_type": "SALE", "quantity": 999,
                                                  "txn_date": "2026-10-07"})
    assert b"not enough stock" in rejected.data
    assert stock() == 40


def test_reorder_alerts_and_abc(client):
    conn = inventory.get_db()
    plans = [inventory.reorder_plan(p, inventory.daily_sales(conn, p["id"]))
             for p in conn.execute("SELECT * FROM products").fetchall()]
    alerts = {p["sku"] for p in plans if p["status"] in ("Reorder Now", "Out of Stock")}
    assert alerts == {"P002", "P004", "P006", "P007", "P010"}
    assert next(p for p in plans if p["sku"] == "P010")["status"] == "Out of Stock"
    abc = inventory.abc_analysis(conn)
    conn.close()
    assert [sum(1 for i in abc if i["cls"] == c) for c in "ABC"] == [5, 5, 4]
    assert abc[0]["sku"] == "P007" and abc[-1]["cumulative"] == 100.0
