from nexus.sensor.core import Sensor
from logging import debug
from http.server import HTTPServer, BaseHTTPRequestHandler


class ApiSensor(Sensor):

    def run(self):
        """
        Initialise a simple HTTP server and listen for incoming requests
        Only POST requests will be serviced, with all other requests return "method not allowed" responses
        """
        ApiRequestHandler.sensor = self

        debug("Initialising HTTP server running on port %s" % self.config.get('port'))
        server = HTTPServer(('127.0.0.1', self.config.get('port')), ApiRequestHandler)
        server.serve_forever()

    def trigger(self, api_payload):
        """
        Raise the full API payload as an event
        """
        event = {
            "api_payload": api_payload
        }
        self.push(event)

    def cleanup_and_end(self):
        debug("Stopped HTTP server that was running on port %s" % self.config.get('port'))
        Sensor.end()


class ApiRequestHandler(BaseHTTPRequestHandler):

    sensor = None

    def do_POST(self):
        with open(self.rfile, 'r') as raw_input:
            payload = raw_input.read()
            debug("Received payload...")
            print(payload)
            self.sensor.trigger(payload)
            self.send_response(200, "Message received!")

    def do_GET(self):
        self.not_allowed()

    def do_PUT(self):
        self.not_allowed()

    def do_DELETE(self):
        self.not_allowed()

    def do_PATCH(self):
        self.not_allowed()

    def not_allowed(self):
        self.send_error(405, "Only post requests are permitted to this API endpoint")