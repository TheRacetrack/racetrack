import re


def remove_ansi_sequences(content: str) -> str:
    """Remove ANSI escape codes controlling font colors"""
    return re.sub(r'\x1b\[\d+(;\d+)?m', '', content)
