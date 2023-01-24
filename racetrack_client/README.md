# Racetrack client context
`racetrack-client` is a CLI client tool for deploying workloads to Racetrack.

Racetrack system allows to deploy jobs in a one step.
It transforms your code to in-operation workloads, e.g. Kubernetes workloads.
You write some code according to a set of coventions, you include the manifest file which explains the code, 
and you submit it to Racetrack. A short while after, the service calling your code is in operation.

# Installation
Install racetrack-client using pip:
```bash
pip3 install racetrack-client
```

Python 3.8+ is required. So if you have any troubles, try with:
```
sudo apt install python3.8 python3.8-dev python3.8-venv
python3.8 -m pip install racetrack-client
```

This will install `racetrack` CLI tool. Verify installation by running `racetrack`.

# Usage
Run `racetrack --help` to see usage.

## Deploying
To deploy a job, just run in the place where `fatman.yaml` is located:
```bash
racetrack deploy . --remote https://racetrack.platform.example.com/lifecycle
```
