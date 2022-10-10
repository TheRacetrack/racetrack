# Quickstart

This tutorial shows how to start a local instance of Racetrack
and how to deploy a sample job there.

## Prerequisites

- Python 3.8+
- [Docker v20.10+](https://docs.docker.com/engine/install/ubuntu/)
  managed by a [non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)

## 1. Setting up local environment (optional)
For your convenience use virtual environment:
```shell
mkdir -p racetrack && cd racetrack
python3 -m venv venv
. venv/bin/activate
```

## 2. Setting up local Racetrack

Start Racetrack components:
```shell
curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/quickstart-up.sh | bash -s
```

Racetrack is now ready to accept `python3` jobs at [localhost:7102](http://localhost:7102).

## 3. Installing Racetrack client

Install `racetrack` CLI client:
```
pip3 install --upgrade racetrack-client
```

## 2. Deploying a Job

Let's create a model which purpose is to add numbers.

Create `sample/entrypoint.py` file containing the logic:
```python
class Entrypoint:
    def perform(self, a: float, b: float) -> float:
        """Add numbers"""
        return a + b
```

And a `sample/fatman.yaml` file describing what's inside:

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
```shell
racetrack deploy sample http://localhost:7102 --context-local
```

This will convert your source code to a REST microservice workload, called "Fatman".

## 3. Calling a fatman

You can find your application on the Racetrack Dashboard,
which is available at [http://localhost:7103/dashboard](http://localhost:7103/dashboard)
(use default login `admin` with password `admin`).

Also, you should get the link to your Fatman from the `racetrack-client` output.
Check it out at [http://localhost:7105/pub/fatman/adder/0.0.1](http://localhost:7105/pub/fatman/adder/0.0.1).

This opens a SwaggerUI page, from which you can call your function
(try `/perform` endpoint with `{"a": 40, "b": 2}` body).
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
curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/quickstart-down.sh | bash -s
```
