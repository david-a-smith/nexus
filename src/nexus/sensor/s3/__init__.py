from nexus.sensor import SensorMetaData


class S3MetaData(SensorMetaData):

    def __init__(self):
        self.name = 's3'
        self.description = """
        Amazon S3 can be configured to emit events to an SQS queue when new objects are added to a particular
        bucket / object key prefix combination. This sensor connects to an SQS queue, waiting for files that match
        the file pattern supplied by the user when setting up the sensor.

        Exactly one event is emitted for each matching event received from the SQS queue
        """
        SensorMetaData.__init__(self)

    def user_config(self):
        return self.schema_from_file('s3/schema/user-config.json')

    def outputs(self):
        return self.schema_from_file('s3/schema/outputs.json')

