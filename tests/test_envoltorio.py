"""Tests del envoltorio RegFactuSistemaFacturacion (F2.1)."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from traazza.modelos import Emisor, Cadena, SistemaInformatico, LineaDesglose
from traazza import envoltorio, validacion
from traazza.errores import DatosInvalidosError

VECTORES = Path(__file__).parent / "vectores"
XSD_OFICIAL = VECTORES / "SuministroInformacion.xsd"
XSD_LR = VECTORES / "SuministroLR.xsd"
_DSIG = {"http://www.w3.org/2000/09/xmldsig#": str(VECTORES / "xmldsig-core-schema.xsd")}

SISTEMA = SistemaInformatico("Mi Software SL", "B00000000", "MiFacturador",
                             "01", "1.0.0", "INST-001")
EMISOR = Emisor("89890001K", "Empresa Ejemplo SL")


def _registros():
    c = Cadena(EMISOR)
    r1 = c.alta(num_serie="2024/A-1", fecha_expedicion="01-01-2024",
                tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                fecha_hora_huso="2024-01-01T10:00:00+01:00",
                descripcion_operacion="Venta",
                desglose=[LineaDesglose("111.10", "12.35", "11.12")])
    r2 = c.anulacion(num_serie="2024/A-0", fecha_expedicion="01-01-2024",
                     fecha_hora_huso="2024-01-01T10:05:00+01:00")
    return [r1, r2]


def _root():
    xml_str = envoltorio.envoltorio_xml(EMISOR, _registros(), SISTEMA, indent=False)
    return ET.fromstring(xml_str)


def _ln(tag):
    return tag.rsplit("}", 1)[-1]


def test_raiz_y_namespace():
    raiz = _root()
    assert _ln(raiz.tag) == "RegFactuSistemaFacturacion"
    assert envoltorio.NS_SUM in raiz.tag


def test_cabecera_obligado_emision():
    raiz = _root()
    obl = next(e for e in raiz.iter() if _ln(e.tag) == "ObligadoEmision")
    campos = {_ln(h.tag): (h.text or "") for h in obl}
    assert campos.get("NombreRazon") == "Empresa Ejemplo SL"
    assert campos.get("NIF") == "89890001K"


def test_un_registrofactura_por_registro():
    raiz = _root()
    rf = [e for e in raiz.iter() if _ln(e.tag) == "RegistroFactura"]
    assert len(rf) == 2
    internos = [_ln(h.tag) for e in rf for h in e if _ln(h.tag) in ("RegistroAlta", "RegistroAnulacion")]
    assert internos == ["RegistroAlta", "RegistroAnulacion"]


def test_lista_vacia_falla():
    with pytest.raises(DatosInvalidosError):
        envoltorio.construir(EMISOR, [], SISTEMA)


def test_supera_maximo_falla():
    reg = _registros()[0]
    with pytest.raises(DatosInvalidosError):
        envoltorio.construir(EMISOR, [reg] * (envoltorio.MAX_REGISTROS + 1), SISTEMA)


def test_emisor_sin_nombre_falla():
    with pytest.raises(DatosInvalidosError):
        envoltorio.construir(Emisor("89890001K"), _registros(), SISTEMA)


@pytest.mark.skipif(not XSD_LR.exists(), reason="Falta SuministroLR.xsd")
def test_envoltorio_completo_valida_contra_lr():
    """El RegFactuSistemaFacturacion entero valida contra SuministroLR.xsd
    (que importa el SuministroInformacion.xsd oficial)."""
    esquema = validacion.cargar_esquema(XSD_LR, locations=_DSIG)
    assert validacion.validar_envoltorio(EMISOR, _registros(), SISTEMA, esquema) is True
