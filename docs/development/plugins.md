# Racetrack plugins
Racetrack instance might be enriched by plugins that add 
customized, tailored functionality to a generic Racetrack.

## Installing plugin
Plugins are installed by adding them to the `plugins` list in the
Lifecycle and/or Image-builder configuration file.

Each plugin may have following fields:

- `name` - required, string, Name of the plugin
- `git_remote` - required, string, git remote url to the plugin module (with credentials if needed)
- `git_ref` - optional, string, git branch or commit hash describing plugin version
- `git_directory` - optional, string, path to the plugin module in the git repository
- `priority` - optional, integer, order in plugins sequence, lowest priority gets executed first

Plugin should be kept in an individual git repository and referenced by its remote URL,
git ref (branch, tag or commit hash) and a subdirectory where the plugin is.
If the repository is private, remote URL address should contain the username and token to access it, eg.:
```yaml
  git_remote: https://plugin-malbolge:pa55w0rd@github.com/theracetrack/plugin-malbolge
```

## Example
To activate the plugin in Racetrack, 
add the following to your Lifecycle or Image-builder configuration
(directly in local YAML or in kustomize ConfigMap):
```yaml
plugins:
- name: eradication
  git_remote: https://racetrack:token@github.com/theracetrack/racetrack
  git_ref: master
  git_directory: docs/development/plugin_sample
  priority: 0
```

See [plugin_sample](plugin_sample) for an example of a plugin.

## How does plugin work?
Loading a plugin happens in Racetrack in a following manner:

1. At startup of racetrack components,
  the plugin is cloned from the remote repository.
1. If plugin directory contains `requirements.txt` file, it is installed using pip.
1. `plugin.py` Python file is loaded. Class `Plugin` is expected to be defined in it. 
  It is then instantiated and kept in internal plugins list.

When some of the customizable events happens, 
the plugin engine is notified and all plugin hooks are called in the order according to their priority:

- Plugin has priority 0 by default. 
- Lowest priority gets executed first. 
- If there are many plugins with the same priority, 
  they are executed in the order they were added in the configuration file.

## Creating a plugin
Create a git repo, copy plugin_sample to it and modify the hooks implementation as you like.
Use same virtualenv from racetrack repository (your plugin can use the same dependencies as Lifecycle does).

Check out [plugins-job-types.md](./plugins-job-types.md)
to see how to create a job-type plugin.

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
