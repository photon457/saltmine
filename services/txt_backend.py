from __future__ import annotations

from pathlib import Path
from typing import Any


class TextBackend:
    def __init__(self, fallback_dir: Path) -> None:
        self.fallback_dir = fallback_dir
        self.brands = self._load_brands(fallback_dir / "brands.txt")
        self.salts = self._load_salts(fallback_dir / "salts.txt")
        self.brand_salts = self._load_brand_salts(fallback_dir / "brand_salts.txt")

    @staticmethod
    def _load_brands(path: Path) -> dict[int, dict[str, Any]]:
        brands: dict[int, dict[str, Any]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            brand_id, name, manufacturer, price, is_ja = line.split("|")
            brands[int(brand_id)] = {
                "id": int(brand_id),
                "brand_name": name,
                "manufacturer": manufacturer,
                "price_inr": float(price),
                "is_jan_aushadhi": int(is_ja),
            }
        return brands

    @staticmethod
    def _load_salts(path: Path) -> dict[int, str]:
        salts: dict[int, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            salt_id, salt_name = line.split("|", maxsplit=1)
            salts[int(salt_id)] = salt_name
        return salts

    @staticmethod
    def _load_brand_salts(path: Path) -> dict[int, list[tuple[int, float]]]:
        mapping: dict[int, list[tuple[int, float]]] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            brand_id, salt_id, strength = line.split("|")
            mapping.setdefault(int(brand_id), []).append((int(salt_id), float(strength)))
        return mapping

    def find_brand_and_alternatives(self, brand_name: str) -> dict[str, Any]:
        prescribed = next(
            (b for b in self.brands.values() if b["brand_name"].lower() == brand_name.strip().lower()),
            None,
        )
        if not prescribed:
            # Try partial match
            query_lower = brand_name.strip().lower()
            prescribed = next(
                (b for b in self.brands.values() if query_lower in b["brand_name"].lower()),
                None,
            )
        if not prescribed:
            raise LookupError(f"Brand not found: {brand_name}")

        brand_id = int(prescribed["id"])
        target_signature = sorted(self.brand_salts.get(brand_id, []))

        composition = [
            {"salt_name": self.salts[salt_id], "strength_mg": strength}
            for salt_id, strength in target_signature
        ]

        alternatives = []
        for other_id, other_brand in self.brands.items():
            if other_id == brand_id:
                continue
            other_signature = sorted(self.brand_salts.get(other_id, []))
            if other_signature == target_signature:
                alternatives.append(other_brand)

        alternatives.sort(key=lambda item: float(item["price_inr"]))
        jan_aushadhi = [row for row in alternatives if int(row["is_jan_aushadhi"]) == 1]

        return {
            "prescribed": prescribed,
            "composition": composition,
            "alternatives": alternatives,
            "jan_aushadhi_alternatives": jan_aushadhi,
            "backend": "txt-fallback",
        }

    def suggest_brands(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        query_lower = query.strip().lower()
        results = [b for b in self.brands.values() if query_lower in b["brand_name"].lower()]
        results.sort(key=lambda x: x["brand_name"])
        return results[:limit]
