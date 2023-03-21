# Bill of Materials
This document contains a non-exhaustive "bill of materials" for the upstream
open source projects on which we depend. The intention is to maintain a list to
help us manage our software supply chain security by being aware of the open
source projects we need to track as part of the long term lifecycle of
Racetrack.

Here's the list of the open source projects we use in Racetrack.
The columns are:

- `Our version`: the version we use in Racetrack
- `Latest version`: newest version from the provider
- `Purpose`: what we use the project for

| Tool                                                                       | Our version | Latest version | Purpose |
| -------------------------------------------------------------------------- | ------------| ---------------|---------|
| [Python](https://www.python.org/downloads/)                                | 3.9         | 3.11           | Racetrack client, Lifecycle, Image builder code |
| [Docker](https://docs.docker.com/engine/release-notes/)                    | 20.10.17    | 23.0.1         | distributing Racetrack, building job images |
| [PostgreSQL](https://www.postgresql.org/docs/release/)                     | 13.1        | 15.2           | Racetrack's database |
| [Go](https://go.dev/dl/)                                                   | 1.19        | 1.20.1         | PUB code |
| [Django](https://pypi.org/project/Django)                                  | 4.1.7       | 4.1.7          | Lifecycle Admin panel, Dashboard UI |
| [jQuery](https://github.com/jquery/jquery/releases)                        | 3.6.0       | 3.6.3          | dynamic behaviours in Dashboard |
| [Bootstrap](https://getbootstrap.com/docs/versions/)                       | 5.0.1       | 5.3            | Dashboard's UI components |
| [TableFilter](https://github.com/koalyptus/TableFilter/releases)           | 0.7.3       | 0.7.3          | Portfolio table in Dashboard |
| [vis-network](https://github.com/visjs/vis-network)                        | 9.1.1       | 9.1.4          | Jobs graph in Dashboard |
| [github-markdown-css](https://github.com/sindresorhus/github-markdown-css) | 5.1.0       | 5.2.0          | rendering docs |
| [Prism](https://github.com/PrismJS/prism/)                                 | 1.28.0      | 1.29.0         | rendering code snippets in docs |
| [python-socketio](https://pypi.org/project/python-socketio/)               | 5.7.2       | 5.7.2          | Streaming logs of the job in *follow* mode |
| [backoff](https://pypi.org/project/backoff/)                               | 2.2.1       | 2.2.1          | repeating attempts in case of error |
| [Kubernetes Python Client](https://pypi.org/project/kubernetes/)           | 26.1.0      | 26.1.0         | managing Kubernetes |
| [prometheus-client](https://pypi.org/project/prometheus-client/)           | 0.16.0      | 0.16.0         | metrics exposure |
| [werkzeug](https://pypi.org/project/Werkzeug/)                             | 2.2.3       | 2.2.3          | serving SocketIO server |
| [GitPython](https://pypi.org/project/GitPython/)                           | 3.1.31      | 3.1.31         | cloning job repositories |
| [Python markdown](https://pypi.org/project/Markdown/)                      | 3.4.1       | 3.4.1          | rendering docs in Dashboard |
| [FastAPI](https://github.com/tiangolo/fastapi)                             | 0.92.0      | 0.92.0         | serving API by Python components |
| [kubectl](https://github.com/kubernetes/kubectl)                           | 1.26.2      | 1.26.2         | managing Kubernetes |
| [psycopg2-binary](https://pypi.org/project/psycopg2-binary/)               | 2.9.5       | 2.9.5          | connecting to PostgreSQL |
| [a2wsgi](https://pypi.org/project/a2wsgi/)                                 | 1.7.0       | 1.7.0          | serving Django app in ASGI server |
| [PyYAML](https://pypi.org/project/PyYAML/)                                 | 6.0         | 6.0            | parsing YAML config files |
| [Jinja2](https://pypi.org/project/Jinja2/)                                 | 3.1.2       | 3.1.2          | templating Dockerfiles |
| [schedule](https://pypi.org/project/schedule/)                             | 1.1.0       | 1.1.0          | running periodic tasks |
| [psutil](https://pypi.org/project/psutil/)                                 | 5.9.4       | 5.9.4          | monitoring running processes |
| [pydantic](https://pypi.org/project/pydantic/)                             | 1.10.5      | 1.10.5         | schema validation |
| [typer](https://pypi.org/project/typer/)                                   | 0.7.0       | 0.7.0          | parsing command line arguments |
| [uvicorn](https://pypi.org/project/uvicorn/)                               | 0.20.0      | 0.20.0         | serving ASGI app |
| [httpx](https://pypi.org/project/httpx/)                                   | 0.23.3      | 0.23.3         | making HTTP requests |
| [pyjwt](https://pypi.org/project/PyJWT/)                                   | 2.6.0       | 2.6.0          | handling JWT tokens |
| [python-multipart](https://pypi.org/project/python-multipart/)             | 0.0.6       | 0.0.6          | handling uploaded plugins |
| [watchdog](https://pypi.org/project/watchdog/)                             | 2.3.1       | 2.3.1          | watching for changes in plugins |
| [protobuf](https://pypi.org/project/protobuf/)                             | 4.22.0      | 4.22.0         | handling OTLP |
| [pytest](https://pypi.org/project/pytest/)                                 | 7.2.1       | 7.2.1          | running tests |
| [coverage](https://pypi.org/project/coverage/)                             | 7.2.1       | 7.2.1          | measuring test coverage |
| [httpretty](https://pypi.org/project/httpretty/)                           | 1.1.4       | 1.1.4          | mocking HTTP requests |
| [opentelemetry-exporter-otlp-proto-http](https://pypi.org/project/opentelemetry-exporter-otlp-proto-http/) | 1.16.0 | 1.16.0 | sending traces to OpenTelemetry |
| [Gin](https://github.com/gin-gonic/gin)                                    | 1.9.0       | 1.9.0          | Web framework for Go |
| [log15](https://github.com/inconshreveable/log15)                          | 3.0.0       | 3.0.0          | structured logging in Go | 
| [pkg/errors](https://github.com/pkg/errors)                                | 0.9.1       | 0.9.1          | wrapping errors context | 
| [Prometheus Go client library](https://github.com/prometheus/client_golang)| 1.14.0      | 1.14.0         | metrics exposure in Go |
