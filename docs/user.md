# User Guide

## Introduction

### What is Racetrack?

Racetrack is a system which transforms your code to in-operation workloads, e.g.
Kubernetes workloads.

You write your code - say for a ML model or micro-service - in a specific style,
you hand it over to Racetrack, and a minute later it is in production.

Racetrack allows you to use several languages and frameworks (provided by [installed plugins](./development/using-plugins.md)):

* [Standard Python 3](https://github.com/TheRacetrack/plugin-python-job-type)
* [Golang services](https://github.com/TheRacetrack/plugin-go-job-type)
* [Rust](https://github.com/TheRacetrack/plugin-rust-job-type)
* And for exotic edge cases, [any Dockerfile-wrapped code](https://github.com/TheRacetrack/plugin-docker-proxy-job-type)
* [HUGO framework](https://github.com/TheRacetrack/plugin-hugo-job-type)
* [Drupal](https://github.com/TheRacetrack/plugin-docker-proxy-job-type/tree/master/sample/drupal)
* [Sphinx](https://github.com/TheRacetrack/plugin-docker-proxy-job-type/tree/master/sample/sphinx)
* [Quake III](https://github.com/iszulcdeepsense/racetrack-quake)

Racetrack can be extended to [introduce new languages and frameworks](./development/plugins-job-types.md).

<video width="100%" controls="true" allowFullscreen="true" src="https://user-images.githubusercontent.com/124889668/259082064-43648168-897c-435f-b2e1-e4f8e0313d7a.mp4">
</video>

### What distinguishes Racetrack?

- You only supply your **function's logic**. No need to write repetitive API code, setting up 
  webservers, creating dockerfiles, kubernetes YAMLs, and so on. Racetrack takes care of that for you.
- **Language agnostic**. Deploy code written in Python 3, Go, Rust,
  or anything else encapsulated in a Dockerfile.
- **Infrastructure independent**. Deploy to either a Kubernetes cluster
  or a Docker environment in a single transparent step.
- **Server-side building**. Code is transformed into a microservice without your computer being involved.
- **Customizable through plugins**,
- **Immutable jobs**
- **Reproducible jobs**. Racetrack ensures that anyone else can deploy the same job effortlessly.
- **Out-of-the-box tools**: web endpoints, API documentation,
  metrics, monitoring, tracing, and more.
- Released under a **permissive open-source license**,
- Suitable for both **on-premises and cloud** environments.

### Architecture and Terminology

![Racetrack architecture for civilians](assets/arch-00.png)

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

### Conventions

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

* For the Python 3 Job Type, you must have a `class JobEntrypoint` with a
  method `perform()` for the Python 3 function which receives input and gives
  output (e.g. receiving a vector, and returning it normalized). Racetrack will
  then know to wrap this in a HTTP server and expose it.
* For the Go Job Type, your main function must have the following signature:
  `func Perform(args []interface{}, kwargs map[string]interface{}) (interface{},
  error)`.

As a concrete example, if you have written a clever Python 3 function which adds
two integers and returns the result, your code pre-Racetrack would look like
this:

```python
# file: model.py
def add_em_up(x, y):
    z = x + y
	return z
```

And refactored to meet the Racetrack Python 3 Job Type Convention:

```python
# file: job_entrypoint.py
class JobEntrypoint:
	def perform(self, x, y):
		return add_em_up(x, y)

def add_em_up(x, y):
    z = x + y
	return z
```

### The Manifest

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

### Submitting a Job

Racetrack Jobs are deployed to operation; that means, they are sent off from
your development computer to run on a server somewhere. This sending is in
Racetrack terminology called Job "submission".

As you will experience in the [tutorials](#tutorials), Racetrack provides a
command line client you can install, and which handles this Submission for you.

When operating with Racetrack (either local instance or production server), the
Racetrack command line client will need authentication.

## The Racetrack Workflow

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

## Tutorials

You can choose from two tutorials on installing Racetrack on your local computer:

- [Quickstart](./quickstart.md) - quickly setup Racetrack on local Docker engine.
- [Local Kubernetes Setup](./local-kubernetes-setup.md) - run Racetrack on KinD - longer, but more comprehensive guide.

## Developing Your Own Jobs

These instructions will work against the local test version described in the
[Tutorials](#tutorials) section, but are also explained such that they make sense
against a production instance of Racetrack on a real Kubernetes cluster.

You will follow the workflow described in the section [The Racetrack Workflow](#the-racetrack-workflow)
in both cases.

### Using a Production Racetrack

As was the case in the tutorial, you need the
[racetrack-client](https://pypi.org/project/racetrack-client/) CLI tool
installed. Something like this ought to work:

```shell
python3 -m venv venv
. venv/bin/activate
python3 -m pip install --upgrade racetrack-client
racetrack -h
```

In the case of a production cluster, the only real change will be to the `racetrack
deploy` invocations. You will need to obtain the Racetrack address instead of
`127.0.0.1:7002`, so that:

```shell
racetrack deploy my/awesome/job --remote http://127.0.0.1:7002
```

becomes

```shell
racetrack deploy my/awesome/job --remote http://racetrack.platform.example.com:12345/lifecycle
```

Other endpoints described in the tutorial will also change away from
`localhost`. for example `http://127.0.0.1:7003/` might become
`https://racetrack-lifecycle.platform.example.com/`. You will need to check with
your local Racetrack admin to get these endpoints.

#### Authentication

Before you can deploy a job to production Racetrack server or even view the list
of Job on RT Dashboard, you need to create user there.

Visit your `https://racetrack.platform.example.com/dashboard/`
(or local [http://127.0.0.1:7003/dashboard](http://127.0.0.1:7003/dashboard)), click link to **Register**.
Type username (an email) and password. Password will be needed to login, 
so manage it carefully. Then notify your admin that he should activate your user.

When he does that, you can **Login**, and in the top right corner click **Profile**.
There will be your user token for racetrack client CLI, along with ready command
to login. It will look like `racetrack login <token> [--remote <remote>]`. When you
run this, then you can finally deploy your Job.

If you need, you can log out with `racetrack logout [--remote <remote>]`. To check your
logged servers, there's `racetrack get config` command.

You can view the Job swagger page if you're logged to Racetrack Dashboard, on
which Job is displayed. Session is maintained through cookie. 

When viewing Job swagger page, you can run there the `/perform` method without specifying
additional credentials, because auth data in cookie from Racetrack Dashboard is 
used as credential. However, if you copy the code to curl in CLI like this:
```shell
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


### Jobs in Private or Protected git Repositories

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

```shell
racetrack set credentials repo_url username token
```
where:

- `repo_url`: url to git repository, ie. `https://github.com/theracetrack/racetrack`
  You can also set this to root domain ie. `https://github.com` to make this token
  handle all projects.
- `username`: it's your gitlab account name, usually in the form of email
- `token`: as above. Keep it secret.

### Setting aliases for Racetrack servers

You can set up aliases for Racetrack server URL addresses by issuing command:
```shell
racetrack set alias ALIAS RACETRACK_URL
```

If you operate with many environments, setting short names may come in handy. For instance:
```shell
racetrack set alias dev https://racetrack.dev.platform.example.com/lifecycle
racetrack set alias test https://racetrack.test.platform.example.com/lifecycle
racetrack set alias prod https://racetrack.prod.platform.example.com/lifecycle
racetrack set alias kind http://127.0.0.1:7002
racetrack set alias docker http://127.0.0.1:7102
```

and then you can use your short names instead of full `RACETRACK_URL` address when calling `racetrack deploy --remote dev`.

You can set the current remote with
```shell
racetrack set remote RACETRACK_URL_OR_ALIAS
```
and then you can omit `--remote` parameter in the next commands.

### The Job Manifest File Schema

See [Job Manifest File Schema](manifest-schema.md)

### The Job Types

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
As you saw earlier in the section on 
[Jobs in Private or Protected git Repositories](#jobs-in-private-or-protected-git-repositories)
it can store Project/Personal Access Tokens.

It is also possible to store the address of the Racetrack server:

```shell
racetrack set remote http://127.0.0.1:7002
```

Local client configuration is stored at `~/.racetrack/config.yaml`

## Guidelines

This document uses the terms may, must, should, should not, and must not in
accord with [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).

### Must

1. You must use one of the pre-defined (currently installed) job types.
   Racetrack will error out if you do not.

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
   types, you may raise the need with the Racetrack developers in the GitHub
   issue tracker.

## FAQ

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
  that pod (ie. `kubectl logs <failing_pod_name>`)
- look into `kubectl logs service/lifecycle`
- Can you access the server at [http://127.0.0.1:7002](http://127.0.0.1:7002/) (in browser)?
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