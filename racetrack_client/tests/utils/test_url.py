from racetrack_client.utils.url import trim_url, join_paths


def test_trim_url():
    url = 'http://localhost:5000/uglypath/'
    trimmed = trim_url(url)
    assert trimmed == 'http://localhost:5000/uglypath'
    assert trimmed == trim_url(trimmed)


def test_join_paths():
    url = join_paths('localhost:5000', 'namespace/', '/repository', '', 'image')
    assert url == 'localhost:5000/namespace/repository/image'
