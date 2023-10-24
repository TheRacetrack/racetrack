# Remote Kubernetes Gateway
Once you have Racetrack up and running somewhere,
you might want to connect it to an external Kubernetes cluster to keep your Jobs there.
In other words, you can distribute services between 2 separate infrastructures:

- Main Hub - hosting core Racetrack services
- Remote Jobs cluster - an infrastructure hosting jobs and remote Pub gateway.

Remote Pub gateway protects Jobs from unauthorized access.

## Requirements

- Python 3.8+ with `pip` and `venv`
- kubectl
- curl

## Install Remote Gateway
Pick an installation directory:
```sh
mkdir -p ~/racetrack && cd ~/racetrack
```
and run
```sh
sh <(curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/standalone-wizard/runner.sh)
```
Follow the installation steps. Choose `remote-kubernetes` infrastructure target.

## Install plugin

On your Racetrack's "Main Hub", install 
[remote Kubernetes plugin](https://github.com/TheRacetrack/plugin-remote-kubernetes).
You can do it with:
```
racetrack plugin install github.com/TheRacetrack/plugin-remote-kubernetes
```

Next, fill plugin's configuration with the content that has been given to you by installer:
```yaml
infrastructure_targets:
  remote-k8s:
    remote_gateway_url: 'http://1.2.3.4:7105/pub'
    remote_gateway_token: '5tr0nG_PA55VoRD'
    job_k8s_namespace: 'racetrack'

docker: 
  docker_registry: 'docker.registry.example.com'
  username: 'DOCKER_USERNAME'
  password: 'READ_WRITE_TOKEN'
```

After that, you should see a new infrastructure target available in Racetrack.
