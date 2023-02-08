from enum import Enum


class AuthScope(Enum):
    READ_JOB = 'read_fatman'  # list job, check job details
    DEPLOY_JOB = 'deploy_fatman'  # deploy job in a particular family, redeploy job
    DEPLOY_NEW_FAMILY = 'deploy_new_family'  # deploy new job family
    DELETE_JOB = 'delete_fatman'  # move to trash, dismantle from a cluster
    CALL_JOB = 'call_fatman'  # call job endpoints
    CALL_ADMIN_API = 'call_admin_api'  # call internal Racetrack endpoints
    FULL_ACCESS = 'full_access'  # all above
