# Installation to standalone host
You can install Racetrack to a standalone host (e.g. EC2 host or fresh VM instance)
using the installer script that runs it on the Docker Engine infrastructure.

## Requirements

- Python 3.8+ with `pip` and `venv`
- [Docker v20.10 (or higher)](https://docs.docker.com/engine/install/)
  managed by a [non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)
- [Docker Compose plugin](https://docs.docker.com/compose/install/linux/#install-using-the-repository)
- curl

For instance, on Debian-based systems do:
```sh
sudo apt update && sudo apt install curl python3 python3-pip python3-venv
# Install user-managed docker
curl -fsSL https://get.docker.com -o install-docker.sh
sh install-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

## Install Racetrack
Pick an installation directory:
```sh
mkdir -p ~/racetrack && cd ~/racetrack
```
and run
```sh
sh <(curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/standalone-wizard/runner.sh)
```
Follow the installation steps. Choose `docker` infrastructure target.
Shortly after, your Racetrack instance will be ready.

### Notes

- Pay attention to the output. The installer will generate unique passwords for your setup,
  you'll be provided with the Dashboard address and superuser credentials.
- Set the environment variable `export RT_NON_INTERACTIVE=1`
  to skip answering installer's questions and go with the defaults.
  You can also set custom values for parameters by setting environment variables:

    - `export RT_EXTERNAL_ADDRESS="http://127.0.0.1"` to set the external address that your Racetrack will be accessed at (IP or domain name).
    - `export RT_INFRASTRUCTURE="docker"` to set the infrastructure target to deploy Racetrack.

- Edit or remove local setup configuration at `setup.json`
  and run installer again to reconfigure installation steps.
- You can use locally installed `racetrack` CLI client after activating venv `. venv/bin/activate`.
  It's already logged in and has remote address configured.

-   The following services are hosted on address `0.0.0.0`, thus publicly available:

    - Dashboard on port `7103`
    - Lifecycle on port `7102`
    - Pub on port `7105`
    - Lifecycle Supervisor on port `7106`
    - Grafana on port `3100`

    Jobs and other services should be running only in the internal network.

- This installer makes use of [Docker Infrastructure plugin](https://github.com/TheRacetrack/plugin-docker-infrastructure)
  to deploy jobs to in-place Docker Engine infrastructure target.

## Manage Racetrack
Installer creates `Makefile`, which contains a few useful commands:

- `make down` to stop the Racetrack.
- `make up` to start it up again or upgrade to the latest version.
- `make clean` to shut down and clean up the Racetrack.
