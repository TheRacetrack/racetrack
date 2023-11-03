# Quickstart

This guide shows how to start a local instance of Racetrack
and how to deploy a sample job there.

## Prerequisites

- Python 3.8 (or higher) - verify with `python3 --version`
- [Docker v20.10 (or higher)](https://docs.docker.com/engine/install/ubuntu/)
  managed by a [non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user) -
  verify with `docker ps && docker --version`
- [Docker Compose plugin](https://docs.docker.com/compose/install/linux/#install-using-the-repository) -
  verify with `docker compose version`
- curl

For instance, on Debian-based systems, it can be installed with:
```sh
sudo apt update && sudo apt install curl python3 python3-pip python3-venv
# Install user-managed docker
curl -fsSL https://get.docker.com -o install-docker.sh
sh install-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

## 1. Install local Racetrack

Pick installation directory:
```shell
mkdir -p racetrack && cd racetrack
```

and install Racetrack components with an [installer script](https://github.com/TheRacetrack/racetrack/blob/master/utils/standalone-wizard/wizard.py):
```shell
sh <(curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/standalone-wizard/runner.sh)
```

Follow the installation steps.
Choose `docker` infrastructure target (default one).
Shortly after, your Racetrack instance will be ready to accept `python3` jobs at [127.0.0.1:7102](http://127.0.0.1:7102).

Pay attention to the output, it contains your unique admin password.

## 2. Install Racetrack client

Install `racetrack` CLI client:
```sh
python3 -m pip install --upgrade racetrack-client
racetrack set remote http://127.0.0.1:7102
racetrack login --username admin # and enter your admin password
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

And a `sample/job.yaml` file describing what's inside:

```yaml
name: adder
owner_email: sample@example.com
jobtype: python3:latest
git:
  remote: https://github.com/TheRacetrack/racetrack
jobtype_extra:
  entrypoint_path: 'entrypoint.py'
  entrypoint_class: 'Entrypoint'
```

Finally, submit your job to Racetrack:
```shell
racetrack deploy sample/
```

This will convert your source code to a REST microservice workload, called "Job".

## 5. Call a Job

You can find your application on the Racetrack Dashboard,
which is available at [http://127.0.0.1:7103/dashboard](http://127.0.0.1:7103/dashboard)
(use login `admin` and password provided by the installer script).

Also, you should get the link to your Job from the `racetrack` client output.
Check it out at [http://127.0.0.1:7105/pub/job/adder/0.0.1](http://127.0.0.1:7105/pub/job/adder/0.0.1).
This opens a SwaggerUI page, from which you can call your function
(try `/perform` endpoint with `{"a": 40, "b": 2}` body).

You can do it from CLI with an HTTP client as well:
```shell
curl -X POST "http://127.0.0.1:7105/pub/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: $(racetrack get auth-token)" \
  -d '{"a": 40, "b": 2}'
# Expect: 42
```

## 6. Clean up

Tear down Racetrack instance using `Makefile` created by the installer script:
```shell
make clean
```

## What's next?

- [User Manual](./user/user-guide-1.md)
- [User Guide - Creating a Job](./user/user-guide-2.md)
- [Local Kubernetes Setup](./deployment/local-kubernetes-setup.md)
- [Available plugins](./user/available-plugins.md)
- [Installation to standalone host](./deployment/standalone-host.md)
