# Using plugins
Racetrack instance might be enriched by [plugins](./available-plugins.md) that add 
customized, tailored functionality to a generic Racetrack.

## Installing / Uninstalling plugin
### From a dashboard
To activate the plugin in Racetrack, you need the ZIP plugin file.
Go to the Dashboard Administration page
(you need to be privileged, staff user to see this tab)
and upload the zipped plugin there.

To disable a plugin, click "Delete" button next to a plugin.

### From a racetrack-client
Plugins can be installed by means of racetrack-client command
`racetrack plugin install <plugin_uri> [--remote <racetrack_url>]`,
where `plugin_uri` can be either:

- local file path (eg. `python3-job-type-2.4.0.zip`),
- URL to a remote HTTP file (eg. `https://github.com/TheRacetrack/plugin/releases/download/2.4.0/python3-job-type-2.4.0.zip`),
- GitHub repository name (eg. `github.com/TheRacetrack/plugin-python-job-type`) -
  it takes the ZIP file from the latest release.
  Pay attention to omit `https://` part.
- GitHub repository name with version (eg. `github.com/TheRacetrack/plugin-python-job-type==2.4.0`) -
  it takes the ZIP file from the specific release.
  Pay attention to omit `https://` part.

In first place, choose the current remote address, so you can omit `--remote` parameter later on:
```shell
racetrack set remote http://127.0.0.1:7002 # use local kind setup
```

For instance, use the following command to activate the latest python3 plugin:
```shell
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
```

Plugins can be uninstalled with a command:
```shell
racetrack plugin uninstall <plugin_name> <plugin_version>
```

List of currently installed plugins can be checked with:
```shell
racetrack plugin list
```

## What's next?
- [Available plugins](./available-plugins.md)
