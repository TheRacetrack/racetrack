# The Job Manifest File Schema

To deploy a Job, the Developer should provide a build recipe called a Manifest,
describing how to build, run, and deploy.

The Manifest should be kept in `job.yaml` file located in the root of a Job's
repository. Some fields are required, while optional ones will be assigned a
default value if not provided. The YAML manifest file can have the following
fields:

- `name`, *string* (**required**) - name of the current service to be deployed by means of
  this mainfest file. It cannot contain underscores (but can contain dashes).
- `jobtype`, *string* (**required**) - Jobtype wrapper used to embed model. This should be one
  of the supported wrapper names combined with the wrapper version:
  `python3:2.4.0`, `python3:latest`, `golang:latest` or `docker-http:latest`, etc.
- `git`, *object* (**required**) - the object describes the place where the source code can be
  found using git VCS.
    - `remote`, *string* (**required**) - **HTTPS** URL of git remote. This is also root of your
      git repo, which will become the "current working directory" at runtime of Job.
      SSH remote URLs are NOT supported.
    - `branch`, *string* - name of the branch (if other than master)
    - `directory`, *string* - subdirectory relative to git repo root where the project is
- `owner_email`, *string* (**required**) - email address of the Job's owner to reach out
- `extends`, *string* - relative path to base manifest file, which will be extended by this manifest
- `version`, *string* - Version of the Job. It must adhere to Semantic Versioning standard.
- `jobtype_extra`, *object* - Jobtype specific extra parameters
    - Fields specified and validated by the jobtype.
- `build_env`, *object: string to string* - dictionary of environment variables that should be set when building the image
- `image_type`, *string* - type of deployed image. Only `docker` is currently available.
- `infrastructure_target`, *string* - Back-end platform where to deploy the service.
- `labels`, *object: string to string* - dictionary with metadata describing job for humans
- `public_endpoints`, *array of strings* - list of public job endpoints that can be accessed without authentication
- `replicas`, *integer* - number of running instances of the Job to deploy
- `resources`, *object* - resources demands to allocate to the Job
    - `memory_min`, *string* - minimum memory amount in bytes, eg. 256Mi
    - `memory_max`, *string* - maximum memory amount in bytes, eg. 1Gi
    - `cpu_min`, *string* - minimum CPU consumption in cores, eg. 10m
    - `cpu_max`, *string* - maximum CPU consumption in cores, eg. 1000m
- `runtime_env`, *object: string to string* - dictionary of environment variables that should be set when running Job
- `secret_build_env_file`, *string* - path to a secret file (on a client machine) with build environment variables
- `secret_runtime_env_file`, *string* - path to a secret file (on a client machine) with runtime environment variables
- `system_dependencies`, *array of strings* - list of system-wide packages that should be installed with package manager
  (apt or apk depending on base image type)

## Example
This example is not valid as a whole, but it contains all fields with exemplary values:
```yaml
name: skynet
jobtype: python3:latest
git:
  remote: https://github.com/racetrack/supersmart-model
  branch: master
  directory: 'examples/skynet'
owner_email: arnold@skynet.com
extends: './base/job.yaml'
version: '1.2.3-alpha'
jobtype_extra:
  requirements_path: 'python/requirements.txt'
  entrypoint_path: 'python/entrypoint.py'
  entrypoint_class: 'JobClazz'
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
