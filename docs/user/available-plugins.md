# Available plugins
Racetrack instance might be enriched by plugins that add 
customized, tailored functionality to a generic Racetrack.

These are the known, public Racetrack plugins that are commonly available to be installed:

- Job types:

    - [Python 3 Job Type](https://github.com/TheRacetrack/plugin-python-job-type)
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
      ```

    - [Dockerfile-based Job Type](https://github.com/TheRacetrack/plugin-docker-proxy-job-type)
      (any language or app wrapped in a Dockerfile like Drupal or Sphinx)
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-docker-proxy-job-type
      ```

    - [Golang (Go) Job Type](https://github.com/TheRacetrack/plugin-go-job-type)
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-go-job-type
      ```

    - [Rust Job Type](https://github.com/TheRacetrack/plugin-rust-job-type)
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-rust-job-type
      ```

    - [HUGO Job Type](https://github.com/TheRacetrack/plugin-hugo-job-type)
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-hugo-job-type
      ```

- Infrastructure Targets:

    - [Docker infrastructure](https://github.com/TheRacetrack/plugin-docker-infrastructure) -
      deploys to a local (in-place) Docker
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-docker-infrastructure
      ```

    - [Kubernetes infrastructure](https://github.com/TheRacetrack/plugin-kubernetes-infrastructure) -
      deploys to local Kubernetes
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
      ```

    - [Remote Docker](https://github.com/TheRacetrack/plugin-remote-docker) -
      deploys to remote Docker Daemon
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-remote-docker
      ```

    - [Remote Kubernetes](https://github.com/TheRacetrack/plugin-remote-kubernetes) -
      deploys to remote Kubernetes
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-remote-kubernetes
      ```

- Others:

    - [Teams notifications](https://github.com/TheRacetrack/plugin-teams-notifications) -
      Sending notifications to Teams channel
      ```
      racetrack plugin install github.com/TheRacetrack/plugin-teams-notifications
      ```

## What's next?
- [How to install a plugin](./using-plugins.md)
