import os
import json
from nexus.util.schema import RefResolver
import jsonschema
import sys
import signal
import logging
import importlib


class Sensor(object):

    def __init__(self, sensor_metadata, **config):
        self.config = config
        self.metadata = sensor_metadata
        self.validate_config()
        self.set_signal_handler()

    def validate_config(self):
        print(self.config)
        print(self.metadata.user_config())
        jsonschema.validate(self.config, self.metadata.user_config())

    def set_signal_handler(self):
        signal.signal(signal.SIGINT, self.handle_signal)

    def handle_signal(self, signum, frame):
        logging.info("Received SIGINT. Cleaning up and ending...")
        self.cleanup_and_end()

    def push(self, event):
        logging.info("Pushing event generated from %s " % self.__class__.__name__)
        print(event)

    def cleanup_and_end(self):
        Sensor.end()

    @staticmethod
    def end():
        sys.exit(0)

    @staticmethod
    def factory(module_name, **config):
        # attempt to load the sensor module. it must consist of a sensor module and a meta module
        meta_module = importlib.import_module(module_name + '.meta')
        sensor_module = importlib.import_module(module_name + '.sensor')
        main_module = importlib.import_module(module_name)
        meta_name = main_module.METADATA_CLASS
        sensor_name = main_module.SENSOR_CLASS

        meta = getattr(meta_module, meta_name)()
        sensor = getattr(sensor_module, sensor_name)(meta, **config)

        return sensor


class SensorMetaData:
    """
    Supplies metadata about a sensor.
     - name of the sensor
     - description of the sensor
     - output variables schema (description of what is emitted by the sensor)
    """

    def __init__(self):
        self._user_config = None
        self._inputs = None
        self._outputs = None
        self._schema_path = os.path.dirname(os.path.realpath(__file__))

    def set_schema_path(self, path):
        self._schema_path = path

    def schema_from_file(self, relative_file_path):
        full_path = self._schema_path + '/' + relative_file_path
        if not os.path.exists(full_path):
            raise FileNotFoundError('No sensor schema found at ' + full_path)

        with open(full_path, 'r') as schema_file:
            "Load the JSONSchema, resolving all references as we parse the schema"
            schema = json.load(schema_file)
            resolver = RefResolver()
            resolver.add_schema_path(self._schema_path)
            resolver.resolve(schema)

        return schema

    def user_config(self):
        pass

    def inputs(self):
        pass

    def outputs(self):
        pass
