"""
Read sensor data from BME280 and send it over local network
"""

import os

import bme280
import smbus2
from dotenv import load_dotenv
import datetime
import requests
import logging
from pathlib import Path

# Set up logging
log_file = Path.home() / "sensor_logs.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Load sensor location from env
load_dotenv()
port = os.getenv("I2C_PORT")
address = os.getenv("I2C_ADDRESS")
bus = smbus2.SMBus(port)

# Load calibration parameters from sensor
sensor_calibration = bme280.load_calibration_params(bus, address)


def main():
    """
    Read BME and send data to a URL
    """

    # Read time
    read_time = datetime.utcnow()

    # Read sensor
    try:
        data = bme280.sample(bus, address, sensor_calibration)
    except Exception as err:
        logging.error(err)

    # Send data
    try:
        response = requests.post(
            os.getenv("POST_URL"),
            json={
                "time": read_time,
                "temperature": data.temperature,
                "pressure": data.pressure,
                "humidity": data.humidity,
            },
        )
        response.raise_for_status()
    except requests.HTTPError as err:
        logging.error(err)

    # If success, log
    logging.info(f"Data read and sent successfully")
