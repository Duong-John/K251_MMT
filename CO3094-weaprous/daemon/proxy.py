#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.proxy
~~~~~~~~~~~~~~~~~

This module implements a simple proxy server using Python's socket and threading libraries.
It routes incoming HTTP requests to backend services based on hostname mappings and returns
the corresponding responses to clients.

Requirement:
-----------------
- socket: provides socket networking interface.
- threading: enables concurrent client handling via threads.
- response: customized :class: `Response <Response>` utilities.
- httpadapter: :class: `HttpAdapter <HttpAdapter >` adapter for HTTP request processing.
- dictionary: :class: `CaseInsensitiveDict <CaseInsensitiveDict>` for managing headers and cookies.

"""
import socket
import threading
from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict
import time

#: A dictionary mapping hostnames to backend IP and port tuples.
#: Used to determine routing targets for incoming requests.
PROXY_PASS = {
    "192.168.56.103:8080": ('192.168.56.103', 9000),
    "app1.local": ('192.168.56.103', 9001),
    "app2.local": ('192.168.56.103', 9002),
}

server_connections = {}
connections_lock = threading.Lock()

def forward_request(host, port, request):
    """
    Forwards an HTTP request to a backend server and retrieves the response.

    :params host (str): IP address of the backend server.
    :params port (int): port number of the backend server.
    :params request (str): incoming HTTP request.

    :rtype bytes: Raw HTTP response from the backend server. If the connection
                  fails, returns a 404 Not Found response.
    """

    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        backend.connect((host, port))
        backend.sendall(request.encode())
        response = b""
        while True:
            chunk = backend.recv(4096)
            if not chunk:
                break
            response += chunk
        return response
    except socket.error as e:
      print("Socket error: {}".format(e))
      return (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode('utf-8')

index = 0
proxy_lock = threading.Lock()

def resolve_routing_policy(hostname, routes):
    """
    Handles an routing policy to return the matching proxy_pass.
    It determines the target backend to forward the request to.

    :params host (str): IP address of the request target server.
    :params port (int): port number of the request target server.
    :params routes (dict): dictionary mapping hostnames and location.
    """

    print(hostname)
    proxy_map, policy = routes.get(hostname,('127.0.0.1:8000','round-robin'))
    print(proxy_map)
    print(policy)

    proxy_host = ''
    proxy_port = '8000'

    if isinstance(proxy_map, list):
        if len(proxy_map) == 0:
            print("[Proxy] Emtpy resolved routing of hostname {}".format(hostname))
            print("Empty proxy_map result")
            # TODO: implement the error handling for non mapped host
            #       the policy is design by team, but it can be 
            #       basic default host in your self-defined system
            # Use a dummy host to raise an invalid connection
            proxy_host = '127.0.0.1'
            proxy_port = '8000'

        elif len(proxy_map) == 1:
            proxy_host, proxy_port = proxy_map[0].split(":", 2)

        elif len(proxy_map) > 1: 
            if policy == 'round-robin':
                global index
                with proxy_lock:
                    server_address = proxy_map[index]
                    index = (index + 1) % len(proxy_map)
                proxy_host, proxy_port = server_address.split(":", 2)
            
            if policy == 'least-conn':
                selected_server_address = None
                
                with connections_lock:
                    active_servers = server_connections.get(hostname)
                    
                    if active_servers:
                        selected_server_address = min(active_servers, key=active_servers.get)
                        
                        active_servers[selected_server_address] += 1
                        
                        print(f"[Proxy LC] Selected {selected_server_address} (connections: {active_servers[selected_server_address]})")
                        print(f"[Proxy LC] Current state: {active_servers}")
                        proxy_host, proxy_port = selected_server_address.split(":", 2)
                        return proxy_host, proxy_port, selected_server_address


        else:
            # Out-of-handle mapped host
            proxy_host = '127.0.0.1'
            proxy_port = '8000'
    else:
        print("[Proxy] resolve route of hostname {} is a singulair to".format(hostname))
        proxy_host, proxy_port = proxy_map.split(":", 2)

    return proxy_host, proxy_port, None

def handle_client(ip, port, conn, addr, routes):
    """
    Handles an individual client connection by parsing the request,
    determining the target backend, and forwarding the request.

    The handler extracts the Host header from the request to
    matches the hostname against known routes. In the matching
    condition,it forwards the request to the appropriate backend.

    The handler sends the backend response back to the client or
    returns 404 if the hostname is unreachable or is not recognized.

    :params ip (str): IP address of the proxy server.
    :params port (int): port number of the proxy server.
    :params conn (socket.socket): client connection socket.
    :params addr (tuple): client address (IP, port).
    :params routes (dict): dictionary mapping hostnames and location.
    """
    resolved_host = None
    resolved_port = None
    selected_server_for_lc = None
    try:
        request = conn.recv(1024).decode()
        hostname = ""
        # Extract hostname
        for line in request.splitlines():
            if line.lower().startswith('host:'):
                hostname = line.split(':', 1)[1].strip()

        print("[Proxy] {} at Host: {}".format(addr, hostname))

        # Resolve the matching destination in routes and need conver port
        # to integer value
        resolved_host, resolved_port, selected_server_for_lc = resolve_routing_policy(hostname, routes)
        try:
            resolved_port = int(resolved_port)
        except ValueError:
            print("Not a valid integer")

        if resolved_host:
            print("[Proxy] Host name {} is forwarded to {}:{}".format(hostname,resolved_host, resolved_port))
            response = forward_request(resolved_host, resolved_port, request)        
        else:
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 13\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 Not Found"
            ).encode('utf-8')
        # print('[Custom-Proxy]: catch respone :')
        # print(response)
        conn.sendall(response)
    except Exception as e:
        print(f"[Proxy Handle Error] {e}")

    finally:

        if selected_server_for_lc:
            with connections_lock:
                hostname_of_server = hostname 

                if (hostname_of_server in server_connections and 
                    selected_server_for_lc in server_connections[hostname_of_server]):
                    
                    server_connections[hostname_of_server][selected_server_for_lc] -= 1

                    print(f"[Proxy LC] Decremented {selected_server_for_lc}. New count: {server_connections[hostname_of_server][selected_server_for_lc]}")
                    print(f"[Proxy LC] Current state: {server_connections[hostname_of_server]}")


        conn.close()
        print("[Proxy] has closed the connection")




request_counts = {} 
banned_ips = {}
rate_limit_lock = threading.Lock()

REQUEST_LIMIT = 100
TIME_WINDOW = 60 
BAN_DURATION = 10

def run_proxy(ip, port, routes):
    """
    Starts the proxy server and listens for incoming connections. 

    The process dinds the proxy server to the specified IP and port.
    In each incomping connection, it accepts the connections and
    spawns a new thread for each client using `handle_client`.
 

    :params ip (str): IP address to bind the proxy server.
    :params port (int): port number to listen on.
    :params routes (dict): dictionary mapping hostnames and location.

    """

    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        proxy.bind((ip, port))
        proxy.listen(50)
        print("[Proxy] Listening on IP {} port {}".format(ip,port))
        while True:
            conn, addr = proxy.accept()
            print("[Proxy]: IP and Port incoming: {} - {}".format(addr[0], addr[1]))
            #
            #  TODO: implement the step of the client incomping connection
            #        using multi-thread programming with the
            #        provided handle_client routine
            #
            # Added by Duong 23/10/2025/j
            # handle_client(ip, port, conn, addr, routes) # Added by Duong 23/10/2025
            # conn.settimeout(5.0)
            
            client_ip = addr[0]
            current_time = time.time()
            is_allowed = True

            with rate_limit_lock:

                if client_ip in banned_ips:
                    
                    if current_time - banned_ips[client_ip]['banned_time'] > BAN_DURATION:
                        request_counts[client_ip] = {'count': 1, 'first_request_time': current_time}
                        del banned_ips[client_ip]
                        print(f"[RateLimit] RESTORE banned IP to be served: {client_ip}")
                    else:
                        is_allowed = False
                        print(f"[RateLimit] BLOCKING IP still in BLACK-LIST: {client_ip}")
                elif client_ip in request_counts:
                    ip_data = request_counts[client_ip]
                    time_diff = current_time - ip_data['first_request_time']

                    if time_diff > TIME_WINDOW:
                        ip_data['count'] = 1
                        ip_data['first_request_time'] = current_time
                    else:
       
                        ip_data['count'] += 1
                else:
                    request_counts[client_ip] = {'count': 1, 'first_request_time': current_time}

                # Pass Rate-limit:
                if client_ip in request_counts and request_counts[client_ip]['count'] > REQUEST_LIMIT:

                    banned_ips[client_ip] = {'banned_time' : current_time}
                    del request_counts[client_ip] 
                    is_allowed = False

                    print(f"[RateLimit] BANNING IP {client_ip} for excessive requests.")

            if is_allowed:
                client_thread = threading.Thread(target=handle_client, args=(ip, port, conn, addr, routes))
                client_thread.start()

    except socket.error as e:
      print("Socket error: {}".format(e))

def create_proxy(ip, port, routes):
    """
    Entry point for launching the proxy server.

    :params ip (str): IP address to bind the proxy server.
    :params port (int): port number to listen on.
    :params routes (dict): dictionary mapping hostnames and location.
    """

    run_proxy(ip, port, routes)
