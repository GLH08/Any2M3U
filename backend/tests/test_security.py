import time
from any2m3u.security import hash_password, verify_password, new_session_id, new_pull_token


def test_password_roundtrip():
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h)
    assert not verify_password("wrong", h)


def test_new_session_id_unique():
    a = new_session_id()
    b = new_session_id()
    assert a != b
    assert len(a) >= 32


def test_new_pull_token_format():
    t = new_pull_token()
    assert len(t) >= 32
    # urlsafe base64 alphabet
    import string
    allowed = string.ascii_letters + string.digits + "-_"
    assert all(c in allowed for c in t)
