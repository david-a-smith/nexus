import argparse
import logging
from nexus.sensor.core import Sensor

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    a = argparse.ArgumentParser(description='This command runs Nexus sensors')
    a.add_argument('sensor', type=str, help="The name of the sensor to run", choices=['s3', 'api'])
    args = a.parse_args()

    sensor = Sensor.factory(args.sensor, port=8080)
    sensor.run()