# Dockerfile job type
Dockerfile jobs should be used as a last resort. You should rather use job types
specifically dedicated to your language if possible.

"docker-http" job type is intended to handle the calls to your Web server written 
in any programming language, enclosed in a docker image by Dockerfile recipe.

Set `lang: docker-http` in your `fatman.yaml` manifest file in order to use this type of job.

# Job standards
Let's assume you want to have a model running in a docker container and calculating
the sum of given numbers in Python:
```python
from typing import List

def sum_numbers(numbers: List[float]) -> float:
    return sum(numbers)
```

Now you need to make a few adjustments to adhere to job standards.
Basically, you need to embed your code in a HTTP server (using the programming language
you chose) with a `/perform` endpoint so that Racetrack can reach it.

For instance, use Flask to serve HTTP API and create `main.py` in your repository:
```python
from typing import List
from flask import Flask, jsonify, request

app = Flask(__name__)

def sum_numbers(numbers: List[float]) -> float:
    return sum(numbers)

@app.route("/perform", methods=['POST'])
def perform_endpoint():
    request_data = request.get_json()
    numbers = request_data.get('numbers', [])
    return jsonify(sum(numbers))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7004)
```

Next, encapsulate your web server in a `Dockerfile`:
```dockerfile
FROM python:3.8-slim-buster
RUN pip install flask
COPY main.py /src/
WORKDIR /src/
CMD python -u main.py
```

Your web server with `/perform` endpoint will be called by Racetrack every time your job is called.

To sum up:

1. You MUST setup an HTTP server on your own. You MUST serve it at `0.0.0.0` listen address on port `7004`.
1. You MUST expose `/perform` endpoint accepting `POST` method, expecting JSON body in a requests, in a format:
    ```json
    {
        "numbers": [20]
    }
    ```
    which contains a dict of parameter names with corresponding values.
1. You SHOULD validate expected data types from request on your own.
1. You MAY use any arbitrary programming language as long as it can start an HTTP server.
1. You MUST encapsulate your web server in a `Dockerfile` and refer to it in a manifest file.
   The root of your repository is a building context for Docker.
1. You MUST NOT use base images from private Docker Registries.
1. You MUST NOT refer to some local files that are not pushed to the repository. 
   Keep in mind that your job is built from your git repository.
1. You MAY fetch some data during initialization and keep them in a working directory
   (eg. load model data from external sources).

# Manifest file
When using `docker-http` job type, you MUST include the following fields in a `fatman.yaml` manifest file:
- `name` - choose a meaningful text name for a job. It should be unique within the Racetrack cluster.
- `owner_email` - email address of the Fatman's owner to reach out
- `lang` - Set base image to "docker-http"
- `git.remote` - URL to your remote repo 

You MAY include the following fields:
- `git.branch` - git branch name (if different from "master").
- `git.directory` - subdirectory relative to git repo root where the project is
- `docker.dockerfile_path` - relative path to a Dockerfile build recipe
- `labels` - dictionary with metadata describing fatman for humans

The final `fatman.yaml` may look like this:
```yaml
name: supersmart
owner_email: nobody@example.com
lang: docker-http

git:
  remote: https://github.com/racetrack/supersmart-model
  branch: master

docker:
  dockerfile_path: Dockerfile
```
