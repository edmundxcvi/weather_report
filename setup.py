from setuptools import setup, find_packages

# Read requirements from requirements.txt
# Sorry abt the strict requirements (not)
with open('requirements.txt', 'r') as file:
    requirements = [line.strip() for line in file if line and not line.startswith('#')]


setup(
    name="weather_report",
    version="0.0.0",
    packages=find_packages(),  
    install_requires=requirements,  # Add any dependencies here if needed
    entry_points={
        "console_scripts": [
            "weather_report=weather_report.src:main",  # Define the CLI command and entry point
        ],
    },
)