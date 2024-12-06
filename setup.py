from setuptools import find_packages, setup

# Read requirements from requirements.txt
# Sorry abt the strict requirements (not)
with open("requirements.txt", "r") as file:
    requirements = [line.strip() for line in file if line and not line.startswith("#")]


setup(
    name="weather_report",
    version="0.0.0",
    packages=find_packages(),
    install_requires=requirements,  
    entry_points={
        "console_scripts": [
            "weather_report=weather_report.src:read_and_post",  
        ],
    },
)
