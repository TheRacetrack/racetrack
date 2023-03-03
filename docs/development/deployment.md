# Deployment & Release

## Versioning

For docker tags on master and release branches (like `cluster-test`, `cluster-preprod` etc),
we use `<semver>` versioning. Examples: `0.0.15`, `1.0.3`.
Versions are bumped only when the new codebase has been tested, and images aren't overridden.

For avoiding docker tag conflicts in dev branches (like `cluster-dev`, `cluster-dev2`)
we extend this format to `<semver>-<MR-number>-<dev-version>`
where MR-number stands for gitlab MR number, and dev-version is just sequentially increasing number.
Examples: `0.0.15-125-1`, `1.0.3-142-11`.

## Release new changes of Racetrack to test or dev Cluster

Do the following in order to apply your changes to your cluster:

In racetrack repository:

1. Increment version `make version-bump MR=123`, where `123` is the id of your merge request.
1. Build & push docker images by running: `make version-release`.

In racetrack-config repository:

1. Checkout to a branch related with your cluster.
1. If new version involves changes in kustomize files, reset repository to corresponding branch.
1. Run `make version-pick VERSION=x.y.z` with `x.y.z` being the version you just bumped.
1. Commit & push to trigger redeployment in Kubernetes.

You don't need to specify MR id for futher dev releases, because `make version-bump` 
will bump the dev part if MR is set in file, otherwise it bumps just the semver part.

## Releasing new Racetrack version

1. Make sure [CHANGELOG.md](../CHANGELOG.md) has all additions and changes
1. Determine new version number `x.y.z` according to [Semver](https://semver.org/) and latest changes:
   ```
   VERSION=x.y.z
   ```
1. In changelog rename section "Unreleased" to `x.y.z` and add date, then
   add a new empty "Unreleased" section.
1. Create release branch ie. `release-x.y.z`:
   ```
   git checkout -b release-$VERSION
   ```
1. Increment version:
    - bump major version:
      ```
      make version-bump-major
      ```
    - bump minor version:
      ```
      make version-bump-minor
      ```
    - or bump patch version:
      ```
      make version-bump
      ```
1. Commit and push all changes from previous points:
   ```
   git commit -am "Release version $VERSION"
   ```
1. Merge `release-x.y.z` branch to `master`:
   ```
   git checkout master && git merge release-$VERSION && git push
   ```
1. Tag the resulting commit and push tag:
   ```
   git tag $VERSION && git push origin $VERSION
   ```
1. Build & push docker images by running:
   ```
   make version-release version-release-github
   ```
1. Release racetrack client (if needed) with
   ```
   (cd racetrack_client && make release-pypi)
   ```
