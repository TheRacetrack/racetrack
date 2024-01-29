from racetrack_client.manifest import Manifest
from racetrack_client.log.context_error import ContextError
from racetrack_commons.deploy.job_type import JobType
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine


def validate_jobtype_manifest(job_type: JobType, manifest: Manifest, plugin_engine: PluginEngine):
    """
    Validate job's manifest according to job type specific rules.
    Call a validator defined by job type plugin.
    Raise Exception in case of any validation error.
    """
    try:
        plugin_engine.invoke_plugin_data_hook(job_type.plugin_data, PluginCore.validate_job_manifest,
                                              manifest, job_type.full_name)
    except Exception as e:
        raise ContextError('invalid manifest according to job type rules') from e
