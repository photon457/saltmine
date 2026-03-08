from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from sqlalchemy.exc import SQLAlchemyError

from services.sql_backend import SQLBackend
from services.txt_backend import TextBackend


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost/salt_mine")

app = Flask(__name__)

sql_backend = SQLBackend(DATABASE_URL)
sql_backend.bootstrap(PROJECT_ROOT)
txt_backend = TextBackend(PROJECT_ROOT / "data" / "fallback")


@app.get("/")
def home() -> str:
    return render_template("index.html")


@app.get("/api/search")
def search() -> tuple[object, int]:
    brand_name = request.args.get("brand", "").strip()
    if not brand_name:
        return jsonify({"error": "Please provide a brand name using ?brand=..."}), 400

    try:
        result = sql_backend.find_brand_and_alternatives(brand_name)
    except LookupError:
        return jsonify({"error": f"Brand '{brand_name}' not found in catalog."}), 404
    except SQLAlchemyError:
        # Automatic redundancy mode: if SQL fails, serve from text backend.
        try:
            result = txt_backend.find_brand_and_alternatives(brand_name)
        except LookupError:
            return jsonify({"error": f"Brand '{brand_name}' not found in fallback catalog."}), 404
    except Exception:
        try:
            result = txt_backend.find_brand_and_alternatives(brand_name)
        except LookupError:
            return jsonify({"error": "Unexpected error while searching."}), 500

    prescribed_price = float(result["prescribed"]["price_inr"])
    for alt in result["alternatives"]:
        alt_price = float(alt["price_inr"])
        savings_pct = ((prescribed_price - alt_price) / prescribed_price) * 100 if prescribed_price > 0 else 0.0
        alt["savings_pct"] = round(max(savings_pct, 0.0), 2)

    response = {
        "query": brand_name,
        "backend_used": result["backend"],
        "prescribed": result["prescribed"],
        "composition": result["composition"],
        "alternatives": result["alternatives"],
        "jan_aushadhi_alternatives": result["jan_aushadhi_alternatives"],
    }
    return jsonify(response), 200


@app.get("/api/suggest")
def suggest() -> tuple[object, int]:
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([]), 200
    try:
        results = sql_backend.suggest_brands(query)
    except SQLAlchemyError:
        results = txt_backend.suggest_brands(query)
    return jsonify(results), 200


@app.get("/api/health")
def health() -> tuple[object, int]:
    sql_ok = sql_backend.check_health()
    return jsonify({"sql_backend": "up" if sql_ok else "down", "txt_fallback": "up"}), 200


if __name__ == "__main__":
    app.run(debug=True)
