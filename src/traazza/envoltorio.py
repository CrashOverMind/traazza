"""Envoltorio de envío: «RegFactuSistemaFacturacion» (F2.1).

Es el documento que se manda a la AEAT: una Cabecera con el obligado a expedir
y una lista de RegistroFactura, cada uno envolviendo un RegistroAlta o
RegistroAnulacion (los que ya genera y valida `xml.py`).

Estructura (esquema SuministroLR.xsd, que importa SuministroInformacion.xsd):

    <sum:RegFactuSistemaFacturacion>
      <sum:Cabecera>
        <sum1:ObligadoEmision>
          <sum1:NombreRazon>...</sum1:NombreRazon>
          <sum1:NIF>...</sum1:NIF>
        </sum1:ObligadoEmision>
      </sum:Cabecera>
      <sum:RegistroFactura>
        <sum1:RegistroAlta>...</sum1:RegistroAlta>
      </sum:RegistroFactura>
      ...
    </sum:RegFactuSistemaFacturacion>

`Cabecera` y `RegistroFactura` van en el namespace de SuministroLR (sum); su
contenido (ObligadoEmision, RegistroAlta/Anulacion) en el de
SuministroInformacion (sum1), porque así lo definen los tipos importados.

Tope por envío: 1000 RegistroFactura (límite del esquema).
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

from . import xml as _xml
from .modelos import Emisor
from .errores import DatosInvalidosError

NS_SUM = _xml.NS_SUM          # SuministroLR.xsd
NS_SUM1 = _xml.NS_SUM1        # SuministroInformacion.xsd

MAX_REGISTROS = 1000

_PREFIJO_SUM = "sum"
_PREFIJO_SUM1 = "sum1"


def _qsum(tag: str) -> str:
    return f"{{{NS_SUM}}}{tag}"


def _qsum1(tag: str) -> str:
    return f"{{{NS_SUM1}}}{tag}"


def construir(emisor: Emisor, registros, sistema) -> ET.Element:
    """Construye el Element <RegFactuSistemaFacturacion>.

    `registros` es una lista de RegistroAlta/RegistroAnulacion (1..1000).
    `emisor` aporta el ObligadoEmision de la cabecera (NombreRazon + NIF).
    """
    registros = list(registros)
    if not registros:
        raise DatosInvalidosError("Hay que enviar al menos un registro.")
    if len(registros) > MAX_REGISTROS:
        raise DatosInvalidosError(
            f"Máximo {MAX_REGISTROS} registros por envío (recibidos {len(registros)}).")
    if not emisor.nombre:
        raise DatosInvalidosError(
            "La cabecera necesita el nombre/razón del obligado (Emisor.nombre).")

    raiz = ET.Element(_qsum("RegFactuSistemaFacturacion"))

    cab = ET.SubElement(raiz, _qsum("Cabecera"))
    obl = ET.SubElement(cab, _qsum1("ObligadoEmision"))
    ET.SubElement(obl, _qsum1("NombreRazon")).text = emisor.nombre
    ET.SubElement(obl, _qsum1("NIF")).text = emisor.nif

    for reg in registros:
        rf = ET.SubElement(raiz, _qsum("RegistroFactura"))
        rf.append(_xml.elemento_registro(reg, sistema))

    return raiz


def _serializar(elem: ET.Element, indent: bool) -> str:
    ET.register_namespace(_PREFIJO_SUM, NS_SUM)
    ET.register_namespace(_PREFIJO_SUM1, NS_SUM1)
    crudo = ET.tostring(elem, encoding="unicode")
    if not indent:
        return crudo
    return minidom.parseString(crudo).toprettyxml(indent="  ").split("\n", 1)[1].strip()


def envoltorio_xml(emisor: Emisor, registros, sistema, indent: bool = True) -> str:
    """Devuelve el XML del <RegFactuSistemaFacturacion> listo para enviar."""
    return _serializar(construir(emisor, registros, sistema), indent)
