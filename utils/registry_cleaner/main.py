#!/usr/bin/env python3
import sys
from typing import List, Set
import argparse

from racetrack_client.log.logs import configure_logs, get_logger

from request import get_request
from settings import PROJECT_ID, GITLAB_API_URL
from images import RegistryImage, ImageTag, ImageRemovalSummary, \
    list_registry_images, images_to_tags, \
    get_latest_racetrack_tags, get_deployed_racetrack_tags, get_deployed_job_tags, \
    group_removal_candidates, delete_image_tag

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    def _print_help(_: argparse.Namespace):
        parser.print_help(sys.stderr)

    parser.set_defaults(func=_print_help)

    subparser = subparsers.add_parser('list', help='List candidates for removal')
    subparser.add_argument('-v', '--verbose', action='count', default=0, help='enable verbose mode')
    subparser.add_argument('--delete', action='store_true', help='delete the images')
    subparser.set_defaults(func=_list)

    args: argparse.Namespace = parser.parse_args()
    args.func(args)


def _list(args: argparse.Namespace):
    verbose = args.verbose > 0
    configure_logs(verbosity=verbose)

    response = get_request(f'{GITLAB_API_URL}/projects/{PROJECT_ID}')
    assert response['path'] == 'racetrack'

    images: List[RegistryImage] = list_registry_images()
    tags: List[ImageTag] = images_to_tags(images)
    all_tag_paths = {tag.path for tag in tags}
    path_to_tag = {tag.path: tag for tag in tags}
    logger.info(f'Found {len(images)} images with {len(tags)} tags in Container Registry')
    if verbose:
        for image in images:
            logger.debug(f'image {image.name} has {len(image.tags)} tags')
    
    latest_rt_tags: Set[str] = set(get_latest_racetrack_tags(images)) & all_tag_paths
    deployed_rt_tags: Set[str] = set(get_deployed_racetrack_tags()) & all_tag_paths
    deployed_job_tags: Set[str] = set(get_deployed_job_tags()) & all_tag_paths

    removal_names: Set[str] = all_tag_paths - latest_rt_tags - deployed_rt_tags - deployed_job_tags
    removal_candidates: List[ImageTag] = [path_to_tag[path] for path in sorted(removal_names)]
    removal_summaries: List[ImageRemovalSummary] = group_removal_candidates(removal_candidates, tags)

    logger.info(f'Keeping latest core Racetrack images in a registry: {len(latest_rt_tags)} tags')
    logger.info(f'Keeping deployed core Racetrack images: {len(deployed_rt_tags)} tags')
    logger.info(f'Keeping deployed Job images: {len(deployed_job_tags)} tags')
    logger.info(f'All tags found in a registry: {len(tags)} tags')
    logger.info(f'Removal candidates: {len(removal_candidates)} tags')

    for image_summary in removal_summaries:
        intact_tags_count = len(image_summary.intact_tags)
        removal_tags_count = len(image_summary.removal_tags)
        all_tags_count = intact_tags_count + removal_tags_count
        removal_tag_names = ', '.join([tag.tag for tag in image_summary.removal_tags])
        intact_tag_names = ', '.join([tag.tag for tag in image_summary.intact_tags])
        print(f'\nImage \033[1;34m{image_summary.name}\033[0m:')
        if removal_tags_count:
            print(f'\033[1;31mRemoving {removal_tags_count}/{all_tags_count} tags\033[0m: {removal_tag_names}')
        if intact_tags_count:
            print(f'\033[0;32mkeeping {intact_tags_count}/{all_tags_count} tags\033[0m: {intact_tag_names}')

    if args.delete:
        logger.info(f'\nYou\'re about to DELETE {len(removal_candidates)} tags from the Container Registry')
        while True:
            logger.info('Do you want to continue? (y/n)')
            if input() == 'y':
                break

        for image_tag in removal_candidates:
            logger.info(f'Deleting {image_tag.path}')
            delete_image_tag(image_tag.image_id, image_tag.tag)


if __name__ == '__main__':
    main()
