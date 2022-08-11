# Registry Cleaner

This is the Container Registry utility for cleaning obsolete images from the registry
(collecting garbage).

It checks what's deployed on Racetrack environments, then it compares it with the
images in the registry. If there are images in the registry that are not needed anymore,
it will list them as candidates for removal.

1. Configure auth tokens for the registry, Racetrack tokens 
  and update the list of active deployment environments.
  Copy `settings.dist.py` file to `settings.py` and update the values there.

2. Activate project's virtual env: `. venv/bin/activate`

3. Run the script: `./main.py list` to list candidate images for removal.
  Review candidates and ensure the list is fine.

4. Do the cleansing: `./main.py list --delete`
