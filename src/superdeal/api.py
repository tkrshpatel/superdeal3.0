"""Small dependency-free HTTP API for SuperDeal 3.0."""

from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .freshness import deal_freshness
from .intelligence import get_price_history, price_intelligence


def list_deals(connection: sqlite3.Connection, *, q: str | None = None, merchant: str | None = None,
               min_price: int | None = None, max_price: int | None = None,
               sort: str = "newest", limit: int = 50) -> list[dict]:
    """Return active deals with search, price and sort filters."""
    if min_price is not None and min_price < 0:
        raise ValueError("min_price must be non-negative")
    if max_price is not None and max_price < 0:
        raise ValueError("max_price must be non-negative")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValueError("min_price cannot exceed max_price")
    limit = max(1, min(limit, 100))
    clauses = ["status = 'active'"]
    params: list[object] = []
    if q:
        clauses.append("LOWER(product_name) LIKE ?")
        params.append(f"%{q.lower()}%")
    if merchant:
        clauses.append("LOWER(merchant) = ?")
        params.append(merchant.lower())
    if min_price is not None:
        clauses.append("current_price >= ?")
        params.append(min_price)
    if max_price is not None:
        clauses.append("current_price <= ?")
        params.append(max_price)

    order_by = {"newest": "last_seen_at DESC", "price_asc": "current_price ASC, last_seen_at DESC",
                "price_desc": "current_price DESC, last_seen_at DESC"}
    if sort not in order_by:
        raise ValueError("sort must be one of: newest, price_asc, price_desc")

    rows = connection.execute(
        f"""SELECT id, product_name, merchant, current_price, source_url, affiliate_url,
                   page_title, canonical_url, image_url, verified_price, last_verified_at,
                   status, first_seen_at, last_seen_at
            FROM deals WHERE {' AND '.join(clauses)}
            ORDER BY {order_by[sort]} LIMIT ?""",
        (*params, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def get_deal(connection: sqlite3.Connection, deal_id: int) -> dict | None:
    row = connection.execute(
        """SELECT id, product_name, merchant, current_price, source_url, affiliate_url,
                  page_title, canonical_url, image_url, verified_price, last_verified_at,
                  status, first_seen_at, last_seen_at
           FROM deals WHERE id = ?""",
        (deal_id,),
    ).fetchone()
    return dict(row) if row else None


def make_handler(connection: sqlite3.Connection):
    """Create a request handler bound to one SQLite connection."""

    class DealAPIHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: object, status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json({"status": "ok", "service": "superdeal3"})
                return
            if parsed.path == "/deals":
                params = parse_qs(parsed.query)
                q = params.get("q", [None])[0]
                merchant = params.get("merchant", [None])[0]
                sort = params.get("sort", ["newest"])[0]
                try:
                    limit = int(params.get("limit", ["50"])[0])
                    min_price = int(params["min_price"][0]) if "min_price" in params else None
                    max_price = int(params["max_price"][0]) if "max_price" in params else None
                    if min_price is not None and min_price < 0:
                        raise ValueError("min_price must be non-negative")
                    if max_price is not None and max_price < 0:
                        raise ValueError("max_price must be non-negative")
                    if min_price is not None and max_price is not None and min_price > max_price:
                        raise ValueError("min_price cannot exceed max_price")
                    if limit < 1:
                        raise ValueError("limit must be at least 1")
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, 400)
                    return
                try:
                    deals = list_deals(connection, q=q, merchant=merchant, min_price=min_price,
                                       max_price=max_price, sort=sort, limit=limit)
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, 400)
                    return
                self._send_json({"deals": deals})
                return
            if parsed.path.startswith("/deals/"):
                parts = parsed.path.strip("/").split("/")
                raw_id = parts[1] if len(parts) > 1 else ""
                try:
                    deal_id = int(raw_id)
                except ValueError:
                    self._send_json({"error": "invalid deal id"}, 400)
                    return
                deal = get_deal(connection, deal_id)
                if deal is None:
                    self._send_json({"error": "deal not found"}, 404)
                    return
                if len(parts) == 3 and parts[2] == "price-history":
                    self._send_json({"deal_id": deal_id, "history": get_price_history(connection, deal_id)})
                    return
                if len(parts) == 3 and parts[2] == "intelligence":
                    self._send_json(price_intelligence(connection, deal_id))
                    return
                if len(parts) == 3 and parts[2] == "freshness":
                    self._send_json(deal_freshness(connection, deal_id))
                    return
                if len(parts) != 2:
                    self._send_json({"error": "not found"}, 404)
                    return
                self._send_json(deal)
                return
            self._send_json({"error": "not found"}, 404)

        def log_message(self, format: str, *args: object) -> None:
            return

    return DealAPIHandler


def serve(connection: sqlite3.Connection, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the API until interrupted."""
    server = HTTPServer((host, port), make_handler(connection))
    try:
        server.serve_forever()
    finally:
        server.server_close()
