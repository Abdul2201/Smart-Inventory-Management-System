# Smart Inventory Management System

Flask web app that keeps the right quantity of every product in stock: it records stock-in / stock-out
transactions, forecasts daily demand (exponential smoothing, α = 0.3), calculates safety stock, reorder point
(ROP) and Economic Order Quantity (EOQ), raises reorder alerts and classifies products with ABC analysis.

DevOps Mini Project (23AD52C) - Abdul Rahuman M, National Engineering College, Kovilpatti.

## Formulas
| Item | Formula |
|---|---|
| Forecast | F(t+1) = α·D(t) + (1 − α)·F(t), α = 0.3 |
| Safety stock | z · σ · √L (z = 1.65 for 95 % service level) |
| Reorder point | d · L + safety stock |
| EOQ | √(2DS / H), S = ₹500, H = 20 % of unit price |
| Status | Out of Stock (0) · Reorder Now (≤ ROP) · Low (≤ 1.5 × ROP) · OK |
| ABC | cumulative yearly value: A ≤ 80 %, B ≤ 95 %, C = rest |

## Run locally
```bash
pip install -r requirements.txt
python seed_data.py        # loads 14 sample products + 60 days of sales
python app.py              # http://localhost:5000   (login: admin / admin123)
```

## Run tests
```bash
python -m pytest -v
```

## Run with Docker
```bash
docker compose up --build  # http://localhost:5000
```

## CI
`.github/workflows/ci.yml` runs the Pytest suite and builds the Docker image on every push to `main`.

## Project layout
```
app.py              Flask app, forecasting, reorder and ABC logic
seed_data.py        sample store (14 products, 60 days of sales)
test_app.py         Pytest test cases
templates/ static/  Jinja2 pages, CSS and SVG charts
Dockerfile, docker-compose.yml, .github/workflows/ci.yml
screenshots/        output images used in the report (Fig 1 - Fig 6 + pytest run)
```
