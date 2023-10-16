#!/bin/bash
set -e

echo "Preparing installer…"
GIT_BRANCH='308-provide-instructions-on-how-to-install-racetrack-to-a-vm-instance'
wget -O wizard.py https://raw.githubusercontent.com/TheRacetrack/racetrack/${GIT_BRANCH}/utils/standalone-wizard/wizard.py

if [ ! -d "venv" ]; then # if venv directory doesn't exist
  echo "Preparing virtual Python environment…"
  python3 -m venv venv
fi
. venv/bin/activate
python -m pip install --upgrade racetrack-client

python wizard.py
