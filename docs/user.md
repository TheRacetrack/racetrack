# Table of Contents

1. [Introduction](#intro)
    1. [What is Racetrack?](#whatisrt)
    1. [Architecture and Terminology](#archterm)
    1. [Conventions](#conventions)
    1. [The Manifest](#manifest)
    1. [Submitting a Job](#submitting)
1. [The Racetrack Workflow](#workflow)
1. [Tutorial](#tut)
    1. [Prerequisites](#tut-prereq)
    1. [Installing Racetrack Locally](#tut-install)
    1. [Submitting a Python Class](#tut-submit)
    1. [Testing the Resulting Job](#tut-test)
        1. [Using the Job](#tut-test-foo)
        1. [Checking the Job Swagger](#tut-test-swagger)
        1. [Checking the Job Health](#tut-test-health)
        1. [Checking Job logs](#tut-logs)
        1. [Inspecting the Job in the Racetrack Dashboard](#tut-test-dashb)
        1. [(optional) Inspecting the Job inside KinD Using k9s](#tut-test-k9s)
    1. [Authentication](#tut-auth)
    1. [Tearing it down](#tut-teardown)
1. [Developing Your Own Jobs](#developing)
    1. [Using a Production Racetrack](#in-prod)
        1. [Authentication](#racetrack-authentication)
    1. [Jobs in Private or Protected git Repositories](#repo-tokens)
    1. [Setting aliases for Racetrack servers](#config-aliases)
    1. [The Job Manifest File](#manifest-deep)
    1. [The Job Types](#job-types)
1. [Guidelines](#guide)
1. [FAQ](#faq)


## Introduction<a name="intro"></a>

![Racetrack architecture for civilians](assets/arch-00.png)

### What is Racetrack?<a name="whatisrt"></a>

Racetrack is a system which transforms your code to in-operation workloads, e.g.
Kubernetes workloads.

You write your code - say for a ML model or micro-service - in a specific style,
you hand it over to Racetrack, and a minute later it is in production.

Out of the box, Racetrack allows you to use several languages and frameworks:

* Standard Python 3
* A specialized Scikit Learn format
* Golang services
* And for exotic edge cases, any Dockerfile-wrapped code

Racetrack can be extended to introduce new languages and frameworks.

### Architecture and Terminology<a name="archterm"></a>

The following terms recur through this document and describe the elements and
actions involved in using Racetrack:

* Job: your code, written in the style required by Racetrack
* Job Type: which of the languages and frameworks supported by Racetrack you
  choose to develop your job in
* Job submission: when you're happy with your code, and you push it to Racetrack
  to be deployed
* Job: when a job is submitted to Racetrack, Racetrack converts it to a
  workload and deploys it. This workload is called a Job
* Convention: when you pick your Job Type, you will be asked to follow a specific
  style for that type which Racetrack understands; that style is a Convention
* Manifest: a YAML file in the root of your Job, which specifies the job type
  and provides configuration values for your Job according to that Job Type

To tie all of these terms together:

> As a data scientist, I selected the Python 3 **Job Type** to develop my ML
> model **Job** in. I wrote my Job according to the Job Type **convention**. I
> composed a **Manifest** in which I specified the Job Type I used, and in it I
> tweaked a few specific parameters for this Job Type. I **submitted** the job
> to Racetrack, after which it was deployed as a **Job**.

### Conventions<a name="conventions"></a>

For Racetrack to convert your Job to a Job, you have to follow a specific
style for your Job Type: a Convention. Broadly speaking, the purpose of this
convention is to guide Racetrack:

> "Look Racetrack! Right *here* is the method to query my model; and right
> *here* is the method for retraining."

You write some code according to a set of conventions, submit it to Racetrack,
and a short while after, your code is in operation. This convention is a key
aspect of Racetrack: you can think of it as a "way the code should look" for
Racetrack to understand it and deploy it to production.

You can browse the documentation for the supported Job Types in the
`docs/job_types/` directory. In there, the Convention for each Job Type is
described.

Conventions for any Job Type are simple, easy to follow, and very few. Some
examples are:

* For the Python 3 Job Type, you must have a `Class JobEntrypoint` with a
  method `perform()` for the Python 3 function which receives input and gives
  output (e.g. receiving a vector, and returning it normalized). Racetrack will
  then know to wrap this in a HTTP server and expose it.
* For the golang Job Type, your main function must have the following signature:
  `func Perform(args []interface{}, kwargs map[string]interface{}) (interface{},
  error)`.

As a concrete example, if you have written a clever Python 3 function which adds
two integers and returns the result, your code pre-Racetrack would look like
this:

```python
# file: model.py
def AddEmUp(x, y):
    z = x + y
	return z
```

And refactored to meet the Racetrack Python 3 Job Type Convention:

```python
# file: job_entrypoint.py
class JobEntrypoint:
	def perform(self, x, y):
		return AddEmUp(x, y)

def AddEmUp(x, y):
    z = x + y
	return z
```

### The Manifest<a name="manifest"></a>

Having picked our Job Type and followed its Convention, the only thing we're
missing is to inform Racetrack what Job Type we're submitting, and apply any
special configuration supported by that Job Type. We do this by creating a file
named `job.yaml` in the root directory of our Job source tree.

This file is YAML formatted. The documentation for each Job Type describes how
it should be formed.

A typical `job.yaml` will look like this:

```yaml
name: my_fantabulous_skynet_AI
owner_email: nobody@example.com
jobtype: python3:latest  # this would be your Job Type

git:
  remote: https://github.com/racetrack/supersmart-model
  branch: master

jobtype_extra:
  requirements_path: 'supersmart/requirements.txt'
  entrypoint_path: 'job_entrypoint.py'

resources:
  memory_max: 2Gi
```

So in a way, the Manifest is to Racetrack what the Dockerfile is to Docker.

Some clever things that can be controlled using the Manifest is installing extra
packages, or processing a Python `requirements.txt` file.

It is recommended to declare maximum memory amount explicitly by defining
```yaml
resources:
  memory_max: 1Gi
```

Please refer to the more comprehensive section
[The Job Manifest File](manifest-schema.md) for more detail.

### Submitting a Job<a name="submitting"></a>

Racetrack Jobs are deployed to operation; that means, they are sent off from
your development computer to run on a server somewhere. This sending is in
Racetrack terminology called Job "submission".

As you will experience in the [tutorial](#tutorial), Racetrack provides a
command line client you can install, and which handles this Submission for you.

When operating with Racetrack (either local instance or production server), the
Racetrack command line client will need authentication.

## The Racetrack Workflow<a name="workflow"></a>

As a Racetrack user, your workflow will typically look similar to this:

1. Write a piece of code doing something useful
1. Pick the appropriate Racetrack Job Type
1. Refactor your code to follow the Convention
1. Compose an appropriate `job.yaml`
1. Push it to GitLab or Github
1. Standing in the root directory of your code, submit the Job using the
   Racetrack command line client
1. Wait briefly
1. Receive the message that it has been deployed
1. Check it by either `curl`'ing to it, looking at it in the Racetrack
   dashboard, or asking your friendly Racetrack admin.

## Tutorial<a name="tut"></a>

This tutorial deploys Racetrack locally on your computer in a
[KinD](https://kind.sigs.k8s.io/) (a baby Kubernetes for testing) cluster. It is
intended to give you the muscle memory for using a production instance of
Racetrack, and to help you get used to the core Racetrack concepts.

### Prerequisites<a name="tut-prereq"></a>

1. A workstation with a sane operating system (currently, Debian and -
   grudgingly - Ubuntu are considered sane)
1. [Docker v20.10+](https://docs.docker.com/engine/install/ubuntu/)
  managed by a [non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user)
1. [Docker Compose plugin](https://docs.docker.com/compose/install/linux/#install-using-the-repository)
1. bash
1. python3 and python3-venv (Python 3.8+)
1. [racetrack-client](https://pypi.org/project/racetrack-client/) (see section
   [Installing Racetrack Locally](#tut-install) for installation instructions if
   unsure)
1. curl
1. [kind](https://kind.sigs.k8s.io/)
1. [Kubectl](https://kubernetes.io/docs/tasks/tools/) (version 1.24.3 or higher)
1. (optional) [k9s](https://github.com/derailed/k9s)

### Installing Racetrack Locally<a name="tut-install"></a>

Fetch the Racetrack sources:

```bash
git clone https://github.com/TheRacetrack/racetrack.git
```

Execute the following:

```bash
# Enter the source root
cd racetrack
# install the command line client
make setup
. venv/bin/activate
# Deploy the KinD cluster and install Racetrack in it
make kind-up
python3 -m pip install --upgrade racetrack-client
```

After a period ranging between 30-50 years, KinD will be up and running and
Racetrack will be deployed inside it.

You are ready to deploy a sample application to it.

### Submitting a Python Class<a name="tut-submit"></a>

The source code ships with a range of sample Jobs; you can find them in the path
`sample/`. In this tutorial, we will be Submitting the `sample/python-class`
Job.

```bash
# Set the current Racetrack's remote address
racetrack set remote http://localhost:7002
# Login to Racetrack prior to deploying a job
racetrack login eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI
# Activate python3 job type in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
# Activate kubernetes infrastructure target in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
# go to the sample directory
cd sample/python-class/
# deploy from the current directory (.) to the Racetrack service which is
# sitting on localhost inside KinD, listening on port 7002
racetrack deploy
```

After a pretty short time, the `racetrack` command will exit successfully and let you
know the Job is deployed, giving you the URL.
Before opening this URL, open [Dashboard page](http://localhost:7003/dashboard/)
and log in with default `admin` username and `admin` password.
That will set up a session allowing you to access Jobs through your browser.

The code in the [sample/python-class/adder.py](../sample/python-class/adder.py)
module has been converted by Racetrack into a
fully functional and well-formed Kubernetes micro-service; our Job. Please
examine this file [sample/python-class/adder.py](../sample/python-class/adder.py) 
in order to understand what to expect.

### Testing the Resulting Job<a name="tut-test"></a>

You now have the following running on your developer workstation:

1. A KinD cluster
1. Racetrack deployed inside it
1. A Python 3 micro-service converted to a Job, running inside this Racetrack

There are several ways you can interact with Racetrack and this Job:

#### Using the Job<a name="tut-test-foo"></a>

The function in `adder.py` now hangs off a HTTP endpoint, and can be used as a
ReST service. You can use `curl` to test this (as described in the [Job Type documentation](../sample/python-class/README.md):

```bash
curl -X POST "http://localhost:7005/pub/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
  -d '{"numbers": [40, 2]}'
# Expect: 42
```

#### Checking the Job Swagger<a name="tut-test-swagger"></a>

Racetrack generates free [Swagger API documentation](https://swagger.io/). You
can access it in your web browser
[here](http://localhost:7005/pub/job/adder/latest), 
but first you need to authenticate in order to make requests through your browser.
Open [Dashboard page](http://localhost:7003/dashboard/) and log in with default `admin` username and `admin` password.
That will set up a session allowing you to call Jobs.

#### Checking the Job Health<a name="tut-test-health"></a>

You also get a free [service health
endpoint](https://kubernetes.io/docs/reference/using-api/health-checks/):

```bash
curl "http://localhost:7005/pub/job/adder/latest/health"
# Expect:
# {"service": "job", "job_name": "adder", "status": "pass"}
```

#### Checking Job logs<a name="tut-logs"></a>

To see recent logs from your Job output, run `racetrack logs` command:
```bash
racetrack logs . http://localhost:7002
```

`racetrack logs [WORKDIR] [RACETRACK_URL]` has 2 arguments:

- `WORKDIR` - a place where the `job.yaml` is, by default it's current directory
- `RACETRACK_URL` - URL address to Racetrack server, where the Job is deployed.

#### Inspecting the Job in the Racetrack Dashboard<a name="tut-test-dashb"></a>

Racetrack ships with a dashboard. In production, it will be the admin who has
access to this, but you're testing locally so you can see it
[here](http://localhost:7003/dashboard) and you can see your adder job.

#### (optional) Inspecting the Job inside KinD Using k9s<a name="tut-test-k9s"></a>

Invoke k9s on your command line and navigate to the pods view using `:pods`. Hit
`0` to display all Kubernetes namespaces. Under the `racetrack` namespace, you
should see `job-adder-blabla-bla`.

### Authentication<a name="tut-auth"></a>

Racetrack requires you to authenticate with a token.
To manage users and tokens, visit Racetrack dashboard page: http://localhost:7003/dashboard/.
Default super user is `admin` with password `admin`.
Once the Racetrack is started, it is recommended to create other users, and deactivate default `admin` user for security purposes.

Then visit your Profile page to see your auth token.

Authentication applies to both deploying a Job and calling it:

- In order to deploy a Job (or use other management commands), run `racetrack login` command with your token in first place. For instance:
  ```bash
  racetrack login eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI --remote http://localhost:7002
  ```
- In order to call a Job (fetch results from it), include your token in `X-Racetrack-Auth` header. For instance:
  ```bash
  curl -X POST "http://localhost:7005/pub/job/adder/latest/api/v1/perform" \
    -H "Content-Type: application/json" \
    -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
    -d '{"numbers": [40, 2]}'
  ```

### Tearing it Down<a name="tut-teardown"></a>

Assuming you are standing in the root directory of the Racetrack source code:

```bash
# kill KinD and what it contains
make kind-down
# stop and remove the local testing docker registry
docker stop kind-registry && docker rm -v kind-registry
# exit the Python venv
deactivate
# optionally, clean up
git clean -fxd
```

## Developing Your Own Jobs<a name="developing"></a>

These instructions will work against the local test version described in the
[Tutorial](#tutorial) section, but are also explained such that they make sense
against a production instance of Racetrack on a real Kubernetes cluster.

You will follow the workflow described in the section [The Racetrack
Workflow](#workflow) in both cases.

### Using a Production Racetrack<a name="in-prod"></a>

As was the case in the tutorial, you need the
[racetrack-client](https://pypi.org/project/racetrack-client/) CLI tool
installed. Something like this ought to work:

```bash
python3 -m venv venv
. venv/bin/activate
python3 -m pip install --upgrade racetrack-client
racetrack -h
```

In the case of a production cluster, the only real change will be to the `racetrack
deploy` invocations. You will need to obtain the Racetrack address instead of
`localhost:7002`, so that:

```bash
racetrack deploy my/awesome/job --remote http://localhost:7002
```

becomes

```bash
racetrack deploy my/awesome/job --remote http://racetrack.platform.example.com:12345/lifecycle
```

Other endpoints described in the tutorial will also change away from
`localhost`. for example `http://localhost:7003/` might become
`https://racetrack-lifecycle.platform.example.com/`. You will need to check with
your local Racetrack admin to get these endpoints.

#### Authentication<a name="racetrack-authentication"></a>

Before you can deploy a job to production Racetrack server or even view the list
of Job on RT Dashboard, you need to create user there.

Visit your `https://racetrack.platform.example.com/dashboard/`
(or local http://localhost:7003/dashboard), click link to **Register**.
Type username (an email) and password. Password will be needed to login, 
so manage it carefully. Then notify your admin that he should activate your user.

When he does that, you can **Login**, and in the top right corner click **Profile**.
There will be your user token for racetrack client CLI, along with ready command
to login. It will look like `racetrack login <token> [--remote <remote>]`. When you
run this, then you can finally deploy your Job.

If you need, you can log out with `racetrack logout <racetrack_url>`. To check your
logged servers, there's `racetrack get config` command.

You can view the Job swagger page if you're logged to Racetrack Dashboard, on
which Job is displayed. Session is maintained through cookie. 

When viewing Job swagger page, you can run there the `/perform` method without specifying
additional credentials, because auth data in cookie from Racetrack Dashboard is 
used as credential. However, if you copy the code to curl in CLI like this:
```
curl -X 'POST' \
  'https://racetrack.platform.example.com/pub/job/adder/0.0.1/api/v1/perform' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "numbers": [
    40,
    2
  ]
}'
```
Then it won't work, because there's no auth data specified: 
`Unauthenticated: no header X-Racetrack-Auth: not logged in`

You will need to include it in curl using `-H 'X-Racetrack-Auth: <token>`.


### Jobs in Private or Protected git Repositories<a name="repo-tokens"></a>

As you noticed earlier, Racetrack requires in the `job.yaml` a git URL from
which to fetch the Job source code. If this repo is private or protected, you
will need to issue a token for the `racetrack` CLI tool to work. In GitLab, there
are two kinds of tokens (either of them can be used):

- Personal Access Token - allows to operate on all user projects. Instructions
  to create it are [here](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) 
- Project Access Token - needs to be issued per project. User has to be Maintainer
  in project to be able to create such token. Instructions to create it are
  [here](https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html). 

In both cases it has to have `read_repository` privilege.

Once you have this token, you need to register it with the `racetrack` CLI tool:

```bash
racetrack set credentials repo_url username token
```
where:

- `repo_url`: url to git repository, ie. `https://github.com/theracetrack/racetrack`
  You can also set this to root domain ie. `https://github.com` to make this token
  handle all projects.
- `username`: it's your gitlab account name, usually in the form of email
- `token`: as above. Keep it secret.

### Setting aliases for Racetrack servers<a name="config-aliases"></a>

You can set up aliases for Racetrack server URL addresses by issuing command:
```bash
racetrack set alias ALIAS RACETRACK_URL
```

If you operate with many environments, setting short names may come in handy. For instance:
```bash
racetrack set alias dev https://racetrack.dev.platform.example.com/lifecycle
racetrack set alias test https://racetrack.test.platform.example.com/lifecycle
racetrack set alias prod https://racetrack.prod.platform.example.com/lifecycle
racetrack set alias kind http://localhost:7002
racetrack set alias docker http://localhost:7102
```

and then you can use your short names instead of full `RACETRACK_URL` address when calling `racetrack deploy . --remote dev`.

You can set the current remote with
```shell
racetrack set remote RACETRACK_URL_OR_ALIAS
```
and then you can omit `--remote` parameter in the next commands.

### The Job Manifest File Schema<a name="manifest-deep"></a>

See [manifest-schema.md](manifest-schema.md)

### The Job Types<a name="job-types"></a>

These links show how to use particular job types installed by the [plugins](./development/using-plugins.md):

- [python3](https://github.com/TheRacetrack/plugin-python-job-type/blob/master/docs/job_python3.md) -
  designed for Python projects
- [golang](https://github.com/TheRacetrack/plugin-go-job-type/blob/master/docs/job_golang.md) -
  designed for Go projects
- [docker-proxy](https://github.com/TheRacetrack/plugin-docker-proxy-job-type/blob/master/docs/job_docker.md) -
  designed for any other Dockefile-based jobs

See the [sample/](../sample) directory for more examples.

### Local Client Configuration

The `racetrack` CLI tool maintains a configuration on your developer workstation. 
As you saw earlier in the section on [Jobs in Private or Protected git
Repositories](#repo-tokens) it can store Project/Personal Access Tokens.

It is also possible to store the address of the Racetrack server:

```bash
racetrack set remote http://localhost:7002
```

Local client configuration is stored at `~/.racetrack/config.yaml`

## Guidelines<a name="guide"></a>

This document uses the terms may, must, should, should not, and must not in
accord with [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).

### Must

1. You must use one of the pre-defined job types. Racetrack will error out if
   you do not.

### Should

1. The call path should be kept shallow. We prefer a bit bigger Job over
   small that creates a deep call path.
1. If part of the functionality of your Job becomes useful to a Service
   Consumer *other* than the current set of Service Consumers, consider if this
   part of its functionality should be split out into a separate Job. This is
   usually only a good idea of this part of the functionality is expensive in
   time or physical resources.

### Should not

1. You are discouraged from creating code boundaries by splitting a RT job up
   into several, if they all serve the same request. While Racetrack supports
   chaining Jobs, it prefers tight coupling in Jobs serving single business
   purposes.
1. The user should not use the Dockerfile job type. It's preferable to use one
   of the more specialised job types, or to coordinate with the RT developers to
   implement new job types. The Dockerfile job type exists as a fallback of last
   resort for tight deadlines and genuinely one-off runs which are demonstrably
   not accomplishable with current specialised job types, or which don't lend
   themselves via curation to improvements in specialised job types.

### May

1. If you have a need which isn't covered by the currently implemented job
   types, you may raise the need with the Racetrack developers in the GitLab
   issue tracker.

## FAQ<a name="faq"></a>

### I've submitted a job, where can I see if it's ready?

When you invoke `racetrack deploy . --remote https://racetrack.platform.example.com/lifecycle`, the client will
block while the deploy operation is in progress. When the command terminates,
unless you are given an error message, your job has been deployed into a Job.

It will be added to the list of running Jobs in the Racetrack dashboard; you
can see it there yourself, or if you don't have access, check with the local
Racetrack admin.

### I've submitted a job, but it's not working. Where can I see my errors?

If the error relates to the deployment action, the racetrack CLI tool will
display an error for you. You can also see it on Racetrack Dashboard.

If the error occurred in the process of converting the Job to a Job, your
Racetrack admin can help you.

### My Job produces raw output, I need it in another format

Racetrack supports chained Jobs; you can retain the original Job, and
deploy a supplemental "handler" Job which calls the original and transforms
its output to your desired format. Then you can simply call your handler.

### My Job takes config parameters, I don't want to pass them every call

You have several options.

You could use the handler pattern, placing a Job in front with the parameters
baked in. This means every time you need to change the parameters, you need to
update and redeploy the handler. This option is good for very slowly changing
parameters.

Another option is to build a Job with a web UI for tweaking the configuration
parameters, and then placing this one in front of your original Job. This
way, you change parameters at runtime rather than build-time. This option is
more work, but suits parameters which change a little more frequently.

As a third option, consider if you could "bake in" the parameters in your
original model. Time to deployment in Racetrack is very quick, and you might be
fine just redeploying the same Job with different config parameters when they
change.

### I need to combine the results of multiple Job

Develop a "handler" Job which calls the other Jobs whose results you want
to combine.

Racetrack supports chaining of Jobs for this purpose.

### I need to have one or more versions of a Job running at the same time

You could use something similar as the handler pattern where you place a Job in 
front of the Jobs you would like to call. The handler is responsible for calling all 
versions of the Job involved in the call and save the result for later evaluation,
but only the result from the active Job should be returned.

***NB*** This might evolve to a standard Job you can deploy and just configure.

### I have other problem running Racetrack locally, please help debug.

Do the following:
```
make clean
rm -rf venv
make setup
source venv/bin/activate
docker system prune -a
make kind-up
# Wait 10 minutes
make kind-test
racetrack set remote http://localhost:7002
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
racetrack deploy sample/python-class
```

If it doesn't work, diagnostic commands:

- `kubectl get pods` - do everything has "Running" status? If not, view logs of 
  that pod (ie. `kubectl logs <failing_pod_name>`)
- look into `kubectl logs service/lifecycle`
- Can you access the server at http://localhost:7002/ (in browser)?
- `netstat -tuanpl | grep 7002` - is the port blocked by something?

If you can't debug the problem yourself, please send the results of above commands
to developer channel.

### I need to be able to receive my answers asynchronously

The way to implement this is to create your own handler that can give you your answers
asynchronously. A simple way of archiving this would be to provide a callback URL in the ESC query. 

So you would send the request to the Job from your ESC; as soon as the Job
receives the request, the request terminates successfully; it does *not* wait to 
provide a response. Then your ESC listens on a defined webhook endpoint - the path
which was for example provided in the request - and when the Job has finished 
processing the request and is ready with a response, it POSTs this to the endpoint
on the ESC. Obviously, asynchronous calls require you to do some work on the ESC side as well.

### I want to build on an ARM system (such as M1 Mac)

Disclaimer: we don't officially support or test for those architectures, but after
little tweaking you should be still able to run on them. 

To build on an ARM system, you need to add the docker arm64 repositories to the 
image_builder and lifecycle Dockerfiles so apt-get can find the docker tools for amd64. 
You can do so by applying the following diff (save it in repo root and `git apply arm64_enable.diff`):
```
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
