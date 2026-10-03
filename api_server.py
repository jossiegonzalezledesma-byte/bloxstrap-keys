from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys
import urllib.parse

sys.path.append(os.path.dirname(__file__))
from database import verify_and_consume_key, get_key_info, get_all_keys

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5055))

BLOXSTRAP_DIR = r"C:\Users\shiro\AppData\Local\Bloxstrap"

def sync_bloxstrap_config(server_url=None):
    """Sincroniza auth_server.txt y keys.json en Bloxstrap para compatibilidad total."""
    try:
        if os.path.exists(BLOXSTRAP_DIR):
            if not server_url:
                server_url = f"http://localhost:{PORT}"
            # 1. auth_server.txt
            auth_file = os.path.join(BLOXSTRAP_DIR, "auth_server.txt")
            with open(auth_file, "w", encoding="utf-8") as f:
                f.write(server_url)

            # 2. keys.json para verificación local instantánea
            all_keys = get_all_keys()
            local_db = {"keys": {}}
            for k in all_keys:
                local_db["keys"][k["key"]] = {
                    "is_active": bool(k["is_active"]),
                    "expires_at": None,
                    "is_super": True
                }
            keys_file = os.path.join(BLOXSTRAP_DIR, "keys.json")
            with open(keys_file, "w", encoding="utf-8") as f:
                json.dump(local_db, f, indent=2)
    except Exception as e:
        print(f"[!] Error sincronizando config con Bloxstrap: {e}")

class KeyVerificationHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # Endpoint nativo que consume Bloxstrap: /api/validate?key=...&hwid=...
        if parsed.path == "/api/validate":
            params = urllib.parse.parse_qs(parsed.query)
            key = params.get("key", [""])[0].strip()
            hwid = params.get("hwid", [""])[0].strip()

            if not key:
                self._send_json(200, {
                    "valid": False,
                    "is_super": False,
                    "tier": "none",
                    "reason": "No se proporcionó una llave."
                })
                return

            result = verify_and_consume_key(key, hwid if hwid else "NO-HWID-PROVIDED")
            sync_bloxstrap_config()

            if result.get("status") == "success":
                self._send_json(200, {
                    "valid": True,
                    "is_super": True,
                    "tier": "super",
                    "reason": f"Acceso concedido para {result.get('username')}"
                })
            else:
                self._send_json(200, {
                    "valid": False,
                    "is_super": False,
                    "tier": "none",
                    "reason": result.get("message", "Llave inválida.")
                })

        elif parsed.path.startswith("/api/status"):
            self._send_json(200, {"status": "online", "service": "Bloxstrap Key System API"})
        else:
            self._send_json(404, {"status": "error", "message": "Ruta no encontrada."})

    def do_POST(self):
        if self.path == "/api/verify":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                self._send_json(400, {"status": "error", "message": "JSON inválido."})
                return

            key = payload.get("key", "").strip()
            hwid = payload.get("hwid", "").strip()

            if not key or not hwid:
                self._send_json(400, {"status": "error", "message": "Se requiere 'key' y 'hwid'."})
                return

            result = verify_and_consume_key(key, hwid)
            sync_bloxstrap_config()
            status_code = 200 if result.get("status") == "success" else 403
            self._send_json(status_code, result)
        else:
            self._send_json(404, {"status": "error", "message": "Ruta no encontrada."})

def run_server():
    sync_bloxstrap_config()
    server = HTTPServer((HOST, PORT), KeyVerificationHandler)
    print(f"[*] API de Verificación de Keys escuchando en http://localhost:{PORT}")
    print(f"[*] Endpoint de Bloxstrap nativo: http://localhost:{PORT}/api/validate?key=...&hwid=...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Servidor detenido.")
        server.server_close()

if __name__ == "__main__":
    run_server()
