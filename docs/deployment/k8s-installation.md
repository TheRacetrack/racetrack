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
kubectl config use-context aks-racetrack # k8s context is `aks-racetrack` in this tutorial
kubectl config set-context --current --namespace=racetrack
```

## Prepare Docker Registry
Racetrack needs a Docker registry to store the images of the jobs.
We need to instruct Kubernetes to pull images from there.

Let's assume we have a Docker registry at `ghcr.io/theracetrack/racetrack/` with
`racetrack-registry` user and `READ_REGISTRY_TOKEN` and `WRITE_REGISTRY_TOKEN`
tokens for reading and writing images respectively.

Create a secret for the registry in **kustomize/aks/docker-registry-secret.yaml**:
```shell
kubectl create secret docker-registry docker-registry-read-secret \
    --docker-server=ghcr.io \
    --docker-username="racetrack-registry" \
    --docker-password="READ_REGISTRY_TOKEN" \
    --namespace=racetrack \
    --dry-run=client -oyaml > kustomize/aks/docker-registry-secret.yaml
echo "---" >> kustomize/aks/docker-registry-secret.yaml
kubectl create secret docker-registry docker-registry-write-secret \
    --docker-server=ghcr.io \
    --docker-username="racetrack-registry" \
    --docker-password="WRITE_REGISTRY_TOKEN" \
    --namespace=racetrack \
    --dry-run=client -oyaml >> kustomize/aks/docker-registry-secret.yaml
```

Accordingly, set the registry address and namespace in these 2 configuration files:

- **kustomize/aks/image-builder.config.yaml**
- **kustomize/aks/lifecycle.config.yaml**

by changing the following lines:
```yaml
docker_registry: ghcr.io
docker_registry_namespace: 'theracetrack/racetrack'
```

## Prepare Kubernetes resources

If needed, make another adjustments in **kustomize/aks/** files.
See [Production Deployment](#production-deployment) section before deploying Racetrack to production.

You can set a static LoadBalancer IP for all public services exposed by an Ingress Controller.
To do so, add the appropriate annotations to the `ingress-nginx-controller` service in a `kustomize/aks/ingress-controller.yaml` file.
In case of AKS, it could look like this:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: ingress-nginx-controller
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-ipv4: 1.1.1.1
    service.beta.kubernetes.io/azure-load-balancer-resource-group: MC_resource_group
spec:
  type: LoadBalancer
...
```

Now, let's make Racetrack aware of this IP address.
If you don't know the exact IP address of the LoadBalancer, you can skip this step for now.
It will be assigned after the first deployment, then you can get back to this step, set the IP address and apply it again.

Fill in the public IP in the following places:

- `EXTERNAL_LIFECYCLE_URL` and `EXTERNAL_PUB_URL` env variables in **kustomize/aks/dashboard.yaml**
- `PUBLIC_IP` env variable in **kustomize/aks/lifecycle.yaml**
- `PUBLIC_IP` env variable in **kustomize/aks/lifecycle-supervisor.yaml**
- `external_pub_url` in **kustomize/aks/lifecycle.config.yaml**

## Deploy Racetrack

Once you're ready, deploy Racetrack's resources to your cluster:
```sh
kubectl apply -k kustomize/aks/
```

After that, verify the status of your deployments using one of your favorite tools:

