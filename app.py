from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, timedelta
import numpy as np
import sqlite3
import math
import os

app = Flask(__name__)
app.secret_key = "devops-mini-project-secret"
DB = os.environ.get("INVENTORY_DB", "inventory.db")

SERVICE_Z = 1.65      # z-value for 95% service level
ORDER_COST = 500      # cost of placing one purchase order (Rs)
HOLDING_RATE = 0.20   # yearly holding cost = 20% of unit price
HISTORY_DAYS = 30     # days of sales used for the demand forecast


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL,
        stock INTEGER NOT NULL,
        lead_time INTEGER NOT NULL,
        supplier TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        txn_date TEXT NOT NULL,
        txn_type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")
    conn.commit()
    conn.close()


def daily_sales(conn, product_id, days=HISTORY_DAYS):
    """Units sold per day for the last `days` days (0 for days without sales)."""
    end = date.fromisoformat(conn.execute(
        "SELECT COALESCE(MAX(txn_date), DATE('now')) FROM transactions").fetchone()[0])
    start = end - timedelta(days=days - 1)
    rows = conn.execute("SELECT txn_date, SUM(quantity) AS q FROM transactions WHERE product_id=? "
                        "AND txn_type='SALE' AND txn_date>=? GROUP BY txn_date",
                        (product_id, start.isoformat())).fetchall()
    sold = {r["txn_date"]: r["q"] for r in rows}
    return [sold.get((start + timedelta(days=i)).isoformat(), 0) for i in range(days)]


def forecast_demand(sales, alpha=0.3):
    """Exponential smoothing forecast of daily demand and its standard deviation."""
    level = sales[0]
    for s in sales[1:]:
        level = alpha * s + (1 - alpha) * level
    return round(level, 2), round(float(np.std(sales)), 2)


def reorder_plan(p, sales):
    demand, sigma = forecast_demand(sales)
    safety = SERVICE_Z * sigma * math.sqrt(p["lead_time"])
    rop = demand * p["lead_time"] + safety
    yearly = demand * 365
    holding = p["unit_price"] * HOLDING_RATE
    eoq = math.sqrt(2 * yearly * ORDER_COST / holding) if yearly else 0
    cover = p["stock"] / demand if demand else 999
    status = "Out of Stock" if p["stock"] == 0 else ("Reorder Now" if p["stock"] <= rop
             else ("Low" if p["stock"] <= rop * 1.5 else "OK"))
    return {"id": p["id"], "sku": p["sku"], "name": p["name"], "stock": p["stock"],
            "demand": demand, "safety": math.ceil(safety), "rop": math.ceil(rop),
            "eoq": math.ceil(eoq), "cover": round(cover, 1), "status": status,
            "supplier": p["supplier"], "lead_time": p["lead_time"]}


def abc_analysis(conn):
    """Classifies products by yearly consumption value: A = top 80%, B = next 15%, C = rest."""
    items = []
    for p in conn.execute("SELECT * FROM products").fetchall():
        demand, _ = forecast_demand(daily_sales(conn, p["id"]))
        items.append({"sku": p["sku"], "name": p["name"],
                      "value": round(demand * 365 * p["unit_price"])})
    items.sort(key=lambda i: -i["value"])
    total = sum(i["value"] for i in items) or 1
    running = 0
    for i in items:
        running += i["value"]
        i["share"] = round(i["value"] / total * 100, 1)
        i["cumulative"] = round(running / total * 100, 1)
        i["cls"] = "A" if i["cumulative"] <= 80 else ("B" if i["cumulative"] <= 95 else "C")
    return items


def logged_in():
    return session.get("logged_in")


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin123":
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))
    conn = get_db()
    products = conn.execute("SELECT * FROM products ORDER BY sku").fetchall()
    plans = [reorder_plan(p, daily_sales(conn, p["id"])) for p in products]
    value = sum(p["stock"] * p["unit_price"] for p in products)
    abc = abc_analysis(conn)
    conn.close()
    alerts = [p for p in plans if p["status"] in ("Reorder Now", "Out of Stock")]
    return render_template("dashboard.html", products=len(products), value=round(value),
                           alerts=alerts, plans=plans, low=sum(p["status"] == "Low" for p in plans),
                           abc={c: sum(1 for i in abc if i["cls"] == c) for c in "ABC"})


@app.route("/products", methods=["GET", "POST"])
def products():
    if not logged_in():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        try:
            conn.execute("INSERT INTO products (sku, name, category, unit_price, stock, lead_time, "
                         "supplier) VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (request.form["sku"], request.form["name"], request.form["category"],
                          float(request.form["unit_price"]), int(request.form["stock"]),
                          int(request.form["lead_time"]), request.form["supplier"]))
            conn.commit()
            flash("Product added successfully")
        except sqlite3.IntegrityError:
            flash("SKU already exists")
        except ValueError:
            flash("Enter valid price, stock and lead time")
    rows = conn.execute("SELECT * FROM products ORDER BY sku").fetchall()
    conn.close()
    return render_template("products.html", rows=rows)


@app.route("/transactions", methods=["GET", "POST"])
def transactions():
    if not logged_in():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        pid, qty, kind = int(request.form["product_id"]), int(request.form["quantity"]), request.form["txn_type"]
        stock = conn.execute("SELECT stock FROM products WHERE id=?", (pid,)).fetchone()["stock"]
        if qty <= 0 or (kind == "SALE" and qty > stock):
            flash("Invalid quantity - not enough stock" if qty > 0 else "Quantity must be positive")
        else:
            conn.execute("INSERT INTO transactions (product_id, txn_date, txn_type, quantity) VALUES (?, ?, ?, ?)",
                         (pid, request.form["txn_date"], kind, qty))
            conn.execute("UPDATE products SET stock = stock + ? WHERE id=?",
                         (qty if kind == "PURCHASE" else -qty, pid))
            conn.commit()
            flash(f"{kind.title()} of {qty} units recorded - stock updated")
    rows = conn.execute("SELECT t.*, p.sku, p.name FROM transactions t JOIN products p ON p.id = t.product_id "
                        "ORDER BY t.id DESC LIMIT 15").fetchall()
    items = conn.execute("SELECT id, sku, name FROM products ORDER BY sku").fetchall()
    last = conn.execute("SELECT COALESCE(MAX(txn_date), DATE('now')) FROM transactions").fetchone()[0]
    conn.close()
    return render_template("transactions.html", rows=rows, items=items, today=last)


@app.route("/reorder")
def reorder():
    if not logged_in():
        return redirect(url_for("login"))
    conn = get_db()
    plans = [reorder_plan(p, daily_sales(conn, p["id"]))
             for p in conn.execute("SELECT * FROM products").fetchall()]
    conn.close()
    plans.sort(key=lambda p: p["cover"])
    return render_template("reorder.html", plans=plans, z=SERVICE_Z, s=ORDER_COST, h=HOLDING_RATE)


@app.route("/analysis")
def analysis():
    if not logged_in():
        return redirect(url_for("login"))
    conn = get_db()
    items = abc_analysis(conn)
    conn.close()
    return render_template("analysis.html", items=items)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
