# The Job Manifest File Schema

To deploy a Job, the Developer should provide a build recipe called a Manifest,
describing how to build, run, and deploy.

The Manifest should be kept in `job.yaml` file located in the root of a Job's
repository. Some fields are required, while optional ones will be assigned a
default value if not provided. The YAML manifest file can have the following
fields:

- `name` (**required**) - name of the current service to be deployed by means of
  this mainfest file. It cannot contain underscores (but can contain dashes).
- `lang` (**required**) - Language wrapper used to embed model. This should be one
  of the supported wrapper names combined with the wrapper version:
  `python3:2.4.0`, `python3:latest`, `golang:latest` or `docker-http:latest`, etc.
- `git` (**required**) - the object describes the place where the source code can be
  found using git VCS.
    - `remote` (**required**) - **HTTPS** URL of git remote. This is also root of your
      git repo, which will become the "current working directory" at runtime of Job.
      SSH remote URLs are NOT supported.
    - `branch` - name of the branch (if other than master)
    - `directory` - subdirectory relative to git repo root where the project is
- `owner_email` (**required**) - email address of the Job's owner to reach out
- `extends` - relative path to base manifest file, which will be extended by this manifest
- `version` - Version of the Job. It should adhere to Semantic Versioning standard.
- `python` - Manifest for Python projects
    - `requirements_path` - path to `requirements.txt` relative to `git.directory`
    - `entrypoint_path` - relative path to a file with Job Entrypoint class
    - `entrypoint_class` - name of Python entrypoint class
- `golang` - Manifest for Go projects
    - `gomod` - relative path to `go.mod` requirements
- `docker` - Manifest for Dockerfile job types
    - `dockerfile_path` - relative path to Dockerfile recipe
- `build_env` - dictionary of environment variables that should be set when building the image
- `image_type` - type of deployed image. Only `docker` is currently available.
- `infrastructure_target` - Back-end platform where to deploy the service.
- `labels` - dictionary with metadata describing job for humans
- `public_endpoints` - list of public job endpoints that can be accessed without authentication
- `replicas` - number of running instances of the Job to deploy
- `resources` - resources demands to allocate to the Job
    - `memory_min` - minimum memory amount in bytes, eg. 256Mi
    - `memory_max` (**required**) - maximum memory amount in bytes, eg. 1Gi
    - `cpu_min` - minimum CPU consumption in cores, eg. 10m
    - `cpu_max` - maximum CPU consumption in cores, eg. 1000m
- `runtime_env` - dictionary of environment variables that should be set when running Job
- `secret_build_env_file` - path to a secret file (on a client machine) with build environment variables
- `secret_runtime_env_file` - path to a secret file (on a client machine) with runtime environment variables
- `system_dependencies` - list of system-wide packages that should be installed with package manager
  (apt or apk depending on base image type)

## Example
This example is not valid as a whole, but it contains all fields with exemplary values:
```yaml
name: skynet
lang: python3:latest
git:
  remote: https://github.com/racetrack/supersmart-model
  branch: master
  directory: 'examples/skynet'
owner_email: arnold@skynet.com
extends: './base/job.yaml'
version: '1.2.3-alpha'
python:
  requirements_path: 'python/requirements.txt'
  entrypoint_path: 'python/entrypoint.py'
  entrypoint_class: 'JobClazz'
golang:
  gomod: 'golang/go.mod'
docker:
  dockerfile_path: 'docker/Dockerfile'
build_env:
  DEBIAN_FRONTEND: 'noninteractive'
image_type: docker
infrastructure_target: kubernetes
labels:
  model: linear-regression
public_endpoints:
  - '/api/v1/perform'
  - '/api/v1/webview'
replicas: 1
resources:
  memory_min: 256Mi
  memory_max: 1Gi
  cpu_min: 10m
  cpu_max: 1000m
runtime_env:
  DJANGO_DEBUG: 'true'
  TORCH_MODEL_ZOO: zoo
secret_build_env_file: '.secrets/build.env'
secret_runtime_env_file: .secrets/runtime.env'
system_dependencies:
  - 'libgomp1'
```
