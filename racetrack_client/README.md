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

Alternatively, command `racetrack login --username ADMIN` allows you to log in with your username and password and saves the auth token without having to visit the Dashboard page.

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

### Extra vars
Manifest values can be overriden with key-value pairs coming from a command line.
It doesn't modify actual file, but its one-time, in-memory version before submitting it.
Racetrack client has `--extra-vars KEY=VALUE` parameter (or `-e` in short)
that overwrites values found in YAML manifest.

- `KEY` is the name of field and it can contain dots to refer to a nested field, for example `git.branch=master`
- `VALUE` can be any YAML or JSON object.

Extra vars parameters can be used multiple times in one command.

Example:
```shell
racetrack deploy -e secret_runtime_env_file=.env.local -e git.branch=$(git rev-parse --abbrev-ref HEAD)
```

It makes CLI commands more script-friendly, so you can overwrite manifest without tracking changes in job.yaml file.  
Tip: Use `racetrack validate` command beforehand to make sure your final manifest is what you expected.

### Getting auth token
Command `racetrack get auth-token` prints out current auth token.
It can be used in CLI scripts: `curl -H "X-Racetrack-Auth: $(racetrack get auth-token)"`
