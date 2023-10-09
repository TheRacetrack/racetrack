from racetrack_client.utils.url import trim_url, join_paths


def test_trim_url():
    url = 'http://127.0.0.1:5000/uglypath/'
    trimmed = trim_url(url)
    assert trimmed == 'http://127.0.0.1:5000/uglypath'
    assert trimmed == trim_url(trimmed)


def test_join_paths():
    url = join_paths('127.0.0.1:5000', 'namespace/', '/repository', '', 'image')
    assert url == '127.0.0.1:5000/namespace/repository/image'
