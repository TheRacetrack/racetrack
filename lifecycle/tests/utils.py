import backoff


@backoff.on_exception(backoff.expo, AssertionError, factor=0.1, max_time=10, jitter=None)
def wait_until_equal(collection1, collection2, err_message: str):
    assert collection1 == collection2, err_message
