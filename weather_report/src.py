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
from typing import Union, Mapping, Any, Optional
from dotenv import load_dotenv
from loguru import logger
from loguru._logger import Logger

load_dotenv()


def load_env_var(var_name: str) -> str:
    try:
        return os.environ[var_name]
    except KeyError:
        logger.error(
            "Could not load required environment variable {var_name}, check .env file"
        )
        exit()


def start_logs(logfile_name: str) -> Logger:

    # Clear any existing logs
    logger.remove()

    # Info goes to file
    log_file_path = (
        Path(load_env_var("OUTPUT_DATA_DIR")) / "logs" / f"{logfile_name}.log"
    )
    logger.debug(f"{log_file_path}")
    logger.add(log_file_path, level="INFO", retention="2 days")

    # Also log at debug to console
    logger.add(sys.stdout, level="DEBUG")
    return logger


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

    @classmethod
    def from_json(cls, data_dict: Mapping[str, Any]):
        return cls(
            observation_time=datetime.fromisoformat(data_dict["observation_time"]),
            temperature=data_dict["temperature"],
            pressure=data_dict["pressure"],
            humidity=data_dict["humidity"],
        )


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

    # Ensure that directory exists
    buffer_dir_path.mkdir(exist_ok=True)

    # Create buffer file name
    obs_time_str = sensor_data.observation_time.strftime("%Y%m%d%H%M%S")
    buffer_file_path = buffer_dir_path / f"read_{obs_time_str}.json"

    # Write buffer file
    with buffer_file_path.open("w") as buffer_file:
        json.dump(sensor_data.to_dict(), buffer_file)


def post_data(
    sensor_data: SensorData, post_config: PostConfig, buffer=True, on_error="exit"
) -> Optional[requests.Response]:
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
                save_data_to_buffer(
                    sensor_data,
                    Path(load_env_var("OUTPUT_DATA_DIR")) / "observation_buffer",
                )
            except OSError as os_err:
                logger.error(
                    f"Post request failed and data could not be saved due to the following exception: {os_err}"
                )
            else:
                logger.warning(
                    f"Post request failed but data was saved to buffer successfuly. Request error was: {request_err}"
                )
        else:
            logger.error(
                f"Post request failed due to the following exception: {request_err}"
            )
        # Leave if requested
        if on_error == "exit":
            exit()

        # Otherwise return response (or null if error was during request)
        if isinstance(request_err, requests.HTTPError):
            return response
        return None

    # If post request succeeds then all good!
    else:
        logger.debug("Post request sent")

    return response


def read_and_post():

    # Start logging
    start_logs("sensor_reads")

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


def flush_buffer():

    # Start logging
    start_logs("buffer_flushes")

    # Check for unsent data files
    buffer_dir =  Path(load_env_var("OUTPUT_DATA_DIR")) / "observation_buffer"
    buffer_file_names = [file for file in buffer_dir.iterdir() if file.is_file()]
    
    # If list is empty then report and leave
    if len(buffer_file_names) == 0:
        logger.info("No files found in buffer")
        exit()
    logger.info(f"{len(buffer_file_names)} files found in buffer")

    # Read post config from env
    post_config = PostConfig.from_env(verify=load_env_var("SSL_CERT_PATH"))

    # Loop through files
    n_attempts = 0
    attempt_limit = int(load_env_var("BUFFER_POST_ATTEMPT_LIMIT"))
    for file_name in buffer_file_names:

        # Check that attempt limit has not been exceeded
        if n_attempts > attempt_limit:
            logger.error(
                f"Post request failed {n_attempts} times (max {attempt_limit}), exiting"
            )
            exit()

        # Load data from file
        try:
            with file_name.open() as buffer_file:
                sensor_data = json.load(buffer_file)
                sensor_data = SensorData.from_json(sensor_data)
        except (OSError, KeyError) as err:
            logger.error(
                f"Could not read data file due to the following exception: {err}"
            )

        # Send post request
        response = post_data(
            sensor_data, post_config, buffer=False, on_error="continue"
        )

        # If response is not as expected move on to next file (but don't delete)
        if response.status_code != 201:
            logger.warning(
                f"Buffer flush received unexpected status code {response.status_code}: {response.reason}"
            )
            n_attempts += 1
            continue

        # Otherwise delete buffer file to prevent duplication
        logger.debug(f"File {file_name.name} posted successfully, removing from buffer")
        file_name.unlink()
        logger.info(
            f"File {file_name.name} posted successfully and removed from buffer"
        )
