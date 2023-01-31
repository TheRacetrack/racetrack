# Quickstart

This tutorial shows how to start a local instance of Racetrack
and how to deploy a sample job there.

## Prerequisites

- Python 3.8 (or higher)
- [Docker v20.10 (or higher)](https://docs.docker.com/engine/install/ubuntu/)
  managed by a [non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)
- [Docker Compose plugin](https://docs.docker.com/compose/install/linux/#install-using-the-repository)

## 1. Set up a local environment (optional)
For your convenience use virtual environment:
```shell
mkdir -p racetrack && cd racetrack
python3 -m venv venv
. venv/bin/activate
```

## 2. Set up local Racetrack

Start Racetrack components with an utility script:
```shell
curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/quickstart-up.sh | bash -s
```

Racetrack is now ready to accept `python3` jobs at [localhost:7102](http://localhost:7102).

## 3. Install Racetrack client

Install `racetrack` CLI client:
```
python3 -m pip install --upgrade racetrack-client
```

## 4. Deploy a Job

Let's create a model which purpose is to add numbers.

Create `sample/entrypoint.py` file with your application logic:
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
lang: python3:latest

git:
  remote: https://github.com/TheRacetrack/racetrack

python:
  entrypoint_path: 'entrypoint.py'
  entrypoint_class: 'Entrypoint'
```

Finally, submit your job to Racetrack:
```shell
racetrack deploy sample/ --remote http://localhost:7102
```

This will convert your source code to a REST microservice workload, called "Fatman".

## 5. Call a fatman

You can find your application on the Racetrack Dashboard,
which is available at [http://localhost:7103/dashboard](http://localhost:7103/dashboard)
(use default login `admin` with password `admin`).

Also, you should get the link to your Fatman from the `racetrack` client output.
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

## 6. Clean up

Tear down all the components:
```shell
curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/quickstart-down.sh | bash -s
```
