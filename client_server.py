# client_server.py
# Minimal, self-contained mini HTTP server for a peer.
# - POST /send-peer  -> accept JSON {"from": "...", "msg": "..."}
# - GET  /inbox      -> return JSON array of received messages
# - responds to OPTIONS for CORS preflight
# - uses only socket + threading, no external libs

import socket
import threading
import json
import datetime
from typing import List, Dict

_inbox: List[Dict] = []
_inbox_lock = threading.Lock()

def _now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"

def _send_http_response(conn: socket.socket, status_code:int=200, reason:str="OK",
                        headers:Dict[str,str]=None, body:bytes=b""):
    if headers is None:
        headers = {}
    # Default CORS headers (allow all origins for dev/demo)
    default = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Connection": "close",
    }
    for k,v in default.items():
        headers.setdefault(k, v)
    headers.setdefault("Content-Length", str(len(body)))
    # Build header block
    lines = [f"HTTP/1.1 {status_code} {reason}"]
    for k,v in headers.items():
        lines.append(f"{k}: {v}")
    lines.append("")  # blank line
    head = ("\r\n".join(lines) + "\r\n").encode("utf-8")
    try:
        conn.sendall(head + body)
    except Exception:
        pass

def _parse_http(raw: str):
    """
    Return (method, path, headers_dict, body_str)
    headers keys lowercased.
    """
    parts = raw.split("\r\n\r\n", 1)
    header_block = parts[0]
    body = parts[1] if len(parts) > 1 else ""
    lines = header_block.split("\r\n")
    request_line = lines[0]
    method = path = ""
    try:
        method, path, _ = request_line.split()
    except Exception:
        pass
    headers = {}
    for h in lines[1:]:
        if ": " in h:
            k,v = h.split(": ",1)
            headers[k.lower()] = v
    return method.upper(), path, headers, body

def handle_connection(conn: socket.socket, addr, username: str):
    try:
        conn.settimeout(2.0)
        data = b""
        # receive available data (simple approach)
        while True:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk
            if len(chunk) < 4096:
                break
        text = data.decode("utf-8", errors="replace")
        if not text:
            _send_http_response(conn, 400, "Bad Request", body=b"")
            return

        method, path, headers, body = _parse_http(text)

        # handle OPTIONS (CORS preflight)
        if method == "OPTIONS":
            _send_http_response(conn, 200, "OK", body=b"")
            return

        # POST /send-peer -> accept JSON body
        if method == "POST" and path.startswith("/send-peer"):
            # try parse JSON from body; if header indicates form-encoded, try basic parse
            content_type = headers.get("content-type", "")
            payload = {}
            if "application/json" in content_type:
                try:
                    payload = json.loads(body)
                except Exception:
                    payload = {}
            else:
                # form-encoded key=value&...
                try:
                    pairs = body.split("&")
                    for p in pairs:
                        if "=" in p:
                            k,v = p.split("=",1)
                            # basic percent decode
                            k = _percent_decode(k)
                            v = _percent_decode(v)
                            payload[k] = v
                except Exception:
                    payload = {}

            sender = payload.get("from") or payload.get("sender") or "unknown"
            msg = payload.get("msg") or payload.get("message") or ""
            if not msg:
                _send_http_response(conn, 400, "Bad Request", body=b"Missing msg")
                return

            entry = {"from": sender, "msg": msg, "time": _now_iso()}
            with _inbox_lock:
                _inbox.append(entry)
            print(f"\n💬 [{username}] Received from [{sender}] @ {addr}: {msg}")
            _send_http_response(conn, 200, "OK", headers={"Content-Type":"text/plain"}, body=b"OK")
            return

        # GET /inbox -> return JSON
        if method == "GET" and path.startswith("/inbox"):
            with _inbox_lock:
                data = json.dumps(list(_inbox)).encode("utf-8")
            _send_http_response(conn, 200, "OK", headers={"Content-Type":"application/json"}, body=data)
            return

        # any other path -> 404
        _send_http_response(conn, 404, "Not Found", body=b"Not Found")
    except Exception as e:
        print(f"[{username}] Error handling {addr}: {e}")
        try:
            _send_http_response(conn, 500, "Internal Server Error", body=str(e).encode("utf-8"))
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def _percent_decode(s: str) -> str:
    # minimal percent-decoding for urlencoded bodies
    try:
        return bytes(s.replace("+"," "), "utf-8").decode("unicode_escape")
    except Exception:
        # best-effort fallback
        import urllib.parse
        return urllib.parse.unquote_plus(s)

def start_peer_server(ip: str, port: int, username: str):
    """
    Start a mini HTTP-like server on (ip,port). This function blocks (should be run in a thread).
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(8)
        print(f"[PeerServer] 🟢 Started for '{username}' at {ip}:{port}")
    except Exception as e:
        print(f"[PeerServer:{username}] 🔴 Failed to bind {ip}:{port}: {e}")
        return

    try:
        while True:
            conn, addr = sock.accept()
            threading.Thread(target=handle_connection, args=(conn, addr, username), daemon=True).start()
    except Exception as e:
        print(f"[PeerServer:{username}] Listener error: {e}")
    finally:
        try:
            sock.close()
        except Exception:
            pass

if __name__ == "__main__":
    start_peer_server("0.0.0.0", 50386, "Duong")

# import socket
# import threading

# def handle_client(conn, addr, username):
#     try:
#         data = conn.recv(2048).decode('utf-8')
#         if not data:
#             return
        
#         print(f"[{username}] Received message from {addr}: {data}")
#         conn.sendall(b"OK")

#         # TODO (sau này):
#         # - Lưu tin nhắn vào log
#         # - Forward lên frontend qua WebSocket / long-polling

#     except Exception as e:
#         print(f"[{username}]Error handling client {addr}: {e}")
#     finally:
#         conn.close()


# def start_peer_server(ip: str, port: int, username: str):
#     """
#     Khởi chạy 1 mini TCP server cho mỗi peer sau khi login thành công.

#     Args:
#         ip (str): địa chỉ IP để bind (thường là '0.0.0.0')
#         port (int): cổng lắng nghe cho peer này
#         username (str): tên người dùng hiện tại
#     """
#     try:
#         peer_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         peer_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         peer_server.bind((ip, port))
#         peer_server.listen(5)

#         print(f"[PeerServer] Started for user '{username}' on {ip}:{port}")

#         while True:
#             conn, addr = peer_server.accept()
#             print(f"[PeerServer:{username}] Connection from {addr}")

#             client_thread = threading.Thread(
#                 target=handle_client,
#                 args=(conn, addr, username),
#                 daemon=True
#             )
#             client_thread.start()

#     except Exception as e:
#         print(f"[PeerServer:{username}] Failed to start: {e}")