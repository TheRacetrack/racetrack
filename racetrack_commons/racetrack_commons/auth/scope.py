from enum import Enum


class AuthScope(Enum):
    READ_FATMAN = 'read_fatman'  # list fatman, check fatman details
    DEPLOY_FATMAN = 'deploy_fatman'  # deploy fatman in a particular family, redeploy fatman
    DEPLOY_NEW_FAMILY = 'deploy_new_family'  # deploy new fatman family
    DELETE_FATMAN = 'delete_fatman'  # move to trash, dismantle from a cluster
    CALL_FATMAN = 'call_fatman'  # call fatman endpoints
    CALL_ADMIN_API = 'call_admin_api'  # call internal Racetrack endpoints
    FULL_ACCESS = 'full_access'  # all above
