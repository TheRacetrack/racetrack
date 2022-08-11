# Deploying Racetrack

Prerequisites:
- k8s cluster

1. Adjust the docker registry urls and build Racetrack images: `make docker-push`
2. Deploy the containers either using manual `kubectl apply -k kustomize/dev`
or with automated system like Flux.

Security warning: make sure to enable TLS traffic to PUB and Lifecycle API, since
they will receive secret tokens, which otherwise would be sent plaintext.

# Maintaining Racetrack

## Managing users

### Creating user account
In order to create an account, 
user needs to go to Racetrack Dashboard and register new account there.
Then he should ask Racetrack Admin to activate his account.
Racetrack Admin goes to Admin panel, `Users` tab, selects user, 
sets `Active` checkbox and clicks `Save`.

### Changing user's password
Admin can change any user's password by going to Admin panel, `Users` tab, 
selecting user, clicking "change the password using this form".


## Managing Fatman Portfolio

### Audit Log
"Audit Log" tab in Dashboard shows activity events done by users,
eg. "fatman F1 of user Alice has been deleted by Bob".
It can be filtered by events related to a logged user,
whole fatman family or a particular fatman.

### Portfolio table
"Portfolio" tab in Dashboard allows to browse fatmen freely
with custom criteria and showing the candidates for removal.
Use the filters above each column to filter and limit table data. 
Advanced searches can be performed by using the following operators:
`<, <=, >, >=, =, *, !, {, }, ||,&&, [empty], [nonempty], rgx:`

You can delete fatman from there.
"Purge score" column shows assessed penalty points representing usability of a fatman.
A higher value means a better candidate for removal.
"Purge score" value is explained in "Purge reasons" column
with suggestions explaining why fatman is a candidate for removal.

### Changing Fatman attributes
If you want to overwrite some deployment attributes of a fatman in runtime 
(eg. minimum memory amount, number of replicas),
you can go to Admin panel, choose "Fatmen" tab, select particular one,
change its "Manifest" field by editing the YAML and click "Save".
Then go back to Racetrack Dashboard, tab "Fatmen" and click Redeploy button under the selected fatman.
However, keep in mind that this change will be overwritten by the next deployment,
so better ask maintaner of a fatman to change the manifest in the git repository as well.

## Permissions

You can view the permissions-graph in Racetrack Dashboard, under Graph page.
Click on the node to see the details and filter out the neighbours of the selected node.

Permissions can be managed in Administration panel, under "Admin panel" tab in dashboard.

### Allowing ESC to Fatman permissions

In the Racetrack admin panel, go to ESC list, create new ESC.

Copy the caller token code. It's base64, so it's not safely encrypted, ie.
`base64 -d <<< caller-token` will view the underlying json structure
with exact esc-id and api-token.

Make sure it's safely transported to ESC developer, ie. using email encrypted with
public-private key scheme like PGP.

If this key becomes stolen, to prevent attacker from using it, reset the ESC api-token
in ESC edit page.


### Allowing Fatman to Fatman permissions

Fatman to Fatman permissions are setup on Fatman family basis; that is you just
have to set it once that family Adder can be called by Badder, then all Badder
versions can communicate with all Adder versions. The relation is one way only,
so Adder won't be able to call Badder unless it's permitted too.

## Resetting admin password

If there's other admin user, ask him to do the reset in admin panel:
Users -> select user, next to password field there will be link to change form.

If none of the admins remember their password, then somebody has to exec
to Lifecycle pod, `cd /src/lifecycle/lifecycle/django` and run 
`python manage.py changepassword <my_admin>`, or `python manage.py createsuperuser`.

## Cleaning up Docker Registry

There is a Container Registry utility for cleaning obsolete images from the registry
(collecting garbage).
See [registry_cleaner](../utils/registry_cleaner/README.md).


## Troubleshooting
If something's malfunctioning, check out the following places to find more information:

- Racetrack dashboard pages: fatmen list, audit log, dependencies graph,
- Fatman logs (Dashboard / Fatmen / Logs / Runtime logs)
- Fatman build logs:
    - via Dashboard (Fatmen / Logs / Build logs),
    - in image-builder container, at `/var/log/racetrack/image-builder/build-logs`,
    - through Django Admin Panel: Deployments model, "Build logs" field,
- Django Admin panel: browse stored models,
- Racetrack component logs: dashboard, lifecycle, lifecycle-supervisor, image-builder, pub, postgres, pgbouncer
