# Nexus
Nexus is a distributed workflow system designed for use by data engineers to move data around their organisations. A modern UI enables data engineers to improve their experience of setting up and monitoring ETL flows, as well as making the ETL system accessible to other users groups, such as business analysts.

The technologies that Nexus uses in abundance are:

* Python 3
* Docker
* RabbitMQ
* vuejs

In addition, many of the sensors and processors included with the Nexus core are designed to be used on the AWS ecosystem. While Nexus can be extended to work with other IaaS platforms, AWS is supported out of the box.

Primary Abstractions
====================

Sensors
-------

Sensors listen for events happening that Nexus may be interested in. When they detect an event of interest, they raise an event and publish it into the Nexus sensor stream. Zero or more executors may decide to execute a flow based on the information received in the sensor.

While being completely decoupled in the codebase, sensors must share a common schema with the executors that consume their messages. This allows executors to validate the structure of the message they have received. Additionally, it allows the Nexus UI to dynamically construct UI input/output components between sensors and executors.

The schema provided by sensors is defined using JSON schema.

Sensors provided in the Nexus core are:

* Amazon S3. Used to listen for updates to objects within an S3 bucket. Can detect creation, modify or delete events.
* MySQL pressure sensor.  This sensor can track how much pressure there is on a particular table. "Pressure" means how many rows have been added/modified/deleted since the last time the sensor was triggered. This sensor requires access to the MySQL binlog of the MySQL server being monitored.
* Temporal. Takes a set of events to trigger at timed intervals - cron for Nexus.
* API. Listens for incoming HTTP requests and triggers an event whenever a new request is received. The sensor is relatively dumb, simply re-raising the payload it receives as a sensor event.