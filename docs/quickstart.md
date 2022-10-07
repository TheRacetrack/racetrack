# Quickstart

This tutorial shows how to start a local instance of Racetrack
and how to deploy a sample job there.

## Prerequisites

- Python 3.8+
- [Docker v20.10+](https://docs.docker.com/engine/install/ubuntu/)
  managed by a [non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)

## 1. Setting up local Racetrack

Clone and setup racetrack repository:
```shell
git clone https://github.com/TheRacetrack/racetrack
cd racetrack
make setup # Setup & activate Python venv
. venv/bin/activate
```

Start Racetrack components and wait a while until it's operational:
```shell
make up
```

Install `racetrack` CLI client:
```
pip3 install --upgrade racetrack-client
```

Then, log in to Racetrack as "admin" prior to do authorized operations:
```
racetrack login http://localhost:7102 eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI
```

Install Python job type in your Racetrack:
```
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type http://localhost:7102
```

Racetrack is now ready to accept `python3` jobs.

## 2. Deploying a Job

Let's create a model which purpose is to add numbers.

```
mkdir -p ../racetrack-sample && cd ../racetrack-sample
```

Create `entrypoint.py` file containing the logic:
```python
class Entrypoint:
    def perform(self, a: float, b: float) -> float:
        """Add numbers"""
        return a + b
```

And a `fatman.yaml` file describing it:

```yaml
name: adder
owner_email: sample@example.com
lang: python3

git:
  remote: https://github.com/TheRacetrack/racetrack

python:
  entrypoint_path: 'entrypoint.py'
  entrypoint_class: 'Entrypoint'
```

Finally, submit your job to Racetrack:
```
racetrack deploy . http://localhost:7102 --context-local
```

This will convert your source code to a REST microservice workload, called "Fatman".

## 3. Calling a fatman

You can find your application on the Racetrack Dashboard,
which is available at [http://localhost:7103/dashboard](http://localhost:7103/dashboard)
(use default login `admin` with password `admin`).

Also, you should get the link to your Fatman from the `racetrack-client` output.
Check it out at [http://localhost:7105/pub/fatman/adder/0.0.1](http://localhost:7105/pub/fatman/adder/0.0.1).

This opens a SwaggerUI page, from which you can call your function (`/perform` endpoint).
You can do it from CLI with an HTTP client as well:
```shell
curl -X POST "http://localhost:7105/pub/fatman/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
  -d '{"a": 40, "b": 2}'
# Expect: 42
```

## 4. Clean up

Tear down all the components:
```shell
cd ../racetrack && make down
```

## All in one script

```shell
# Clone and setup racetrack repository
git clone https://github.com/TheRacetrack/racetrack
cd racetrack
make setup
. venv/bin/activate

# Start Racetrack components
make up
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

# Deploy Job to create a Fatman
racetrack deploy . http://localhost:7102 --context-local

# Call your application
curl -X POST "http://localhost:7105/pub/fatman/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
  -d '{"a": 40, "b": 2}'
# Expect: 42

# Clean up
cd ../racetrack && make down
```
