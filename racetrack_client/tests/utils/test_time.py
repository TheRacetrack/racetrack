from unittest import mock

from racetrack_client.utils.time import timestamp_pretty_ago, timestamp_to_datetime


@mock.patch('racetrack_client.utils.time.now')
def test_timestamp_pretty_ago(now):
    now_s = 1_000_000
    now.return_value = timestamp_to_datetime(now_s)

    assert timestamp_pretty_ago(now_s - 9) == 'just now'
    assert timestamp_pretty_ago(now_s - 59) == '59 seconds ago'
    assert timestamp_pretty_ago(now_s - 60) == 'a minute ago'
    assert timestamp_pretty_ago(now_s - 59 * 60 - 59) == '59 minutes ago'
    assert timestamp_pretty_ago(now_s - 3600) == 'an hour ago'
    assert timestamp_pretty_ago(now_s - 3600 * 24 - 59) == 'yesterday'
    assert timestamp_pretty_ago(now_s - 3600 * 24 * 10) == 'a week ago'
    assert timestamp_pretty_ago(now_s - 3600 * 24 * 30) == '4 weeks ago'
    assert timestamp_pretty_ago(now_s - 3600 * 24 * 31) == 'a month ago'
    assert timestamp_pretty_ago(now_s - 3600 * 24 * 59) == 'a month ago'
    assert timestamp_pretty_ago(now_s - 3600 * 24 * 60) == '2 months ago'
