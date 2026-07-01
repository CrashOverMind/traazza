"""Cliente de envío a la AEAT del SOAP de Veri*factu (F2.1).

Cubre: construcción del sobre SOAP, endpoints (pruebas/producción), mTLS con
certificado, reintentos con backoff, idempotencia y parseo de la respuesta.

⚠️ Traazza sigue siendo una LIBRERÍA. Este cliente envía lo que el integrador
   (productor del SIF) le pasa, bajo SU certificado y SU responsabilidad. No
   firma ni emite nada en nombre de Traazza.

Dependencias: el envío real usa `requests` (extra opcional `traazza[envio]`,
con soporte mTLS). El cliente está partido en dos para poder probarlo sin red:
construye/parsea por un lado y delega el POST en un "transporte" inyectable;
el transporte por defecto (requests) solo se importa al enviar de verdad.

Idempotencia: la AEAT deduplica por (NIF emisor + nº serie + fecha) y huella.
Reenviar el mismo registro devuelve su estado almacenado ("Duplicada"), así que
reintentar ante un fallo de red es seguro: no duplica la factura.

Endpoints (verificar contra el WSDL oficial antes de producción):
  Pruebas      : https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP
  Pruebas sello: https://prewww10.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP
  Producción   : https://www1.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP
  Prod. sello  : https://www10.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP
"""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum

from . import envoltorio as _env
from .errores import TraazzaError, DatosInvalidosError

NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"


class Entorno(Enum):
    PRUEBAS = "pruebas"
    PRODUCCION = "produccion"


# (entorno, sello) -> endpoint. sello=True para certificado de sello de empresa.
ENDPOINTS = {
    (Entorno.PRUEBAS, False): "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
    (Entorno.PRUEBAS, True): "https://prewww10.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
    (Entorno.PRODUCCION, False): "https://www1.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
    (Entorno.PRODUCCION, True): "https://www10.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
}


class EnvioError(TraazzaError):
    """Fallo de transporte/HTTP al enviar a la AEAT."""


# --- Construcción del sobre SOAP ------------------------------------------

def construir_soap(emisor, registros, sistema) -> str:
    """Devuelve el sobre SOAP (cadena) con el RegFactuSistemaFacturacion dentro."""
    cuerpo = _env.construir(emisor, registros, sistema)
    env = ET.Element(f"{{{NS_SOAP}}}Envelope")
    ET.SubElement(env, f"{{{NS_SOAP}}}Header")
    body = ET.SubElement(env, f"{{{NS_SOAP}}}Body")
    body.append(cuerpo)
    ET.register_namespace("soapenv", NS_SOAP)
    ET.register_namespace("sum", _env.NS_SUM)
    ET.register_namespace("sum1", _env.NS_SUM1)
    return ET.tostring(env, encoding="unicode")


# --- Parseo de la respuesta -----------------------------------------------

@dataclass
class LineaRespuesta:
    num_serie: str = ""
    operacion: str = ""           # Alta / Anulacion
    estado: str = ""              # Correcto / AceptadoConErrores / Incorrecto
    codigo_error: str = ""
    descripcion_error: str = ""


@dataclass
class RespuestaEnvio:
    estado_envio: str = ""        # Correcto / ParcialmenteCorrecto / Incorrecto
    csv: str = ""
    lineas: list = field(default_factory=list)
    crudo: str = ""

    @property
    def ok(self) -> bool:
        return self.estado_envio == "Correcto"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _texto(elem, nombre_local) -> str:
    for hijo in elem.iter():
        if _local(hijo.tag) == nombre_local and hijo.text:
            return hijo.text.strip()
    return ""


def parsear_respuesta(xml_respuesta: str) -> RespuestaEnvio:
    """Parsea la respuesta de la AEAT de forma robusta al namespace.

    Busca por nombre local (EstadoEnvio, CSV, RespuestaLinea, EstadoRegistro,
    ...) para no depender de prefijos ni del URI exacto del esquema de
    respuesta, que puede variar entre versiones.
    """
    raiz = ET.fromstring(xml_respuesta)
    resp = RespuestaEnvio(crudo=xml_respuesta)
    resp.estado_envio = _texto(raiz, "EstadoEnvio")
    resp.csv = _texto(raiz, "CSV")
    for nodo in raiz.iter():
        if _local(nodo.tag) != "RespuestaLinea":
            continue
        linea = LineaRespuesta(
            num_serie=_texto(nodo, "NumSerieFactura"),
            operacion=_texto(nodo, "TipoOperacion") or _texto(nodo, "Operacion"),
            estado=_texto(nodo, "EstadoRegistro"),
            codigo_error=_texto(nodo, "CodigoErrorRegistro"),
            descripcion_error=_texto(nodo, "DescripcionErrorRegistro"),
        )
        resp.lineas.append(linea)
    return resp


# --- Transporte (costura para test / inyección) ---------------------------

def _transporte_requests(url, soap_xml, *, cert, timeout):
    """Transporte por defecto: POST con mTLS vía requests (import perezoso)."""
    try:
        import requests
    except ImportError as e:  # pragma: no cover
        raise EnvioError(
            "El envío real requiere 'requests'. Instala: pip install traazza[envio]"
        ) from e
    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}
    r = requests.post(url, data=soap_xml.encode("utf-8"),
                      headers=headers, cert=cert, timeout=timeout)
    r.raise_for_status()
    return r.text


@dataclass
class Cliente:
    """Cliente de envío a la AEAT.

    `cert` es lo que espera requests para mTLS: ruta a un PEM que incluya
    certificado+clave, o tupla (cert_pem, clave_pem). `transporte` permite
    inyectar otro POST (tests, proxies, otra librería HTTP).
    """
    entorno: Entorno = Entorno.PRUEBAS
    sello: bool = False
    cert: object = None
    timeout: int = 30
    reintentos: int = 3
    backoff: float = 1.0
    transporte: object = None

    @property
    def url(self) -> str:
        return ENDPOINTS[(self.entorno, self.sello)]

    def enviar(self, emisor, registros, sistema) -> RespuestaEnvio:
        """Construye el SOAP, lo manda y devuelve la respuesta parseada.

        Reintenta solo ante fallos de transporte (red/5xx), con backoff
        exponencial. Es seguro: la AEAT deduplica, reenviar no duplica.
        """
        soap = construir_soap(emisor, registros, sistema)
        envia = self.transporte or _transporte_requests
        if self.transporte is None and self.cert is None:
            raise DatosInvalidosError(
                "Falta el certificado (cert) para el envío con mTLS a la AEAT.")

        ultimo = None
        for intento in range(1, self.reintentos + 1):
            try:
                crudo = envia(self.url, soap, cert=self.cert, timeout=self.timeout)
                return parsear_respuesta(crudo)
            except (EnvioError, DatosInvalidosError):
                raise
            except Exception as e:  # fallo de transporte → reintentar
                ultimo = e
                if intento < self.reintentos:
                    time.sleep(self.backoff * (2 ** (intento - 1)))
        raise EnvioError(
            f"No se pudo enviar a la AEAT tras {self.reintentos} intentos: {ultimo}")
