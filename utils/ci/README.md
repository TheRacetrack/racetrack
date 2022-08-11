# Continuous Integration

## Usage

Unit tests are run everytime commit is pushed to branch. But tests aren't run
when commit message contains `WIP:`.

## Development

Upon making changes to ci-test.Dockerfile, publish it:

```
DOCKER_IMAGE_NAME="" ./push.sh <VERSION>
```

Where `<VERSION>` is ie. 2021-07-22. Then update `.gitlab-ci.yml`.
