# Racetrack client context
`racetrack-client` is a CLI client tool for deploying workloads to Racetrack.

Racetrack system allows to deploy jobs in a one step.
It transforms your code to in-operation workloads, e.g. Kubernetes workloads.
You write some code according to a set of coventions, you include the manifest file which explains the code, 
and you submit it to Racetrack. A short while after, the service calling your code is in operation.

# Quickstart
1. [Install](#installation) `racetrack` client: `pip3 install racetrack-client`
1. [Configure access token](#private-job-repositories) to your git repository: `racetrack config credentials set REPO_URL USERNAME TOKEN`
1. [Deploy](#deploying) your job to Racetrack: `racetrack deploy . https://racetrack.platform.example.com/lifecycle`
1. You will see the URL of your deployed job in the output.

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
racetrack deploy . https://racetrack.platform.example.com/lifecycle
```

`racetrack deploy [WORKDIR] [RACETRACK_URL]` has 2 optional arguments:
- `WORKDIR` - a place where the `fatman.yaml` is, by default it's current directory
- `RACETRACK_URL` - URL address to Racetrack server, where a job should be deployed. 
  If not given, it will be deployed to a URL configured in a local client config, 
  by default it's set to a local cluster at `http://localhost:7002`.
