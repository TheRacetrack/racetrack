# Prerequisites

Install:

- Python 3.8+ (`sudo apt install python3.8 python3.8-dev python3.8-venv` on Ubuntu 18+)
- [Docker v20.10+](https://docs.docker.com/engine/install/ubuntu/)
- [kubectl v1.24.3+](https://kubernetes.io/docs/tasks/tools/#kubectl) - if you're going to deploy to Kind
- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) - if you're going to deploy to Kind
- [Go 1.16+](https://go.dev/doc/install) - if you're going to develop components in Go (PUB, go_wrapper)

# Development Setup

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

Then, you can visit http://localhost:7103 to see the Racetrack Dashboard (default user/password: admin/admin).

Lifecycle server runs on http://localhost:7102 (it's the URL you deploy your jobs there).
Let's create a "dev" alias for it:
```bash
racetrack config alias set dev http://localhost:7102
```

Login to Racetrack prior to deploying a job (you can find it in the "Profile" tab of the Dashboard):
```bash
racetrack login dev eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0._XIg7ainazrLnU6-4pJ1BW63vPpgtX41O2RhxshW-E0
```

Finally, you can deploy some jobs there, eg.:
```bash
racetrack deploy sample/python-class dev
```

After all, run `make clean` to dismantle the local instance.

## Components Diagram

![Components Diagram](../assets/racetrack-components.drawio.png)

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
- pub - use `make send-payload-post` for testing the proxying of payload to Fatman
- dashboard - it will print out on which port a Django UI is available
- fatman_wrapper - Call `fatman_wrapper run adder.py` in `sample/python-class/`
  to just test a Python class wrapper.

Submitting a job:

```bash
racetrack deploy sample/python-class/ http://localhost:7202
# or: cd racetrack_client && make deploy-sample
```

New container should be created. It can be accessed at http://localhost:7000
You need to `docker rm` or `make docker-clean-fatman` to clean leftover fatman on your own.
In case of errors, troubleshoot with `docker ps` and `docker logs -f <fatman-name>`.

Fatman can be accessed through the PUB at http://localhost:7205/pub/fatman/adder/latest,
where "adder" is a name of a job from `fatman.yaml`.

## Docker compose

Fatmen can also run as local docker containers. 

- `make compose-up` - runs services in detached mode
- `make compose-up-service service=dashboard` - rebuilds and reruns one selected service
- `make compose-run` - runs services with logs 
- `make compose-down` to clean up the setup

Submitting a job:

```bash
racetrack deploy sample/python-class/ http://localhost:7102
# or: compose-deploy-sample
```

Fatman management/access is the same as in **Localhost** case.

## Kind

A Kubernetes cluster in a Docker container. `make kind-up` to set it up,
`make kind-down` to tear down. After applying some changes, redeploy using `make kind-redeploy`.

Submitting a job:

```bash
racetrack deploy sample/python-class/ http://localhost:7002
# or make kind-deploy-sample
```

Fatmen are deployed as k8s pods, and should be managed as such.

## Dashboard

- Racetrack admin panel is at: http://localhost:7002/lifecycle/admin/
  (user/password: admin)
- Racetrack dashboard (for public consumption) is at: http://localhost:7003/dashboard/
  
(ports might need to be adjusted according to below table)

## Port numbers

| service       | kind/Kubernetes (X) | docker-compose (X+100) | localhost (X+200) |
| -------       | ---------------     | --------------         | ---------         |
| Lifecycle     | 7002                | 7102                   | 7202              |
| Image Builder | 7001                | 7101                   | 7201              |
| Dashboard     | 7003                | 7103                   | 7203              |
| Fatman        | 7000                | 7100                   | 7200              |
| PUB           | 7005                | 7105                   | 7205              |
| postgres      | 5432                | 5532                   | --- (1)           |

(1) - none as Postgres is not run on localhost

# Calling a model

On any of localhost setups:

```bash
curl -X POST "http://localhost:7005/pub/fatman/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{"numbers": [40, 2]}'
# Expect: 42
```

The 7005 port needs to be adjusted according to dev setup, as in table above.

Calling model on remote Racetrack instance:

```bash
curl -k -X POST "https://<cluster ip>/pub/fatman/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -d '{"numbers": [40, 2]}'
# Expect: 42
```

# Deploy Job to Kubernetes

Enter directory with `fatman.yaml` and issue:

```
racetrack deploy . https://racetrack.<cluster name>/lifecycle
```

See [User Guide](./docs/user-guide.md) for more details on how to deploy a job
to the Racetrack instance running on Kubernetes as an end user.

# Testing

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

# Debugging

In order to view Lifecycle Postgres db, in k8s dashboard exec into postgres pod and:
```
psql -h localhost -d lifecycle_db -U racetrack -p 5432
```

# Deployment


## Versioning

For docker tags on master and release branches (like `cluster-test`, `cluster-preprod` etc),
we use `<semver>` versioning. Examples: `0.0.15`, `1.0.3`.
Versions are bumped only when the new codebase has been tested, and images aren't overridden.

For avoiding docker tag conflicts in dev branches (like `cluster-dev`, `cluster-dev2`)
we extend this format to `<semver>-<MR-number>-<dev-version>`
where MR-number stands for gitlab MR number, and dev-version is just sequentially increasing number.
Examples: `0.0.15-125-1`, `1.0.3-142-11`.


## Release new changes of Racetrack to test or dev Cluster

Do the following in order to apply your changes to your cluster:

In racetrack repository:

1. Increment version `make version-bump MR=123`, where `123` is the id of your merge request.
1. Build & push docker images by running: `make version-release`.

In racetrack-config repository:

1. Checkout to a branch related with your cluster.
1. If new version involves changes in kustomize files, reset repository to corresponding branch.
1. Run `make version-pick VERSION=x.y.z` with `x.y.z` being the version you just bumped.
1. Commit & push to trigger redeployment in Kubernetes.

You don't need to specify MR id for futher dev releases, because `make version-bump` 
will bump the dev part if MR is set in file, otherwise it bumps just the semver part.


## Releasing new Racetrack version

1. Make sure [changelog](../CHANGELOG.md) has all additions and changes
1. Determine new version number `x.y.z` according to [Semver](https://semver.org/) and latest changes. (`VERSION=x.y.z`)
1. In changelog rename section "Unreleased" to `x.y.z` and add date, then
   add a new empty "Unreleased" section 
1. Create release branch ie. `release-x.y.z`: `git checkout -b release-$VERSION`
1. Increment version with:
  - `make version-bump` to bump patch version, 
  - `make version-bump-minor` to bump minor version,
  - or `make version-bump-major` to bump major version.
1. Commit and push all changes from previous points: `git commit -am "Release version $VERSION"`
1. Merge `release-x.y.z` branch to `master`: `git checkout master && git merge release-$VERSION && git push`
1. Tag the resulting commit and push tag: `git tag $VERSION && git push origin $VERSION`
1. Build & push docker images by running: `make version-release`
1. Release racetrack client (if needed) with `(cd racetrack_client && make release-pypi)`
