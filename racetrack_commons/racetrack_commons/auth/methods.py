from racetrack_client.utils.auth import RT_AUTH_HEADER, RacetrackAuthMethod


def get_racetrack_authorizations_methods():
    return {
        RacetrackAuthMethod.TOKEN.value: {
            'type': 'apiKey',
            'in': 'header',
            'name': RT_AUTH_HEADER,
        },
    }
