from http.server import BaseHTTPRequestHandler, HTTPServer


class TestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        print("\nReceived POST request")
        print("Headers:", dict(self.headers))
        print("Body:", body.decode("utf-8"))

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Webhook received successfully")


server = HTTPServer(("127.0.0.1", 8000), TestHandler)

print("Test webhook server running on http://127.0.0.1:8000")
print("Press Ctrl+C to stop")

server.serve_forever()
