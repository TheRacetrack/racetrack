# Racetrack plugins
Racetrack instance might be enriched by plugins that add 
customized, tailored functionality to a generic Racetrack.

## Installing / Uninstalling plugin
To activate the plugin in Racetrack, you need the ZIP plugin file.
Go to the Dashboard Administration page
(you need to be privileged, staff user to see this tab)
and upload the zipped plugin there.

To disable a plugin, click "Delete" button next to a plugin.

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
Source code of the plugin can be bundled into a ZIP file
by means of a `racetrack-plugin-bundler` tool.
Here's [how to install racetrack-plugin-bundler](../../utils/plugin_bundler/README.md).

Make sure the plugin version inside `plugin-manifest.yaml` is up-to-date.

Then, you can run `racetrack-plugin-bundler bundle` to turn a plugin into a ZIP file.
Zipped plugin will be generated in a plugin directory.

See [plugin_sample](plugin_sample) for an example of a plugin.

## Supported hooks
Supported hooks (events) that can be overriden in the plugin class:

- `post_fatman_deploy` - Supplementary actions invoked after fatman is deployed
```python
def post_fatman_deploy(self, manifest: Manifest, fatman: FatmanDto, image_name: str, deployer_username: str = None):
```

- `fatman_runtime_env_vars` - Supplementary env vars dictionary added to runtime vars when deploying a Fatman
```python
def fatman_runtime_env_vars(self) -> Optional[Dict[str, str]]:
```

- `fatman_job_types` - Job types provided by this plugin
```python
def fatman_job_types(self, docker_registry_prefix: str) -> Dict[str, Tuple[str, Path]]:
    """
    Job types provided by this plugin
    :param docker_registry_prefix: prefix for the image names (docker registry + namespace)
    :return dict of job name -> (base image name, dockerfile template path)
    """
```

- `fatman_deployers` - Fatman Deployers provided by this plugin
```python
def fatman_deployers(self) -> Dict[str, Any]:
    """
    Fatman Deployers provided by this plugin
    :return dict of deployer name -> an instance of lifecycle.deployer.base.FatmanDeployer
    """
```

- `fatman_monitors` - Fatman Monitors provided by this plugin
```python
def fatman_monitors(self) -> Dict[str, Any]:
    """
    Fatman Monitors provided by this plugin
    :return dict of deployer name -> an instance of lifecycle.monitor.base.FatmanMonitor
    """
```

- `fatman_logs_streamers` - Fatman Monitors provided by this plugin
```python
def fatman_logs_streamers(self) -> Dict[str, Any]:
    """
    Fatman Monitors provided by this plugin
    :return dict of deployer name -> an instance of lifecycle.monitor.base.LogsStreamer
    """
```

- `markdown_docs` - Return documentation for this plugin in markdown format
```python
def markdown_docs(self) -> Optional[str]:
```

- `post_fatman_delete` - Supplementary actions invoked after fatman is deleted
```python
def post_fatman_delete(self, fatman: FatmanDto, username_executor: str = None):
    """
    Supplementary actions invoked after fatman is deleted
    :param username_executor: username of the user who deleted the fatman
    """
```
