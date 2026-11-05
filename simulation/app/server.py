"""Tiny stdlib HTTP service used only by the local failure lab."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import os


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            unhealthy = os.getenv("APP_MODE", "healthy") == "unhealthy"
            self.send_response(503 if unhealthy else 200)
            self.end_headers()
            self.wfile.write(b"unhealthy" if unhealthy else b"ok")
        elif self.path == "/fail":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"simulated application error")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"CloudPulse demo service")

    def log_message(self, fmt, *args):
        print("app: " + fmt % args, flush=True)


HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
