from lifecycle.auth.hasher import make_password
from lifecycle.auth.authenticate_password import check_password


def test_password_verification():
    test_password = "complex_password_123!"
    hashed = make_password(test_password)
    
    assert check_password(test_password, hashed)
    assert not check_password("wrong_password", hashed)

def test_password_uniqueness():
    password = "test_password"
    hash1 = make_password(password)
    hash2 = make_password(password)
    
    assert hash1 != hash2  # Different salts should produce different hashes
    assert check_password(password, hash1)
    assert check_password(password, hash2)

def test_password_compatibility():
    django_hash = "pbkdf2_sha256$600000$ToUqATye4PAvPsSe9rzUVY$eMWAQNMhb1L22JOXMI92AzSmvUtZKeTzZvbWyJMvakE="

    assert check_password("admin", django_hash)
    assert not check_password("wrong_password", django_hash)