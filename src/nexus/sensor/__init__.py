import os
import json
from nexus.util.schema import RefResolver


class SensorMetaData(object):
    """
    Supplies metadata about a sensor.
     - name of the sensor
     - description of the sensor
     - output variables schema (description of what is emitted by the sensor)
    """

    def __init__(self):
        self.schema = None
        self.schema_path = os.path.dirname(os.path.realpath(__file__)) + '/schema'

    def set_schema_path(self, path):
        self.schema_path = path

    def schema_from_file(self, relative_file_path):
        full_path = self.schema_path + '/' + relative_file_path
        if not os.path.exists(full_path):
            raise FileNotFoundError('No sensor schema found at ' + full_path)

        with open(full_path, 'r') as schema:
            "Load the JSONSchema, resolving all references as we parse the schema"
            schema = json.load(schema)
            resolver = RefResolver()
            resolver.add_schema_path(self.schema_path)
            resolver.resolve(schema)
            self.schema = schema

        return self.schema
