from prometheus_client import Counter, Gauge, Histogram

metric_requested_job_deployments = Counter(
    'requested_job_deployments',
    'Number of started job deployments',
)
metric_done_job_deployments = Counter(
    'done_job_deployments',
    'Number of finished job deployments (processed or failed)',
)
metric_deployed_job = Counter('deployed_job', 'Number of Jobs deployed successfully')
metric_metrics_scrapes = Counter('metrics_scrapes', 'Number of Prometheus metrics scrapes')

metric_jobs_count_by_status = Gauge(
    "jobs_count_by_status",
    "Number of jobs with a particular status",
    labelnames=['status'],
)
metric_event_stream_client_connected = Gauge(
    "lifecycle_event_stream_client_connected",
    "Total number of successful connections to the event stream",
)
metric_event_stream_client_disconnected = Gauge(
    "lifecycle_event_stream_client_disconnected",
    "Total number of disconnections from the event stream",
)

metric_database_connection_opened = Counter(
    'lifecycle_database_connection_opened',
    'Number of attempts to open a connection to a database (successful or failed)',
)
metric_database_connection_failed = Counter(
    'lifecycle_database_connection_failed',
    'Number of times connection to a database has failed',
)
metric_database_connection_closed = Counter(
    'lifecycle_database_connection_closed',
    'Number of times connection to a database has been closed',
)
metric_database_cursor_created = Counter(
    'lifecycle_database_cursor_created',
    'Number of times database cursor has been created',
)

metric_job_model_fetch_duration = Histogram(
    'lifecycle_job_model_fetch_duration',
    'Duration of fetching Job model from a database in seconds',
    buckets=(.001, .0025, .005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5,
             10.0, 25.0, 50.0, 75.0, 100.0, 250.0, 500.0, 750.0, 1000.0, float("inf")),
)
