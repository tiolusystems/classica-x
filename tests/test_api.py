import http.client
import json
import threading

from classica_x.app import create_server


class StubService:
    def snapshot(self): return {"status": "pronto"}
    def preview(self, url): return {"url": url}
    def start(self, *args): pass
    def cancel(self): pass
    def shutdown(self): pass


def request(server, method, path, token=None, origin=None, host=None):
    port = server.server_port
    headers = {"Host": host or f"127.0.0.1:{port}"}
    if token: headers["X-Classica-Session"] = token
    if origin: headers["Origin"] = origin
    body = json.dumps({}).encode() if method == "POST" else None
    if body: headers["Content-Type"] = "application/json"
    connection = http.client.HTTPConnection("127.0.0.1", port)
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    response.read()
    return response.status


def test_api_rejects_missing_session_and_invalid_host():
    server = create_server(service=StubService(), session_token="test-session")
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    try:
        assert request(server, "GET", "/api/state") == 401
        assert request(server, "GET", "/api/state", token="test-session", host="evil.test") == 400
        assert request(server, "GET", "/api/state", token="test-session") == 200
    finally:
        server.shutdown(); server.server_close(); worker.join()


def test_api_rejects_post_without_matching_origin():
    server = create_server(service=StubService(), session_token="test-session")
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    try:
        assert request(server, "POST", "/api/cancel", token="test-session") == 403
        assert request(server, "POST", "/api/cancel", token="test-session", origin=f"http://127.0.0.1:{server.server_port}") == 200
    finally:
        server.shutdown(); server.server_close(); worker.join()
