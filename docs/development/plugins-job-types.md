# Job type plugins

This tutorial shows  how to create a plugin extending Racetrack with your own job types.
Job types allow you to run applications written in specific programming languages.

## How to create a job-type plugin

As an example, let's make a plugin to run jobs written in [Go programming language](https://www.go.dev/).

### 1. Create a git repository
Create a git repository (or use existing one) to keep the source code of the plugin.

We're going to use https://github.com/TheRacetrack/plugin-go-job-type 
repository and we'll place the plugin inside `golang-job-type` subdirectory.

### 2. Initialize plugin manifest
Create `plugin-manifest.yaml` file in a `golang-job-type` subdirectory.
It contains the metadata of the plugin, including name, version
and the URL of the plugin home page.

```yaml
name: golang-job-type
version: 0.0.0
url: https://github.com/TheRacetrack/plugin-go-job-type
```

### 3. Write the wrapper
Let's create the "wrapper" written in the language of choice.
Wrapper is a program that runs given source code, wraps it up in a Web server,
adds some features to it (eg. metrics, swagger page) 
and forwards the HTTP requests, calling the wrapped code.
In other words, "Language Wrapper" converts your code written in your language
to a standardized Job web service.

This section would be different for each language.
When it comes to Go, we can organize the wrapper code in the following structure:
```
go_wrapper
├── go.mod
├── go.sum
├── handler
│   ├── go.mod
│   ├── go.sum
│   └── perform.go
├── health.go
├── main.go
├── Makefile
├── openapi.go
├── server.go
└── swaggerui
    ├── favicon-16x16.png
    ├── favicon-32x32.png
    ├── index.css
    ├── index.html
    ├── oauth2-redirect.html
    ├── openapi.json
    ├── swagger-initializer.js
    ├── swagger-ui-bundle.js
    ├── swagger-ui-bundle.js.map
    ├── swagger-ui.css
    ├── swagger-ui.css.map
    ├── swagger-ui-es-bundle-core.js
    ├── swagger-ui-es-bundle-core.js.map
    ├── swagger-ui-es-bundle.js
    ├── swagger-ui-es-bundle.js.map
    ├── swagger-ui.js
    ├── swagger-ui.js.map
    ├── swagger-ui-standalone-preset.js
    └── swagger-ui-standalone-preset.js.map
```

Let's assume that the user's source code will be placed in `go_wrapper/src/handler/` subfolder.
It will be injected there by docker during building the image.

