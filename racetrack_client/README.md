# Racetrack CLI client
`racetrack-client` is a CLI client tool for deploying and managing workloads in Racetrack.

Racetrack system allows to deploy jobs in a one step.
It transforms your code to in-operation workloads, e.g. Kubernetes workloads.
You write some code according to a set of coventions, you include the manifest file which explains the code, 
and you submit it to Racetrack. A short while after, the service calling your code is in operation.

## Quickstart
```shell
# Install racetrack-client
python3 -m pip install --upgrade racetrack-client

# Set current remote
racetrack set remote https://racetrack.platform.example.com

# Log in
racetrack login T0k3n.g0es.H3r3

# Deploy a Job
racetrack deploy
```

## Installation
Install racetrack-client using pip:
```shell
python3 -m pip install --upgrade racetrack-client
```

Python 3.8 (or higher) is required.

This will install `racetrack` CLI tool. Verify installation by running `racetrack` command.

## Usage
Run `racetrack --help` to see usage.

### Adding a remote
Assuming your Racetrack server is running on https://racetrack.platform.example.com/lifecycle,
you can add this remote as an alias:
```shell
racetrack set alias my-dev https://racetrack.platform.example.com/lifecycle
```

Alias is a short, friendly name for the URL of your Racetrack server, which is also known as "remote".
From now on, you can refer to your remote with an alias.

### Switching remotes
Set your current remote with:
```shell
racetrack set remote my-dev
```
This will set up a "remote" context for later use.

### Logging in
Log in to Racetrack with your user account (you can get your token from the Dashboard's profile page):
```shell
racetrack login T0k3n.g0es.H3r3
```

In case you're going to use a private repository, provide your git credentials so the job can be built from your code:
```shell
racetrack set credentials https://github.com/YourUser/YourRepository USERNAME TOKEN
```

### Installing plugins
Extend Racetrack's possibilities by installing a bunch of plugins:
```shell
# This plugin allows you to deploy jobs written in Python
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type

# This plugin allows you to deploy jobs to a local Docker infrastructure
racetrack plugin install github.com/TheRacetrack/plugin-docker-infrastructure
```

Plugins can only be installed by admin users.

### Deploying a job
When your code is ready and you pushed your changes to a repository, it's time to deploy it;
that means, upload it to Racetrack so it can become a proper running Job.

To deploy a job, just run it in the place where `job.yaml` is located:
```shell
cd MuffinDestroyer
racetrack deploy 
```

You will see the URL of your deployed job in the output.

### Listing jobs
You can see the list of all deployed jobs with a command:
```shell
racetrack list
```

### Checking runtime logs
Check the logs of a running job by means of:
```shell
racetrack logs MuffinDestroyer
```

### Deleting a job
Delete your running job with:
```shell
racetrack delete MuffinDestroyer
```
