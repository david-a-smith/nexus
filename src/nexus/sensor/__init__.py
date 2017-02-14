import os
import json
from nexus.util.schema import RefResolver
import jsonschema
import sys
import signal
import logging


class Sensor(object):

    def __init__(self, sensor_metadata, **config):
        self.config = config
        self.metadata = sensor_metadata
        self.validate_config()
        self.set_signal_handler()

    def validate_config(self):
        jsonschema.validate(self.config, self.metadata.user_config())

    def set_signal_handler(self):
        signal.signal(signal.SIGINT, self.handle_signal)

    def handle_signal(self, signum, frame):
        logging.info("Received SIGINT. Cleaning up and ending...")
        self.cleanup_and_end()

    def push(self, event):
        pass

    def cleanup_and_end(self):
        Sensor.end()

    @staticmethod
    def end():
        sys.exit(0)


class SensorMetaData(object):
    """
    Supplies metadata about a sensor.
     - name of the sensor
     - description of the sensor
     - output variables schema (description of what is emitted by the sensor)
    """

    def __init__(self):
        self.user_config = None
        self.inputs = None
        self.outputs = None
        self.schema_path = os.path.dirname(os.path.realpath(__file__))

    def set_schema_path(self, path):
        self.schema_path = path

    def schema_from_file(self, relative_file_path):
        full_path = self.schema_path + '/' + relative_file_path
        if not os.path.exists(full_path):
            raise FileNotFoundError('No sensor schema found at ' + full_path)

        with open(full_path, 'r') as schema_file:
            "Load the JSONSchema, resolving all references as we parse the schema"
            schema = json.load(schema_file)
            resolver = RefResolver()
            resolver.add_schema_path(self.schema_path)
            resolver.resolve(schema)

        return schema

    def user_config(self):
        pass

    def inputs(self):
        pass

    def outputs(self):
        pass
