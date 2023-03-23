# Installation to non-local Kubernetes

This guide covers installation of Racetrack to a non-local Kubernetes cluster,
such as [AKS](https://azure.microsoft.com/en-us/products/kubernetes-service), GKE, EKS or self-hosted Kubernetes.

## Prerequisites

1. Install [Kubectl](https://kubernetes.io/docs/tasks/tools/) (version 1.24.3 or higher)

## Create a Kubernetes cluster

In first place, you need a Kubernetes cluster.
For instance, let's assume we've already
[created AKS cluster on Azure](https://learn.microsoft.com/en-us/azure/aks/learn/quick-kubernetes-deploy-cli#create-aks-cluster),
and we have access to it with a `kubectl` tool.

In this tutorial the address of the `aks-racetrack` cluster is `aks-racetrack.example.com`.

Verify the connection to your cluster using the `kubectl get nodes` command.

Set this cluster as the default one:
```sh
kubectl config get-contexts
kubectl config use-context aks-racetrack
kubectl config set-context --current --namespace=racetrack
```

## Prepare Docker Registry
Racetrack needs a Docker registry to store the images of the jobs.
We need to instruct Kubernetes to pull them from there.

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

## Deploy Racetrack

If needed, make another adjustments in **kustomize/aks/** files.
See [Production Deployment](#production-deployment) section before deploying Racetrack to production.

Once you're ready, deploy Racetrack to your cluster:
```sh
kubectl apply -k kustomize/aks/
```

## Configure Racetrack

Install racetrack-client using pip:
```shell
python3 -m pip install --upgrade racetrack-client
```

Log in to the Racetrack Dashboard at http://aks-racetrack.example.com:7003/dashboard with default login `admin` and password `admin`.
Then, go to the *Profile* tab and copy your auth token.

Configure a few things with the racetrack client:
```sh
# Set the current Racetrack's remote address
racetrack set remote http://aks-racetrack.example.com:7002/lifecycle
# Login to Racetrack
racetrack login eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI
# Activate python3 job type in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-python-job-type
# Activate kubernetes infrastructure target in the Racetrack
racetrack plugin install github.com/TheRacetrack/plugin-kubernetes-infrastructure
```

## Deploy a first job

Let's create a model which purpose is to add numbers.
Keep it in a `adder` directory.

Create `adder/entrypoint.py` file with your application logic:
```python
class Entrypoint:
    def perform(self, a: float, b: float) -> float:
        """Add numbers"""
        return a + b
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

Remember to put your git remote URL in `git.remote` field and to push your changes to it.

Finally, submit your job to Racetrack:
```shell
racetrack deploy adder
```

This will convert your source code to a REST microservice workload, called **Job**.

## Call your Job

You can find your job on the Racetrack Dashboard,
which is available at http://aks-racetrack.example.com:7003/dashboard
(use default login `admin` with password `admin`).

Also, you should get the link to your Job from the `racetrack` client output.
Check it out at http://aks-racetrack.example.com:7105/pub/job/adder/latest.
This opens a SwaggerUI page, from which you can call your function
(try `/perform` endpoint with `{"a": 40, "b": 2}` body).

![](../assets/swaggerino.png)

You can do it from CLI with an HTTP client as well:
```shell
curl -X POST "http://aks-racetrack.example.com:7105/pub/job/adder/latest/api/v1/perform" \
  -H "Content-Type: application/json" \
  -H "X-Racetrack-Auth: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZWVkIjoiY2UwODFiMDUtYTRhMC00MTRhLThmNmEtODRjMDIzMTkxNmE2Iiwic3ViamVjdCI6ImFkbWluIiwic3ViamVjdF90eXBlIjoidXNlciIsInNjb3BlcyI6bnVsbH0.xDUcEmR7USck5RId0nwDo_xtZZBD6pUvB2vL6i39DQI" \
  -d '{"a": 40, "b": 2}'
# Expect: 42
```

## Troubleshooting

Consider using [k9s](https://github.com/derailed/k9s) tool to inspect your cluster.

### (Optional) Deploy Kubernetes Dashboard

You can use Kubernetes Dashboard UI to troubleshoot your application, and manage the cluster resources.

```shell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml
```

Create a token for the admin user:
```shell
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

kubectl -n kubernetes-dashboard create token admin-user
```

The last command should print out the token that lets you log in to the Kubernetes Dashboard.

Enable access to the Dashboard from your local computer, by running the following command:
```shell
kubectl proxy
```

It will make Dashboard available at [http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/](http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/).

## Production Deployment

Few improvements to keep in mind before deploying Racetrack to production:

- Make sure to enable TLS traffic to your cluster, since PUB and Lifecycle API
  will receive secret tokens, which otherwise would be sent plaintext.
- Encrypt your secrets, for instance, using [SOPS](https://github.com/mozilla/sops) tool
  in order not to store them in your repository.
- Use different database password by changing `POSTGRES_PASSWORD` in **kustomize/aks/postgres.env**.
- Use different secrets `AUTH_KEY` and `SECRET_KEY` by modifying them in **kustomize/aks/lifecycle.env**.
- Generate new tokens `LIFECYCLE_AUTH_TOKEN` for internal communication between components.
- After logging in to Dashboard, create a new Adminitrator user with a strong password and deactivate default *admin* user.

