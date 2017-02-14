import boto3
from nexus.sensor import Sensor
import nexus.util.validate as validate
import logging
import re


class S3Sensor(Sensor):

    OP_EXISTS = 'exists'
    OP_CREATED = 'created'
    OP_MODIFIED = 'modified'
    OP_DELETED = 'deleted'

    def validate_config(self):
        """
        Perform validation of the user supplied config options
        """

        # perform the JSON schema validation
        Sensor.validate_config(self)

        # if we need to check the bucket for existence of a file
        # check we have access to the S3 bucket with the account details we've been supplied with
        if self.config.get('trigger_on_existing_file'):
            boto3.resource('s3').Bucket(self.config.get('bucket')).objects.limit(count=1)

        # if we've been given a regex, verify it compiles correctly
        if self.config['key_matcher']['type'] == 'regex' and not validate.regex_compiles(self.config['key_matcher']['pattern']):
            raise validate.ConfigError("Key matcher regex %s does not compile" % self.config['key_matcher']['pattern'])

        # if we've been given a regex, verify it compiles correctly
        if self.config['op_matcher']['type'] == 'regex' and not validate.regex_compiles(self.config['op_matcher']['pattern']):
            raise validate.ConfigError("Op matcher regex %s does not compile" % self.config['op_matcher']['pattern'])

        # if we are being asked to check for an existing file, we can only ever do this if an exact pattern match is used
        if self.config.get('trigger_on_existing_file') and self.config['key_matcher']['type'] != 'exact':
            raise validate.ConfigError("You can only use trigger_on_existing_file when the key_matcher pattern type is 'exact'")

    def run(self):
        """
        Main loop for the sensor
        """
        # we'll trigger an event if the file already exists
        key, op = self.check_existing_file()
        if key and op:
            self.trigger(key, op)

        # now we need to create an SQS binding on the bucket. this will allow us to receive notifications when
        # something happens within the bucket that we might be interested in
        transport = NotificationTransport.factory(
            self.config.get('notification_transport'),
            bucket=self.config.get('bucket')
        )
        transport.bind()

        while True:
            # every time we receive an event, we'll check if we should handle it
            notification = transport.receive()
            if notification is False:
                self.cleanup_and_end(transport)

            print("Received notification: %s", notification)

            if self.notification_should_trigger_sensor(notification):
                # the event matches what we're looking for... let's trigger an event
                self.trigger(notification.key, notification.op, transport=transport)

    def notification_should_trigger_sensor(self, notification):
        """
        Determine whether or not a notification should trigger the sensor
        The config options supplied to the sensor on start up are used to determine if the notification
        should cause the sensor to be triggered
        """
        return self._key_matches(notification.object_key) and self._op_matches(notification.op)

    def _key_matches(self, key):
        """
        Check if the object key pattern specified in the user config matches what we have just received
         Handles exact, partial and regex matches
        """
        key_match_type = self.config['key_matcher']['type']
        key_match_pattern = self.config['key_matcher']['pattern']

        if key_match_type == 'exact':
            return key_match_pattern == key

        if key_match_type == 'partial':
            key_match_pattern = '^' + key_match_pattern + '.*'
            key_match_type = 'regex'

        if key_match_type == 'regex':
            return re.match(key_match_pattern, key) is not None

        return False

    def _op_matches(self, op):
        """
        Check if the operation specified in the user config for the sensor matches what we have just received
         Handles both exact and regex matches
         If no op_matcher was specified, we will always treat that as a match
        """
        op_match_type = self.config.get('op_matcher', {}).get('type')
        op_match_pattern = self.config.get('op_matcher', {}).get('pattern')

        if op_match_type == 'exact':
            return op == op_match_pattern

        if op_match_type == 'regex':
            return re.match(op_match_pattern, op) is not None

        return True

    def check_existing_file(self):
        """
        If the sensor has been configured to look for an existing file, we perform that check here
         Connect to the S3 bucket and look for the file matching the object key_match.pattern
         If we find an object, we check that it complies with the existing_file_max_age_minutes config option, if
         that has been provided.
        """
        bucket = boto3.resource('s3').Bucket(self.config.get('bucket'))
        if not self.config.get('trigger_on_existing_file'):
            return

        obj = bucket.object(self.config['key_matcher']['pattern'])
        if not obj:
            return

        last_modified_threshold = self.config.get('existing_file_max_age_minutes')

        if last_modified_threshold:
            print("Last modified...")
            print(obj.last_modified)
            # we found the object and it was created within the allowed threshold, so we'll trigger the sensor
            # immediately
            return self.config['key_matcher']['pattern'], S3Sensor.OP_EXISTS

        return

    def trigger(self, object_key, operation, transport=None):
        """
        Trigger a new sensor event
        If the sensor has been configured to end after the sensor is triggered, this will happen immediately after
        the event has been pushed.
        """
        event = {
            "s3_object": {
                "bucket": {
                    "aws_account": self.config['bucket']['aws_account'],
                    "name": self.config['bucket']['name']
                },
                "object_key": object_key
            },
            "operation": operation
        }

        self.push(event)

        if self.config.get('standard', {}).get('end_on_trigger'):
            self.cleanup_and_end(transport)

    def cleanup_and_end(self, transport=None):
        """
        When the sensor needs to end, we need to cleanup the transport then exit gracefully
        This can occur when the sensor is configured to exit immediately after being triggered,
         or when the sensor receives a KILL signal
        """
        if transport:
            transport.cleanup()

        Sensor.end()