For interpreted languages one could possibly load code modules 
on the fly from a given source code location
(see [Python wrapper](https://github.com/TheRacetrack/plugin-python-job-type/tree/master/python3-job-type/python_wrapper) as an example).

Here's how `go_wrapper/handler/go.mod` looks like:

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

The stub above will be replaced by user's code.
`func Perform(input map[string]interface{}) (interface{}, error)` function is our interface
between wrapper and user's code.
User is only required to provide the function matching this interface.

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
and redirects calls to perform function:
<details>
  <summary>File `go_wrapper/server.go`</summary>

```go
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "os"

    "github.com/gorilla/mux"
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
        fmt.Sprintf("/pub/job/%s/{version}", jobName),
        "",
    }

    router := mux.NewRouter()

    for _, baseUrl := range baseUrls {

        router.HandleFunc(baseUrl+"/api/v1/perform", performHandler)
        router.HandleFunc(baseUrl+"/health", HealthHandler)
        router.HandleFunc(baseUrl+"/live", LiveHandler)
        router.HandleFunc(baseUrl+"/ready", ReadyHandler)
        MountOpenApi(router, baseUrl)
    }

    loggingMiddleware := func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            log.Info("Request", log.Ctx{
                "method": r.Method,
                "uri":    r.RequestURI,
                "ip":     r.RemoteAddr,
            })
            next.ServeHTTP(w, r)
        })
    }
    router.Use(loggingMiddleware)

    listenAddress := "0.0.0.0:7000"
    log.Info("Listening on", log.Ctx{
        "listenAddress": listenAddress,
        "baseUrls":      baseUrls,
    })
    if err := http.ListenAndServe(listenAddress, router); err != nil {
        log.Error("Serving http", log.Ctx{"error": err})
        return errors.Wrap(err, "Failed to serve")
    }
    return nil
}

type EntrypointHandler func(input map[string]interface{}) (interface{}, error)

func buildHandler(entrypointHandler EntrypointHandler) func(http.ResponseWriter, *http.Request) {
    return func(w http.ResponseWriter, req *http.Request) {
        log.Debug("Perform request received")

        var input map[string]interface{}
        err := json.NewDecoder(req.Body).Decode(&input)
        if err != nil {
            http.Error(w, err.Error(), http.StatusBadRequest)
            return
        }

        output, err := entrypointHandler(input)
        if err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }

        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(output)
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
    "net/http"
    "os"
    "strconv"
)

type HealthResponse struct {
    Service                    string `json:"service"`
    JobName                 string `json:"job_name"`
    JobVersion              string `json:"job_version"`
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

func HealthHandler(w http.ResponseWriter, req *http.Request) {
    deploymentTimestamp, _ := strconv.Atoi(os.Getenv("JOB_DEPLOYMENT_TIMESTAMP"))
    output := &HealthResponse{
        Service:                    "job",
        JobName:                 os.Getenv("JOB_NAME"),
        JobVersion:              os.Getenv("JOB_VERSION"),
        GitVersion:                 os.Getenv("GIT_VERSION"),
        DeployedByRacetrackVersion: os.Getenv("DEPLOYED_BY_RACETRACK_VERSION"),
        DeploymentTimestamp:        deploymentTimestamp,
        Status:                     "pass",
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(output)
}

func LiveHandler(w http.ResponseWriter, req *http.Request) {
    deploymentTimestamp, _ := strconv.Atoi(os.Getenv("JOB_DEPLOYMENT_TIMESTAMP"))
    output := &LiveResponse{
        Status:              "live",
        DeploymentTimestamp: deploymentTimestamp,
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(output)
}

func ReadyHandler(w http.ResponseWriter, req *http.Request) {
    output := &ReadyResponse{
        Status: "ready",
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(output)
}
```
</details>

`go_wrapper/go.mod` and `go_wrapper/go.sum` are the files with package dependencies used by Go:
<details>
  <summary>File `go_wrapper/go.mod`</summary>

```
module github.com/TheRacetrack/plugin-go-job-type/golang-job-type  
go 1.16

require (
    github.com/gorilla/mux v1.8.0
    github.com/inconshreveable/log15 v0.0.0-20201112154412-8562bdadbbac
    github.com/pkg/errors v0.9.1
    racetrack/job v0.0.0
)
replace racetrack/job => ./handler
```
</details>

<details>
  <summary>File `go_wrapper/go.sum`</summary>

```
github.com/go-stack/stack v1.8.1 h1:ntEHSVwIt7PNXNpgPmVfMrNhLtgjlmnZha2kOpuRiDw=
github.com/go-stack/stack v1.8.1/go.mod h1:dcoOX6HbPZSZptuspn9bctJ+N/CnF5gGygcUP3XYfe4=
github.com/gorilla/mux v1.8.0 h1:i40aqfkR1h2SlN9hojwV5ZA91wcXFOvkdNIeFDP5koI=
github.com/gorilla/mux v1.8.0/go.mod h1:DVbg23sWSpFRCP0SfiEN6jmj59UnW/n46BH5rLB71So=
github.com/inconshreveable/log15 v0.0.0-20201112154412-8562bdadbbac h1:n1DqxAo4oWPMvH1+v+DLYlMCecgumhhgnxAPdqDIFHI=
github.com/inconshreveable/log15 v0.0.0-20201112154412-8562bdadbbac/go.mod h1:cOaXtrgN4ScfRrD9Bre7U1thNq5RtJ8ZoP4iXVGRj6o=
github.com/mattn/go-colorable v0.1.12 h1:jF+Du6AlPIjs2BiUiQlKOX0rt3SujHxPnksPKZbaA40=
github.com/mattn/go-colorable v0.1.12/go.mod h1:u5H1YNBxpqRaxsYJYSkiCWKzEfiAb1Gb520KVy5xxl4=
github.com/mattn/go-isatty v0.0.14 h1:yVuAays6BHfxijgZPzw+3Zlu5yQgKGP2/hcQbHb7S9Y=
github.com/mattn/go-isatty v0.0.14/go.mod h1:7GGIvUiUoEMVVmxf/4nioHXj79iQHKdU27kJ6hsGG94=
github.com/pkg/errors v0.9.1 h1:FEBLx1zS214owpjy7qsBeixbURkuhQAwrK5UwLGTwt4=
github.com/pkg/errors v0.9.1/go.mod h1:bwawxfHBFNV+L2hUp1rHADufV3IMtnDRdf1r5NINEl0=
golang.org/x/sys v0.0.0-20210630005230-0f9fa26af87c/go.mod h1:oPkhp1MJrh7nUepCBck5+mAzfO9JrbApNNgaTdGDITg=
golang.org/x/sys v0.0.0-20210927094055-39ccf1dd6fa6 h1:foEbQz/B0Oz6YIqu/69kfXPYeFQAuuMYFkjaqXzl5Wo=
golang.org/x/sys v0.0.0-20210927094055-39ccf1dd6fa6/go.mod h1:oPkhp1MJrh7nUepCBck5+               mAzfO9JrbApNNgaTdGDITg=
```
</details>

We can test the server locally by running:
```bash
cd golang-job-type/go_wrapper &&\
JOB_NAME=golang-function JOB_VERSION=0.0.1 go run .
```

We can test its response with:
```bash
curl -X POST \
    "http://localhost:7000/pub/job/golang-function/latest/api/v1/perform" \
    -H "Content-Type: application/json" \
    -d '{"numbers": [40, 2]}'
```

#### Wrapper Principles

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
- You MAY implement swagger documentation for your endpoints on root endpoint.
- You MAY implement `/metrics` endpoint for exposing Prometheus metrics.
- You MAY expose any other endpoints.
- Be careful to isolate libraries / requirements installed by the user
  from the versions of the libraries used by the core wrapper.

### 4. Prepare base Dockerfile

Building of the job docker image is split into two steps, having performance of the building in mind:

1. **Building base image** - 
  Base image contains files common to every Job (wrapper code).
  Base image doesn't depend on any particular Job or manifest.
  The image is built by Racetrack once on first use.
2. **Building Job from template** - 
  Job Dockerfile is the outcome of the Dockerfile template and the manifest of the Job that is about to be deployed.
  The Job image extends the base image.
  The job source code is injected into the image during building.
  This step is done for every Job and the building is done by Racetrack on the cluster servers.
  If there's some logic that depends on the particular Job manifest, it should be included here.
  For instance, `JOB_NAME` env variable is configured here because it depends on the Job manifest.

Having that in mind, let's create a `base.Dockerfile`:

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

We can test it if it builds without errors:
```bash
cd golang-job-type &&\
DOCKER_BUILDKIT=1 docker build \
    -t ghcr.io/theracetrack/racetrack/job-base/golang:latest \
    -f base.Dockerfile .
```

### 5. Prepare Job template Dockerfile
Next, we need to create a template for Dockerfile that will be generated for each Job.

It should be a Jinja2 template, it can make use of the following variables:

- `base_image` - the name of the base docker image to use for building a Job
- `env_vars` - dict with environment variables that should be assigned to the Job container
- `manifest` - whole Job Manifest object (see [Job Manifest Schema](../manifest-schema.md))
- `git_version` - version of the Job code taken from git repository
- `deployed_by_racetrack_version` - version of the Racetrack that has been used to build this image 
  (you can use it in the application to present it somewhere)

Here's `job-template.Dockerfile`:

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

{% if manifest.golang.gomod %}
COPY "{{ manifest.golang.gomod }}" /src/job/
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

We won't build this Dockerfile now, it will be handled by Racetrack once the job is submitted.

### 6. Create `plugin.py` file

`plugin.py` is a file that is read by the Racetrack instance, when loading the plugin.
It should contain the `Plugin` class with the implemented methods,
depending on the functionality that it targets to provide.
See [developing-plugins.md](./developing-plugins.md) for the list of all supported hooks.

We want to provide job types with this plugin,
so let's implement `job_types` method.
It defines what's the name of our new job type (`'go'`).
Also it has the reference to the base Dockerfile path
and the dockerfile template path we created earlier.

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

### 7. Create `.racetrackignore` file
We don't need to incorporate all the local files into a plugin ZIP file.
We can instruct `racetrack` plugin bundler to ignore these files by adding `.racetrackignore` file:
```
go_wrapper/swaggerui/*.map
Makefile
go.sum
```

### 8. Bundle plugin into a ZIP file
Local source code of the plugin can be turned into a ZIP file
by means of a `racetrack` client tool.
Install it with: 
```shell
python3 -m pip install --upgrade racetrack-client
```

Let's run `racetrack plugin bundle` in a directory where the plugin is located (`go-job-type` dir)
to turn a plugin into a ZIP file.

## Installing plugin to Racetrack

Now, we can make use of the plugin by installing it to Racetrack.

Let's go to the Dashboard Administration page
(you need to be staff user to see this tab)
and upload the zipped plugin there.

## Deploying sample Job

Let's create an exemplary Job `sample-golang-function` that will be deployed to Racetrack.

`perform.go` file contains the logic we want to deploy:
```go
package dummyserver

import (
    "github.com/pkg/errors"
)

func Perform(input map[string]interface{}) (interface{}, error) {
    numbers, ok := input["numbers"]
    if !ok {
        return nil, errors.New("'numbers' parameter was not given")
    }
    numbersList, ok := numbers.([]interface{})
    if !ok {
        return nil, errors.New("'numbers' is not a list")
    }
    inputFloats := make([]float64, len(numbersList))
    var err error
    for i, arg := range numbersList {
        inputFloats[i] = arg.(float64)
        if err != nil {
            return nil, errors.Wrap(err, "converting argument to float64")
        }
    }

    var sum float64 = 0
    for _, number := range inputFloats {
        sum += number
    }

    return sum, nil
}
```

and the Job manifest `job.yaml` might look like this:
```yaml
name: golang-function
owner_email: sample@example.com
lang: golang:latest

git:
  remote: https://github.com/TheRacetrack/plugin-go-job-type
  directory: sample-golang-function
```

Don't forget to push the Job code to a git repository.

Finally, we can deploy this Job to Racetrack:
```bash
racetrack deploy
```
