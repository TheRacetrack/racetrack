# Setting Up Racetrack with HTTPS
This guide will walk you through how to serve Racetrack behind a secure HTTPS protocol.

## TLS/SSL Certificate
To start, you'll need a valid TLS certificate.
While this guide will show you how to create a self-signed certificate,
keep in mind that it's not suitable for production environments due to security risks,
such as being prone to man-in-the-middle attacks.
For better security, consider obtaining a certificate from a trusted source, such as Let's Encrypt.

## TLS Termination
It's a common practice to split responsibilities into two separate tasks that can be handled by different teams:

- Core Application Setup (using HTTP) - not accessible externally, developers don't need to worry about implementing TLS properly
- TLS Termination at the Edge - a secure HTTPS gateway at the system's first public entry point.

## Example of using a self-signed certificate in local Kubernetes

### Prerequisites

- Local Kubernetes running in [Kind](https://kind.sigs.k8s.io/).
- Racetrack deployed in the `racetrack` namespace.

### Setup
To create a custom self-signed TLS certificate for use on an HTTPS server, follow these steps:

1.  Generate a private key and certificate:
    ```sh
    openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout tls.key -out tls.crt -subj "/CN=ingress.local/O=nginxsvc"
    ```

2.  Create a Kubernetes secret:
    ```sh
    kubectl create secret tls tls-secret --namespace=racetrack --key tls.key --cert tls.crt
    ```
    
    Note that this will create `tls.crt` which is a self-signed certificate,
    which is not trusted by browsers and will trigger security warnings.
    Self-signed certificates are suitable for development and testing purposes,
    but not recommended for production environments.
    For production use, obtain a certificate from a trusted CA. If using a self-signed certificate
    in a controlled environment, you can create a root CA and use it to sign server certificates,
    then install the root CA certificate on client machines to avoid security warnings.

3.  Set up an Ingress Controller:
    ```sh
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
    ```
    
    If you're using a local Kubernetes environment like [Kind](https://kind.sigs.k8s.io/) or Minikube,
    you might need to patch the ingress-nginx-controller service to use NodePort
    ```sh
    kubectl patch svc ingress-nginx-controller -n ingress-nginx -p '{"spec": {"type": "NodePort", "ports": [{"nodePort": 30443, "port": 443, "targetPort": 443, "protocol": "TCP", "name": "https"}]}}'
    ```
    Don't forget to open port 443 in your Kind configuration:
    ```yaml
    apiVersion: kind.x-k8s.io/v1alpha4
    kind: Cluster
    nodes:
        extraPortMappings:
          # TLS Ingress
          - hostPort: 443
            containerPort: 30443
            listenAddress: "127.0.0.1"
            protocol: TCP
    ```

4.  Create Ingress in a `ingress.yaml` file.
    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
      namespace: racetrack
      name: nginx-test
      annotations:
        nginx.ingress.kubernetes.io/ssl-redirect: "true"
    spec:
      tls:
        - hosts:
          - ingress.local
          secretName: tls-secret
      ingressClassName: nginx
      rules:
      - http:
          paths:
          - path: /lifecycle
            pathType: Prefix
            backend:
              service:
                name: lifecycle
                port:
                  number: 7002
          - path: /lifecycle-supervisor
            pathType: Prefix
            backend:
              service:
                name: lifecycle-supervisor
                port:
                  number: 7006
          - path: /image-builder
            pathType: Prefix
            backend:
              service:
                name: image-builder
                port:
                  number: 7001
          - path: /dashboard
            pathType: Prefix
            backend:
              service:
                name: dashboard
                port:
                  number: 7003
          - path: /pub
            pathType: Prefix
            backend:
              service:
                name: pub
                port:
                  number: 7005
          - path: /prometheus
            pathType: Prefix
            backend:
              service:
                name: prometheus
                port:
                  number: 9090
          - path: /grafana
            pathType: Prefix
            backend:
              service:
                name: grafana
                port:
                  number: 3000
    ```
    
    Apply this configuration to Kubernetes:
    ```sh
    kubectl apply -f ingress.yaml
    ```

Now you should be able to access the application at [https://127.0.0.1/dashboard](https://127.0.0.1/dashboard)
or [https://ingress.local/dashboard](https://ingress.local/dashboard).

For more detailed information, visit the
[TLS Termination with Ingress-Nginx Controller](https://kubernetes.github.io/ingress-nginx/examples/tls-termination/)
documentation.
