"""
gen_cert.py

Gera um par de chave privada RSA + certificado autoassinado, usados
para configurar o JWT Bearer Flow no Salesforce (upload do .crt na
Connected App; a .key assina o JWT em gen_jwt.py).

── USO ─────────────────────────────────────────────────────────
python gen_cert.py
"""

import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

KEY_PATH = "salesforce.key"
CERT_PATH = "connectedAppCertificate.crt"


def generate_key_and_cert():
    """Gera a chave privada RSA e o certificado autoassinado.
    Retorna (key_pem: bytes, cert_pem: bytes).
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "SaoPaulo"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "SaoPaulo"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FictionalOrg"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, "fictional-jwt-test"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )

    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    return key_pem, cert_pem


def main():
    key_pem, cert_pem = generate_key_and_cert()

    with open(KEY_PATH, "wb") as f:
        f.write(key_pem)

    with open(CERT_PATH, "wb") as f:
        f.write(cert_pem)

    print(f"{KEY_PATH} e {CERT_PATH} gerados com sucesso.")


if __name__ == "__main__":
    main()
