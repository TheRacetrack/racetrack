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

Example:
```yaml
name: skynet-watcher
version: 1.2.3
url: https://github.com/TheRacetrack/racetrack
priority: -1
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
    :return dict of infrastructure name -> an instance of lifecycle.deployer.infra_target.InfrastructureTarget
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
