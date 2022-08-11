from prometheus_client import Counter

metric_requested_fatman_deployments = Counter('requested_fatman_deployments', 'Number of requests to deploy fatman')
metric_deployed_fatman = Counter('deployed_fatman', 'Number of Fatman deployed successfully')
