import base64
import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=64,
    )
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_key = base64.b64encode(derived_key).decode("ascii")
    return f"scrypt$16384$8$1${encoded_salt}${encoded_key}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, raw_n, raw_r, raw_p, encoded_salt, encoded_key = password_hash.split(
            "$",
            maxsplit=5,
        )
    except ValueError:
        return False

    if algorithm != "scrypt":
        return False

    try:
        expected_key = base64.b64decode(encoded_key.encode("ascii"))
        derived_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(encoded_salt.encode("ascii")),
            n=int(raw_n),
            r=int(raw_r),
            p=int(raw_p),
            dklen=len(expected_key),
        )
    except (ValueError, TypeError):
        return False

    return secrets.compare_digest(derived_key, expected_key)
