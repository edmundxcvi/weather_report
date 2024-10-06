from setuptools import setup

setup(
    name="weather_report",
    version="0.0.0",
    py_modules=["weather_report"],  # Your main script file without the .py extension
    install_requires=[],  # Add any dependencies here if needed
    entry_points={
        "console_scripts": [
            "weather_report=weather_report:main",  # Define the CLI command and entry point
        ],
    },
)