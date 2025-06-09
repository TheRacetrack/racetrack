from lifecycle.auth.authenticate_password import authenticate
from lifecycle.auth.hasher import get_hasher, make_password

def test_authenticate_password():
    # assert False
    password = make_password("admin")
    # assert password == "pbkdf2_sha256$600000$A2mQCW1yCYUhNJP2Fu63s5$aLj15pX6orVYwN0A41/qY3vlH32xjr9Fqu9jO8W25vM="

    hasher = get_hasher()
    assert hasher.verify("admin", password)