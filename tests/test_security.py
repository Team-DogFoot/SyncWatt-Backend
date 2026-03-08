from app.core.security import create_access_token, verify_token


def test_create_and_verify_token():
    token = create_access_token(user_id=1)
    payload = verify_token(token)
    assert payload["user_id"] == 1
    assert payload["sub"] == "1"
    assert payload["type"] == "access"
    assert payload["iss"] == "SyncWatt-Backend"
    assert "iat" in payload


def test_invalid_token_returns_none():
    payload = verify_token("invalid.token.here")
    assert payload is None


def test_expired_token_returns_none():
    token = create_access_token(user_id=1, expire_minutes=-1)
    payload = verify_token(token)
    assert payload is None
