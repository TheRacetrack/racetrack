#!/bin/bash
set -e

if [ "$1" == "up" ]; then

    # Clone and setup racetrack repository
    git clone https://github.com/TheRacetrack/racetrack
    cd racetrack
    make setup-racetrack-client
    . venv/bin/activate

    # Start Racetrack components
    make compose-up-pull
    LIFECYCLE_URL=http://localhost:7102 ./utils/wait-for-lifecycle.sh # and wait a while until it's operational

    # Login to Racetrack with an admin user
    racetrack login http://localhost:7102 eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI

    # Install Python job type in your Racetrack
    racetrack plugin install github.com/TheRacetrack/plugin-python-job-type http://localhost:7102

    # Create sample Job to be deployed
    mkdir -p ../racetrack-sample && cd ../racetrack-sample
    cat << EOF > entrypoint.py
class Entrypoint:
    def perform(self, a: float, b: float) -> float:
        """Add numbers"""
        return a + b
EOF

    cat << EOF > fatman.yaml
name: adder
owner_email: sample@example.com
lang: python3
git:
remote: https://github.com/TheRacetrack/racetrack
python:
entrypoint_path: 'entrypoint.py'
entrypoint_class: 'Entrypoint'
EOF

    # Deploy Job to create a running Fatman
    racetrack deploy . http://localhost:7102 --context-local

    # Call your application
    curl -X POST "http://localhost:7105/pub/fatman/adder/latest/api/v1/perform" \
    -H "Content-Type: application/json" \
    -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
    -d '{"a": 40, "b": 2}'
    # Expect: 42

elif [ "$1" == "down" ]; then

    cd racetrack && make down

else
    echo "Unknown first argument"
    exit 1
fi
