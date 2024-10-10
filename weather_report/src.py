"""
Read sensor data from BME280 and send it over local network
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import bme280
import requests
import smbus2
from dotenv import load_dotenv

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
port = int(os.getenv("I2C_PORT"))
address = int(os.getenv("I2C_ADDRESS"), 16)
bus = smbus2.SMBus(port)

# Load calibration parameters from sensor
sensor_calibration = bme280.load_calibration_params(bus, address)

# Set post timeout
POST_TIMEOUT = 5  # seconds


def main():
    """
    Read BME and send data to a URL
    """

    # Read time
    read_time = datetime.now(timezone.utc)

    # Read sensor
    try:
        data = bme280.sample(bus, address, sensor_calibration)
    except Exception as err:
        logging.error("Error reading sensor: %s", err)

    # Send data
    response = requests.post(
        os.getenv("POST_URL"),
        json={
            "time": read_time.isoformat(),
            "temperature": data.temperature,
            "pressure": data.pressure,
            "humidity": data.humidity,
        },
        timeout=POST_TIMEOUT,
    )
    if response.status_code != 200:
        logging.error(
            logging.error(
                "Sensor read successfully but data post failed with error: %s",
                response.reason,
            )
        )
    else:
        logging.info("Data read and sent successfully")
