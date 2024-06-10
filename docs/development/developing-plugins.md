# Developing plugins

## How does plugin work?
When Racetrack starts up, it scans for plugins. Each plugin is a zip file,
and the process for loading them goes like this:
 
1. Extract the plugin code from the zip file.
2. If the plugin includes a `requirements.txt` file, it installs the dependencies.
3. Racetrack loads the `plugin.py` file, which should define a class called `Plugin`.
   This class is then instantiated and kept in internal plugins list.
 
When certain customizable events occur, the plugin engine is notified.
All the plugin hooks are then called, in order of their priority:
 
- Plugins have a default priority of 0.
- Plugins with the lowest priority get executed first.
- If multiple plugins have the same priority, they are executed in the order they were added in the configuration file.

## Creating a plugin
Create a git repo, copy [plugin_sample](plugin_sample) to it
and modify the hooks implementation as you like.
Use same virtualenv from racetrack repository 
(your plugin can use the same dependencies as Lifecycle does).

Check out [plugins-job-types.md](./plugins-job-types.md)
to see how to create a job-type plugin.

### Using additional dependencies
Plugins can use additional dependencies (Python packages).
You can include them in a `requirements.txt` file.
It will be installed using pip so you can use these dependencies in your plugin's code.

### Create a plugin manifest
Create `plugin-manifest.yaml` file in a plugin directory.
Basically, it contains the metadata of the plugin.
It can have the following fields in YAML format:

- `name` (**required**, **string**) - name of the plugin
- `version` (**required**, **string**) - version of the plugin
- `url` (optional, **string**) - a link to the plugin page
- `priority` (optional, **integer**) - order in plugins sequence, lowest priority gets executed first. Integer field, 0 by default.
- `category` (optional, **string**) - kind of the plugin, either 'infrastructure', 'job-type' or 'core'
- `components` (optional, **list of strings**) - list of Racetrack components that the plugin should be running on, e.g. `lifecycle`, `image-builder`.
  If it's empty, plugins are loaded on all components.

Example:
```yaml
name: skynet-watcher
version: 1.2.3
url: https://github.com/TheRacetrack/racetrack
priority: -1
category: core
components:
  - lifecycle
```

### Building a plugin
Local source code of the plugin can be turned into a ZIP file
by means of a `racetrack` client tool.

1.  Install `racetrack` client:
    ```shell
    python3 -m pip install --upgrade racetrack-client
    ```
2. Go to the directory where your plugin is located.
3. Make sure the plugin version inside `plugin-manifest.yaml` is up-to-date.
4. Run `racetrack plugin bundle` to turn a plugin into a ZIP file.
  Zipped plugin will be generated in a plugin directory.
  See the output to locate the outcome package.

See [plugin_sample](plugin_sample) for an example of a plugin.

## Supported hooks
To add functionality to the plugin, you can implement one of the following hooks (Python methods):

### `post_job_deploy`
`post_job_deploy` implements supplementary actions invoked after a job is deployed.
```python
from racetrack_client.manifest import Manifest
from racetrack_commons.entities.dto import JobDto

class Plugin:
    def post_job_deploy(self, manifest: Manifest, job: JobDto, image_name: str, deployer_username: str = None):
        ...
```

### `job_runtime_env_vars`
`job_runtime_env_vars` provides supplementary env vars dictionary added to runtime vars when deploying a Job.
```python
class Plugin:
    def job_runtime_env_vars(self) -> dict[str, str] | None:
        return {
            'SKYNET_ENGAGED': '1',
        }
```

### `job_types`
`job_types` method declares all Job types provided by this plugin.
It returns a dictionary, where a key is a job type name with version (e.g. `python3:1.0.2`)
and the value is a **Job Type Definition** object.

**Job Type Definition** describes the details of the job images used by the job.
It's a dictionary that has the key `images`, which is a list of **Job Image Definition** objects.
If the job consists of a single container, the list will contain only one element.

**Job Image Definition** is a dictionary with the following properties:

