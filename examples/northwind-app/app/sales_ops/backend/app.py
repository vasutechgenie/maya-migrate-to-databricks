"""Legacy Sales Ops Console backend (reference source).

This is the ORIGINAL app backend (FastAPI over the legacy OLTP app DB). MAYA reads it
for reference and regenerates an equivalent backend that runs on Databricks Apps and
reads from Databricks Lakebase. Provided so the migration has a real source to compare.
"""
import os

import psycopg
from fastapi import FastAPI

app = FastAPI(title="Sales Ops Console")


def _rows(sql: str):
    with psycopg.connect(os.environ["APP_DB_DSN"]) as cx, cx.cursor() as cur:
        cur.execute(sql)
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@app.get("/api/orders")
def orders():
    return {"data": _rows("SELECT * FROM app.orders_ops ORDER BY order_date DESC LIMIT 500")}


@app.get("/api/customers")
def customers():
    return {"data": _rows("SELECT * FROM app.customer_360 ORDER BY lifetime_revenue DESC LIMIT 500")}


@app.get("/api/reorder-alerts")
def reorder_alerts():
    return {"data": _rows("SELECT * FROM app.reorder_alerts WHERE alert = true LIMIT 500")}
