from cryptography import x509
from cryptography.hazmat.primitives import serialization

from gen_cert import generate_key_and_cert


def _validity_days(cert):
    try:
        delta = cert.not_valid_after_utc - cert.not_valid_before_utc
    except AttributeError:  # versões antigas de cryptography
        delta = cert.not_valid_after - cert.not_valid_before
    return delta.days


def test_generate_key_and_cert_returns_valid_pem():
    key_pem, cert_pem = generate_key_and_cert()

    private_key = serialization.load_pem_private_key(key_pem, password=None)
    assert private_key.key_size == 2048

    cert = x509.load_pem_x509_certificate(cert_pem)
    assert cert.public_key().public_numbers() == private_key.public_key().public_numbers()


def test_generate_key_and_cert_is_self_signed():
    _, cert_pem = generate_key_and_cert()
    cert = x509.load_pem_x509_certificate(cert_pem)
    assert cert.subject == cert.issuer


def test_generate_key_and_cert_validity_is_one_year():
    _, cert_pem = generate_key_and_cert()
    cert = x509.load_pem_x509_certificate(cert_pem)
    assert _validity_days(cert) == 365


def test_generate_key_and_cert_is_deterministic_shape_but_unique_keys():
    """Duas chamadas geram chaves DIFERENTES (cada rodada é um par novo)."""
    key_pem_1, _ = generate_key_and_cert()
    key_pem_2, _ = generate_key_and_cert()
    assert key_pem_1 != key_pem_2
