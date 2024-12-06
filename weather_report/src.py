"""
Read sensor data from BME280 and send it over local network
"""

import os
from datetime import datetime, timezone
from pathlib import Path
import json

import bme280
import requests
import smbus2
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# Set up logging
logger.remove()
logger.add(os.getenv('LOG_FILE_PATH'), level='INFO', retention='2 days')

# Load sensor location from env
port = int(os.getenv("I2C_PORT"))
address = int(os.getenv("I2C_ADDRESS"), 16)
bus = smbus2.SMBus(port)

# Load calibration parameters from sensor
sensor_calibration = bme280.load_calibration_params(bus, address)

# Set post timeout
POST_TIMEOUT = 5  # seconds

# Prepare for failure
post_buffer_path = Path(os.getenv('POST_BUFFER_PATH'))

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
        logger.error("Error reading sensor: %s", err)
    else:
        logger.debug("Sensor read successfully")

    # Collate into dict
    data_dict = {
                "time": read_time.isoformat(),
                "temperature": data.temperature,
                "pressure": data.pressure,
                "humidity": data.humidity,
            }

    # Send data
    try:
        response = requests.post(
            os.getenv("POST_URL"),
            json=data_dict,
            headers={"Authorization": os.getenv("API_KEY")},
            timeout=POST_TIMEOUT,
            verify=os.getenv("SSL_CERT_PATH"),
        )
        response.raise_for_status()
    # If data coun't be sent try to save it
    # (This would be triggered by e.g. server unavailable)
    except requests.HTTPError as e:
        logger.error("Failed to send post request: %s", e)
        try:
            json.dump(data_dict, post_buffer_path / f"read_{read_time.strftime('%Y%m%d%H%M%S')}.json")
        except OSError:
            logger.error(f"Post request could not be saved: {e}")
        else:
            logger.warning(f"Post request saved to buffer.")
    else:
        logger.debug("Post request sent")

    # If unexpected error code returned but post request successful then warn
    if response.status_code != 201:
        logger.warning(
            f"Sensor read received unexpected status code {response.status_code}: {response.reason}"
        )
    else:
        logger.info("Data read and sent successfully")
