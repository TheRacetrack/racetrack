# Developing plugins

## How does plugin work?
Loading a plugin happens in Racetrack in a following manner:

1. At startup of racetrack components,
  the plugin code is extracted from the zipped file.
1. If plugin contains `requirements.txt` file, it is installed using pip.
1. `plugin.py` Python file is loaded. Class `Plugin` is expected to be defined in it. 
  It is then instantiated and kept in internal plugins list.

When some of the customizable events happens, 
the plugin engine is notified and all plugin hooks are called in the order according to their priority:

- Plugin has priority 0 by default. 
- Lowest priority gets executed first. 
- If there are many plugins with the same priority, 
  they are executed in the order they were added in the configuration file.

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

- `name` (**required**) - name of the plugin
- `version` (**required**) - version of the plugin
- `url` (optional) - a link to the plugin page
- `priority` (optional) - order in plugins sequence, lowest priority gets executed first. Integer field, 0 by default.
- `category` (optional) - kind of the plugin, either 'infrastructure', 'job-type' or 'core'
- `components` (optional) - list of Racetrack components that the plugin should be running on, e.g. 'lifecycle', 'image-builder'.
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

1. Install `racetrack` client:
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
Supported hooks (events) that can be overriden in the plugin class:

- `post_job_deploy` - Supplementary actions invoked after job is deployed
```python
def post_job_deploy(self, manifest: Manifest, job: JobDto, image_name: str, deployer_username: str = None):
```

- `job_runtime_env_vars` - Supplementary env vars dictionary added to runtime vars when deploying a Job
```python
def job_runtime_env_vars(self) -> Optional[Dict[str, str]]:
```

- `job_types` - Job types provided by this plugin
```python
def job_types(self) -> dict[str, list[tuple[Path, Path]]]:
    """
    Job types provided by this plugin
        :return dict of job type name (with version) -> list of images: (base image path, dockerfile template path)
    """
```

- `infrastructure_targets` - Infrastructure Targets (deployment targets for Jobs) provided by this plugin.
```python
def infrastructure_targets(self) -> dict[str, Any]:
    """
    Infrastructure Targets (deployment targets for Jobs) provided by this plugin
    Infrastructure Target should contain Job Deployer, Job Monitor and Job Logs Streamer.
    :return dict of infrastructure name -> an instance of lifecycle.infrastructure.model.InfrastructureTarget
    """
    return {}
```

- `markdown_docs` - Return documentation for this plugin in markdown format
```python
def markdown_docs(self) -> Optional[str]:
```

- `post_job_delete` - Supplementary actions invoked after job is deleted
```python
def post_job_delete(self, job: JobDto, username_executor: str = None):
    """
    Supplementary actions invoked after job is deleted
    :param username_executor: username of the user who deleted the job
    """
```

- `run_action` - Call a supplementary action of a plugin
```python
def run_action(self, **kwargs) -> Any:
    """Call a supplementary action of a plugin"""
```

### Infrastructure targets
`infrastructure_targets` hook expects instances of `lifecycle.infrastructure.model.InfrastructureTarget`.
Here's the overview of the most important classes: 

#### Class `lifecycle.infrastructure.model.InfrastructureTarget`

- `name: str | None` - name of the infrastructure target
- `job_deployer: JobDeployer | None` - instance of `lifecycle.deployer.base.JobDeployer`, see below.
-  `job_monitor: JobMonitor | None` - instance of `lifecycle.monitor.base.JobMonitor`, see below.
-  `logs_streamer: LogsStreamer | None` - instance of `lifecycle.monitor.base.LogsStreamer`, see below.
-  `remote_gateway_url: str | None` - Address of a remote Pub in case of "remote gateway mode".
-  `remote_gateway_token: str | None` - Auth token for internal communication in case of "remote gateway mode".

#### Class `lifecycle.deployer.base.JobDeployer`

`JobDeployer` should contain the logic responsible for deploying jobs, deleting jobs and managing secrets.

- `deploy_job` - Deploy a Job from a manifest file
```python
    def deploy_job(
        self,
        manifest: Manifest,
        config: Config,
        plugin_engine: PluginEngine,
        tag: str,
        runtime_env_vars: Dict[str, str],
        family: JobFamilyDto,
        containers_num: int = 1,
        runtime_secret_vars: Dict[str, str] | None = None,
    ) -> JobDto:
    """Deploy a Job from a manifest file"""
```

- `delete_job` - Delete a Job based on its name
```python
    def delete_job(self, job_name: str, job_version: str):
```

- `job_exists` - Tell whether a Job already exists or not
```python
    def job_exists(self, job_name: str, job_version: str) -> bool:
```

- `save_job_secrets` - Create or update secrets needed to build and deploy a Job
```python
    def save_job_secrets(
        self,
        job_name: str,
        job_version: str,
        job_secrets: JobSecrets,
    ):
```

- `get_job_secrets` - Retrieve secrets for building and deploying a Job
```python
    def get_job_secrets(
        self,
        job_name: str,
        job_version: str,
    ) -> JobSecrets:
```

#### Class `lifecycle.monitor.base.JobMonitor`

`JobMonitor` implements the logic responsible for discovering workloads running in a cluster and monitoring their condition.

- `list_jobs` - List jobs deployed in a cluster
```python
    def list_jobs(self, config: Config) -> Iterable[JobDto]:
```

- `check_job_condition` - Verify if deployed Job is really operational. If not, raise exception with reason
```python
    def check_job_condition(self,
                            job: JobDto,
                            deployment_timestamp: int = 0,
                            on_job_alive: Callable = None,
                            logs_on_error: bool = True,
                            ):
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
    def create_session(self, session_id: str, resource_properties: dict[str, str], on_next_line: Callable[[str, str], None]):
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
    def close_session(self, session_id: str):
```
