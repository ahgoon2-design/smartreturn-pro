from app.core.security import hash_password, validate_password_policy, verify_password


def test_hash_password_returns_non_plain_text_hash():
    plain_password = "DummyPass123!"

    password_hash = hash_password(plain_password)

    assert password_hash != plain_password
    assert verify_password(plain_password, password_hash) is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password("DummyPass123!")

    assert verify_password("WrongPass123!", password_hash) is False


def test_validate_password_policy_rejects_short_password():
    errors = validate_password_policy("short")

    assert errors


def test_validate_password_policy_rejects_blank_password():
    errors = validate_password_policy("   ")

    assert errors
