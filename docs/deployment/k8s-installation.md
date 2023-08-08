# Installation to non-local Kubernetes

This guide will walk you through the steps to install Racetrack on a non-local Kubernetes cluster,
such as AKS, GKE, EKS or a self-hosted Kubernetes.

## Prerequisites

1. Install [kubectl](https://kubernetes.io/docs/tasks/tools/) (version 1.24.3 or higher)

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

## Prepare Docker Registry
Racetrack needs a Docker registry to store the images of the jobs.
We need to instruct Kubernetes to pull images from there.

Let's assume we have a Docker registry at `ghcr.io/theracetrack/racetrack/` with
`racetrack-registry` user and `READ_REGISTRY_TOKEN` and `WRITE_REGISTRY_TOKEN`
tokens for reading and writing images respectively.

Fill in your secrets for the registry in the **kustomize/external/docker-registry-secret.yaml** file.
Remember to replace `READ_REGISTRY_TOKEN`, `WRITE_REGISTRY_TOKEN`, `REGISTRY_HOSTNAME` and `REGISTRY_USERNAME`.
```shell
REGISTRY_HOSTNAME=ghcr.io
REGISTRY_USERNAME=racetrack-registry
READ_REGISTRY_TOKEN=blahblah
WRITE_REGISTRY_TOKEN=blahblah

kubectl create secret docker-registry docker-registry-read-secret \
    --docker-server="$REGISTRY_HOSTNAME" \
    --docker-username="$REGISTRY_USERNAME" \
    --docker-password="$READ_REGISTRY_TOKEN" \
    --namespace=racetrack \
    --dry-run=client -oyaml > kustomize/external/docker-registry-secret.yaml
echo "---" >> kustomize/external/docker-registry-secret.yaml
kubectl create secret docker-registry docker-registry-write-secret \
    --docker-server="$REGISTRY_HOSTNAME" \
    --docker-username="$REGISTRY_USERNAME" \
    --docker-password="$WRITE_REGISTRY_TOKEN" \
    --namespace=racetrack \
    --dry-run=client -oyaml >> kustomize/external/docker-registry-secret.yaml
```

Accordingly, set the registry address and namespace in these 2 configuration files:

- **kustomize/external/image-builder.config.yaml**
- **kustomize/external/lifecycle.config.yaml**

by changing the following lines:
```yaml
docker_registry: ghcr.io
docker_registry_namespace: 'theracetrack/racetrack'
```

## Prepare Kubernetes resources

If needed, make another adjustments in **kustomize/external/** files.
See [Production Deployment](#production-deployment) section before deploying Racetrack to production.

You can set a static LoadBalancer IP for all public services exposed by an Ingress Controller.
To do so, add the appropriate annotations to the `ingress-nginx-controller` service in a `kustomize/external/ingress-controller.yaml` file.

Remember to replace all occurrences of `$YOUR_IP` with your IP address in all the places below:
```
YOUR_IP=1.1.1.1
```

In case of AKS, it could look like this:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ingress-nginx-controller
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-ipv4: $YOUR_IP
    service.beta.kubernetes.io/azure-load-balancer-resource-group: MC_resource_group
spec:
  type: LoadBalancer
...
```

Now, let's make Racetrack aware of this IP address.
If you don't know the exact IP address of the LoadBalancer, you can skip this step for now.
It will be assigned after the first deployment, then you can get back to this step, set the IP address and apply it again.

Fill in the public IP in the following places, replacing `$YOUR_IP` placeholder:

- `EXTERNAL_LIFECYCLE_URL` and `EXTERNAL_PUB_URL` env variables in **kustomize/external/dashboard.yaml**
- `PUBLIC_IP` env variable in **kustomize/external/lifecycle.yaml**
- `PUBLIC_IP` env variable in **kustomize/external/lifecycle-supervisor.yaml**
- `external_pub_url` in **kustomize/external/lifecycle.config.yaml**

## Generate passwords & auth tokens

Let's generate unique, secure passwords for the database, authentication encryption and tokens.

### Database password
```shell
POSTGRES_PASSWORD="$(openssl rand -base64 24)"
echo POSTGRES_PASSWORD = $POSTGRES_PASSWORD
```

Use the provided database password in the following places, replacing `$POSTGRES_PASSWORD` placeholder:

- **kustomize/external/postgres.env**, in `POSTGRES_PASSWORD` env variable
- **kustomize/external/pgbouncer.env**, in `DB_PASSWORD` and `DATA_SOURCE_NAME` variables
- **kustomize/external/postgres.yaml**, in `db.sql`

### Django secret
```shell
SECRET_KEY="django-secret-$(openssl rand -base64 24)"
echo SECRET_KEY = $SECRET_KEY
```

Use the provided secret in the following places, replacing `$SECRET_KEY` placeholder:

- **kustomize/external/lifecycle.env**, in `SECRET_KEY` env variable

### Auth key
```shell
export AUTH_KEY="$(openssl rand -base64 24)"
echo AUTH_KEY = $AUTH_KEY
```

Use the provided secret key in the following places, replacing `$AUTH_KEY` placeholder:

- **kustomize/external/lifecycle.env**, in `AUTH_KEY` env variable

### Internal tokens

Now that you have `AUTH_KEY`, you can generate the tokens for components of Racetrack, 
which will be used for their internal communication.

```shell
export AUTH_KEY
python -m lifecycle generate-auth pub # PUB's token
python -m lifecycle generate-auth dashboard # Dashboard's token
python -m lifecycle generate-auth image-builder # Image-builder's token
```
Make sure you've run `make setup` and `. venv/bin/activate` in the root of
[racetrack](https://github.com/TheRacetrack/racetrack)'s repository beforehand, to be able to run Lifecycle's script.

Copy the tokens provided and paste them into the following files:

- Replace `$PUB_LIFECYCLE_AUTH_TOKEN` in **kustomize/external/pub.yaml** with PUB's token.
- Replace `$DASHBOARD_LIFECYCLE_AUTH_TOKEN` in **kustomize/external/dashboard.yaml** with Dashboard's token.
- Replace `$IMAGE_BUILDER_LIFECYCLE_AUTH_TOKEN` in **kustomize/external/image-builder.yaml** with Image-builder's token.

## Deploy Racetrack

Once you're ready, deploy Racetrack's resources to your cluster:
```sh
kubectl apply -k kustomize/external/
```

After that, verify the status of your deployments using one of your favorite tools:

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

Install racetrack-client using pip:
```shell
python3 -m pip install --upgrade racetrack-client
```

Log in to the *Racetrack Dashboard* at `http://$YOUR_IP/dashboard` with default login `admin` and password `admin`.
Then, go to the *Profile* tab and copy your auth token.
Please replace the following occurrences of `$USER_TOKEN` with your token or set it as an environment variable:
```shell
USER_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI
```

Go back to the command line and configure a few things with the racetrack client:
```sh
# Set the current Racetrack's remote address
racetrack set remote http://$YOUR_IP/lifecycle
# Login to Racetrack (use your Auth Token)
racetrack login $USER_TOKEN
# Activate python3 job type in the Racetrack - we're gonna deploy Python jobs
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
# Activate kubernetes infrastructure target in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
```

## Deploy a first job

Let's use the Racetrack's sample model which purpose is to add numbers.

Clone the [Racetrack's repository](https://github.com/TheRacetrack/racetrack)
and run `racetrack deploy` command:
```shell
git clone https://github.com/TheRacetrack/racetrack
cd racetrack
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
curl -X POST "http://$YOUR_IP/pub/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: $USER_TOKEN" \
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

- Check what resources you're actually trying to deploy with `kubectl kustomize kustomize/external`

## Production Deployment

Bunch of improvements to keep in mind before deploying Racetrack to production:

- After logging in to Dashboard, create a new adminitrator account with a strong password and deactivate the default *admin* user.
- Make sure to enable TLS traffic to your cluster, since **PUB** and **Lifecycle API**
  will receive secret tokens, which otherwise would be sent plaintext.
- Encrypt your secrets, for instance, using [SOPS](https://github.com/mozilla/sops) tool
  in order not to store them in your repository.

## Clean up
Delete the resources when you're done:
```shell
kubectl delete -k kustomize/external/
```
