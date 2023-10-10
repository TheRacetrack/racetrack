def format_bytes(count: int):
    """Format bytes amount as a human friendly string with KiB, MiB, GiB"""
    if count == 1:
        return '1 byte'
    elif count < 1024:
        return f'{count} bytes'
    elif count < 1024**2:
        return f'{count/1024:.2f} KiB'
    elif count < 1024**3:
        return f'{count/1024/1024:.2f} MiB'
    else:
        return f'{count/1024/1024/1024:.2f} GiB'
