# Installation to standalone host
Standalone Racetrack installer lets you install Racetrack to a standalone host (fresh VM instance, EC2 host, etc.)
using Docker Engine infrastructure.

## Requirements

- Python 3.8+ with `pip` and `venv`
- [Docker v20.10 (or higher)](https://docs.docker.com/engine/install/ubuntu/)
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
Follow the installation steps. Shortly after, your Racetrack instance will be ready.

Pay attention to the output. The installer will generate unique passwords for your setup
and you'll get the Dashboard address and superuser credentials.

## Administering
Take a look at `Makefile` created by the installer. There's a few useful steps:

`make clean` to shut down and clean up the Racetrack.
`make up` to start it up again or upgrade to the latest version.
