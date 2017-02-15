from nexus.sensor.core import SensorMetaData


class ApiMetaData(SensorMetaData):

    def __init__(self):
        self.name = 'api'
        self.description = """
        Listens for incoming HTTP requests on a configured port. Requests must be made to a specific flow.
        Is relatively dumb in its functionality. Request payloads are simply re-raised as triggered sensor events.
        """
        SensorMetaData.__init__(self)

    def user_config(self):
        return self.schema_from_file('api/schema/user-config.json')

    def outputs(self):
        return self.schema_from_file('api/schema/outputs.json')

    def inputs(self):
        return self.schema_from_file('api/schema/inputs.json')