- `dockerfile_path` (**string**) - a relative path to the Dockerfile
- `source` (**string enum**) -
  it's either `"jobtype"` or `"job"`, depending on the location of the expected Dockerfile.

  - Choose `"jobtype"`, if a Dockerfile is provided by a job type plugin, in a ZIP bundle.
  - Choose `"job"`, if a Dockerfile will be provided by the Job itself, taken from the Job's repository.

- `template` (**boolean**) - whether Dockerfile is a template and contains variables to evaluate.

For instance, if a job type needs just one container, `job_types` may return the following object with a path pointing to a Dockerfile template:
```python
class Plugin:
    def job_types(self) -> dict[str, dict]:
        return {
            'python3:1.0.2': {
                'images': [
                    {
                        'source': 'jobtype',
                        'dockerfile_path': 'job-template.Dockerfile',
                        'template': True,
                    },
                ],
            },
        }
```
Another example of a "dockerfile" job type, where the Jobs provide its own image:
```python
class Plugin:
    def job_types(self) -> dict[str, dict]:
        return {
            'dockerfile:1.0.0': {
                'images': [
                    {
                        'source': 'job',
                        'dockerfile_path': 'Dockerfile',
                        'template': False,
                    },
                ],
            },
        }
```

### `infrastructure_targets`
**Infrastructure Targets** (deployment targets for Jobs) are provided by `infrastructure_targets` method of the plugin.
```python
from typing import Any

class Plugin:
    def infrastructure_targets(self) -> dict[str, Any]:
        """
        Infrastructure Targets (deployment targets for Jobs) provided by this plugin
        Infrastructure Target should contain Job Deployer, Job Monitor and Job Logs Streamer.
        :return dict of infrastructure name -> an instance of lifecycle.infrastructure.model.InfrastructureTarget
        """
        return {}
```

`infrastructure_targets` hook expects instances of `lifecycle.infrastructure.model.InfrastructureTarget`.
Here's the overview of the most important classes: 

#### Class `lifecycle.infrastructure.model.InfrastructureTarget`

- `name: str | None` - name of the infrastructure target
- `job_deployer: JobDeployer | None` - instance of `lifecycle.deployer.base.JobDeployer`, see below.
- `job_monitor: JobMonitor | None` - instance of `lifecycle.monitor.base.JobMonitor`, see below.
- `logs_streamer: LogsStreamer | None` - instance of `lifecycle.monitor.base.LogsStreamer`, see below.
- `remote_gateway_url: str | None` - Address of a remote Pub in case of "remote gateway mode".
- `remote_gateway_token: str | None` - Auth token for internal communication in case of "remote gateway mode".

#### Class `lifecycle.deployer.base.JobDeployer`

`JobDeployer` should contain the logic responsible for deploying jobs, deleting jobs and managing secrets.

- `deploy_job` - Deploy a Job from a manifest file
```python
from racetrack_client.manifest import Manifest
from racetrack_commons.entities.dto import JobDto, JobFamilyDto
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config

class JobDeployer:
    def deploy_job(
        self,
        manifest: Manifest,
        config: Config,
        plugin_engine: PluginEngine,
        tag: str,
        runtime_env_vars: dict[str, str],
        family: JobFamilyDto,
        containers_num: int = 1,
        runtime_secret_vars: dict[str, str] | None = None,
    ) -> JobDto:
        ...
```

- `delete_job` - Delete a Job based on its name
```python
class JobDeployer:
    def delete_job(self, job_name: str, job_version: str) -> None:
        ...
```

- `job_exists` - Tell whether a Job already exists or not
```python
class JobDeployer:
    def job_exists(self, job_name: str, job_version: str) -> bool:
        ...
```

- `save_job_secrets` - Create or update secrets needed to build and deploy a Job
```python
from lifecycle.deployer.secrets import JobSecrets

class JobDeployer:
    def save_job_secrets(
        self,
        job_name: str,
        job_version: str,
        job_secrets: JobSecrets,
    ) -> None:
        ...
```

