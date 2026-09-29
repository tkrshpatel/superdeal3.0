"""Small dependency-free HTTP API for SuperDeal 3.0."""

from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def list_deals(connection: sqlite3.Connection, *, q: str | None = None, merchant: str | None = None, limit: int = 50) -> list[dict]:
    """Return active deals with optional product/merchant filters."""
    limit = max(1, min(limit, 100))
    clauses = ["status = 'active'"]
    params: list[object] = []
    if q:
        clauses.append("LOWER(product_name) LIKE ?")
        params.append(f"%{q.lower()}%")
    if merchant:
        clauses.append("LOWER(merchant) = ?")
        params.append(merchant.lower())
    rows = connection.execute(
        f"""SELECT id, product_name, merchant, current_price, source_url,
                   status, first_seen_at, last_seen_at
            FROM deals
            WHERE {' AND '.join(clauses)}
            ORDER BY last_seen_at DESC
            LIMIT ?""",
        (*params, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def get_deal(connection: sqlite3.Connection, deal_id: int) -> dict | None:
    row = connection.execute(
        """SELECT id, product_name, merchant, current_price, source_url,
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
                try:
                    limit = int(params.get("limit", ["50"])[0])
                except ValueError:
                    self._send_json({"error": "limit must be an integer"}, 400)
                    return
                self._send_json({"deals": list_deals(connection, q=q, merchant=merchant, limit=limit)})
                return
            if parsed.path.startswith("/deals/"):
                raw_id = parsed.path.removeprefix("/deals/")
                try:
                    deal_id = int(raw_id)
                except ValueError:
                    self._send_json({"error": "invalid deal id"}, 400)
                    return
                deal = get_deal(connection, deal_id)
                if deal is None:
                    self._send_json({"error": "deal not found"}, 404)
                else:
                    self._send_json(deal)
                return
            self._send_json({"error": "not found"}, 404)

        def log_message(self, format: str, *args: object) -> None:
            return

    return DealAPIHandler


def serve(connection: sqlite3.Connection, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the API until interrupted."""
    server = ThreadingHTTPServer((host, port), make_handler(connection))
    try:
        server.serve_forever()
    finally:
        server.server_close()
