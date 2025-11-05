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
# from client_server import start_peer_server

from daemon.weaprous import WeApRous

PORT = 8000  # Default port

app = WeApRous()

registered_users = {
    "Duong": "14112005",
    "admin": "password"
}
users_lock = threading.Lock()
active_peers = {}
peers_lock = threading.Lock()
active_connections = {}

@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    
    print("[SampleApp] Handling POST /login request.")

    username = body.get('username')
    password = body.get('password')

    print(f"[SampleApp] Login attempt - User: {username}, Pass: {password}")

    is_valid = False
    with users_lock:
        if username in registered_users and registered_users[username] == password:
            is_valid = True


    if is_valid:
        print(f"[SampleApp] User '{username}' authenticated successfully.")
        ip = body.get('IP')
        port = body.get('Port')

        with peers_lock:
            active_peers[username] = {"ip":ip, "port":port, "time":time.time()}
            print(active_peers)
        
        # try:
        #     threading.Thread(target=start_peer_server,args=('0.0.0.0', int(port), username),daemon=True).start()
        #     print(f"[SampleApp] Peer server started for '{username}' on port {port}")
        # except Exception as e:
        #     print(f"[SampleApp] Failed to start peer server for {username}: {e}")

        return 'Login Success'
    else:
        print(f"[SampleApp] Authentication failed for user '{username}'.")
        return 'Login Fail'

@app.route('/hello', methods=['PUT'])
def hello(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or message payload.
    """
    print("[SampleApp] ['PUT'] Hello in {} to {}".format(headers, body))

#Added by Duong 26/10/2025
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
        if not username in registered_users:
            is_valid = True
            registered_users[username] = password
    
    if is_valid:
        print(f"[SampleApp] User '{username}' registered successfully.")
        ip = body.get('IP')
        port = body.get('Port')

        with peers_lock:
            active_peers[username] = {"ip":ip, "port":port, "time":time.time()}
            print(active_peers)
            print(registered_users)
        return 'Register Success'
    else:
        print(f"[SampleApp] Registation failed for user '{username}'.")
        return 'Register Fail'

@app.route('/peers', methods=['GET'])
def get_active_peers(headers, body):
    print("[API] Received request for active peer list.")
    with peers_lock:
        peers_copy = dict(active_peers)
    return ('application/json', json.dumps(peers_copy))

@app.route('/connect', methods=['GET'])
def connect(headers, body):
    print(f"[SampleApp]:")
    print(body)
    # target = body.get('target', 'unknown')
    # print(f"[SampleApp] Connecting to peer: {target}")
    # return '/chat.html'
    target = body.get('target')
    print(f"[SampleApp] Connect request to {target}")

    # Giả định: headers chứa username hiện tại (hoặc đọc từ cookie/session)
    current_user = headers.get('username', 'unknown')

    with peers_lock:
        target_info = active_peers.get(target)

    if not target_info:
        print(f"[SampleApp] Peer '{target}' not found in active list.")
        return '/chat.html'

    with users_lock:
        active_connections[current_user] = target

    print(f"[SampleApp] {current_user} is now connected to {target} ({target_info['ip']}:{target_info['port']})")

    return '/chat.html'
    # return ('text/html', open('www/chat.html', 'r').read())

@app.route('/send_message', methods=['POST'])
def send_message(headers, body):
    
    sender_ip = body.get('IP')
    sender_port = body.get('Port')
    target = body.get('target')
    msg = body.get('msg')

    print(f"[SampleApp] {sender_ip}:{sender_port} → sending message to {target}: {msg}")

    if not target or not msg:
        return 'Invalid request'

    with peers_lock:
        peer_info = active_peers.get(target)
    
    if not peer_info:
        print(f"[SampleApp] Target '{target}' not found in active_peers.")
        return 'Peer not found'

    target_ip = peer_info['ip']
    target_port = int(peer_info['port'])

    # Gửi tin nhắn tới peer đó
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((target_ip, target_port))
            s.sendall(msg.encode('utf-8'))
            print(f"[SampleApp] Sent message '{msg}' to {target_ip}:{target_port}")
        return 'Message sent'
    except Exception as e:
        print(f"[SampleApp] Failed to send message: {e}")
        return f"Send failed: {e}"

    
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
    app.run()