#!/bin/bash
ROOT_DIR="$(readlink -f $(dirname $(dirname "$BASH_SOURCE[0]}")))"
source "$ROOT_DIR/.venv/bin/activate"
weather_report