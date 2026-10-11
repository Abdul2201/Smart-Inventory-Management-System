FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 INVENTORY_DB=/data/inventory.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data

EXPOSE 5000
# load the sample store on first start, then run the web app
CMD ["sh", "-c", "python seed_data.py && python app.py"]
