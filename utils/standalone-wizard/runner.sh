#!/bin/bash
set -e

echo "Preparing installer…"
RT_BRANCH="${RT_BRANCH:-master}"
curl -#o wizard.py https://raw.githubusercontent.com/TheRacetrack/racetrack/${RT_BRANCH}/utils/standalone-wizard/wizard.py
curl -#o wizard.py https://raw.githubusercontent.com/TheRacetrack/racetrack/${RT_BRANCH}/utils/standalone-wizard/utils.py

if [ ! -d "venv" ]; then # if dir doesn't exist
  echo "Preparing virtual Python environment…"
  python3 -m venv venv
fi
. venv/bin/activate
python -m pip install --upgrade racetrack-client

python wizard.py
