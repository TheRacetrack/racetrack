# User Guide: part 1 - Introduction

## What is Racetrack?

Racetrack is a system which transforms your code to in-operation workloads, e.g.
Kubernetes workloads.

You write your code - say for a ML model or micro-service - in a specific style,
you hand it over to Racetrack, and a minute later it is in production.

Racetrack allows you to use several languages and frameworks (provided by [installed plugins](./available-plugins.md)), for example:

* [Standard Python 3](https://github.com/TheRacetrack/plugin-python-job-type)
* [Golang services](https://github.com/TheRacetrack/plugin-go-job-type)
* [Rust](https://github.com/TheRacetrack/plugin-rust-job-type)
* And for exotic edge cases, [any Dockerfile-wrapped code](https://github.com/TheRacetrack/plugin-docker-proxy-job-type)
* [HUGO framework](https://github.com/TheRacetrack/plugin-hugo-job-type)
* [Drupal](https://github.com/TheRacetrack/plugin-docker-proxy-job-type/tree/master/sample/drupal)
* [Sphinx](https://github.com/TheRacetrack/plugin-docker-proxy-job-type/tree/master/sample/sphinx)
* [Quake III](https://github.com/iszulcdeepsense/racetrack-quake)

Racetrack can be extended to [introduce new languages and frameworks](../development/plugins-job-types.md).

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

## Architecture and Terminology

![Racetrack architecture for civilians](../assets/arch-00.png)

The following terms recur through this documentation and describe the elements and
actions involved in using Racetrack:

* **Job code**: your code, written in the style required by Racetrack
* **Job Type**: which of the languages and frameworks supported by Racetrack you
  choose to develop your job in
* **Job submission**: when you're happy with your code, and you push it to Racetrack
  to be deployed
* **Job**: when a job code is submitted to Racetrack, Racetrack converts it to a
  workload and deploys it. This workload is called a Job
* **Convention**: when you pick your Job Type, you will be asked to follow a specific
  style for that type which Racetrack understands; that style is a Convention
* **Manifest**: a YAML file in the root of your Job, which specifies the job type
  and provides configuration values for your Job according to that Job Type

To tie all of these terms together:

> As a data scientist, I selected the Python 3 **Job Type** to develop my ML
> model **Job** in. I wrote my **Job code** according to the Job Type **convention**. I
> composed a **Manifest** in which I specified the Job Type I used, and in it I
> tweaked a few specific parameters for this Job Type. I **submitted** the job code
> to Racetrack, after which it was deployed as a **Job**.

## Conventions

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

## The Manifest

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
[The Job Manifest File](../manifest-schema.md) for more detail.

## Submitting a Job

Racetrack Jobs are deployed to operation; that means, they are sent off from
your development computer to run on a server somewhere. This sending is in
Racetrack terminology called Job "submission".

As you will experience in the [Local Kubernetes Setup](../deployment/local-kubernetes-setup.md), Racetrack provides a
command line client you can install, and which handles this Submission for you.

When operating with Racetrack (either local instance or production server), the
Racetrack command line client will need authentication.

## What's next?

You can choose from these tutorials on installing Racetrack on your local computer:

- [Quickstart](../quickstart.md) - quickly setup Racetrack on local Docker engine.
- [Local Kubernetes Setup](../deployment/local-kubernetes-setup.md) - run Racetrack on KinD - longer, but more comprehensive guide.

How-to guides:
- [User Guide: part 2 - Creating a Job](./user-guide-2.md)
- [Installation to standalone host](../deployment/standalone-host.md)

Reference:
- [Available plugins](./available-plugins.md)
- [Job Manifest File Schema](../manifest-schema.md)

Explanation:
- [Glossary](../glossary.md)
