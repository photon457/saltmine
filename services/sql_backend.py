from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


class SQLBackend:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)

    # ── Bootstrap ──────────────────────────────────────────────

    def bootstrap(self, project_root: Path) -> None:
        if self.database_url.startswith("sqlite"):
            self._bootstrap_sqlite(project_root)
        elif "mysql" in self.database_url or "pymysql" in self.database_url:
            self._bootstrap_mysql(project_root)

    def _bootstrap_sqlite(self, project_root: Path) -> None:
        db_path = project_root / "salt_mine.db"
        if db_path.exists():
            return

        sqlite_ddl = """
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY,
            brand_name VARCHAR(255) NOT NULL UNIQUE,
            manufacturer VARCHAR(255) NOT NULL,
            price_inr DECIMAL(10,2) NOT NULL,
            is_jan_aushadhi BOOLEAN NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS salts (
            id INTEGER PRIMARY KEY,
            salt_name VARCHAR(255) NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS brand_salts (
            brand_id INTEGER NOT NULL,
            salt_id  INTEGER NOT NULL,
            strength_mg DECIMAL(10,2) NOT NULL,
            PRIMARY KEY (brand_id, salt_id, strength_mg),
            FOREIGN KEY (brand_id) REFERENCES brands(id),
            FOREIGN KEY (salt_id) REFERENCES salts(id)
        );
        CREATE INDEX IF NOT EXISTS idx_brand_salts_brand ON brand_salts(brand_id);
        CREATE INDEX IF NOT EXISTS idx_brand_salts_salt_strength ON brand_salts(salt_id, strength_mg);
        CREATE INDEX IF NOT EXISTS idx_brands_price ON brands(price_inr);
        """
        seed_sql = (project_root / "seed.sql").read_text(encoding="utf-8")

        with self.engine.begin() as conn:
            for stmt in [s.strip() for s in sqlite_ddl.split(";") if s.strip()]:
                conn.execute(text(stmt))
            for stmt in [s.strip() for s in seed_sql.split(";") if s.strip()]:
                conn.execute(text(stmt))

    def _bootstrap_mysql(self, project_root: Path) -> None:
        parsed = urlparse(self.database_url)
        db_name = parsed.path.lstrip("/")

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", db_name):
            raise ValueError(f"Invalid database name: {db_name}")

        # Connect without a database to create it
        base_url = urlunparse(parsed._replace(path="/"))
        temp_engine = create_engine(base_url, pool_pre_ping=True)
        with temp_engine.begin() as conn:
            conn.execute(
                text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                     "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            )
        temp_engine.dispose()

        # Check if tables already exist
        with self.engine.begin() as conn:
            result = conn.execute(text("SHOW TABLES LIKE 'brands'")).fetchone()
            if result:
                return

        # Run schema and seed
        schema_sql = (project_root / "schema.sql").read_text(encoding="utf-8")
        seed_sql = (project_root / "seed.sql").read_text(encoding="utf-8")

        with self.engine.begin() as conn:
            for stmt in [s.strip() for s in schema_sql.split(";") if s.strip()]:
                conn.execute(text(stmt))
            for stmt in [s.strip() for s in seed_sql.split(";") if s.strip()]:
                conn.execute(text(stmt))

    def find_brand_and_alternatives(self, brand_name: str) -> dict[str, Any]:
        with self.engine.begin() as conn:
            prescribed = conn.execute(
                text(
                    """
                    SELECT id, brand_name, manufacturer, price_inr, is_jan_aushadhi
                    FROM brands
                    WHERE LOWER(brand_name) = LOWER(:brand_name)
                    LIMIT 1
                    """
                ),
                {"brand_name": brand_name.strip()},
            ).mappings().first()

            if not prescribed:
                # Try partial match (LIKE-based fuzzy search)
                prescribed = conn.execute(
                    text(
                        """
                        SELECT id, brand_name, manufacturer, price_inr, is_jan_aushadhi
                        FROM brands
                        WHERE LOWER(brand_name) LIKE LOWER(:pattern)
                        ORDER BY brand_name ASC
                        LIMIT 1
                        """
                    ),
                    {"pattern": f"%{brand_name.strip()}%"},
                ).mappings().first()

            if not prescribed:
                raise LookupError(f"Brand not found: {brand_name}")

            brand_id = int(prescribed["id"])

            composition = conn.execute(
                text(
                    """
                    SELECT s.salt_name, bs.strength_mg
                    FROM brand_salts bs
                    JOIN salts s ON s.id = bs.salt_id
                    WHERE bs.brand_id = :brand_id
                    ORDER BY s.salt_name ASC
                    """
                ),
                {"brand_id": brand_id},
            ).mappings().all()

            alternatives = conn.execute(
                text(
                    """
                    SELECT b2.id, b2.brand_name, b2.manufacturer, b2.price_inr, b2.is_jan_aushadhi
                    FROM brands b2
                    WHERE b2.id <> :brand_id
                      AND NOT EXISTS (
                          SELECT 1
                          FROM brand_salts target
                          WHERE target.brand_id = :brand_id
                            AND NOT EXISTS (
                                SELECT 1
                                FROM brand_salts candidate
                                WHERE candidate.brand_id = b2.id
                                  AND candidate.salt_id = target.salt_id
                                  AND candidate.strength_mg = target.strength_mg
                            )
                      )
                      AND NOT EXISTS (
                          SELECT 1
                          FROM brand_salts candidate
                          WHERE candidate.brand_id = b2.id
                            AND NOT EXISTS (
                                SELECT 1
                                FROM brand_salts target
                                WHERE target.brand_id = :brand_id
                                  AND target.salt_id = candidate.salt_id
                                  AND target.strength_mg = candidate.strength_mg
                            )
                      )
                    ORDER BY b2.price_inr ASC
                    """
                ),
                {"brand_id": brand_id},
            ).mappings().all()

            jan_aushadhi = [row for row in alternatives if int(row["is_jan_aushadhi"]) == 1]

            return {
                "prescribed": dict(prescribed),
                "composition": [dict(item) for item in composition],
                "alternatives": [dict(item) for item in alternatives],
                "jan_aushadhi_alternatives": [dict(item) for item in jan_aushadhi],
                "backend": "sql",
            }

    def suggest_brands(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, brand_name, manufacturer, price_inr, is_jan_aushadhi
                    FROM brands
                    WHERE LOWER(brand_name) LIKE LOWER(:pattern)
                    ORDER BY brand_name ASC
                    LIMIT :limit
                    """
                ),
                {"pattern": f"%{query.strip()}%", "limit": limit},
            ).mappings().all()
            return [dict(row) for row in rows]

    def check_health(self) -> bool:
        try:
            with self.engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False
