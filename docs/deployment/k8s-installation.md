# Installation to non-local Kubernetes

This guide will walk you through the steps to install Racetrack on a non-localhost Kubernetes cluster,
such as AKS, GKE, EKS or a self-hosted Kubernetes.

## Prerequisites

- Python 3.8+ with `pip` and `venv`
- [kubectl](https://kubernetes.io/docs/tasks/tools/) (version 1.24.3 or higher)
- curl

## Create a Kubernetes cluster

The first step is to create a Kubernetes cluster.
Let's assume you have already created an
[AKS cluster on Azure](https://learn.microsoft.com/en-us/azure/aks/learn/quick-kubernetes-deploy-cli#create-aks-cluster),
and you have access to it using the `kubectl` tool.
Verify the connection to your cluster using the `kubectl get nodes` command.

Next, set this cluster as the default one:
```sh
kubectl config get-contexts
kubectl config use-context cloud-racetrack # k8s context is `cloud-racetrack` in this tutorial
kubectl config set-context --current --namespace=racetrack
```

## Install Racetrack
Pick an installation directory:
```sh
mkdir -p ~/racetrack && cd ~/racetrack
```
and run
```sh
sh <(curl -fsSL https://raw.githubusercontent.com/TheRacetrack/racetrack/master/utils/standalone-wizard/runner.sh)
```
Follow the installation steps. Choose `kubernetes` infrastructure target.
Shortly after, your Racetrack instance will be ready.

Pay attention to the output, it contains your unique admin password.

### Docker Registry
Racetrack needs a Docker registry to store the images of the jobs.
We need to instruct Kubernetes to pull images from there.
That's why you need to provide Docker registry hostname, username, `READ_REGISTRY_TOKEN` and `WRITE_REGISTRY_TOKEN`
tokens for reading and writing images respectively.

### Static IP
During the installation, you can set a static LoadBalancer IP for all public services exposed by an Ingress Controller.

Sometimes cloud providers doesn't let you know the IP address before creating a resource.
If you don't know the exact IP address of the LoadBalancer, you can skip this step for now.
It will be assigned after the first deployment, then you can get back to this step, set the IP address and apply it again.

### Reviewing Kubernetes resources
Installer generates unique, secure database password, authentication secrets and tokens.
It creates Kubernetes resources files in "generated" directory, based on your configuration.
Please review them before applying.
If needed, abort, make adjustments in **generated/** files and apply them on your own.

See [Production Deployment](#production-deployment) section before deploying Racetrack to production.

## Verify Racetrack

After running the installer, verify the status of your deployments using one of your favorite tools:

- `kubectl get pods`
- Cloud Console
- [Kubernetes Dashboard](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/)
- [k9s](https://github.com/derailed/k9s)

Assuming your Ingress Controller is now deployed at public IP `$YOUR_IP`,
you can look up the following services:

- **Racetrack Dashboard** at `http://$YOUR_IP/dashboard`,
- **Lifecycle** at `http://$YOUR_IP/lifecycle`,
- **PUB** at `http://$YOUR_IP/pub`,

## Configure Racetrack

Install racetrack-client:
```shell
python3 -m pip install --upgrade racetrack-client
```

Log in to the *Racetrack Dashboard* at `http://$YOUR_IP/dashboard`
with login `admin` and password provided to you by the installer.
Then, go to the *Profile* tab and get your auth token.

Go back to the command line and configure a few things with the racetrack client:
```sh
# Set the current Racetrack's remote address
racetrack set remote http://$YOUR_IP/lifecycle
# Login to Racetrack (enter your admin password provided by the installer)
racetrack login --username admin
# Activate python3 job type in the Racetrack - we're gonna deploy Python jobs
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
# Activate kubernetes infrastructure target in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
```

## Deploy a first job

Let's use the Racetrack's sample model which purpose is to add numbers.

Run `racetrack deploy` command on the sample directory:
```shell
racetrack deploy sample/python-class
```

This will convert the source code to a REST microservice workload, called **Job**.

## Call your Job

Go to the Dashboard at `http://$YOUR_IP/dashboard` to find your job there.

Also, you should get the link to your job from the `racetrack` client's output.
Check it out at `http://$YOUR_IP/pub/job/adder/latest`.
This opens a SwaggerUI page, from which you can call your function
(try `/perform` endpoint with `{"numbers": [40, 2]}` body).

![](../assets/swaggerino.png)

You can do it from CLI with an HTTP client as well:
```shell
curl -X POST "$(racetrack get pub)/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: $(racetrack get auth-token)" \
  -d '{"numbers": [40, 2]}'
# Expect: 42
```

Congratulations, your Racetrack Job is up and running!

## Troubleshooting

Use one of these tools to inspect your cluster resources:

- `kubectl`
- Cloud Console
- [Kubernetes Dashboard](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/)
- [k9s](https://github.com/derailed/k9s)

- Check what resources you're actually trying to deploy with `kubectl kustomize generated`

## Production Deployment

Bunch of improvements to keep in mind before deploying Racetrack to production:

- Make sure to enable TLS traffic to your cluster, since **PUB** and **Lifecycle API**
  will receive secret tokens, which otherwise would be sent plaintext.
- Encrypt your secrets, for instance, using [SOPS](https://github.com/mozilla/sops) tool
  in order not to store them in your repository.

## Clean up
Delete the resources when you're done:
```shell
kubectl delete -k generated/
```
