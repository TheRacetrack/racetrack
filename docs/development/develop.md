# Developer Manual

## Components Diagram

[![Components Diagram](../assets/racetrack-components.drawio.png)](../assets/racetrack-components.drawio.png)

## Prerequisites

Install:

- Python 3.8+ (`sudo apt install python3.8 python3.8-dev python3.8-venv` on Ubuntu 18+)
- [Docker v20.10+](https://docs.docker.com/engine/install/ubuntu/)
- [kubectl v1.24.3+](https://kubernetes.io/docs/tasks/tools/#kubectl) - if you're going to deploy to Kind
- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) - if you're going to deploy to Kind
- [Go 1.19+](https://go.dev/doc/install) - if you're going to develop components in Go (PUB, go_wrapper)
- [nvm](https://github.com/nvm-sh/nvm) - if you're going to rebuild Dashboard front-end

## Development Setup

Setup & activate Python venv (this is required for all next steps):

```bash
# in a project-root directory
make setup
. venv/bin/activate
```

Components can be run in 3 different ways, every next way is more integrated and
closer to target setup, but it boots up longer:

- [Localhost](#localhost)
- [Docker compose](#docker-compose)
- [Kind](#kind)

## Quickstart

If you're new to Racetrack, you can just run the following command to launch a local Racetrack instance relatively quickly:
```bash
make compose-up
```

Then, you can visit http://127.0.0.1:7103 to see the Racetrack Dashboard (default user/password: admin/admin).

Lifecycle server runs on http://127.0.0.1:7102 (it's the URL you deploy your jobs there).
Let's create a "dev" alias for it and set it as a current remote:
```bash
racetrack set alias dev http://127.0.0.1:7102
racetrack set remote dev
```

Login to Racetrack prior to deploying a job (you can find it in the "Profile" tab of the Dashboard):
```bash
racetrack login eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI
```

Activate `python3` job type in the Racetrack by installing the plugin:
```bash
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
```

Finally, you can deploy some jobs there, eg.:
```bash
racetrack deploy sample/python-class
```

After all, run `make clean` to dismantle the local instance.

## Localhost

Single components running on localhost (outside docker), independently of the others.
Best for developing/debugging single component, as changes can be most quickly
tested. 

Each component supports `make run` for directly running it, ie.

```bash
cd lifecycle && make run
```

Notes:

- image_builder - Call `image_builder build` in `sample/python-class/` to
   test just building a job image.
- pub - use `make send-payload-post` for testing the proxying of payload to Job
- dashboard - it will print out on which port a Django UI is available
- job_wrapper - Call `job_wrapper run adder.py` in `sample/python-class/`
  to just test a Python class wrapper.

Submitting a job:

```bash
racetrack deploy sample/python-class/ --remote http://127.0.0.1:7202
```

New container should be created. It can be accessed at http://127.0.0.1:7000
You need to `docker rm` or `make docker-clean-job` to clean leftover job on your own.
In case of errors, troubleshoot with `docker ps` and `docker logs -f <job_name>`.

Job can be accessed through the PUB at http://127.0.0.1:7205/pub/job/adder/latest,
where "adder" is a name of a job from `job.yaml`.

## Docker compose

Jobs can also run as local docker containers. 

- `make compose-up` - runs services in detached mode
- `make compose-up-service service=dashboard` - rebuilds and reruns one selected service
- `make compose-run` - runs services with logs 
- `make compose-down` to clean up the setup

Submitting a job:

```bash
racetrack deploy sample/python-class/ --remote http://127.0.0.1:7102
# or: compose-deploy-sample
```

Job management/access is the same as in **Localhost** case.

## Kind

A Kubernetes cluster in a Docker container. `make kind-up` to set it up,
`make kind-down` to tear down. After applying some changes, redeploy using `make kind-redeploy`.

Submitting a job:

```bash
racetrack deploy sample/python-class/ --remote http://127.0.0.1:7002
# or make kind-deploy-sample
```

Jobs are deployed as k8s pods, and should be managed as such.

## Dashboard

- Racetrack admin panel is at: http://127.0.0.1:7002/lifecycle/admin/
  (user/password: admin)
- Racetrack dashboard (for public consumption) is at: http://127.0.0.1:7003/dashboard/
  
(ports might need to be adjusted according to below table)

## Port numbers

| service              | kind/Kubernetes (X) | docker-compose (X+100) | localhost (X+200) |
|----------------------|---------------------|------------------------|-------------------|
| Lifecycle            | 7002                | 7102                   | 7202              |
| Image Builder        | 7001                | 7101                   | 7201              |
| Dashboard            | 7003                | 7103                   | 7203              |
| Job                  | 7000                | 7100                   | 7200              |
| PUB                  | 7005                | 7105                   | 7205              |
| Lifecycle Supervisor | 7006                | 7106                   | 7202              |
| postgres             | 5432                | 5532                   | --- (1)           |
| Prometheus           | 9090                | 9192                   |                   |
| Grafana              | 3000                | 3100                   |                   |

(1) - none as Postgres is not run on localhost

## Calling a model

On any of localhost setups:

```bash
curl -X POST "http://127.0.0.1:7005/pub/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{"numbers": [40, 2]}'
# Expect: 42
```

The 7005 port needs to be adjusted according to dev setup, as in table above.

Calling model on remote Racetrack instance:

```bash
curl -k -X POST "https://<cluster ip>/pub/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{"numbers": [40, 2]}'
# Expect: 42
```

## Deploy Job to Kubernetes

Enter directory with `job.yaml` and issue:

```
racetrack deploy . --remote https://racetrack.<cluster name>/lifecycle
```

See [User Guide](../user.md) for more details on how to deploy a job
to the Racetrack instance running on Kubernetes as an end user.

## Testing

Run the following command to perform all tests (unit tests and End-to-End):

```bash
make kind-up test clean
```

You can also run E2E tests on docker-compose setup:

```bash
make compose-up compose-test clean
```

Run unit tests only:

```bash
make test-unit
```

## Debugging

In order to view Lifecycle Postgres db, in k8s dashboard exec into postgres pod and:
```
psql -h 127.0.0.1 -d racetrack -U racetrack -p 5432
```
