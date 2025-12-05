import socket
import threading
import argparse
import json
import time

connections = {}  # store the peer connected to :)
connections_lock = threading.Lock()
incoming_messages = []
notification_messages = []
notification_lock = threading.Lock()
messages_lock = threading.Lock()

# broadcast_connections = {}


list_method = ['POST', 'OPTIONS', 'GET']
list_action = ["/send-peer", "/poll", "/connect-peer", "/connect-all", "/broadcast", "/notification", "/ping"]
http = 'HTTP/1.1'

def handle_client(conn, addr, name):
    global incoming_messages
    global notification_messages
    try:
        method = ''
        data = conn.recv(4096).decode()

        if not data:
            conn.close()
            return

        # Parse route:
        first_line = data.splitlines()[0]

        # print(first_line)
        if len(first_line.split(" ")) == 3:
            method, path, http = first_line.split()
            if method in list_method and (path in list_action or path.startswith("/poll") or path.startswith("/send-peer")):
                if (not path.startswith("/poll")) and (not path == "/notification"):
                    print(f"[MiniServer] Request from {addr}:")
                    print("--- RAW REQUEST ---")
                    print(data)
                    print("-------------------")
            else:
                # message = data.strip()
                print(f"[MiniServer] Received message: {data}")
                with messages_lock:
                    incoming_messages.append({"from": data.split(":")[0], "msg": data.split(":")[1]})

                    with notification_lock:
                        notification_messages.append({"from": data.split(":")[0], "msg": data.split(":")[1]})

                    print(incoming_messages)
                    print(notification_messages)
                    
                conn.sendall(b"OK")
                conn.close()
                return
        else:
            # path = "/send-peer"
            # message = data.strip()
            print(f"[MiniServer] Received message: {data}")
            with messages_lock:
                incoming_messages.append({"from": data.split(":")[0], "msg": data.split(":")[1]})
                print(incoming_messages)
                print(notification_messages)
                with notification_lock:
                    notification_messages.append({"from": data.split(":")[0], "msg": data.split(":")[1]})
 
            conn.sendall(b"OK")
            conn.close()
            return


        if method == 'OPTIONS':
            print("[Mini-Server]: Preparing OPTIONS Response")
            resp = (
                "HTTP/1.1 204 No Content\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
                "Access-Control-Allow-Headers: Content-Type\r\n"
                "Access-Control-Max-Age: 86400\r\n"
                "Connection: close\r\n"
                "Content-Length: 0\r\n"
                "\r\n"
            )
            conn.sendall(resp.encode('utf-8'))

            conn.close()
            return

        body = ""
        if "\r\n\r\n" in data:
            body = data.split("\r\n\r\n", 1)[1].strip()

        if path == "/connect-peer":

            try:
                info = json.loads(body)
                with connections_lock:
                    connections[info["target"]] = (info["target_ip"], int(info["target_port"]))
                    # print(connections)
                    
                response_body = "Peer connection established"

            except Exception as e:
                response_body = f"Bad request: {e}"

        elif path.startswith("/send-peer"):
            print("[MiniServer]: Calling API /send-peer")
            target_name = path.split("?")[1].split("=")[1]
            try:

                if method != 'POST':
                    response_body = "Method Not Allowed"
                else:
                    msg = json.loads(body)["msg"]
                    msg = str(name) + ":" + msg
                    if target_name not in connections:
                        response_body = "No peer connected yet"
                    else:
                        target_ip, target_port = connections[target_name]
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

                            print('[MiniSErver]: Connecting...')
                            print(target_ip, target_port)
                            s.connect((target_ip, target_port))
                            
                            s.sendall(msg.encode())
                        response_body = "Message sent"
            except Exception as e:
                response_body = f"Send failed: {e}"

        elif path.startswith("/poll"):
            with messages_lock:
                # print("[Polling]:")
                # print(incoming_messages)
                target_name = path.split("?")[1].split("=")[1]
                if incoming_messages:

                    forward_list = []
                    remain_list = []
                    for fg in incoming_messages:
                        if fg.get("from") == target_name:
                            forward_list.append(fg)
                        else:
                            remain_list.append(fg)

                    response_body = json.dumps(forward_list)
                    incoming_messages = remain_list

                    with notification_lock:
                        notification_messages.clear()
                        for msg in remain_list:
                            notification_messages.append(msg)
                else:
                    response_body = json.dumps([])

        elif path == "/broadcast":
            print('[Mini-Server]: Calling Broadcast')
            try:
                msg = json.loads(body).get("msg", "")
                msg = str(name) + ":" + msg

                sent_count = 0

                with connections_lock:

                    for username, (ip, port) in connections.items():
                        try:

                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

                                s.connect((ip, port))
                                s.sendall(msg.encode())
                            sent_count += 1

                        except Exception as se:
                            print(f"[MiniServer] Broadcast to {username} failed: {se}")
                    
                response_body = f"Broadcast sent to {sent_count} peers"


            except Exception as e:
                response_body = f"Broadcast failed: {e}"
        
        elif path == "/notification":
            # print('[Mini-Server]: Fetching notifications')
            with notification_lock:
                if notification_messages:
                    response_body = json.dumps(notification_messages)
                    notification_messages.clear()
                else:
                    response_body = json.dumps([])

        else:
            response_body = "Unknown endpoint"

        resp = (
            "HTTP/1.1 200 OK\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Content-Type\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "\r\n"
            f"{response_body}"
        )
        conn.sendall(resp.encode())
    except Exception as e:
        print(f"[MiniServer] Error handling client: {e}")
    finally:
        conn.close()

def run_server(ip, port, name):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((ip, port))
    s.listen(5)
    print(f"[MiniServer] Listening on {ip}:{port}")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr, name), daemon=True).start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-port", type=int, default=9001)
    parser.add_argument("--name", type=str, default="Duong")
    args = parser.parse_args()

    run_server("0.0.0.0", args.server_port, args.name)
