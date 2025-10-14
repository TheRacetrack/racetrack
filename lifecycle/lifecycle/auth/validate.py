from pathlib import Path


def validate_password(password: str):
    for validator in [validate_password_length, validate_numeric_password, validate_common_password]:
        validator(password)


def validate_password_length(password: str):
    if len(password) < 8:
        raise ValidationError("This password is too short. It must contain at least 8 characters.")


def validate_numeric_password(password: str):
    if password.isdigit():
        raise ValidationError("This password is entirely numeric.")


def validate_common_password(password: str):
    # password list based on https://gist.github.com/roycewilliams/226886fd01572964e1431ac8afc999ce
    # by Royce Williams
    passwords_path: Path = Path(__file__).resolve().parent / "common-passwords.txt"

    with open(passwords_path, "rt", encoding="utf-8") as f:
        passwords = {x.strip() for x in f}

    if password.lower().strip() in passwords:
        raise ValidationError("This password is too common.")


class ValidationError(Exception):
    pass
