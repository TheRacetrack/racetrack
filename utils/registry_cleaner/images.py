from typing import List, Iterable
from dataclasses import dataclass
from collections import defaultdict

from racetrack_client.log.logs import get_logger

from semver import SemanticVersion
from request import get_request, get_request_paging, delete_request
from settings import PROJECT_ID, GITLAB_API_URL, CORE_RT_IMAGES, LAST_IMAGES_SPARE, DEPLOYMENT_ENVIRONMENTS, REGISTRY_IMAGE_PREFIX, RT_AUTH_TOKENS

logger = get_logger(__name__)


@dataclass
class RegistryImage:
    id: int  # repository (image) ids
    location: str  # full path to the image (without tag)
    name: str  # name after /namespace/
    tags: List[str]


@dataclass
class ImageTag:
    image_id: int  # repository (image) id
    path: str  # full path to the image tag
    name: str  # name after /namespace/
    tag: str


@dataclass
class ImageRemovalSummary:
    image_id: int  # repository (image) id
    name: str  # name after /namespace/
    intact_tags: List[ImageTag]
    removal_tags: List[ImageTag]


def list_registry_images() -> List[RegistryImage]:
    response = get_request_paging(f'{GITLAB_API_URL}/projects/{PROJECT_ID}/registry/repositories?tags=true&tags_count=true')
    results = []
    for item in response:
        assert item['tags_count'] == len(item['tags'])
        tag_names = [tag['name'] for tag in item['tags']]
        tag_names = SemanticVersion.sort_by_version(tag_names)
        results.append(RegistryImage(
            id=item['id'],
            location=item['location'],
            name=item['name'],
            tags=tag_names,
        ))
    return results


def images_to_tags(images: List[RegistryImage]) -> List[ImageTag]:
    results = []
    for image in images:
        for tag in image.tags:
            results.append(ImageTag(
                image_id=image.id,
                path=f'{image.location}:{tag}',
                name=image.name,
                tag=tag,
            ))
    return results


def delete_image_tag(repository_id: str, tag_name: str):
    delete_request(f'{GITLAB_API_URL}/projects/{PROJECT_ID}/registry/repositories/{repository_id}/tags/{tag_name}')


def get_latest_racetrack_tags(images: List[RegistryImage]) -> Iterable[str]:
    for image in images:
        if image.name in CORE_RT_IMAGES:
            latest_tags = image.tags[-LAST_IMAGES_SPARE:]
            for tag in latest_tags:
                yield f'{image.location}:{tag}'
            yield f'{image.location}:latest'


def get_deployed_racetrack_tags() -> Iterable[str]:
    for environment in DEPLOYMENT_ENVIRONMENTS:
        response = get_request(f'{environment}/lifecycle/health')
        docker_tag = response['docker_tag']
        logger.info(f'environment {environment} runs on {docker_tag}')

        for image_name in CORE_RT_IMAGES:
            yield f'{REGISTRY_IMAGE_PREFIX}/{image_name}:{docker_tag}'


def get_deployed_job_tags() -> Iterable[str]:
    for environment in DEPLOYMENT_ENVIRONMENTS:
        rt_token = RT_AUTH_TOKENS[environment]
        response = get_request(f'{environment}/lifecycle/api/v1/job', headers={
            'accept': 'application/json',
            'X-Racetrack-Auth': rt_token,
        })

        logger.info(f'{len(response)} jobs found at {environment} environment')

        for job_response in response:
            job_name = job_response['name']
            image_tag = job_response['image_tag']
            yield f'{REGISTRY_IMAGE_PREFIX}/job-entrypoint/{job_name}:{image_tag}'
            yield f'{REGISTRY_IMAGE_PREFIX}/job-user-module/{job_name}:{image_tag}'


def group_removal_candidates(removal_candidates: List[ImageTag], all_tags: List[ImageTag]) -> List[ImageRemovalSummary]:
    image_summaries: List[ImageRemovalSummary] = []

    removal_paths = set((tag.path for tag in removal_candidates))

    removal_tags_by_image_name = defaultdict(list)
    for removal_candidate in removal_candidates:
        removal_tags_by_image_name[removal_candidate.name].append(removal_candidate)
    all_tags_by_image_name = defaultdict(list)
    for tag in all_tags:
        all_tags_by_image_name[tag.name].append(tag)

    for image_name in sorted(all_tags_by_image_name.keys()):
        removal_tags: List[ImageTag] = removal_tags_by_image_name[image_name]
        all_image_tags: List[ImageTag] = all_tags_by_image_name[image_name]
        intact_tags = [tag for tag in all_image_tags if tag.path not in removal_paths]

        image_summaries.append(ImageRemovalSummary(
            image_id=all_image_tags[0].image_id,
            name=image_name,
            intact_tags=intact_tags,
            removal_tags=removal_tags,
        ))

    return image_summaries
