# Project Access Token with read_registry, write_registry scope
API_TOKEN = ''
PROJECT_ID = 1856  # Check in Project / General Settings
GITLAB_API_URL = 'https://gitlab.com/api/v4'
RESULTS_PER_PAGE = 20
HEADERS = {'Authorization': f'Bearer {API_TOKEN}'}

CORE_RT_IMAGES = [
    'lifecycle',
    'image-builder',
    'dashboard',
    'pub',
    'pgbouncer',
    'postgres',
    'postgres-exporter',
    'job-base/docker-http',
    'job-base/golang',
    'job-base/python3',
    'job-base/rust',
    'ci-test',
]
LAST_IMAGES_SPARE = 10  # how many latest RT images to leave

REGISTRY_IMAGE_PREFIX = 'ghcr.io/theracetrack/racetrack'

# List of live deployment environments to check what's running there
DEPLOYMENT_ENVIRONMENTS = [
    # 'https://racetrack-dev-1.kubernetes.example.com',
]

# Put your Racetrack auth tokens here for each environment
RT_AUTH_TOKENS = {
    # 'https://racetrack-dev-1.kubernetes.example.com': '',
}
