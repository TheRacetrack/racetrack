# Standalone Racetrack installer
Standalone Racetrack installer allows you to install Racetrack to fresh VM instance
using local Docker Engine.

## Requirements

- python3
- python3-pip
- python3 venv
- docker (managed by non-root user)
- docker compose
- curl

On Debian-based systems do:
```sh
sudo apt update && sudo apt install curl python3 python3-pip python3-venv

curl -fsSL https://get.docker.com -o install-docker.sh
sh install-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

## Install Racetrack
```sh
mkdir -p ~/racetrack && cd ~/racetrack
sh <(curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/308-provide-instructions-on-how-to-install-racetrack-to-a-vm-instance/utils/standalone-wizard/runner.sh)
```
