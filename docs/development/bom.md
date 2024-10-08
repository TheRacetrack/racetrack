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

| Tool                                                                                                       | Our version | Latest version | Purpose                                         |
|------------------------------------------------------------------------------------------------------------|-------------|----------------|-------------------------------------------------|
| [a2wsgi](https://pypi.org/project/a2wsgi/)                                                                 | 1.7.0       | 1.7.0          | serving Django app in ASGI server               |
| [Axios](https://github.com/axios/axios)                                                                    | 1.3.5       | 1.4.0          | HTTP front-end client                           |
| [backoff](https://pypi.org/project/backoff/)                                                               | 2.2.1       | 2.2.1          | repeating attempts in case of error             |
| [Bootstrap](https://getbootstrap.com/docs/versions/)                                                       | 5.0.1       | 5.3            | Dashboard's UI components                       |
| [coverage](https://pypi.org/project/coverage/)                                                             | 7.2.1       | 7.2.1          | measuring test coverage                         |
| [Django](https://pypi.org/project/Django)                                                                  | 4.1.7       | 4.1.7          | Lifecycle Admin panel, Dashboard UI             |
| [Docker](https://docs.docker.com/engine/release-notes/)                                                    | 20.10.17    | 23.0.1         | distributing Racetrack, building job images     |
| [FastAPI](https://github.com/tiangolo/fastapi)                                                             | 0.92.0      | 0.92.0         | serving API by Python components                |
| [Gin](https://github.com/gin-gonic/gin)                                                                    | 1.9.0       | 1.9.0          | Web framework for Go                            |
| [Grafana](https://github.com/grafana/grafana)                                                              | 10.1.4      | 10.1.4         | Metrics visualization                           |
| [github-markdown-css](https://github.com/sindresorhus/github-markdown-css)                                 | 5.1.0       | 5.2.0          | rendering docs                                  |
| [git](https://github.com/git/git)                                                                          | 2.44.0      | 2.44.0         | cloning job repositories                        |
| [Go](https://go.dev/dl/)                                                                                   | 1.22        | 1.22           | PUB code                                        |
| [httpretty](https://pypi.org/project/httpretty/)                                                           | 1.1.4       | 1.1.4          | mocking HTTP requests                           |
| [httpx](https://pypi.org/project/httpx/)                                                                   | 0.23.3      | 0.23.3         | making HTTP requests                            |
| [Jinja2](https://pypi.org/project/Jinja2/)                                                                 | 3.1.2       | 3.1.2          | templating Dockerfiles                          |
| [Highlight.js](https://github.com/highlightjs/highlight.js)                                                | 11.8.0      | 11.8.0         | YAML syntax highlighter on front-end            |
| [kubectl](https://github.com/kubernetes/kubectl)                                                           | 1.26.2      | 1.26.2         | managing Kubernetes                             |
| [Kubernetes Python Client](https://pypi.org/project/kubernetes/)                                           | 26.1.0      | 26.1.0         | managing Kubernetes                             |
| [log15](https://github.com/inconshreveable/log15)                                                          | 3.0.0       | 3.0.0          | structured logging in Go                        | 
| [Node.js](https://github.com/nodejs/node)                                                                  | 18.16       | 20.1.0         | Dashboard's development environment             |
| [nvm](https://github.com/nvm-sh/nvm)                                                                       | 0.39.3      | 0.39.3         | Management of Node versions                     |
| [pkg/errors](https://github.com/pkg/errors) (**archived repository**)                                      | 0.9.1       | 0.9.1          | wrapping errors context                         | 
| [PostgreSQL](https://www.postgresql.org/docs/release/)                                                     | 16.0        | 16.0           | Database for jobs and users                     |
| [PostgreSQL Server Exporter](https://github.com/prometheus-community/postgres_exporter)                    | 0.14.0      | 0.14.0         | PostgreSQL metrics                              |
| [PgBouncer](https://github.com/pgbouncer/pgbouncer)                                                        | 1.20.1      | 1.20.1         | Connection pooling for PostgreSQL               |
| [Prism](https://github.com/PrismJS/prism/)                                                                 | 1.28.0      | 1.29.0         | rendering code snippets in docs                 |
| [Prometheus](https://github.com/prometheus/prometheus)                                                     | 2.47.1      | 2.47.1         | collecting metrics                              |
| [Prometheus Go client library](https://github.com/prometheus/client_golang)                                | 1.14.0      | 1.14.0         | metrics exposure in Go                          |
| [prometheus-client](https://pypi.org/project/prometheus-client/)                                           | 0.16.0      | 0.16.0         | metrics exposure                                |
| [psutil](https://pypi.org/project/psutil/)                                                                 | 5.9.4       | 5.9.4          | monitoring running processes                    |
| [psycopg](https://pypi.org/project/psycopg)                                                                | 3.1.12      | 3.1.12         | connecting to PostgreSQL                        |
| [pydantic](https://pypi.org/project/pydantic/)                                                             | 1.10.5      | 1.10.5         | schema validation                               |
| [pyjwt](https://pypi.org/project/PyJWT/)                                                                   | 2.6.0       | 2.6.0          | handling JWT tokens                             |
| [pytest](https://pypi.org/project/pytest/)                                                                 | 7.2.1       | 7.2.1          | running tests                                   |
| [Python markdown](https://pypi.org/project/Markdown/)                                                      | 3.4.1       | 3.4.1          | rendering docs in Dashboard                     |
| [python-multipart](https://pypi.org/project/python-multipart/)                                             | 0.0.6       | 0.0.6          | handling uploaded plugins                       |
| [python-socketio](https://pypi.org/project/python-socketio/)                                               | 5.7.2       | 5.7.2          | Streaming logs of the job in follow mode        |
| [Python](https://www.python.org/downloads/)                                                                | 3.11        | 3.12           | Racetrack client, Lifecycle, Image builder code |
| [PyYAML](https://pypi.org/project/PyYAML/)                                                                 | 6.0         | 6.0            | parsing YAML config files                       |
| [Quasar Framework](https://github.com/quasarframework/quasar)                                              | 2.11.10     | 2.11.10        | UI components on Dashboard                      |
| [schedule](https://pypi.org/project/schedule/)                                                             | 1.1.0       | 1.1.0          | running periodic tasks                          |
| [typer](https://pypi.org/project/typer/)                                                                   | 0.7.0       | 0.7.0          | parsing command line arguments                  |
| [Typescript](https://github.com/microsoft/TypeScript)                                                      | 4.8.4       | 5.0.4          | Dashboard UI code                               |
| [uvicorn](https://pypi.org/project/uvicorn/)                                                               | 0.20.0      | 0.20.0         | serving ASGI app                                |
| [vis-network](https://github.com/visjs/vis-network)                                                        | 9.1.1       | 9.1.4          | Jobs graph in Dashboard                         |
| [Vite](https://github.com/vitejs/vite)                                                                     | 4.1.4       | 4.3.4          | Dashboard's local development and packaging     |
| [vue-router](https://github.com/vuejs/router)                                                              | 4.1.6       | 4.1.6          | Routing Vue.js pages                            |
| [vue-toastification](https://github.com/Maronato/vue-toastification)                                       | 2.0.0-rc.5  | 2.0.0-rc.5     | Web UI notifications                            |
| [Vue.js](https://github.com/vuejs/core)                                                                    | 3.2.47      | 3.2.47         | UI Web framework                                |
| [watchdog](https://pypi.org/project/watchdog/)                                                             | 2.3.1       | 2.3.1          | watching for changes in plugins                 |
| [werkzeug](https://pypi.org/project/Werkzeug/)                                                             | 2.2.3       | 2.2.3          | serving SocketIO server in tests                |
