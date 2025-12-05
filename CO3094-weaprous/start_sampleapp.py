#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""
import time
import threading
import json
import socket
import argparse
import subprocess
import os
from filelock import FileLock
# from client_server import start_peer_server

from daemon.weaprous import WeApRous

PORT = 8000  # Default port
HEARTBEAT_INTERVAL = 15 
PING_TIMEOUT = 5       

app = WeApRous()

users_lock = threading.Lock()
peers_lock = threading.Lock()

# active_peers = {}
# active_connections = {}
# registered_users = {
#     "Duong": "14112005",
#     "admin": "password"
# }

# current_port = 9000
# port_lock = threading.Lock()
# Database
DB_LOCK = FileLock("static/database/db.lock")
DB_DIR = os.path.join("static", "database")
USERS_FILE = os.path.join(DB_DIR, "registered_users.json")
PEERS_FILE = os.path.join(DB_DIR, "active_peers.json")
CONN_FILE = os.path.join(DB_DIR, "active_connections.json")
os.makedirs(DB_DIR, exist_ok=True)

def load_json(path):
    """Safe read JSON file"""
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Error] load_json({path}): {e}")
        return {}

def save_json(path, data):
    """Safe write JSON file (thread-safe)"""
    try:
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        print(f"[Error] save_json({path}): {e}")


@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    print("[SampleApp] Handling POST /login request.")
    username = body.get('username')
    password = body.get('password')
    print(f"[SampleApp] Login attempt - User: {username}, Pass: {password}")
    is_valid = False
    with users_lock:
        users = load_json(USERS_FILE)
        if username in users and users[username] == password:
            is_valid = True

    if is_valid:
        print(f"[SampleApp] User '{username}' authenticated successfully.")
        ip = body.get('Ip')
        port = int(body.get('Port'))
        with peers_lock:
            peers = load_json(PEERS_FILE)
            peers[username] = {"ip": ip, "port": port, "time": time.time()}
            print('[SampeApp-Login-Active-Peer]:')
            print(peers)
            save_json(PEERS_FILE, peers)
        
        print(f"[SampleApp] Starting mini-server for {username} on port {port}")
        return 'Login Success'
    else:
        print(f"[SampleApp] Authentication failed for user '{username}'.")
        return 'Login Fail'
    

@app.route('/get_port', methods=['GET'])
def get_port(headers, body):
    username = headers.get("Cookie", "")
    if not username:
        print("[Error] Missing Cookie in /get_port")

        return ('application/json', json.dumps({"error": "Missing cookie"}))

    with peers_lock:
        peers = load_json(PEERS_FILE)
        user_info = peers.get(username)

    if not user_info:
        print(f"[Error] No active peer found for {username}")

        return ('application/json', json.dumps({"error": "User not found"}))

    ip = user_info["ip"]
    port = user_info["port"]

    response_data = {"ip": ip, "port": port, "time": time.time()}

    print(f"[SampleApp] /get_port for {username}: {response_data}")

    return ('application/json', json.dumps(response_data))


@app.route('/test', methods=['GET'])
def hello(headers, body):
    print("[SampleApp] ['TEST'] Testing web in {} to {}".format(headers, body))

@app.route('/register', methods=['POST'])
def register(headers, body):
    print("[SampleApp] Handling POST /register request.")
    username = body.get('username')
    password = body.get('password')

    print(f"[SampleApp] Register attempt - User: {username}, Pass: {password}")
    is_valid = False
    with users_lock:
        users = load_json(USERS_FILE)
        if username in users:
            print(f"[SampleApp] Registration failed: '{username}' already exists.")
            return 'Register Fail'
        users[username] = password
        save_json(USERS_FILE, users)
        is_valid = True
    
    if is_valid:
        print(f"[SampleApp] User '{username}' registered successfully.")
        return 'Register Success'
    else:
        print(f"[SampleApp] Registation failed for user '{username}'.")
        return 'Register Fail'

@app.route('/peers', methods=['GET', 'OPTIONS'])
def get_active_peers(headers, body):
    print("[API] Received request for active peer list.")
    with peers_lock:

        peers = load_json(PEERS_FILE)
        peers_copy = dict(peers)
        peers_copy.pop(headers.get("Cookie"), None)
    return ('application/json', json.dumps(peers_copy))

@app.route('/connect', methods=['GET', 'POST'])
def connect(headers, body):
    username = headers.get('Cookie', '...')
    if username == '...':
        print("[Error-SampleApp]: Something went wrong with username not being saved into cookie")
    
    target = body.get('target')
    print(f"[SampleApp] {username} wants to connect to {target}")

    with peers_lock:
        peers = load_json(PEERS_FILE)
        sender_info = peers.get(username)
        target_info = peers.get(target)

    if not sender_info or not target_info:
        print("[SampleApp] Missing peer info.")
        return 'Peer not found'

    sender_ip, sender_port = sender_info['ip'], sender_info['port']
    target_ip, target_port = target_info['ip'], target_info['port']

    try:
        payload = json.dumps({
            "target": target,
            "target_ip": target_ip,
            "target_port": target_port
        })
        http_body = payload.encode('utf-8')
        http_header = (
            f"POST /connect-peer HTTP/1.1\r\n"
            f"Host: {sender_ip}:{sender_port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(http_body)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode('utf-8')

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((sender_ip, int(sender_port)))
            s.sendall(http_header + http_body)

            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk

        print(f"[SampleApp] Connect-peer response from {username}'s mini-server:")
        print(response.decode(errors='ignore'))

    except Exception as e:
        print(f"[SampleApp] Socket connect-peer failed: {e}")
        return f"Failed to connect peer: {e}"

    print("[SampleApp]: From Connect")
    print(sender_info["port"])
    return f'/chat.html?target={target}&my_port={sender_info["port"]}'



def ping_peer(ip, port):
    try:
        req = (
            "OPTIONS /ping HTTP/1.1\r\n"
            f"Host: {ip}:{port}\r\n"
            "Content-Length: 0\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.settimeout(PING_TIMEOUT)
            s.connect((ip, port))
            s.sendall(req)
            resp = s.recv(128)
            # if b"200" in resp or b"204" in resp:
            if b"OK" or b"200" in resp or b"204" in resp:
                return True
    except Exception as e:
        print(f"[Heartbeat] Peer {ip}:{port} unreachable: {e}")
        return False
    return False

def heartbeat_thread():
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        print("\n[Heartbeat] Checking active peers...")

        with peers_lock:
            peers = load_json(PEERS_FILE)

        to_remove = []
        for username, info in peers.items():
            ip = info["ip"]
            port = int(info["port"])
            alive = ping_peer(ip, port)

            if not alive:
                print(f"[Heartbeat] Peer {username} ({ip}:{port}) is offline")
                to_remove.append(username)
            else:
                print(f"[Heartbeat] Peer {username} alive")

        if to_remove:
            with peers_lock:
                peers = load_json(PEERS_FILE)

                for u in to_remove:
                    peers.pop(u, None)
                save_json(PEERS_FILE, peers)
            print(f"[Heartbeat] Removed {len(to_remove)} offline peers.")

    
if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    threading.Thread(target=heartbeat_thread, daemon=True).start()
    app.run()