class NotificationTransport(object):

    def __init__(self, **kwargs):
        self.config = kwargs

    @staticmethod
    def factory(transport, **kwargs):
        """
        Create a new instance of a notification transport
        """
        if transport == 'sqs':
            return SqsTransport(**kwargs)

        raise NotImplementedError("[%s] is not a valid notification transport" % transport)

    def receive(self):
        raise NotImplementedError("Method receive() has not been implemented")

    def bind(self):
        raise NotImplementedError("Method bind() has not been implemented")

    def cleanup(self):
        raise NotImplementedError("Method cleanup() has not been implemented")


class SqsTransport(NotificationTransport):

    def __init__(self, **kwargs):
        NotificationTransport.__init__(self, **kwargs)
        self.queue_arn = None
        self.sqs = None

    def bind(self):
        """
        Create a temporary SQS queue and bind it to the S3 bucket using the bucket notifications API
        """
        bucket = self.config.get('bucket')

        logging.info("Creating SQS queue on AWS account %s" % bucket['aws_account'])

        self.queue_arn = None  #TODO set queue ARN after creating the SQS resource
        logging.info("Successfully created SQS queue with ARN %s" % self.queue_arn)

        logging.info("Binding SQS queue to S3 bucket %s" % bucket['name'])

        bind_pattern = None #TODO we get the resulting bind pattern in the response from the S3 bucket notification
                            #operation. we'll log this pattern as it is the source of truth

        logging.info("SQS queue is now bound to S3 bucket %s with pattern %s" % (bucket['name'], bind_pattern,))

    def receive(self):
        """
        Long poll the SQS queue, returning a notification whenever a message is received
        Long polling the queue will save requests to SQS, which is billed on # requests
        """

        # enter the long poll loop
        while True:
            # if the long poll operations fails, we'll break out of this loop and the method will return false.
            # this will cause the sensor to "cleanup_and_end()"

            # we'll delete the message as soon as it is received to keep things simple
            logging.debug("Message received from SQS %s" % self.queue_arn)

            # extract the message body from the SQS payload
            message_body = None
            logging.debug("Message body: %s" % message_body)

            # create and return the new Notification
            key = op = None
            return Notification(key, op)

        return False

    def cleanup(self):
        """
        Remove the SQS queue that was temporarily created, keeping things tidy.
        """
        logging.info("Cleaning up SQS transport...")

        logging.debug("Removing SQS queue %s" % self.queue_arn)

        logging.debug("Removing all references to SQS queue from S3 bucket notifications for %s")


class Notification(object):

    def __init__(self, object_key, op):
        self.key = object_key
        self.op = op
