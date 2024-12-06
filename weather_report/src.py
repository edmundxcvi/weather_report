"""
Read sensor data from BME280 and send it over local network
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import json
from dataclasses import dataclass

import bme280
import requests
import smbus2
from typing import Union
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


def load_env_var(var_name: str) -> str:
    try:
        return os.environ[var_name]
    except KeyError:
        logger.error(
            "Could not load required environment variable {var_name}, check .env file"
        )
        exit()


# Set up logging
logger.remove()
logger.add(load_env_var("LOG_FILE_PATH"), level="INFO", retention="2 days")
logger.add(sys.stdout, level="DEBUG")


@dataclass
class SensorData:
    """
    Data class for sensor read
    """

    observation_time: datetime
    temperature: float
    pressure: float
    humidity: float

    def to_dict(self):
        return {
            "observation_time": self.observation_time.isoformat(),
            "temperature": self.temperature,
            "pressure": self.pressure,
            "humidity": self.humidity,
        }


@dataclass
class PostConfig:
    """
    Data class for requests kwargs
    """

    post_url: str
    api_key: str
    timeout: int
    verify: bool

    def to_dict(self):
        return {
            "url": self.post_url,
            "headers": {"Authorization": self.api_key},
            "timeout": self.timeout,
            "verify": self.verify,
        }

    @classmethod
    def from_env(cls, verify=True):

        return cls(
            post_url=load_env_var("POST_URL"),
            api_key=load_env_var("API_KEY"),
            timeout=int(load_env_var("POST_TIMEOUT_SECONDS")),
            verify=verify,
        )


def read_sensor(port: Union[int, str], address: Union[int, str]) -> SensorData:
    """Gets data from sensor

    Can pass the address in as a string representation of address as a base
    sixteen integer, which will be converted to int in function

    Args:
        port (Union[int, str]) address (Union[int, str])

    Returns:
        SensorData
    """
    # Convert inputs to integers (if not already)
    if not isinstance(port, int):
        port = int(port)
    if not isinstance(address, int):
        address = int(address, 16)

    # Get bus for port
    bus = smbus2.SMBus(port)

    # Load calibration parameters from sensor
    sensor_calibration = bme280.load_calibration_params(bus, address)

    # Get time ahead of read
    read_time = datetime.now(timezone.utc)

    # Read sensor
    sensor_data = bme280.sample(bus, address, sensor_calibration)

    # Convert to a sensible object
    return SensorData(
        observation_time=read_time,
        temperature=sensor_data.temperature,
        pressure=sensor_data.pressure,
        humidity=sensor_data.humidity,
    )


def save_data_to_buffer(sensor_data: SensorData, buffer_dir_path: Path):

    obs_time_str = sensor_data.observation_time.strftime("%Y%m%d%H%M%S")
    buffer_file_path = buffer_dir_path / f"read_{obs_time_str}.json"
    with open(buffer_file_path) as buffer_file:
        json.dump(sensor_data.to_dict(), buffer_file)


def post_data(
    sensor_data: SensorData, post_config: PostConfig, buffer=True
) -> requests.Response:
    """Sends data to server

    Args:
        sensor_data (SensorData)
        post_config (PostConfig)
        buffer (bool, optional): Defaults to True.

    Returns:
        requests.Response
    """

    # Try post
    try:
        response = requests.post(
            **post_config.to_dict(),
            json=sensor_data.to_dict(),
        )
        response.raise_for_status()

    # If post fails
    # Request exception covers error return codes, but also covers other connection issues like SSL and Connection Errors
    except requests.RequestException as request_err:
        # Attempt to save in file buffer if requested
        if buffer:
            try:
                save_data_to_buffer(sensor_data, Path(load_env_var("POST_BUFFER_PATH")))
            except OSError as os_err:
                logger.error(
                    f"Post request failed and data could not be saved due to the following exception: {os_err}"
                )
            else:
                logger.warning(
                    f"Post request failed but data was saved to buffer successfuly"
                )
        else:
            logger.error(
                f"Post request failed due to the following exception: {request_err}"
            )
        exit()

    # If post request succeeds then all good!
    else:
        logger.debug("Post request sent")

    return response


def read_and_post():

    # Load sensor location from env
    port = int(load_env_var("I2C_PORT"))
    address = int(load_env_var("I2C_ADDRESS"), 16)

    # Read sensor
    try:
        sensor_data = read_sensor(port, address)
    except Exception as err:
        logger.error(f"Error reading sensor: {err}")
        exit()
    else:
        logger.debug("Sensor read successfully")

    # Read post config from env
    post_config = PostConfig.from_env(verify=load_env_var("SSL_CERT_PATH"))

    # Send post request
    response = post_data(sensor_data, post_config)

    # Check for unexpected status
    if response.status_code != 201:
        logger.warning(
            f"Sensor read received unexpected status code {response.status_code}: {response.reason}"
        )
    else:
        logger.info("Data read and sent successfully")
