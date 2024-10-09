from setuptools import setup

# Read requirements from requirements.txt
# Sorry abt the strict requirements (not)
with open('requirements.txt', 'r') as file:
    requirements = [line.strip() for line in file if line and not line.startswith('#')]


setup(
    name="weather_report",
    version="0.0.0",
    py_modules=["weather_report"],  # Your main script file without the .py extension
    install_requires=requirements,  # Add any dependencies here if needed
    entry_points={
        "console_scripts": [
            "weather_report=weather_report:main",  # Define the CLI command and entry point
        ],
    },
)