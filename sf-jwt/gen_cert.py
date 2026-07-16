from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime

# Gera a chave privada RSA
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Monta o certificado autoassinado
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
    .not_valid_before(datetime.datetime.utcnow())
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    .sign(private_key, hashes.SHA256())
)

# Salva a chave privada (salesforce.key)
with open("salesforce.key", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))

# Salva o certificado (connectedAppCertificate.crt)
with open("connectedAppCertificate.crt", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("salesforce.key e connectedAppCertificate.crt gerados com sucesso.")
