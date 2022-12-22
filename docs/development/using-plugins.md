# Using plugins
Racetrack instance might be enriched by plugins that add 
customized, tailored functionality to a generic Racetrack.

## Available plugins
These are the known, public Racetrack plugins that are commonly available to be installed:

- Job types:
    - [github.com/TheRacetrack/plugin-python-job-type](https://github.com/TheRacetrack/plugin-python-job-type) -
      Python 3 Job Type
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
      ```

    - [github.com/TheRacetrack/plugin-docker-http-job-type](https://github.com/TheRacetrack/plugin-docker-http-job-type) -
      Dockerfile-based Job Type
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-docker-http-job-type
      ```

    - [github.com/TheRacetrack/plugin-go-job-type](https://github.com/TheRacetrack/plugin-go-job-type) -
      Golang (Go) Job Type
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-go-job-type
      ```

    - [github.com/TheRacetrack/plugin-rust-job-type](https://github.com/TheRacetrack/plugin-rust-job-type) -
      Rust Job Type
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-rust-job-type
      ```

    - [github.com/TheRacetrack/plugin-docker-proxy-job-type](https://github.com/TheRacetrack/plugin-docker-proxy-job-type) -
      Docker Proxy jobs (like Drupal or Sphinx)
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-docker-proxy-job-type
      ```

    - [https://github.com/TheRacetrack/plugin-hugo-job-type](https://github.com/TheRacetrack/plugin-hugo-job-type) -
      HUGO Job Type
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-hugo-job-type
      ```

- Infrastructure Targets:
    - [github.com/TheRacetrack/plugin-docker-daemon-deployer](https://github.com/TheRacetrack/plugin-docker-daemon-deployer) -
      deploys to remote Docker Daemon
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-docker-daemon-deployer
      ```

    - [github.com/TheRacetrack/plugin-docker-infrastructure](https://github.com/TheRacetrack/plugin-docker-infrastructure) -
      deploys to a local Docker
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-docker-infrastructure
      ```

    - [github.com/TheRacetrack/plugin-kubernetes-infrastructure](https://github.com/TheRacetrack/plugin-kubernetes-infrastructure) -
      deploys to Kubernetes
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
      ```

- Others:
    - [github.com/TheRacetrack/plugin-teams-notifications](https://github.com/TheRacetrack/plugin-teams-notifications) -
      Sending notifications to Teams channel
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-teams-notifications
      ```

## Installing / Uninstalling plugin
### From a dashboard
To activate the plugin in Racetrack, you need the ZIP plugin file.
Go to the Dashboard Administration page
(you need to be privileged, staff user to see this tab)
and upload the zipped plugin there.

To disable a plugin, click "Delete" button next to a plugin.

### From a racetrack-client
Plugins can be installed by means of racetrack-client command
`racetrack plugin install <plugin_uri> <racetrack_url>`,
where `plugin_uri` can be either:

- local file path (eg. `python3-job-type-2.4.0.zip`),
- URL to a remote HTTP file (eg. `https://github.com/TheRacetrack/plugin/releases/download/2.4.0/python3-job-type-2.4.0.zip`),
- GitHub repository name (eg. `github.com/TheRacetrack/plugin-python-job-type`) -
  it takes the ZIP file from the latest release.
  Pay attention to omit `https://` part.
- GitHub repository name with version (eg. `github.com/TheRacetrack/plugin-python-job-type==2.4.0`) -
  it takes the ZIP file from the specific release.
  Pay attention to omit `https://` part.

For instance, use the following command to activate the latest python3 plugin on your local kind setup:
```
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type http://localhost:7002
```

Plugins can be uninstalled with a command:
```
racetrack plugin uninstall <plugin_name> <plugin_version> <racetrack_url>
```

List of currently installed plugins can be checked with:
```
racetrack plugin list <racetrack_url>
```

`<racetrack_url>` argument is not needed in above commands,
once you specified the current remote address with:
```
racetrack config racetrack_url <name_or_url>
```