- `get_job_secrets` - Retrieve secrets for building and deploying a Job
```python
from lifecycle.deployer.secrets import JobSecrets

class JobDeployer:
    def get_job_secrets(
        self,
        job_name: str,
        job_version: str,
    ) -> JobSecrets:
        ...
```

#### Class `lifecycle.monitor.base.JobMonitor`

`JobMonitor` implements the logic responsible for discovering workloads running in a cluster and monitoring their condition.

- `list_jobs` - List jobs deployed in a cluster
```python
from typing import Iterable
from racetrack_commons.entities.dto import JobDto
from lifecycle.config import Config

class JobMonitor:
    def list_jobs(self, config: Config) -> Iterable[JobDto]:
        yield JobDto(...)
```

- `check_job_condition` - Verify if deployed Job is really operational. If not, raise exception with reason
```python
from typing import Callable
from racetrack_commons.entities.dto import JobDto

class JobMonitor:
    def check_job_condition(self,
                            job: JobDto,
                            deployment_timestamp: int = 0,
                            on_job_alive: Callable = None,
                            logs_on_error: bool = True,
                            ) -> None:
        """
        Verify if deployed Job is really operational. If not, raise exception with reason
        :param job: job data
        :param deployment_timestamp: timestamp of deployment to verify if the running version is really the expected one
        If set to zero, checking version is skipped.
        :param on_job_alive: handler called when Job is live, but not ready yet
        (server running already, but still initializing)
        :param logs_on_error: if True, logs are read from the Job and returned in the exception in case of failure
        """
```

- `read_recent_logs` - Return last output logs from a Job
```python
from racetrack_commons.entities.dto import JobDto

class JobMonitor:
    def read_recent_logs(self, job: JobDto, tail: int = 20) -> str:
        """
        Return last output logs from a Job
        :param job: job data
        :param tail: number of recent lines to show
        :return logs output lines joined in a one string
        """
```

#### Class `lifecycle.monitor.base.LogsStreamer`

`LogsStreamer` is responsible for producing logs from the jobs, setting up & tearing down sessions providing live logs stream.

- `create_session` - Start a session transmitting messages to client
```python
from typing import Callable

class LogsStreamer:
    def create_session(self, session_id: str, resource_properties: dict[str, str], on_next_line: Callable[[str, str], None]) -> None:
        """
        Start a session transmitting messages to client.
        Session should call `broadcast` method when next message arrives.
        :param session_id: ID of a client session to be referred when closing
        :param resource_properties: properties describing a resource to be monitored (job name, version, etc)
        :param on_next_line: callback for sending log messages to connected clients. Parameters: session_id: str, message: str
        """
```

- `close_session` - Close session when a client disconnects
```python
class LogsStreamer:
    def close_session(self, session_id: str) -> None:
        ...
```


### `markdown_docs`
Return documentation for this plugin in markdown format
```python
class Plugin:
    def markdown_docs(self) -> str | None:
        return "# Plugin Reference"
```

### `post_job_delete`
Supplementary actions invoked after job is deleted
```python
from racetrack_commons.entities.dto import JobDto

class Plugin:
    def post_job_delete(self, job: JobDto, username_executor: str = None):
        """
        Supplementary actions invoked after job is deleted
        :param username_executor: username of the user who deleted the job
        """
```

### `run_action` 
Call a supplementary action of a plugin
```python
from typing import Any

class Plugin:
    def run_action(self, **kwargs) -> Any:
        """Call a supplementary action of a plugin"""
```

### `validate_job_manifest` 
Validate job's manifest in terms of job type specific parts
```python
from racetrack_client.manifest import Manifest

class Plugin:
    def validate_job_manifest(self, manifest: Manifest, job_type: str):
        """
        Validate job's manifest in terms of job type specific parts.
        :param manifest: job's manifest
        :param job_type: job type name with the version
        :raise Exception in case of validation error
        """
```
