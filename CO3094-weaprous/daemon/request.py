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
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
        "auth", #Added by Duong 26/10/2025
        "body_override", #Added by Duong 26/10/2025
        "content_type_override",
        "query_string",
        "auth_register",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None
        #Added by Duong 26/10/2025
        self.auth = False

        self.body_override = None

        self.content_type_override = None

        self.query_string = None

        self.auth_register = False

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if '?' in path:
                path = path.split('?', 1)[0]
        
            if path == '/':
                path = '/index.html'
            if path == '/test':
                path = '/test.html'
        except Exception:
            return None, None, None

        
        return method, path, version
             
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        self.method, self.path, self.version = self.extract_request_line(request)
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))
        print("[Custom Request]:" + request)

        if not routes == {}:
            self.routes = routes
            self.hook = routes.get((self.method, self.path))

        self.headers = self.prepare_headers(request)
        self.body = self.prepare_body(request)

        self.headers["Cookie"] = self.prepare_cookies(self.headers)
        return

    def prepare_body(self, request):
        form_data = {}
        if self.path == '/connect':

            try:
                first_line = request.splitlines()[0]  # "GET /connect?target=Duong HTTP/1.1"
                _, full_path, _ = first_line.split()

                if '?' in full_path:
                    path, query = full_path.split('?', 1)
                    pairs = query.split('&')
                    for pair in pairs:
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            form_data[key] = value
                
                return form_data
            except Exception as e:
                print(f"[Request] Query parse error: {e}")

        else:
            try:
                header_part, body_part = request.split('\r\n\r\n', 1)
            except ValueError:
                return None

            pairs = body_part.split('&')
            for pair in pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    form_data[key] = value
                    
            return form_data


    # def prepare_body(self, data, files, json=None):
    #     self.prepare_content_length(self.body)
    #     self.body = body
    #     #
    #     # TODO prepare the request authentication
    #     #
	# # self.auth = ...
    #     return


    def prepare_content_length(self, body):
        self.headers["Content-Length"] = "0"
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        return


    def prepare_auth(self, auth, url=""):
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        return

    # def prepare_cookies(self, cookies):
    #         self.headers["Cookie"] = cookies

    def prepare_cookies(self, header):
        cookies = self.headers.get('cookie', '')
        print("[Request-Cookie]: " + cookies if cookies != '' else "No cookie" )
        return cookies
