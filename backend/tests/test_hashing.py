from app.utils.hashing import sha256_bytes


def test_sha256_known_vector() -> None:
    # NIST SHA-256 test vector for "abc"
    assert sha256_bytes(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
