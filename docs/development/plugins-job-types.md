# Creating Job Type plugins

This document covers how to create your own [job type](../glossary.md) plugin
to extend Racetrack.

## Quickstart Step-by-step
1. Create a git repository for your plugin

2. Create a [plugin manifest](../manifest-schema.md) in a plugin subdirectory

3. Write a wrapper for the software you are making a job type for

    A wrapper is a program that runs given piece of software,
  wraps it up in a web server, adds features to it (eg. metrics, swagger page)
  and forwards HTTP requests calling the wrapped code.

4. Prepare the base dockerfile

    The base dockerfile contains the wrapper code and is common to every Job
  using the Job type provided by it. As such, it doesn't depend on any
  particular Job or manifest. The image is built by Racetrack on first use.

5. Prepare the Job template dockerfile

    The Job template dockerfile is a [Jinja2](https://github.com/pallets/jinja)
  template with the following variables, that gets built for each individual
  Job automatically by Racetrack.

    - `base_image` - the name of the base docker image to use for building a Job
    - `env_vars` - dict with environment variables that should be assigned to the Job container
    - `manifest` - whole Job Manifest object (see [Job Manifest Schema](../manifest-schema.md))
    - `git_version` - version of the Job code taken from git repository
    - `deployed_by_racetrack_version` - version of the Racetrack that has been
    used to build this image.

    As it is built for every individual job, if there's any logic that depends
  on the specific job manifest should be done here and not in the previous step.

6. Create an appropriate `plugin.py`

    `plugin.py` describes the Plugin class - to be considered a job type, your
  `plugin.py` must at minimum implements the `job_types` method as described here in
  [the documentation of all available hooks.](./developing-plugins.md#supported-hooks)

7. Create a `.racetrackignore`

    Files not needed for the plugin should be added to the `.racetrackignore` file.

8. Bundle plugin into a zipfile with `racetrack plugin bundle`

## Wrapper Principles

Every wrapper has to follow some rules:

- HTTP server MUST run on port 7000, address `0.0.0.0`.
- HTTP server MUST mount endpoints at `/pub/job/{name}/{version}` base URL,
  where `{name}` is the name of the job taken from `JOB_NAME` environment
  variable (it will be assigned by docker) and `{version}` should match any string
  (due to job can be accessed by explicit version or by `latest` alias).
- HTTP server MUST have `/live` and `/ready` endpoints returning `200` status code,
  once it's alive and ready to accept requests.
- `/live` endpoint MUST return `{"deployment_timestamp": 1654779364}` JSON object.
  `"deployment_timestamp"` integer value should be taken from
  `JOB_DEPLOYMENT_TIMESTAMP` environment variable (it will be set by docker).
  This is the timestamp of the deployment, it's needed to distinguish versions
  in case of asynchronous redeployment of the job.
  `/live` endpoint MAY contain other JSON fields as well.
- You MAY implement [swagger](https://swagger.io/tools/swagger-ui/) documentation for your endpoints on root endpoint.
- You MAY implement `/metrics` endpoint for exposing [Prometheus](https://prometheus.io/) metrics.
- You MAY expose any other endpoints.
- Calls from jobs to other jobs SHOULD be made by
  importing a dedicated function from the job type plugin's library
  ([example](https://github.com/TheRacetrack/plugin-python-job-type/blob/29f9ecc04b182072f3549c82923e252728bd7b61/sample/python-chain/entrypoint.py#LL9C19-L9C83)).
- Be careful to isolate libraries / requirements installed by the user
  from the versions of the libraries used by the core wrapper.

## Example job type

The [Go job type](https://github.com/TheRacetrack/plugin-go-job-type) is a
fully featured job type maintained by the racetrack team that serves as an
example job type that implements all features (including optional ones)
provided by racetrack. A barebones quickstart version of said jobtype
following the guide above would look as follows:

### 1. Create a git repository

Create [https://github.com/TheRacetrack/plugin-go-job-type](https://github.com/TheRacetrack/plugin-go-job-type).

### 2. Create a plugin manifest in a plugin subdirectory

Create `golang-job-type` subdirectory, create `plugin-manifest.yaml` in it.
It should look as follows:

```yaml
name: golang-job-type
version: 1.3.0
url: https://github.com/TheRacetrack/plugin-go-job-type
```

### 3. Write a wrapper for running Go code

Create the `go_wrapper` subdirectory in the `golang-job-type` subdirectory.
It should look like:
```
go_wrapper
├── go.mod
├── go.sum
├── handler
│   ├── go.mod
│   ├── go.sum
│   └── perform.go
├── health.go
├── main.go
├── Makefile
└── server.go
```

`go_wrapper/src/handler/` is for handling the user's code, it will be
injected there by docker when building the image. It looks like this:

```go
// This is just a stub for IDE.
// It gets replaced by user's Job code in wrappers/docker/golang/job-template.Dockerfile
module stub
go 1.16
require (
    github.com/go-stack/stack v1.8.1 // indirect
    github.com/inconshreveable/log15 v0.0.0-20201112154412-8562bdadbbac
    github.com/mattn/go-colorable v0.1.12 // indirect
)
```

`go_wrapper/main.go` contains the main function setting up the server:

<details>
  <summary>File `go_wrapper/main.go`</summary>

```go
package main
import (
    handler "racetrack/job"
)
func main() {
    err := WrapAndServe(handler.Perform)
    if err != nil {
        panic(err)
    }
}
```
</details>

`go_wrapper/server.go` contains the function that starts the server
and redirects calls to the `perform` function:

<details>
  <summary>File `go_wrapper/server.go`</summary>

```go
package main
import (
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "github.com/gin-gonic/gin"
    log "github.com/inconshreveable/log15"
    "github.com/pkg/errors"
)
// WrapAndServe embeds given function in a HTTP server and listens for requests
func WrapAndServe(entrypoint EntrypointHandler) error {
    performHandler := buildHandler(entrypoint)
    jobName := os.Getenv("JOB_NAME")
    // Serve endpoints at raw path (to facilitate debugging) and prefixed path (when accessed through   PUB).
    // Accept any version so that job can be called by its many version names ("latest", "1.x").
    baseUrls := []string{
        fmt.Sprintf("/pub/job/%s/:version", jobName),
        "",
    }
    gin.SetMode(gin.ReleaseMode) //Hide debug routings
    router := gin.New()
    router.Use(gin.Recovery())
    for _, baseUrl := range baseUrls {
        router.POST(baseUrl+"/api/v1/perform", performHandler)
        router.GET(baseUrl+"/health", HealthHandler)
        router.GET(baseUrl+"/live", LiveHandler)
        router.GET(baseUrl+"/ready", ReadyHandler)
        MountOpenApi(router, baseUrl)
    }
    router.Use(gin.Logger())
    listenAddress := "0.0.0.0:7000"
    log.Info("Listening on", log.Ctx{
        "listenAddress": listenAddress,
        "baseUrls":      baseUrls,
    })
    if err := router.Run(listenAddress); err != nil {
        log.Error("Serving http", log.Ctx{"error": err})
        return errors.Wrap(err, "Failed to serve")
    }
    return nil
}
type EntrypointHandler func(input map[string]interface{}) (interface{}, error)
func buildHandler(entrypointHandler EntrypointHandler) func(c *gin.Context) {
    return func(c *gin.Context) {
        log.Debug("Perform request received")
        var input map[string]interface{}
        err := json.NewDecoder(c.Request.Body).Decode(&input)
        if err != nil {
            http.Error(c.Writer, err.Error(), http.StatusBadRequest)
            return
        }
        output, err := entrypointHandler(input)
        if err != nil {
            http.Error(c.Writer, err.Error(), http.StatusInternalServerError)
            return
        }
        c.Writer.Header().Set("Content-Type", "application/json")
        json.NewEncoder(c.Writer).Encode(output)
    }
}
func wrapHandler(h http.Handler) gin.HandlerFunc {
    return func(c *gin.Context) {
        h.ServeHTTP(c.Writer, c.Request)
    }
}
```
</details>

`go_wrapper/health.go` handles liveness and readiness probes:
<details>
  <summary>File `go_wrapper/health.go`</summary>

```go
package main
import (
    "encoding/json"
    "os"
    "strconv"
    "github.com/gin-gonic/gin"
)
type HealthResponse struct {
    Service                    string `json:"service"`
    JobName                    string `json:"job_name"`
    JobVersion                 string `json:"job_version"`
    GitVersion                 string `json:"git_version"`
    DeployedByRacetrackVersion string `json:"deployed_by_racetrack_version"`
    Status                     string `json:"status"`
    DeploymentTimestamp        int    `json:"deployment_timestamp"`
}
type LiveResponse struct {
    Status              string `json:"status"`
    DeploymentTimestamp int    `json:"deployment_timestamp"`
}
type ReadyResponse struct {
    Status string `json:"status"`
}
func HealthHandler(c *gin.Context) {
    deploymentTimestamp, _ := strconv.Atoi(os.Getenv("JOB_DEPLOYMENT_TIMESTAMP"))
    output := &HealthResponse{
        Service:                    "job",
        JobName:                    os.Getenv("JOB_NAME"),
        JobVersion:                 os.Getenv("JOB_VERSION"),
        GitVersion:                 os.Getenv("GIT_VERSION"),
        DeployedByRacetrackVersion: os.Getenv("DEPLOYED_BY_RACETRACK_VERSION"),
        DeploymentTimestamp:        deploymentTimestamp,
        Status:                     "pass",
    }
    c.Writer.Header().Set("Content-Type", "application/json")
    json.NewEncoder(c.Writer).Encode(output)
}
func LiveHandler(c *gin.Context) {
    deploymentTimestamp, _ := strconv.Atoi(os.Getenv("JOB_DEPLOYMENT_TIMESTAMP"))
    output := &LiveResponse{
        Status:              "live",
        DeploymentTimestamp: deploymentTimestamp,
    }
    c.Writer.Header().Set("Content-Type", "application/json")
    json.NewEncoder(c.Writer).Encode(output)
}
func ReadyHandler(c *gin.Context) {
    output := &ReadyResponse{
        Status: "ready",
    }
    c.Writer.Header().Set("Content-Type", "application/json")
    json.NewEncoder(c.Writer).Encode(output)
}
```
</details>

`go_wrapper/go.mod` and `go_wrapper/go.sum` are Go specific dependency files.

### 4 through 7: Put needed files in the `golang-job-type` subdirectory

<details>
  <summary>File `go-job-type/base.Dockerfile`</summary>

```dockerfile
FROM golang:1.16-alpine
WORKDIR /src/go_wrapper
# Copy wrapper code to the image & remove the stub that is about to be replaced
COPY go_wrapper/. /src/go_wrapper/
RUN go get ./... && rm -rf /src/go_wrapper/handler
CMD ./go_wrapper < /dev/null
# Label image so the container can be identified as Job (for automated cleanup)
LABEL racetrack-component="job"
```
</details>

<details>
  <summary>File `go-job-type/job-template.Dockerfile`</summary>

```Dockerfile
# It extends wrapper image
FROM {{ base_image }}
# Setting environment variables from env_vars
{% for env_key, env_value in env_vars.items() %}
ENV {{ env_key }} "{{ env_value }}"
{% endfor %}
# Install additional libraries requested by user in its manifest
# Note: package manager should be compliant with the base image we used earlier
{% if manifest.system_dependencies and manifest.system_dependencies|length > 0 %}
RUN apk add \
    {{ manifest.system_dependencies | join(' ') }}
{% endif %}
{% if manifest.jobtype_extra.gomod %}
COPY "{{ manifest.jobtype_extra.gomod }}" /src/job/
RUN cd /src/job && go mod download
{% endif %
# Finally, copy the Job source code in the place where the wrapper expects it
COPY . /src/go_wrapper/handler/
# Make sure directory is writable and build the executable
RUN chmod -R a+rw /src/go_wrapper && cd /src/go_wrapper/ && go mod download
# Build Go Job
RUN go get ./... && go build -o go_wrapper
# Set environment variables that are expected by Job executable
ENV JOB_NAME "{{ manifest.name }}"
ENV JOB_VERSION "{{ manifest.version }}"
ENV GIT_VERSION "{{ git_version }}"
ENV DEPLOYED_BY_RACETRACK_VERSION "{{ deployed_by_racetrack_version }}"
```
</details>

<details>
  <summary>File `go-job-type/plugin.py`</summary>

```python
from __future__ import annotations
from pathlib import Path
class Plugin:
    def job_types(self) -> dict[str, tuple[Path, Path]]:
        """
        Job types provided by this plugin
        :return dict of job type name (with version) -> (base image path, dockerfile template path)
        """
        return {
            f'golang:{self.plugin_manifest.version}': (
                self.plugin_dir / 'base.Dockerfile',
                self.plugin_dir / 'job-template.Dockerfile',
            ),
        }
```
</details>

Finally, also create the `.racetrackignore` file:
```
Makefile
go.sum
```

### 8. Bundle plugin into a ZIP file
Install the racetrack client
```shell
python3 -m pip install --upgrade racetrack-client
```

And then run `racetrack plugin bundle` in the `go-job-type` directory.

## FAQ
**Q: What distinguishes a base image from a job template?**

**A:** A Job is created in two distinct stages. First, a *base image* is
created, which is common to all jobs of a single job type. Primarily, the
wrapper. The *job template* is then combined with the user-facing manifest,
creating a job image that extends the base image. This job image is unique
to each job, and is what will be deployed on racetrack.
