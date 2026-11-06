#!/usr/bin/env python3

# Simple HTTP Backend Server for Proxy Demonstration

from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8080

class BackendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

        # Build response body with headers forwarded by Nginx
        client_ip = self.client_address[0]
        host_header = self.headers.get("Host", "Unknown")
        x_real_ip = self.headers.get("X-Real-IP", "Not forwarded")
        x_proto = self.headers.get("X-Forwarded-Proto", "Not forwarded")

        response = (
            "========================================\n"
            "Backend Server Response (Port 8080)\n"
            "========================================\n"
            f"Host Header:       {host_header}\n"
            f"Direct Client IP:  {client_ip}\n"
            f"X-Real-IP:         {x_real_ip}\n"
            f"X-Forwarded-Proto: {x_proto}\n"
            "========================================\n"
            "Status: Request handled successfully via Reverse Proxy.\n"
        )

        self.wfile.write(response.encode("utf-8"))

    # Suppress default server log lines to keep terminal output clean
    def log_message(self, format, *args):
        print(f"[Backend Log] Request received from {self.client_address[0]}")

def run():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, BackendHandler)
    print(f"Backend HTTP service listening on http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping backend service...")
        httpd.server_close()

if __name__ == "__main__":
    run()