- `kubectl get pods`
- Cloud Console
- [Kubernetes Dashboard](#deploy-kubernetes-dashboard)
- [k9s](https://github.com/derailed/k9s)

Assuming your Ingress Controller is now deployed at public IP:
```sh
RT_HOST=http://1.1.1.1  
```
you can look up the following services:
- **Racetrack Dashboard** at `$RT_HOST/dashboard`,
- **Lifecycle** at `$RT_HOST/lifecycle`,
- **PUB** at `$RT_HOST/pub`,
- **Grafana** at `$RT_HOST/grafana`,

## Configure Racetrack

Install racetrack-client using pip:
```shell
python3 -m pip install --upgrade racetrack-client
```

Log in to the *Racetrack Dashboard* at `$RT_HOST/dashboard` with default login `admin` and password `admin`.
Then, go to the *Profile* tab and copy your auth token.

Go back to the command line and configure a few things with the racetrack client:
```sh
# Set the current Racetrack's remote address
racetrack set remote $RT_HOST/lifecycle
# Login to Racetrack (use your Auth Token)
racetrack login eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI
# Activate python3 job type in the Racetrack - we're gonna deploy Python jobs
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
# Activate kubernetes infrastructure target in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
```

## Deploy a first job

Let's create a model which purpose is to add numbers.
Let's keep it in a `adder` directory.

Create `adder/entrypoint.py` file with your application logic:
```python
class Entrypoint:
    def perform(self, numbers) -> float:
        """Add numbers"""
        return sum(numbers)
```

And a `adder/job.yaml` file describing what's inside:
```yaml
name: adder
owner_email: sample@example.com
lang: python3:latest

git:
  remote: https://github.com/TheRacetrack/samples
  directory: adder

python:
  entrypoint_path: 'entrypoint.py'
  entrypoint_class: 'Entrypoint'
```

Remember to put your git remote URL in `git.remote` field and push your changes to it.

Finally, submit your job to Racetrack:
```shell
racetrack deploy adder
```

This will convert your source code to a REST microservice workload, called **Job**.

Alternatively, you can deploy a sample from a root of the [Racetrack's repository](https://github.com/TheRacetrack/racetrack):
```shell
racetrack deploy sample/python-class
```

## Call your Job

Go to the Dashboard at `$RT_HOST/dashboard` to find your job there.

Also, you should get the link to your job from the `racetrack` client's output.
Check it out at `$RT_HOST/pub/job/adder/latest`.
This opens a SwaggerUI page, from which you can call your function
(try `/perform` endpoint with `{"numbers": [40, 2]}` body).

![](../assets/swaggerino.png)

You can do it from CLI with an HTTP client as well:
```shell
curl -X POST "$RT_HOST/pub/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
  -d '{"numbers": [40, 2]}'
# Expect: 42
```

Congratulations, your Racetrack Job is up and running!

## Troubleshooting

Use one of these tools to inspect your cluster resources:

- `kubectl`
- Cloud Console
- [Kubernetes Dashboard](#deploy-kubernetes-dashboard)
- [k9s](https://github.com/derailed/k9s)

### Deploy Kubernetes Dashboard

You can use Kubernetes Dashboard UI to troubleshoot your application, and manage the cluster resources.

```shell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Create an admin user account
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kubernetes-dashboard
EOF

cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kubernetes-dashboard
EOF

# Create a token for the admin user
kubectl -n kubernetes-dashboard create token admin-user
```

The last command should print out the token that lets you log in to the Kubernetes Dashboard.

Enable access to the Dashboard from your local computer, by running the following command:
```shell
kubectl proxy
```

It will make k8s Dashboard available at [http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/](http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/).

## Production Deployment

Bunch of improvements to keep in mind before deploying Racetrack to production:

- Make sure to enable TLS traffic to your cluster, since **PUB** and **Lifecycle API**
  will receive secret tokens, which otherwise would be sent plaintext.
- Encrypt your secrets, for instance, using [SOPS](https://github.com/mozilla/sops) tool
  in order not to store them in your repository.
- Use different database password by changing `POSTGRES_PASSWORD` in **kustomize/aks/postgres.env**.
- Use different secrets `AUTH_KEY` and `SECRET_KEY` by modifying them in **kustomize/aks/lifecycle.env**.
- Generate new tokens `LIFECYCLE_AUTH_TOKEN` for internal communication between components.
- After logging in to Dashboard, create a new adminitrator account with a strong password and deactivate the default *admin* user.
