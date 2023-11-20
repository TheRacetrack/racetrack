# Local Kubernetes setup

This tutorial deploys Racetrack locally on your computer in a
[KinD](https://kind.sigs.k8s.io/) (a baby Kubernetes for testing) cluster. It is
intended to give you the muscle memory for using a production instance of
Racetrack, and to help you get used to the core Racetrack concepts.

If you want to set up Racetrack on local Docker engine, see [Quickstart](../quickstart.md).

## Prerequisites

1. [Docker v20.10+](https://docs.docker.com/engine/install/ubuntu/)
  managed by a [non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)
2. [Docker Compose plugin](https://docs.docker.com/compose/install/linux/#install-using-the-repository)
3. Python 3.8+ (python3 and python3-venv)
4. [kind](https://kind.sigs.k8s.io/)
5. [Kubectl](https://kubernetes.io/docs/tasks/tools/) (version 1.24.3 or higher)
6. (optional) [k9s](https://github.com/derailed/k9s)

## Installing Racetrack Locally

Fetch the Racetrack sources:

```shell
git clone https://github.com/TheRacetrack/racetrack.git
```

Execute the following:

```shell
# Enter the source root
cd racetrack
# install the command line client
make setup
# Activate Python virtual environment
. venv/bin/activate
# Install racetrack CLI
python3 -m pip install --upgrade racetrack-client
# Deploy the KinD cluster and install Racetrack in it
make kind-up
```

After a period ranging between 30-50 years, KinD will be up and running and
Racetrack will be deployed inside it.

You are ready to deploy a sample application to it.

## Submitting a Python Class

The source code ships with a range of sample Jobs; you can find them in the path
`sample/`. In this tutorial, we will be Submitting the `sample/python-class`
Job.

```shell
# Set the current Racetrack's remote address - localhost inside KinD, listening on port 7002
racetrack set remote http://127.0.0.1:7002
# Login to Racetrack prior to deploying a job (with a dev token)
racetrack login eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI
# Install python3 job type in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
# Install kubernetes infrastructure target in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
# go to the sample directory
cd sample/python-class/
# deploy from the current directory to the Racetrack service
racetrack deploy
```

After a pretty short time, the `racetrack` command will exit successfully and let you
know the Job is deployed, giving you the URL.
Before opening this URL, open [Dashboard page](http://127.0.0.1:7003/dashboard/)
and log in with default `admin` username and `admin` password.
That will set up a session cookie allowing you to access Jobs through your browser.

The code in the [sample/python-class/adder.py](../../sample/python-class/adder.py)
module has been converted by Racetrack into a
fully functional and well-formed Kubernetes micro-service; our Job. Please
examine this file [sample/python-class/adder.py](../../sample/python-class/adder.py) 
in order to understand what to expect.

## Testing the Resulting Job

You now have the following running on your developer workstation:

1. A KinD cluster
2. Racetrack deployed inside it
3. A Python 3 micro-service converted to a Job, running inside this Racetrack

There are several ways you can interact with Racetrack and this Job:

### Calling the Job

The function in `adder.py` now hangs off an HTTP endpoint, and can be used as a
ReST service. You can use `curl` to test this:

```shell
curl -X POST "$(racetrack get pub)/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: $(racetrack get auth-token)" \
  -d '{"numbers": [40, 2]}'
# Expect: 42
```

### Checking the Job Swagger

Racetrack generates free [Swagger API documentation](https://swagger.io/). You
can access it in your web browser
[here](http://127.0.0.1:7005/pub/job/adder/latest), 
but first you need to authenticate in order to make requests through your browser.
Open [Dashboard page](http://127.0.0.1:7003/dashboard/) and log in with default `admin` username and `admin` password.
That will set up a session cookie allowing you to call Jobs.

### Checking the Job Health

You also get a free [service health
endpoint](https://kubernetes.io/docs/reference/using-api/health-checks/):

```shell
curl "$(racetrack get pub)/job/adder/latest/health"
# Expect:
# {"service": "job", "job_name": "adder", "status": "pass"}
```

### Checking Job logs

To see recent logs from your Job output, run `racetrack logs` command:
```shell
racetrack logs adder
```

`racetrack logs [NAME]` has 1 argument `NAME` (name of the job) and a couple of options:

- `--version VERSION` - version of the job, default is the latest one
- `--remote REMOTE` - Racetrack server's URL or alias name.
- `--tail LINES` - number of recent lines to show, default is 20.
- `--follow` or `-f` - follow logs output stream

### Inspecting the Job in the Racetrack Dashboard

Racetrack ships with a dashboard. In production, it will be the admin who has
access to this, but you're testing locally, so you can see it
[here](http://127.0.0.1:7003/dashboard) and you can see your adder job.

### (optional) Inspecting the Job inside KinD Using k9s

Invoke k9s on your command line and navigate to the pods view using `:pods`. Hit
`0` to display all Kubernetes namespaces. Under the `racetrack` namespace, you
should see `job-adder-v-0-0-2`.

## Authentication

Racetrack requires you to authenticate with a token.
To manage users and tokens, visit [Racetrack dashboard page](http://127.0.0.1:7003/dashboard/).
Default super-user is `admin` with password `admin`.
Once the Racetrack is started, it is recommended to create other users, and deactivate default `admin` user for security purposes.

Then visit your Profile page to see your auth token.

Authentication applies to both deploying a Job and calling it:

- In order to deploy a Job (or use other management commands), run `racetrack login` command with your token in first place. For instance:
  ```shell
  racetrack login eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI --remote http://127.0.0.1:7002
  ```
- In order to call a Job (fetch results from it), include your token in `X-Racetrack-Auth` header. For instance:
  ```shell
  curl -X POST "$(racetrack get pub)/job/adder/latest/api/v1/perform" \
    -H "Content-Type: application/json" \
    -H "X-Racetrack-Auth: $(racetrack get auth-token)" \
    -d '{"numbers": [40, 2]}'
  ```

## Tearing it Down

Assuming you are standing in the root directory of the Racetrack source code:

```shell
# kill KinD and what it contains
make kind-down
# stop and remove the local testing docker registry
docker stop racetrack-registry && docker rm -v racetrack-registry
# exit the Python venv
deactivate
# optionally, clean up
git clean -fxd
```

## Troubleshooting
If you have problems running Racetrack locally, please do the following:

```shell
make clean
rm -rf venv
make setup
source venv/bin/activate
docker system prune -a
make kind-up
# Wait 10 minutes
make kind-test
racetrack set remote http://127.0.0.1:7002
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
racetrack deploy sample/python-class
```

If it doesn't work, diagnostic commands:

- `kubectl get pods` - do everything has "Running" status? If not, view logs of 
  that pod (i.e. `kubectl logs <failing_pod_name>`)
- look into `kubectl logs service/lifecycle`
- Can you access the server at [http://127.0.0.1:7002](http://127.0.0.1:7002/) (in browser)?
- `netstat -tuanpl | grep 7002` - is the port blocked by something?

## FAQ
### I want to build on an ARM system (such as M1 Mac)

Disclaimer: we don't officially support or test for those architectures, but after
little tweaking you should be still able to run on them. 

To build on an ARM system, you need to add the docker arm64 repositories to the 
image_builder and lifecycle Dockerfiles so apt-get can find the docker tools for amd64. 
You can do so by applying the following diff (save it in repo root and `git apply arm64_enable.diff`):
<details>
  <summary>File `arm64_enable.diff`</summary>
    
    ```diff
    diff --git a/image_builder/Dockerfile b/image_builder/Dockerfile
    index 4dddd57..110564e 100644
    --- a/image_builder/Dockerfile
    +++ b/image_builder/Dockerfile
    @@ -11,6 +11,9 @@ RUN apt-get update -y && apt-get install -y \
     RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg &&\
         echo \
       "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    +  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null &&\
    +    echo \
    +  "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
       $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null &&\
         apt-get update -y && apt-get install -y docker-ce-cli

    diff --git a/lifecycle/Dockerfile b/lifecycle/Dockerfile
    index 2063911..a2e196d 100644
    --- a/lifecycle/Dockerfile
    +++ b/lifecycle/Dockerfile
    @@ -11,6 +11,9 @@ RUN apt-get update -y && apt-get install -y \
     RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg &&\
         echo \
       "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    +  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null &&\
    +    echo \
    +  "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
       $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null &&\
         apt-get update -y && apt-get install -y docker-ce-cli
    ```
</details>
