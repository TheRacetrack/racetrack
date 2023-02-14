from prometheus_client import Counter, Gauge

metric_images_built = Counter(
    "images_built",
    "Number of Job images built successfully",
)
metric_images_building_errors = Counter(
    "images_buidling_errors",
    "Number of failures when building Job images",
)
metric_image_building_requests = Counter(
    "image_building_requests",
    "Number of Job images requested for building",
    labelnames=['job_name', 'job_version'],
)
metric_image_building_done_requests = Counter(
    "image_building_done_requests",
    "Number of building requests already processed",
    labelnames=['job_name', 'job_version'],
)
metric_image_building_request_duration = Counter(
    "image_building_request_duration_seconds",
    "Total number of seconds spent on image building",
    labelnames=['job_name', 'job_version'],
)
metric_images_pushed = Counter(
    "images_pushed",
    "Number of images pushed to registry",
    labelnames=['job_name', 'job_version'],
)
metric_images_pushed_duration = Counter(
    "images_pushed_duration",
    "Total number of seconds spent on pushing images to registry",
    labelnames=['job_name', 'job_version'],
)

metric_active_building_tasks = Gauge(
    "active_building_tasks",
    "Current number of building tasks running concurrently",
)
