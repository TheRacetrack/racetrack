# Changelog
All **user-facing**, notable changes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Structure logging can be enabled by setting `LOG_STRUCTURED` environment variable to `true`.
  It will make the logs to be produced in JSON format.

### Changed
- Racetrack components use [Loguru](https://loguru.readthedocs.io/en/stable/index.html) for logging.
  The new `logger` object may accept additional keyword arguments to add an extra context to a log message.
  For example: `logger.info('not great not terrible', radioactivity=3.6)`

## [2.26.0] - 2024-01-24
### Changed
- Job type plugins can now build job images from a single Dockerfile.
  Base Dockerfile has been merged with a job template.
  It gives more flexibility by allowing to parameterize
  all build commands of a base image with a user-defined configuration.
  See [Developing plugins](./development/developing-plugins.md#supported-hooks)
  and [Job type plugins](./development/plugins-job-types.md) documents.
  Old style is still supported to keep backwards compatibility.
  ([#403](https://github.com/TheRacetrack/racetrack/issues/403))

## [2.25.0] - 2024-01-16
### Added
- *Administration* tab in Dashboard shows number of jobs using the particular job type or infrastructure.
  This helps to indicate which job types are actually in use and which can be deleted.
  It also shows which job types and infrastructures are provided by which plugins in a tree view.
  ([#392](https://github.com/TheRacetrack/racetrack/issues/392))
-   *Activity* tab on Dashboard tracks more kinds of events:
    
    - Plugin installed
    - Plugin uninstalled
    - Deployment attempt failed
    - Job moved (to other infrastructure)
  
    ([#382](https://github.com/TheRacetrack/racetrack/issues/382))

### Changed
- Dashboard's "Audit Log" tab is now called "Activity".

### Fixed
- Dashboard's auto-update feature works with multiple Lifecycle replicas.
  Live updates can now be enabled on the jobs list. It is turned off by default.
  ([#317](https://github.com/TheRacetrack/racetrack/issues/317))

## [2.24.0] - 2023-12-14
### Added
- `racetrack plugin bundle` command has `--out-filename` parameter that allows you
  to overwrite the filename of the output ZIP file.
  ([#391](https://github.com/TheRacetrack/racetrack/issues/391))

### Changed
- Infrastructure targets can now mount secret vars to a job regardless of environment variables.
  Secret variables are passed as a separate argument, they're no longer mixed with regular env vars.
  Infrastructure plugins should be updated accordingly due to interface change.
  Specifically, `deploy_job` function of `JobDeployer` class now has
  a new argument `runtime_secret_vars: Dict[str, str]` with secret env vars for a job.
  See [Supported hooks](./development/developing-plugins.md#supported-hooks).
  ([#394](https://github.com/TheRacetrack/racetrack/issues/394))

## [2.23.0] - 2023-12-04
### Added
- A command `racetrack get remote -q` (with flag `-q` or `--quiet`)
  prints only the current address of Lifecycle (without other logs), which makes it usable for scripts.
  Likewise, a command `racetrack get pub -q` (with flag `-q` or `--quiet`)
  prints the current address of Pub service.
  "Quiet" mode is automatically applied when not in a TTY.
- Racetrack can be turned into a Maintenance mode.
  During that time, users are unable to make changes.
  Therefore, deploying, deleting and moving jobs is disabled.
  See [how to enable maintenance mode](./admin.md#maintenance-mode)
  ([#370](https://github.com/TheRacetrack/racetrack/issues/370))
- A job can be deployed through the Dashboard.
  To submit a job manifest, go to the *"Deployments"* tab and then *"Deploy a new job"* .
  Note that secret variables are not supported in this manner; instead, use the command line client.
  ([#306](https://github.com/TheRacetrack/racetrack/issues/306))
- A new tab called *"Deployments"* displays a list of recent deployment attempts.
  After selecting one, you may view deployment data such as status, failure cause, duration, and so on.
  In case of trouble with deployment, you can share this link with a support team.

### Fixed
- Fixed checking job condition in case of a missing `Content-Type` header of job's live endpoint.
  [#376](https://github.com/TheRacetrack/racetrack/issues/376)
- Word wrapping applied to job logs in Dashboard.
  [#372](https://github.com/TheRacetrack/racetrack/issues/372)
- SIGTERM signal triggers graceful shutdown.
  [#379](https://github.com/TheRacetrack/racetrack/issues/379)

## [2.22.0] - 2023-11-07
### Added
-   Manifest values can be overriden with key-value pairs coming from a command line.
    It doesn't modify actual file, but its one-time, in-memory version before submitting it.
    Racetrack client has `--extra-vars KEY=VALUE` parameter (or `-e` in short)
    that overwrites values found in YAML manifest.

    - `KEY` is the name of field and it can contain dots to refer to a nested field, for example `git.branch=master`.
    - `VALUE` can be any YAML or JSON object.

    Extra vars parameters can be used multiple times in one command.  
    Example: `racetrack deploy -e secret_runtime_env_file=.env.local -e git.branch=$(git rev-parse --abbrev-ref HEAD)`  
    It makes CLI commands more script-friendly, so you can overwrite manifest without tracking changes in job.yaml file.  
    Tip: Use `racetrack validate` command beforehand to make sure your final manifest is what you expected.
    ([#340](https://github.com/TheRacetrack/racetrack/issues/340))

- You can install Racetrack to a standalone host (e.g. EC2 host or fresh VM instance)
  using the installer script that runs it on the Docker Engine infrastructure.
  ([#308](https://github.com/TheRacetrack/racetrack/issues/308))

- Command `racetrack get auth-token` prints out current auth token.
  It can be used in CLI scripts: `curl -H "X-Racetrack-Auth: $(racetrack get auth-token)"`
  ([#357](https://github.com/TheRacetrack/racetrack/issues/357))
- Command `racetrack login --username <username>` allows you to log in with your username and password
  (entered into the standard input) and saves the auth token without having to visit the Dashboard page.

### Fixed
- Manifest is validated after updating it on Dashboard.
  Changing primary keys (name or value) is forbidden.
  ([#293](https://github.com/TheRacetrack/racetrack/issues/293))
- Fixed reviving a dead job after deleting it.
  ([#366](https://github.com/TheRacetrack/racetrack/issues/366))

## [2.21.0] - 2023-10-16
### Added
-   Pub can now be turned into a remote gateway mode.
    It allows to distribute services between clusters as 2 (or more) separate infrastructures:

    - main hub - hosting core Racetrack services: Lifecycle, image-builder, Dashboard, main Pub
    - remote jobs - infrastructure hosting jobs and remote Pub gateway that protects jobs from unauthorized access.

    It can cooperate with the following infrastructure plugins:

    - [remote Kubernetes plugin](https://github.com/TheRacetrack/plugin-remote-kubernetes)
    - [remote docker plugin](https://github.com/TheRacetrack/plugin-remote-docker)

- New administrative endpoint for cleaning up plugins mess.
  ([#331](https://github.com/TheRacetrack/racetrack/issues/331))
  
### Changed
- Streaming live logs of a job can now work with multiple infrastructures.
  Logs streamer interface has been redesigned so infrastructure plugins has to be updated accordingly.
- Prometheus, Grafana and PostgreSQL have been upgraded.

### Fixed
- Database connection is checked in background to avoid blocking metrics endpoint.
  It reduced number of open database connections.
  ([#318](https://github.com/TheRacetrack/racetrack/issues/318))
- Faulty plugins can be deleted.

## [2.20.0] - 2023-09-27
### Added
- Lifecycle has more metrics and Grafana panels for monitoring:
  number of requests, websocket clients, server errors, open connections and active threads.
- Improved error handling and logging in Lifecycle.

### Fixed
- Fixed metrics endpoint, which was making Lifecycle unresponsive to liveness probes
  in case of database connection errors.
  ([#314](https://github.com/TheRacetrack/racetrack/issues/314))
- Fixed TypeError in racetrack client on Python 3.8
  ([#320](https://github.com/TheRacetrack/racetrack/issues/320))

### Removed
- Auto-Update feature has been disabled temporarily due to generating too many requests on multiple replicas.

## [2.19.0] - 2023-09-04
### Added
- Plugin's manifest can declare its category, which makes the label to be displayed on the plugins list.
  Category is a kind of the plugin and can be either "job-type", "infrastructure" or "core".
- If you don't want the plugin to be loaded by Racetrack's Lifecycle or Image-builder (due to missing imports),
  you can enable it selectively for particular components.
  Declare `components` field in a `plugin-manifest.yaml` and add 'lifecycle' or 'image-builder' to the list.
  See [Developing plugins](./development/developing-plugins.md#create-a-plugin-manifest).
  ([#291](https://github.com/TheRacetrack/racetrack/issues/291))
- Plugins can implement `run_action` method for calling a supplementary action with an endpoint.
  It can be used for debugging purposes or to extend plugin's functionality that is not covered by a plugin interface.

### Changed
- Installation to non-local cluster is done by utility script
  that automatically generates resources and unique passwords for your setup.
  ([#298](https://github.com/TheRacetrack/racetrack/issues/298))

### Fixed
- Fixed `racetrack run-local` command.
  ([#312](https://github.com/TheRacetrack/racetrack/issues/312))
- Improved finalizing database connections. 
  ([#295](https://github.com/TheRacetrack/racetrack/issues/295))

## [2.18.0] - 2023-08-04
### Added
- Job types can read the manifest file from the job's directory.
  It might be useful to configure the home page of a job
  ([see example](https://github.com/TheRacetrack/plugin-python-job-type/blob/5625a2b892704da3a935df0049c5b9a0fc49870d/docs/job_python3.md#home-page)).
- Racetrack-client has new flag `--replace` available when uploading a plugin:
  `racetrack plugin install <file.zip> --replace`.
  It will delete the existing versions (with the same name) on uploading a new one.
  Accordingly, there is a checkbox on the Dashboard's *Administration* tab for replacing a plugin on upload.
  By default, uploading a new plugin doesn't replace the older versions.
  ([#270](https://github.com/TheRacetrack/racetrack/issues/270))

### Changed
- When a job is built from local files (with `--build-context=local`),
  files matching `.gitignore` are excluded.
  ([#281](https://github.com/TheRacetrack/racetrack/issues/281))

## [2.17.0] - 2023-07-17
### Added
- When a job is running a deprecated job type version (due to being no longer available),
  there is a notice displayed on a dashboard - "info" icon in a jobs tree
  and a "Notice" field after selecting a job.
  ([#269](https://github.com/TheRacetrack/racetrack/issues/269))

### Fixed
- Missing schema.json is now distributed in PyPI packages.
  ([#283](https://github.com/TheRacetrack/racetrack/issues/283))
- Corrected aggregated metrics on Grafana Dashboards.
  ([#273](https://github.com/TheRacetrack/racetrack/issues/273))
- Fixed reloading local modules by plugins.
  ([#275](https://github.com/TheRacetrack/racetrack/issues/275))

## [2.16.1] - 2023-06-19
### Changed
- Dashboard displays original YAML for the job's manifest.
  ([#262](https://github.com/TheRacetrack/racetrack/issues/262))
- Dashboard now renders a table on the portfolio tab with QTable rather than TableFilter,
  which occasionally seemed to have rendering issues.
  Plus, it's more consistent with the current UI styling.
  ([#258](https://github.com/TheRacetrack/racetrack/issues/258))

### Fixed
- Dashboard redirects to login page when session expires.
  ([#266](https://github.com/TheRacetrack/racetrack/issues/266))

## [2.16.0] - 2023-06-05
### Added
- Jobs tree on the Dashboard is refreshed in real time as soon as someone else's change is detected.
  You can turn it off on the "Jobs" page by clicking "3 dots menu", "Auto-update" toggle.
  ([#239](https://github.com/TheRacetrack/racetrack/issues/239))

### Changed
- Chain calls to the jobs should be made by importing a dedicated function
  from a library provided by the job type plugin.
  This will keep the chain call function always up-to-date with the Racetrack version.
  See the [example](https://github.com/TheRacetrack/plugin-python-job-type/blob/29f9ecc04b182072f3549c82923e252728bd7b61/sample/python-chain/entrypoint.py#LL9C19-L9C83).
  ([#20](https://github.com/TheRacetrack/plugin-python-job-type/issues/20))

## [2.15.0] - 2023-05-26
### Changed
- The name of the caller is recorded in the internal logs,
  giving the ability to track down who made the request based on its ID.
  Job types can also retrieve that information by extracting it from an HTTP header.
  See the [python-job-type docs](https://github.com/TheRacetrack/plugin-python-job-type/blob/master/docs/job_python3.md#caller-name)
  and [a job](https://github.com/TheRacetrack/racetrack/blob/master/sample/python-logger/job.yaml#LL14C1-L15C26) for example.
  ([#246](https://github.com/TheRacetrack/racetrack/issues/246))
- racetrack-client shows more details in case of an HTTP error.
  ([#245](https://github.com/TheRacetrack/racetrack/issues/245))
- `golang`, `python`, and `wrapper_properties` fields are deprecated in Manifest schema,
  use `jobtype_extra` instead. This is backwards compatible.
  ([#231](https://github.com/TheRacetrack/racetrack/issues/231))
- Editing the manifest online triggers a redeployment of the job, keeping manifest up-to-date with running job.
  ([#250](https://github.com/TheRacetrack/racetrack/issues/250))

## [2.14.0] - 2023-05-18
### Added
- Dashboard links to job-related Grafana dashobards.
  [issue #206](https://github.com/TheRacetrack/racetrack/issues/206)
- Manifest of a job can be edited online on the Dashboard after selecting a job.
  Keep in mind that your online changes can be overwritten by the next deployment,
  if you didn't reflect these temporary changes in git after all.
  [issue #217](https://github.com/TheRacetrack/racetrack/issues/217)

### Changed
- Minor UI improvements and styling for Dashboard, including:
  - Sorting jobs by status (starting from faulty ones)
  - Jobs ordering is persisted in local storage
  - Spinner indicators during loading the data
  - Status indicator (green/red/yellow) and number of jobs on a jobs tree
  - Panel takes up the whole space available - no white bars on the sides
  - Jobs tree has its own scrollbar
  - "10 seconds ago" labels are refreshed over time.

### Fixed
- Tree of jobs is refreshed after deleting a job.
  [issue #211](https://github.com/TheRacetrack/racetrack/issues/211)

## [2.13.0] - 2023-05-10
### Added
- "Jobs" tab now shows the tree of jobs grouped by the family name.
  Jobs tree can be filtered by name, version, owner, job type version or infrastructure target.
  [issue #212](https://github.com/TheRacetrack/racetrack/issues/212)

### Changed
- Dashboard UI has been revamped and turned into Single Page Application
  using modern front-end frameworks, which made it more smooth and responsive.
  [issue #212](https://github.com/TheRacetrack/racetrack/issues/212)

## [2.12.1] - 2023-04-21
### Changed
- Racetrack client returns non-zero exit code in case of error.
  [issue #224](https://github.com/TheRacetrack/racetrack/issues/224)
- Dashboard is more responsive in case of a database malfunction (shows error rather than hanging indefinitely),
  since Postgres is no longer its hard dependency.

## [2.12.0] - 2023-03-29
### Added
- New column in the *list* command of the Racetrack client displays a job type.
  Try it out by running `racetrack list -c job_type`.
  [issue #207](https://github.com/TheRacetrack/racetrack/issues/207)
- New command `racetrack call NAME ENDPOINT PAYLOAD [--version VERSION] [--remote REMOTE] [--curl]`
  allows you to call an endpoint of a job.
  Provide the name of the job and the payload of the request in JSON or YAML format,
  for example `racetrack call adder /api/v1/perform '{"numbers": [40,2]}'`.
  Use `--curl` flag, if you want to generate a curl query instead of calling the job.
  Check out `racetrack call --help` for more details.
  [issue #146](https://github.com/TheRacetrack/racetrack/issues/146)
- Name of the job can be autocompleted by hitting `Tab` while typing a CLI command.
  Remember to run `racetrack --install-completion` beforehand.
  Under the hood, it fetches the available jobs from the current remote.

### Changed
- The *list* command of the Racetrack client drops the fancy formatting and *INFO*/*DEBUG* logs
  when being piped into another command (ie. not connected to a terminal/tty device). Try `racetrack list | cat`.
  [issue #207](https://github.com/TheRacetrack/racetrack/issues/207)

### Fixed
- Performance of PUB component has been improved
  by reducing number of requests made to the Lifecycle and to the database.
  [issue #155](https://github.com/TheRacetrack/racetrack/issues/155)
- Fixed saving plugin's config.
  [issue #218](https://github.com/TheRacetrack/racetrack/issues/218)
- Racetrack's cookie can work even on non-HTTPS deployments.
  [issue #225](https://github.com/TheRacetrack/racetrack/issues/225)

## [2.11.0] - 2023-03-17
### Added
- When specifying a job type version, wildcards can be used.
  For instance, `mllab:1.3.*-3.9-bullseye` to subscribe for the latest patches
  or `mllab:1.*.*-3.9-bullseye` if you feel more adventurous.
  The job could be upgraded without committing to manifest then.
  It's the extension of the existing `latest` tag, but it now supports multiple job type variants.
  Note: The release of a new job type version has no effect on existing jobs until they are redeployed.
  [issue #183](https://github.com/TheRacetrack/racetrack/issues/183)

### Changed
- *Portfolio* tab on Dashboard shows the exact version of a job type,
  even if its manifest specifies a wildcard version or "latest".
  [issue #203](https://github.com/TheRacetrack/racetrack/issues/203)

### Fixed
- Fixed opening a job after regenerating the token.
  [issue #200](https://github.com/TheRacetrack/racetrack/issues/200)
- Fixed CSRF Trusted Origins protection.
  [issue #197](https://github.com/TheRacetrack/racetrack/issues/197)

## [2.10.1] - 2023-03-10
### Added
- Grafana's "Lifecycle" dashboard now includes
  a new panel that tracks the number of jobs with the particular status.

### Changed
- "Orhpaned" jobs are no longer adopted by Racetrack.
  This was causing spurious "Lost" status after all.
  [issue #163](https://github.com/TheRacetrack/racetrack/issues/163),
  [issue #134](https://github.com/TheRacetrack/racetrack/issues/134)
- Third-party dependencies have been upgraded.

### Fixed
- Regenerating a user token via the button on your profile now no longer requires a refresh.
  [issue #188](https://github.com/TheRacetrack/racetrack/issues/188)

## [2.10.0] - 2023-03-03
### Added
- Deletion pop-up contains the name of the job to confirm that you're about to delete the right one.
  [issue #176](https://github.com/TheRacetrack/racetrack/issues/176)
- Button added to the profile page that lets you regenerate your authentication token.
  [issue #139](https://github.com/TheRacetrack/racetrack/issues/139)

### Changed
- Racetrack client keeps the local config file `~/.racetrack/config.yaml` with mode `600`
  (not readable by others) and warns you if this file has insecure permissions
  since it may contain credentials.
  [issue #179](https://github.com/TheRacetrack/racetrack/issues/179)

## [2.9.1] - 2023-02-20
### Changed
- *Fatman* has been renamed to *Job* in all database tables, columns and values.
  For instance, scope `call_fatman` is now `call_job`.
  [issue #162](https://github.com/TheRacetrack/racetrack/issues/162)

## [2.9.0] - 2023-02-14
### Added
- Deployment phases, shown by a racetrack client, are more granular,
  including image building steps.
  [issue #145](https://github.com/TheRacetrack/racetrack/issues/145)
- Racetrack comes with standalone Prometheus and Grafana.
  It contains dedicated dashboards for monitoring the jobs and internal services.
  [issue #144](https://github.com/TheRacetrack/racetrack/issues/144)
- Database connection is being monitored closely by Lifecycle and displayed on a Grafana dashboard.
  [issue #165](https://github.com/TheRacetrack/racetrack/issues/165)

### Changed
- *Fatman* is renamed to *Job*.
  `fatman.yaml` is thus deprecated in favour of `job.yaml` file name.
  Although the endpoint for calling the Job has changed to `/pub/job/NAME/VERSION/PATH`,
  the old endpoint `/pub/fatman/NAME/VERSION/PATH` is still supported for backward compatibility.
  [issue #136](https://github.com/TheRacetrack/racetrack/issues/136)

## [2.8.1] - 2023-01-27
### Changed
- Set `User-agent` header in all CLI requests to circumvent silly Cloudflare's protection.

## [2.8.0] - 2023-01-26
### Added
- A job can be moved from one infrastructure target to another by using a new CLI command.
  Check out `racetrack move --help`.
- A new command `racetrack list` allows to fetch the list of all deployed fatmen with the selected columns.
  See `racetrack list --help` for more details.

### Changed
- Syntax of Racetrack client has been rearranged.
  Check out `racetrack --help` for more details.
  Notable changes:

  - Racetrack URL is now called "remote" and it can be explicitly set with an optional parameter
    `--remote alias` in most of the commands. "Remote" can be a direct URL or an alias.
  - The current remote can be set once with `racetrack set remote ALIAS_OR_URL`
    and then you can omit `--remote` parameter in the next commands like `racetrack list`.
    Check your current remote with `racetrack get remote`.
  - Although `racetrack deploy [WORKDIR] [REMOTE]` syntax is still supported,
    it's deprecated now and `racetrack deploy [WORKDIR] [--remote REMOTE]` should be used instead.
  - Automatic completion can be activated by running `racetrack --install-completion`.
    Then, you'll see relevant prompts after hitting `Tab`.
  - To show the runtime logs, use `racetrack logs NAME [--version VERSION] [--remote REMOTE]`.
    No need to pass workdir with a manifest file any longer.
  - To show the build logs, use `racetrack build-logs NAME [--version VERSION] [--remote REMOTE]`.
    No need to pass workdir with a manifest file any longer.
  - To delete a job, use new syntax: `racetrack delete NAME --version VERSION [--remote REMOTE]` -
    job name and version is now required.
    No need to pass workdir with a manifest file any longer.
  - `racetrack plugin install PLUGIN_URI [--remote REMOTE]` -
    "remote" is now an optional parameter instead of a required argument.
  - To set up an alias for Racetrack's remote URL, use `racetrack set alias ALIAS RACETRACK_URL`
    (former `racetrack config alias set`).
  - To set read-access credentials for a git repository,
    use `racetrack set credentials REPO_URL USERNAME TOKEN_PASSWORD`
    (former `racetrack config credentials set`).
  - To save user's Racetrack Auth Token for Racetrack server,
    use `racetrack login USER_TOKEN [--remote REMOTE]`
    (former `racetrack login RACETRACK_URL USER_TOKEN`).
  - `racetrack logout [--remote REMOTE]`
    (former `racetrack logout RACETRACK_URL`).

- In case of problems with reaching the Job,
  PUB shows the error page (JSON with the meaningful reason), instead of a white page of death.
- The "Open" button gets deactivated on the Dashboard for jobs that are not *Running*.

## [2.7.0] - 2023-01-05
### Added
- Every plugin can have its own configuration, stored in a YAML file.
  After uploading the plugin, the configuration can be edited on Dashboard's *Administration* tab,
  with a *Edit Config* button.
  Plugin can read the configuration from a file `self.config_path: pathlib.Path`.
- Racetrack instance can operate with multiple infrastructure targets.
  By default, there is no infrastructure target. It has to be extended by installing a plugin.
  The infrastructure target is displayed next to the fatman name, on Dashboard's list.
  There is a new, optional field `infrastructure_target` in a Manifest.
  If given, it enforces using the specific target in case of many infrastructures are in use.
  Otherwise, the deafult infrastructure is applied.
- Fatman can be composed of multiple Docker images provided by a plugin or user's manifest.

## [2.6.0] - 2022-12-02
### Added
- "Portfolio" table in a Dashboard has a new column "Job type version".
- List of available job types can be checked with:
  `racetrack plugin list --job-types <racetrack_url>`.
  It is also listed in the *Administration* tab on *Dashboard*.
- Exact job type version can be checked at Fatman's `/health` endpoint.

### Fixed
- When uploading a faulty plugin, the errors are handled in a more reliable manner.
- Plugin's requirements are installed with non-root user context.
- Plugin directory is accessible when initializing the plugin in `__init__` method.
- Fixed conflict between newer protobuf version and opentelemetry package.

## [2.5.1] - 2022-10-28
### Added
- Users can change their password on a Dashboard -> Profile tab -> Change Password
- Fatman webviews can now serve ASGI applications (like FastAPI)

### Fixed
- Added missing `__init__.py` file in one of the racetrack-client modules.

## [2.5.0] - 2022-10-18
### Changed
- One job type can be installed in multiple versions at the same time.
  Users have to pick one of these versions and specify it in the manifest of their fatman,
  eg. `lang: python3:2.4.0`.
  Version of a job type is now required in the `lang` field of Manifest in a manner `name:version`.
  `latest` version can be used (resolving to the highest semantic version), though it's discouraged.
- Plugin bundler has been moved to racetrack-client.
  Now you can do `racetrack plugin bundle` instead of `racetrack-plugin-bundler bundle`.

## [2.4.0] - 2022-10-11
### Added
- Plugins can be installed by means of racetrack-client command
  `racetrack plugin install <plugin_uri> <racetrack_url>`,
  where `plugin_uri` can be either:
    - local file path (eg. `python3-job-type-2.4.0.zip`),
    - URL to a remote HTTP file (eg. `https://github.com/TheRacetrack/plugin/releases/download/2.4.0/python3-job-type-2.4.0.zip`),
    - GitHub repository name (eg. `github.com/TheRacetrack/plugin-python-job-type`) - it takes the ZIP file from the latest release.
    - GitHub repository name with version (eg. `github.com/TheRacetrack/plugin-python-job-type==2.4.0`) - it takes the ZIP file from the specific release.

- Plugins can be uninstalled with a new command:
  `racetrack plugin uninstall <plugin_name> <plugin_version> <racetrack_url>`.

- List of currently installed plugins can be checked with:
  `racetrack plugin list <racetrack_url>`.

### Changed
- All job types are individual plugins now.
  Racetrack starts without any job type by default.
- Base Fatman images are built inside Racetrack by image-builder
  so it's no longer needed to push images prior to the plugin release.

## [2.3.0] - 2022-09-23
### Added
- Fatman access can be narrowed down to single endpoints.
  When adding Auth Resource Permission (in Admin panel), there is a new `endpoint` field,
  which narrows down the permission only to this particular Fatman's endpoint.
  If not set, it covers all endpoints (just as other resource filters do).
  For instance, ESC can have a permission with `call_fatman` scope to only call one endpoint.
- OpenTelemetry can be turned on in Racetrack.
  Given the OTLP collector endpoint,
  the traces from lifecycle, pub and fatman will be sent there.

### Changed
- `python3` job type is now based on `3.9-slim-bullseye` image
  instead of `3.8-slim-buster`.
- Plugins are distributed as ZIP files.
  They can be installed and uninstalled in a Dashboard's Administration page.
  See [using-plugins.md](user/using-plugins.md).

## [2.2.1] - 2022-08-25
### Changed
- Maximum amount of memory for a fatman is reduced to `1GiB` by default
  (if not set explicitly in a manifest).
  In general the maximum memory can't be more than 4 times higher than the minimum memory.
  Racetrack keeps an eye on this rule by automatically adjusting minimum memory amount, if needed.
  It is recommended to declare maximum memory amount explicitly
  in a manifest by defining `resources.memory_max` field.
- Fatman versions in PUB's metrics are always resolved to the exact version
  instead of wildcards.

## [2.2.0] - 2022-08-16
### Added
- Golang job types serve interactive Swagger UI with API documentation on the home page.

### Changed
- Function `fatman_job_types` of plugins changed its signature.
  Now the first parameter is a Docker Registry prefix to work well
  with different Docker registry namespaces.
  All job-type plugins has to be adjusted accordingly.
  See [plugins-job-types.md](development/plugins-job-types.md) for more details.
- A namespace for docker images in a Docker Registry is configurable
  so that Racetrack can be released to any Docker Registry.
- A namespace for fatman workloads running on Kubernetes is now configurable
  by means of `FATMAN_K8S_NAMESPACE` environment variable,
  by default it's set to `racetrack`.
- Hostname subdomain of Racetrack services is now configurable by means of
  `RACETRACK_SUBDOMAIN` environment variable, by default it's set to `racetrack`.
- Golang job type has been moved to [Plugin - Go Job Type](https://github.com/TheRacetrack/plugin-go-job-type).
  Now it's not enabled by default in Racetrack.

## [2.1.2] - 2022-07-29
### Changed
- Overall requests performance has been improved by switching from 
  Flask & twisted (WSGI) to FastAPI & Uvicorn (ASGI) web server.
  Fatman server should now be less laggy under heavy load.
  Additionaly, FastAPI comes with better request validation and newer SwaggerUI page.
  Fatman redeployment is needed for the changes to take effect.

## [2.1.1] - 2022-07-25
### Added
- Plugins can provide its own Fatman Deployers
  to deploy workloads to other types of platforms.
  See [developing-plugins.md](development/developing-plugins.md) and
  [Docker Daemon Deployer Plugin](https://github.com/TheRacetrack/plugin-docker-daemon-deployer)

### Changed
- Fatman's metrics now contain number of requests and duration for each endpoint
  (including auxiliary endpoints).

### Fixed
- Fixed redeploying fatmen from the dashboard
- Making multiple attempts to deploy the same fatman at the same time is now disallowed.
- "In progress" deployments are halted when Lifecycle restarts
  (due to upgrade or eviction)

## [2.1.0] - 2022-07-08
### Changed
- Fatman secrets (git credentials and secret vars) are kept in Racetrack,
  so fatmen are fully reproducible again.
  In other words, it is technically possible to rebuild and reprovision fatman
  by anyone who is allowed to do so (anyone with permissions, not just the author)
  to apply latest Racetrack changes.
  You can click "Rebuild and provision" to do a complete redeployment of a fatman,
  or just "Reprovision" to apply changes without rebuilding the image
  (eg. useful when changing replicas count).

- Racetrack client no longer depends on `requests` package 
  in favour of using the built-in `urllib` module.

## [2.0.0] - 2022-06-30
### Added
- Plugins can hook into the `post_fatman_delete` event to add their
  actions after deleting a fatman.
  See [Teams Notifications Racetrack Plugin](https://github.com/TheRacetrack/plugin-teams-notifications)

- Response errors are also displayed in the logs 
  in addition to returning message in HTTP payload.

- Racetrack client has new command `racetrack run-local . <racetrack_url>`
  allowing to run fatman locally based on docker image built by remote Racetrack.
  Docker has to be installed on your system.

### Changed
-   Fatman permissions model is more restrictive.
    Now users, ESCs and fatman families can be granted fine-grained permissions.
    Users can have access to a subset of fatmen and they
    can see and manage only those that are allowed for them.
    Old permissions have been migrated (Fatman-to-Fatman and ESC-to-fatman access).

    By default, Users can now do the following:
    
    - read all fatman status (browse on a dashboard)
    - call endpoints of every fatman
    - deploy and redeploy fatmen
    - delete only fatmen that has been deployed by the user (starting from the newly deployed ones)

    Admin can grant or revoke permissions.
    Permisssion can cover either all fatmen, whole fatman family or a single fatman.

    Permission is related to one of the operation type (called "scope"):

    - `read_fatman` - list fatman, check fatman details
    - `deploy_fatman` - deploy fatman in a particular family, redeploy fatman
    - `deploy_new_family` - deploy new fatman family
    - `delete_fatman` - move to trash, dismantle from a cluster
    - `call_fatman` - call fatman endpoints
    - `call_admin_api` - not important for regular users
    - `full_access` - not important for regular users

- Authentication tokens have been revamped and format changed.
  Users are required to use new tokens in order to use CLI racetrack client.
  Log in to Dashboard, copy the token and run `racetrack login` again.
  Old ESC tokens are still supported to keep backwards compatibility, 
  but they should be regenerated if possible.

- A method for calling fatman from inside of other fatman has been changed due to new auth model.
  See [python-chain sample](../sample/python-chain/entrypoint.py).
  All fatmen calling another fatman are required to be redeployed (to use new tokens).

- Since there is one type of tokens, 
  Auth header has been unified and renamed to `X-Racetrack-Auth`.
  It should be used no matter if it's ESC, User or a Fatman.
  Old headers are still supported but may be abandoned in the future:
  `X-Racetrack-User-Auth`, `X-Racetrack-Esc-Auth`, `X-Racetrack-Fatman-Auth`

- Racetrack services has been adjusted to the new URL format. 
  `/ikp-rt` prefix has been removed from all URLs.
  Instead, `ikp-rt` part may be included in the cluster hostname, making session cookies to work hassle-free and more secure.
  For instance, Racetrack Dashboard address is now: `https://ikp-rt.<cluster.address>/dashboard`.
  Lifecycle address is: `https://ikp-rt.<cluster.address>/lifecycle`.
  PUB runs on: `https://ikp-rt.<cluster.address>/pub`.
  Thus, Fatman instances can be accessed at: `https://ikp-rt.<cluster.address>/pub/fatman/<name>/<version>/<path>`.

## [1.2.0] - 2022-05-31
### Added
- `fatman.yaml` manifest file supports overlays.
  Including `extends` field (with a path to base manifest)
  will make it to merge base and overlay layers.
  It may come in handy when working with multiple environments (dev/test/prod)
  referring to the same base manifest.
  See [overlays sample](../sample/overlays).
- Job types can be extended with plugins.
  Check out [sample job-type plugin](https://github.com/TheRacetrack/plugin-rust-job-type)
  and [developing-plugins.md](development/developing-plugins.md) to see a guide how to create and activate plugins.
- Racetrack documentation is now served at "Docs" tab in Dashboard.
  Check out "Home" page to get started.
- Plugins can extend Racetrack documentation with its own pages written in Markdown
  (it may be generated at runtime depending on plugin configuration).

### Changed
- `racetrack validate PATH` now evaluates the manifest outcome
  and prints it to verify the result of extending overlay manifest.
- Critical actions like deleting fatman or redeploying it
  open a modal window with confirmation button to prevent accidental removal.
- Racetrack environments are easier distinguishable between dev, test, preprod and prod
  due to different colors of the dashboard navbar and additional prefix `[prod]` in the title.

## [1.1.0] - 2022-04-21
### Added
- New "Audit Log" tab in Dashboard shows activity events done by users,
  eg. "fatman F1 of user Alice has been deleted by Bob".
  It can be filtered by events related to a logged user,
  whole fatman family or a particular fatman.

### Changed
- Once a fatman name (and version) has been claimed,
  it can never be deployed again to prevent accidental/hostile reusing.
- Login page has been revamped.

### Fixed
- Display error cause on dashboard in case of "Redeploy" failure.

## [1.0.2] - 2022-04-06
### Changed
- Set default fatman maximum memory to 8GiB

## [1.0.1] - 2022-04-06
### Changed
- Fatman dependency graph is interactive, nodes are movable.
  Clicking on a node filters out all its neighbours 
  to see which fatmen can be accessed by particular ESC 
  or which ESCs have access to a particular fatman.

### Changed
- Set default fatman minimum memory to 150MiB

## [1.0.0] - 2022-03-29
### Added
- Fatman manifest can declare resources to be allocated to the Fatman
  with `resources` field, including minimum/maximum memory, minimum/maximum CPU cores.
  See [Fatman Manifest File](manifest-schema.md)
- Dashboard shows datetime when the last call was made to a fatman.
  Fatman redeployment is needed for the changes to take effect.
- Dashboard has a new "Portfolio" tab for browsing fatmen freely
  with custom criteria and showing the candidates for removal.

## [0.7.8] - 2022-03-18

## [0.7.7] - 2022-03-18
### Changed
- Racetrack client validates given token when running `racetrack login`
  and complains immediately if it's wrong
- Fatman returns 400 BAD REQUEST response in case of missing argument,
  unexpected argument or any other TypeError.

### Fixed
- Fixed Fatmen getting Lost.
  Fatmen shouldn't wrongly change its status to "Lost" any longer.

## [0.7.6] - 2022-03-04

## [0.7.5] - 2022-03-01
### Added
- Log messages contain Request Tracing ID, 
  which allows to track down what was happening during the request processing by different services.
  PUB can read tracing ID from a specific HTTP request header. If not given, it will be generated.
  On IKP clusters this header is named `traceparent` (by default it's `X-Request-Tracing-Id`).
  ID is also returned in the response headers, so you can use it when reporting bugs.
  Fatman redeployment is needed for the changes to take effect.

## [0.7.4] - 2022-03-01
### Added
- PUB collects histogram of fatman response times
  and metrics related to endless requests and response codes.

## [0.7.3] - 2022-02-28
### Changed
- `GET /metrics 200` requests are hidden from access logs.
- Reading from `stdin` is prohibited at fatman initialization and it raises an error once detected,
  showing stack trace with the place where there was an attempt.
  Fatman doesn't go unresponsive any longer, awaiting input indefinitely.

### Fixed
- Fatman logs doesn't show misleading "Timing out client" errors anymore.
  It was related to HTTP sessions kept alive by browsers, not actual fatman request time-outs.

## [0.7.2] - 2022-02-14
### Changed
- Access logs are not polluted with redundant `/live`, `/ready` & `/health` requests.

### Fixed
- Racetrack logs show non-ASCII characters

## [0.7.1] - 2022-02-07
### Added
- Racetrack dashboard shows active plugins along with their versions.

### Changed
- Fatman manifest is checked against using HTTPS git remote only (SSH is not supported).
- `None` values metrics are allowed. They're ignored instead of logging error
  as there is no null in Prometheus, only samples that don't exist.
- Fatman access logs have shorter, concise format.
  Time, HTTP method, path and response code are the only ones displayed.

## [0.7.0] - 2022-01-31
### Added
- When accessing a Fatman through a PUB, there can be used wildcard version format: `1.x` or `1.2.x`.
  This points to a highest stable version of the Fatman that matches the pattern.
  For instance, `1.x` keeps track of all v1 updates, but skips next major versions `2.0.0` and above.
  Fatman redeployment is needed for the changes to take effect.

### Changed
- "latest" fatman version now points to the highest version disregarding versions with any label (eg. `-dev`).
  Thus deploying `2.0.0-alpha` pre-release versions doesn't affect "latest" alias until `2.0.0` is deployed.

### Fixed
- Public endpoints are properly handled with version aliases (eg. "latest", "1.x")

## [0.6.1] - 2022-01-24
### Added
- Phases of deployment are tracked by showing "building image", "creating cluster resources",
  "initializing Fatman entrypoint", etc. in RT client in place of bare "deployment in progress..." message.

### Changed
- Fatman versions are validated according to [SemVer format](https://semver.org/).
  Version should match `MAJOR.MINOR.PATCH[LABEL]`, eg.: `0.1.2` or `0.0.0-dev`.

### Fixed
- Zero-value metrics are shown properly at `/metrics` endpoint of a Fatman.

## [0.6.0] - 2022-01-17
### Added
- Racetrack functionality can be extended with plugins.
  Check out [developing-plugins.md](development/developing-plugins.md) to see a guide how to create and activate plugins.

### Changed
- Whole directories are handled in `static_endpoints` to serve recursively all of its content.
- Metrics from Postgres database and PUB are exported. 
  It gives better monitoring of Fatman requests performance.
- Registration form has been revamped to show errors in a more user-friendly way.
- Pods resource requests have been adjusted to its actual needs.
  Cluster resource shortages shouldn't happen so prematurely anymore.

### Fixed
- Show real reason of internal exceptions, eg. Neo4j auth error

## [0.5.0] - 2022-01-10
### Changed
- Overwriting fatmen is disabled.
  It's not allowed to deploy a fatman with the same name & version as an existing one,
  unless it's deployed with `--force` flag.
- Duplicated env vars error is now more meaningful:
  "found illegal runtime env vars, which conflict with reserved names: RK_HOST"

## [0.4.1] - 2022-01-05
### Fixed
- Fixed Manifests getting empty on Racetrack upgrade.

## [0.4.0] - 2022-01-03
### Added
- Number of running instances of the Fatman 
  can be configured with `replicas` field in a manifest.yaml.
  In case of multiple replicas, `racetrack logs` collects logs from all instances at once.
- Deployed fatmen can be deleted through racetrack client using new command:
  `racetrack delete <workdir> <racetrack_url> [--version X.Y.Z]`.

## [0.3.5] - 2021-12-09
### Added
- Fatman endpoints that are supposed to be accessed publicly (without authentication)
  can be declared in `public_endpoints` field of manifest.
  This makes a request that needs to be approved by Racetrack admin.
  See [python-ui-flask sample](../sample/python-ui-flask).

### Fixed
- Improved overall Fatman response time.

## [0.3.4] - 2021-12-06
### Changed
- Fatman's `/live`, `/ready` and `/health` endpoints doesn't require authentication.

## [0.3.3] - 2021-11-22
### Changed
- Fatman "dashboard" renamed to "webview". See Python Job Type docs: Custom Webview UI.
- On local dev Racetrack there's no need to commit every job change prior to deployment
  (it gets the working directory snapshot).

### Fixed
- Default admin account is no longer recreated.

## [0.3.1] - 2021-11-15
### Added
- New optional field in Manifest: `labels` - dictionary with metadata describing fatman for humans.
  Labels are shown on a dashboard page besides fatman name.
- Example input data (shown on Swagger UI) can be defined for auxiliary endpoints 
  by implementing `docs_input_examples`.
  See Python Job Type docs: Auxiliary endpoints
  section and [python-auxiliary-endpoints sample](../sample/python-auxiliary-endpoints).

### Fixed
- RT specific Dashboard cookie is removed upon logout
- Error returned by Fatman contains more information (including Lifecycle response)
  and uses correct status code (instead of 500)
- Fixed showing spurious success of Fatman redeployment 
  (ensure new Fatman responds to health probes).

## [0.3.0] - 2021-11-08
### Added
- `racetrack logs` command follows Fatman logs when called along with `--follow` flag.
### Changed
- Lifecycle API is fully authenticated, every request to Fatman needs to have either User, ESC or Fatman token.
- `X-Racetrack-Caller` header has changed to `X-Racetrack-Esc-Auth`

## [0.2.1] - 2021-10-25
### Added
- Multiple versions of the same fatman are allowed. 
  Obsolete versions are not removed automatically. 
  ESC permissions are assigned to whole fatmen family by its name.
- Build logs are always captured and can be seen on Racetrack Dashboard by clicking "Logs" / "Build logs"
  or by issuing `racetrack build-logs <workdir> <racetrack_url>`.
- Fatman logs are displayed on Dashboard under option "Logs" / "Runtime logs". 

### Changed
- Fatman base URL is changed to `/ikp-rt/pub/fatman/<fatman-name>/<version>/`. 
  Version can be e.g. `0.0.1` or `latest`.

## [0.2.0] - 2021-10-11
### Added
- Environment vars can be configured in manifest (including build time env, runtime env and secrets).
  Therefore, pip dependencies can be installed from a private repository. 
  See Python Job Type docs: Environment variables section.
- Swagger UI allows to set `X-Racetrack-Caller` header for making authorized Fatman calls.
- Dashboard profile shows a user token 
- Racetrack client `deploy` and `logs` commands enforces logging with token
- `racetrack login` and `logout` commands
- `racetrack config show` for viewing racetrack config

### Changed
- `docs_input_example` outcome is validated at deployment stage. 
  It's checked against JSON-serializability and its size should not exceed 1 MB.
  This solves unresponsive Swagger UI pages, 
  but it may enforce to use a brief example at the expense of having representative one.

## [0.1.1] - 2021-10-04
### Added
- Customized Prometheus metrics can be exported by implementing `metrics` method.

### Changed
- Dashboard allows users to register, to be able to login and view list of Fatmen.

### Fixed
- Generating graph on RT Dashboard
- Generating token for ESC in RT admin panel

## [0.1.0] - 2021-09-27
### Changed
- Hide "Open" button for erroneous Fatman on Dashboard page.
  Instead, show a section containing error message and logs. 
- Racetrack client infers full lifecycle URL, namely https protocol and `/ikp-rt/lifecycle` path, if not given. 
  For instance, `ikp-dev-cluster.example.com` is a valid URL to deploy fatmen.
- Admin panel not available on Dashboard (moved to Lifecycle).

### Fixed
- Use DNS hostname of a cluster instead of raw IP address when redirecting to a Fatman URL
  (fixed in dashboard "Open" link as well as in `racetrack deploy` output).

## [0.0.17] - 2021-09-20
### Added
- Fatman serves 3 version numbers at `/health` endpoint: 
    - `git_version` - arising from the git history of a job source code,
    - `fatman_version` - taken from `version` field in manifest (this is also displayed at SwaggerUI page).
    - `deployed_by_racetrack_version` - version of the Racetrack the Fatman was deployed with.
- Dashboard displays current Racetrack version in the footer.
- Static endpoints for serving local files at particular path (eg: `/xrai` endpoint serving `xrai.yaml`)
- Authorization to PUB (optional right now) for accessing Fatman `/perform`.
  Requires creating ESC and distributing its token to user.

### Fixed
- Show localized Dashboard dates on Firefox

## [0.0.16] - 2021-09-13
### Added
- `build-essential` package is incorporated into python3 base image. `gcc` and `g++` packages are
  there out-of-the-box, so there is no need to include them manually to your `system_dependencies` any longer.
- Dashboard page shows both dates for each Fatman: "Created at" and "Last updated" 
  (deployed at) along with its age (e.g. "5 minutes ago", "5 days ago").

### Changed
- In case of python3 initialization error, full traceback coming from fatman is 
  displayed to a user (eg: it's easier to find out where is a bad import).
- Deployment errors displayed by CLI client are shortened and yet more meaningful.
  Client's traceback is not displayed if not needed.
- Datetimes shown on Dashboard get a localized timezone from a browser, so it's
  no longer UTC time (unless you work from UK).
- Fatmen list on Dashboard is ordered by last deployment date.

### Fixed
- Fix retrieving logs right after deploying a Fatman.
- Increased timeout for creating a pod. It takes into account longer image pulling.

## [0.0.15] - 2021-09-07
### Added
- New required `owner_email` field (email address of the Fatman's owner to reach out) in manifest
- List of Fatmen (in Dashboard) shows who deployed the fatman recently 
  (username is taken from git credentials)
- Auxiliary endpoints - custom endpoint paths handled by entrypoint methods (eg. `/explain` endpoint)

### Changed
- Racetrack client shows full logs from building the image in case of failure.

## [0.0.14] - 2021-09-06
### Changed
- Fatman has read-write access to local working directory.
- Deployment errors are more meaningful and less misleading due to revised health checks
  (ie. cluster errors are distinguished from job syntax errors or initialization errors).
- One common versioning for all Racetrack components (backend and CLI client)

### Fixed
- Fix "Critical worker timeout" WSGI error
- Increase memory limits for building images (up to 8Gi)
- Fix Lifecycle resurrecting dead jobs

## [0.0.5] - 2021-08-26
### Added
- Setting aliases for Racetrack servers

### Changed
- Syntax for configuring private registries credentials
- Input payload is flattened (without "args" & "kwargs")

## [0.0.4] - 2021-08-20
### Added
- Showing recent logs from Fatman

## [0.0.2] - 2021-08-10
### Added
- Deploying Fatman
