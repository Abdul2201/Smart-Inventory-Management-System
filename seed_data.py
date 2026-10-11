"""Loads a sample store (14 products, 60 days of sales history) into the database.

Run:  python seed_data.py          (does nothing if products already exist)
      python seed_data.py --reset  (wipes the database and reloads the sample store)
"""
import os
import sys
from datetime import date, timedelta

import app as inventory

END_DATE = date(2026, 10, 7)   # last day of the sales history
DAYS = 60

# sku, name, category, unit price, current stock, lead time (days), supplier
PRODUCTS = [
    ("P001", "USB Keyboard", "Electronics", 650, 42, 5, "TechSupply Co"),
    ("P002", "Wireless Mouse", "Electronics", 450, 18, 5, "TechSupply Co"),
    ("P003", "HDMI Cable 1.5m", "Electronics", 250, 95, 4, "TechSupply Co"),
    ("P004", "A4 Paper Ream", "Stationery", 280, 30, 3, "PaperMart"),
    ("P005", "Ball Pen Box", "Stationery", 120, 160, 3, "PaperMart"),
    ("P006", "Notebook 200 Pages", "Stationery", 60, 40, 3, "PaperMart"),
    ("P007", "Printer Toner", "Electronics", 2400, 14, 7, "PrintWorld"),
    ("P008", "LED Bulb 9W", "Electrical", 110, 210, 4, "BrightLite"),
    ("P009", "Extension Board", "Electrical", 520, 25, 6, "BrightLite"),
    ("P010", "Hand Sanitizer", "Hygiene", 150, 0, 2, "CleanCare"),
    ("P011", "Water Bottle 1L", "Household", 180, 64, 4, "HomeNeeds"),
    ("P012", "Pendrive 32GB", "Electronics", 420, 38, 5, "TechSupply Co"),
    ("P013", "Stapler", "Stationery", 160, 44, 3, "PaperMart"),
    ("P014", "Whiteboard Marker Set", "Stationery", 220, 22, 3, "PaperMart"),
]

