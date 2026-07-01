"""Tests de la firma XAdES (F2.3).

Usa un certificado autofirmado generado al vuelo (solo para test) para probar
el round-trip firma→verificación. NO es un certificado cualificado: la
aceptación por la AEAT necesita tu certificado real y su validador.
"""

from datetime import datetime, timedelta, timezone

import pytest

from traazza.modelos import Emisor, Cadena, SistemaInformatico, LineaDesglose
from traazza import firma
from traazza.firma import FirmaError

# signxml/lxml/cryptography son del extra [firma]; si faltan, se salta.
cryptography = pytest.importorskip("cryptography")
pytest.importorskip("signxml")

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

SISTEMA = SistemaInformatico("Mi Software SL", "B00000000", "MiFacturador",
                             "01", "1.0.0", "INST-001")


@pytest.fixture(scope="module")
def cert_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Traazza")])
    cert = (x509.CertificateBuilder()
            .subject_name(nombre).issuer_name(nombre)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
            .sign(key, hashes.SHA256()))
    key_pem = key.private_bytes(serialization.Encoding.PEM,
                                serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return cert_pem, key_pem


def _alta():
    c = Cadena(Emisor("89890001K", "Empresa Ejemplo SL"))
    return c.alta(num_serie="2024/A-1", fecha_expedicion="01-01-2024",
                  tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                  fecha_hora_huso="2024-01-01T10:00:00+01:00",
                  descripcion_operacion="Venta",
                  desglose=[LineaDesglose("111.10", "12.35", "11.12")])


def test_firma_anade_signature_y_xades(cert_key):
    cert_pem, key_pem = cert_key
    firmado = firma.firmar_registro(_alta(), SISTEMA, key=key_pem, cert=cert_pem)
    assert "Signature" in firmado
    assert "QualifyingProperties" in firmado  # marca de XAdES


def test_firma_y_verificacion_roundtrip(cert_key):
    cert_pem, key_pem = cert_key
    firmado = firma.firmar_registro(_alta(), SISTEMA, key=key_pem, cert=cert_pem)
    assert firma.verificar(firmado, cert=cert_pem) is True


def test_verificacion_falla_con_xml_manipulado(cert_key):
    cert_pem, key_pem = cert_key
    firmado = firma.firmar_registro(_alta(), SISTEMA, key=key_pem, cert=cert_pem)
    manipulado = firmado.replace("123.45", "999.99")
    with pytest.raises(FirmaError):
        firma.verificar(manipulado, cert=cert_pem)


def test_firma_xades_epes_con_politica(cert_key):
    cert_pem, key_pem = cert_key
    pol = firma.politica(
        identificador="urn:traazza:politica-test",
        descripcion="Politica de prueba",
        digest_value="K2tQT2g5N0VuYW1wbGVEaWdlc3RWYWx1ZQ==")
    firmado = firma.firmar_registro(_alta(), SISTEMA, key=key_pem, cert=cert_pem,
                                    politica=pol)
    assert "SignaturePolicyIdentifier" in firmado
