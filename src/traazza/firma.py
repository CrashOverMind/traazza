"""Firma XAdES de registros para el modo NO Veri*factu (F2.3).

En el modo NO Veri*factu el SIF no remite los registros a la AEAT: los CONSERVA
y los FIRMA con una firma electrónica XAdES (enveloped) que sella cada registro.
El XSD ya contempla ese `ds:Signature` opcional como último hijo del registro;
aquí lo generamos.

⚠️ Traazza es una LIBRERÍA: la firma se hace con el certificado del integrador
   (productor del SIF) y bajo su responsabilidad. Traazza no firma nada en su
   propio nombre ni incorpora certificados.

Dependencias: extra opcional `traazza[firma]` → `signxml` (que usa `lxml` y
`cryptography`; sin dependencias de sistema). Import perezoso.

Estado: el mecanismo de firma+verificación está implementado y probado en
round-trip. La «política de firma» oficial de Veri*factu (identificador + hash),
si la AEAT la exige, se pasa como `politica`; mientras tanto se firma XAdES-BES.
"""

import os

from .errores import TraazzaError, DatosInvalidosError


class FirmaError(TraazzaError):
    """Error al firmar o verificar."""


def _signxml():
    try:
        from signxml.xades import XAdESSigner, XAdESVerifier, XAdESSignaturePolicy
        from signxml import SignatureConfiguration
        from lxml import etree
    except ImportError as e:  # pragma: no cover
        raise FirmaError(
            "La firma XAdES requiere 'signxml'. Instala: pip install traazza[firma]"
        ) from e
    return XAdESSigner, XAdESVerifier, XAdESSignaturePolicy, SignatureConfiguration, etree


def politica(identificador: str, descripcion: str, digest_value: str,
             digest_method: str = "http://www.w3.org/2001/04/xmlenc#sha256"):
    """Construye una política de firma XAdES-EPES.

    Úsala solo si la AEAT publica una política obligatoria para Veri*factu
    (identificador + hash). Si no, no pases política y se firma XAdES-BES.
    """
    _, _, XAdESSignaturePolicy, _, _ = _signxml()
    return XAdESSignaturePolicy(
        Identifier=identificador, Description=descripcion,
        DigestMethod=digest_method, DigestValue=digest_value)


def _leer(material):
    """Acepta bytes PEM o una ruta a fichero PEM."""
    if isinstance(material, (bytes, bytearray)):
        return bytes(material)
    if isinstance(material, str) and os.path.exists(material):
        with open(material, "rb") as f:
            return f.read()
    if isinstance(material, str):
        return material.encode("utf-8")
    return material


def firmar_xml(xml_str: str, *, key, cert, passphrase: bytes = None,
               politica=None) -> str:
    """Firma un XML con XAdES enveloped y devuelve el XML firmado (cadena).

    - `key`/`cert`: PEM en bytes, ruta a fichero PEM, o (para cert) lista de PEM.
    - `passphrase`: contraseña de la clave si está cifrada.
    - `politica`: objeto de `politica(...)` para XAdES-EPES; None → XAdES-BES.

    La `ds:Signature` se inserta como último hijo del elemento raíz, que es
    justo donde el XSD la admite en RegistroAlta/RegistroAnulacion.
    """
    XAdESSigner, _, _, _, etree = _signxml()
    raiz = etree.fromstring(xml_str.encode("utf-8"))
    signer = XAdESSigner(signature_policy=politica)
    try:
        firmado = signer.sign(raiz, key=_leer(key), cert=_leer(cert),
                              passphrase=passphrase)
    except Exception as e:
        raise FirmaError(f"No se pudo firmar el XML: {e}") from e
    return etree.tostring(firmado, encoding="unicode")


def firmar_registro(reg, sistema, *, key, cert, passphrase: bytes = None,
                    politica=None) -> str:
    """Serializa un RegistroAlta/RegistroAnulacion y lo firma con XAdES."""
    from . import xml as _xml
    from .modelos import RegistroAlta, RegistroAnulacion
    if isinstance(reg, RegistroAlta):
        xml_str = _xml.registro_alta_xml(reg, sistema, indent=False)
    elif isinstance(reg, RegistroAnulacion):
        xml_str = _xml.registro_anulacion_xml(reg, sistema, indent=False)
    else:
        raise DatosInvalidosError(f"Tipo de registro no soportado: {type(reg).__name__}")
    return firmar_xml(xml_str, key=key, cert=cert, passphrase=passphrase, politica=politica)


def verificar(xml_firmado: str, *, cert, num_referencias: int = 3) -> bool:
    """Verifica una firma XAdES. Devuelve True o lanza FirmaError.

    `cert` es el certificado (PEM) frente al que validar. `num_referencias` es
    el nº de Reference esperadas en la firma (XAdES añade la de
    SignedProperties y, según config, la de KeyInfo además de la del documento).
    """
    _, XAdESVerifier, _, SignatureConfiguration, etree = _signxml()
    raiz = etree.fromstring(xml_firmado.encode("utf-8"))
    verifier = XAdESVerifier()
    try:
        verifier.verify(raiz, x509_cert=_leer(cert),
                        expect_config=SignatureConfiguration(
                            expect_references=num_referencias))
    except Exception as e:
        raise FirmaError(f"Firma XAdES no válida: {e}") from e
    return True