# Units sold per day, oldest day first (60 values per product, the last value is 2026-10-07).
SALES = {
    "P001": [3, 7, 2, 5, 10, 5, 17, 4, 4, 2, 10, 6, 6, 10, 1, 0, 5, 8, 7, 2, 3, 5, 14, 10, 12, 9, 6, 5, 4, 8, 8, 6, 6, 11, 3, 7, 7, 6, 3, 4, 5, 6, 4, 6, 3, 4, 4, 4, 5, 3, 3, 3, 5, 3, 5, 0, 5, 9, 7, 5],
    "P002": [0, 3, 11, 9, 18, 6, 5, 6, 7, 5, 7, 1, 4, 3, 20, 0, 2, 12, 13, 12, 7, 5, 9, 1, 11, 7, 3, 2, 4, 4, 6, 5, 0, 8, 5, 10, 8, 5, 9, 7, 8, 8, 4, 10, 4, 11, 7, 5, 0, 4, 5, 6, 4, 11, 5, 6, 3, 5, 7, 8],
    "P003": [2, 0, 0, 4, 3, 4, 3, 0, 3, 4, 1, 0, 0, 3, 3, 0, 2, 4, 2, 0, 1, 2, 4, 4, 5, 0, 1, 3, 3, 2, 4, 1, 1, 3, 3, 2, 3, 1, 3, 0, 3, 1, 2, 0, 3, 3, 2, 1, 3, 2, 2, 0, 0, 1, 2, 1, 2, 4, 2, 2],
    "P004": [28, 31, 10, 39, 20, 29, 24, 33, 33, 34, 25, 20, 16, 31, 0, 37, 23, 22, 37, 30, 22, 34, 2, 42, 24, 26, 0, 27, 32, 13, 26, 28, 40, 11, 27, 24, 24, 18, 32, 40, 26, 23, 29, 27, 32, 25, 27, 28, 30, 21, 45, 29, 44, 29, 32, 33, 30, 21, 30, 0],  # 2026-10-07: 12 units are sold live in the demo
    "P005": [0, 1, 2, 9, 3, 2, 1, 5, 6, 9, 2, 3, 0, 6, 6, 2, 3, 3, 5, 6, 7, 3, 1, 2, 4, 1, 5, 9, 5, 7, 4, 4, 6, 3, 9, 7, 3, 5, 3, 7, 6, 1, 3, 7, 4, 2, 4, 4, 2, 0, 8, 1, 5, 4, 4, 1, 6, 2, 1, 8],
    "P006": [14, 19, 18, 17, 15, 15, 11, 15, 14, 20, 20, 14, 22, 21, 12, 8, 19, 6, 20, 16, 10, 4, 15, 21, 17, 1, 15, 15, 16, 11, 6, 19, 14, 9, 19, 9, 15, 11, 14, 15, 22, 9, 14, 20, 23, 15, 11, 12, 5, 19, 18, 19, 21, 17, 23, 11, 27, 16, 11, 9],
    "P007": [3, 4, 0, 0, 8, 5, 6, 7, 5, 3, 8, 4, 2, 0, 6, 3, 5, 1, 3, 5, 2, 1, 4, 4, 6, 2, 2, 0, 4, 2, 4, 5, 1, 4, 4, 4, 4, 3, 3, 3, 5, 4, 3, 4, 3, 5, 2, 4, 5, 5, 4, 4, 0, 3, 4, 1, 5, 6, 5, 2],
    "P008": [9, 5, 8, 4, 13, 2, 1, 10, 4, 6, 13, 3, 4, 4, 7, 15, 13, 9, 8, 10, 0, 1, 4, 2, 6, 9, 7, 6, 5, 10, 3, 5, 6, 4, 3, 4, 7, 4, 3, 5, 1, 4, 5, 9, 8, 3, 7, 8, 5, 6, 6, 6, 7, 5, 6, 6, 4, 5, 3, 7],
    "P009": [4, 3, 3, 1, 0, 7, 0, 2, 1, 2, 2, 6, 0, 2, 2, 2, 2, 1, 0, 4, 7, 2, 1, 1, 2, 2, 1, 2, 2, 3, 2, 2, 2, 2, 1, 2, 2, 3, 1, 3, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 3, 0, 2, 3, 2, 1, 1, 3],
    "P010": [7, 7, 2, 10, 1, 10, 3, 9, 11, 9, 4, 5, 7, 11, 4, 7, 9, 1, 4, 6, 9, 6, 5, 3, 12, 5, 1, 8, 12, 5, 5, 7, 7, 2, 7, 4, 10, 6, 5, 7, 6, 6, 4, 5, 4, 4, 3, 3, 5, 1, 3, 1, 2, 5, 6, 5, 4, 4, 6, 7],
    "P011": [5, 5, 4, 2, 3, 0, 0, 2, 10, 2, 7, 0, 2, 9, 4, 2, 6, 6, 6, 8, 3, 4, 7, 7, 4, 8, 2, 5, 4, 6, 3, 5, 4, 5, 4, 5, 4, 4, 3, 4, 3, 5, 3, 3, 4, 0, 4, 4, 4, 5, 5, 4, 4, 4, 7, 3, 4, 2, 5, 3],
    "P012": [3, 3, 5, 2, 3, 3, 3, 5, 2, 1, 1, 3, 1, 1, 2, 3, 3, 3, 7, 1, 2, 0, 2, 5, 0, 2, 2, 0, 2, 0, 3, 2, 2, 3, 2, 2, 3, 4, 4, 2, 3, 3, 2, 3, 4, 2, 5, 2, 2, 1, 4, 4, 5, 2, 2, 4, 4, 3, 3, 1],
    "P013": [5, 3, 1, 0, 2, 8, 0, 0, 7, 0, 7, 6, 4, 0, 2, 7, 6, 1, 0, 7, 2, 10, 10, 2, 0, 1, 7, 12, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1],
    "P014": [5, 6, 14, 4, 2, 5, 5, 8, 7, 12, 10, 10, 12, 5, 4, 5, 3, 8, 5, 8, 4, 1, 4, 7, 5, 6, 2, 0, 6, 3, 3, 4, 3, 6, 9, 7, 5, 5, 5, 7, 8, 4, 2, 5, 5, 7, 3, 6, 3, 6, 4, 4, 5, 3, 4, 4, 4, 4, 5, 6],
}

# a few stock-in (purchase) entries: sku, days before END_DATE, quantity
PURCHASES = [("P003", 45, 100), ("P005", 40, 150), ("P008", 38, 200),
             ("P011", 33, 80), ("P009", 30, 30), ("P012", 28, 50)]


def seed(reset=False):
    if reset and os.path.exists(inventory.DB):
        os.remove(inventory.DB)
    inventory.init_db()
    conn = inventory.get_db()
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
        conn.close()
        return False
    ids = {}
    for sku, name, cat, price, stock, lead, sup in PRODUCTS:
        cur = conn.execute("INSERT INTO products (sku, name, category, unit_price, stock, lead_time, supplier) "
                           "VALUES (?, ?, ?, ?, ?, ?, ?)", (sku, name, cat, price, stock, lead, sup))
        ids[sku] = cur.lastrowid
    start = END_DATE - timedelta(days=DAYS - 1)
    for sku, series in SALES.items():
        for i, qty in enumerate(series):
            if qty:
                conn.execute("INSERT INTO transactions (product_id, txn_date, txn_type, quantity) VALUES (?, ?, 'SALE', ?)",
                             (ids[sku], (start + timedelta(days=i)).isoformat(), qty))
    for sku, ago, qty in PURCHASES:
        conn.execute("INSERT INTO transactions (product_id, txn_date, txn_type, quantity) VALUES (?, ?, 'PURCHASE', ?)",
                     (ids[sku], (END_DATE - timedelta(days=ago)).isoformat(), qty))
    conn.commit()
    conn.close()
    return True


if __name__ == "__main__":
    done = seed(reset="--reset" in sys.argv)
    print("Sample store loaded: 14 products, 60 days of sales." if done else "Database already has data - nothing to do.")
