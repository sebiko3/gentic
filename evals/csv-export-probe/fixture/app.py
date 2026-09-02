"""Admin dashboard: a users table and an orders table, served over plain HTTP."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

USERS = [
    {"id": 1, "name": "Ada Lovelace", "email": "ada@example.com",
     "password_hash": "sha256$9f86d081884c7d659a2feaa0c55ad015", "created_at": "2025-01-03"},
    {"id": 2, "name": "Grace Hopper", "email": "grace@example.com",
     "password_hash": "sha256$2c26b46b68ffc68ff99b453c1d304134", "created_at": "2025-02-14"},
    {"id": 3, "name": "Linus Torvalds", "email": "linus@example.com",
     "password_hash": "sha256$fcde2b2edba56bf408601fb721fe9b5c", "created_at": "2025-03-21"},
]

ORDERS = [
    {"id": 101, "user_id": 1, "total_cents": 4200, "status": "paid"},
    {"id": 102, "user_id": 2, "total_cents": 1300, "status": "refunded"},
    {"id": 103, "user_id": 1, "total_cents": 8900, "status": "paid"},
]

TABLES = {"users": USERS, "orders": ORDERS}


def render_table(rows):
    """An HTML table with one header row taken from the first row's keys."""
    if not rows:
        return "<table></table>"
    header = "".join(f"<th>{key}</th>" for key in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{value}</td>" for value in row.values()) + "</tr>" for row in rows)
    return f"<table><tr>{header}</tr>{body}</table>"


def route(path):
    """(status, content type, body) for a request path."""
    parts = urlparse(path).path.strip("/").split("/")
    if len(parts) == 2 and parts[0] == "admin" and parts[1] in TABLES:
        return 200, "text/html", render_table(TABLES[parts[1]])
    return 404, "text/plain", "not found"


class AdminHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, content_type, body = route(self.path)
        payload = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve(port=8000):
    HTTPServer(("127.0.0.1", port), AdminHandler).serve_forever()


if __name__ == "__main__":
    serve()
