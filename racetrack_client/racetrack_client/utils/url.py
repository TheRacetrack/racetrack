from urllib.parse import urlsplit


def trim_url(url: str) -> str:
    """Trim trailing slash from the end of URL address"""
    split = urlsplit(url)
    path = split.path
    while path.endswith('/'):
        path = path[:-1]
    split = split._replace(path=path)
    return split.geturl()


def join_paths(*paths: str) -> str:
    """Join paths trimming trailing slashes"""
    parts = []
    for i, path in enumerate(paths):
        if i > 0:
            while path.startswith('/'):
                path = path[1:]
        while path.endswith('/'):
            path = path[:-1]
        if path:
            parts.append(path)
    return '/'.join(parts)
