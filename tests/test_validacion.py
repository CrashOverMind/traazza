"""Tests de validación XML contra XSD (F1.8.2).

Dos niveles:
  1. SMOKE — usa un XSD local de humo (tests/vectores/_smoke/) para probar que
     el motor de validación funciona: acepta un registro correcto y rechaza
     uno incompleto. NO valida contra el diseño oficial.
  2. OFICIAL — busca el SuministroInformacion.xsd oficial en tests/vectores/.
     Si no está, el test se salta (skip) con un mensaje que dice qué falta.
     En cuanto se coloca el XSD oficial, valida el XML real contra él.
"""

from pathlib import Path

import pytest

from traazza.modelos import Emisor, Cadena, SistemaInformatico, LineaDesglose
from traazza import xml as tx
from traazza import validacion
from traazza.errores import DatosInvalidosError

VECTORES = Path(__file__).parent / "vectores"
XSD_SMOKE = VECTORES / "_smoke" / "registro_smoke.xsd"
XSD_OFICIAL = VECTORES / "SuministroInformacion.xsd"
XSD_DSIG_STUB = VECTORES / "xmldsig-core-schema.xsd"

# El XSD oficial importa xmldsig desde w3.org; lo redirigimos a un stub local
# para compilar sin red (ds:Signature es opcional y nunca se emite).
_DSIG_NS = "http://www.w3.org/2000/09/xmldsig#"
_LOCATIONS_OFICIAL = {_DSIG_NS: str(XSD_DSIG_STUB)}


def _esquema_oficial():
    return validacion.cargar_esquema(XSD_OFICIAL, locations=_LOCATIONS_OFICIAL)

SISTEMA = SistemaInformatico(
    nombre_razon="Mi Software SL", nif="B00000000", nombre_sif="MiFacturador",
    id_sif="01", version="1.0.0", numero_instalacion="INST-001")


def _alta():
    c = Cadena(Emisor("89890001K", "Empresa Ejemplo SL"))
    return c.alta(num_serie="12345678/G33", fecha_expedicion="01-01-2024",
                  tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                  fecha_hora_huso="2024-01-01T19:20:30+01:00",
                  descripcion_operacion="Venta de prueba",
                  desglose=[LineaDesglose(base_imponible="111.10",
                                          cuota_repercutida="12.35",
                                          tipo_impositivo="11.12")])


def _anulacion():
    c = Cadena(Emisor("89890001K"))
    return c.anulacion(num_serie="12345678/G33", fecha_expedicion="01-01-2024",
                       fecha_hora_huso="2024-01-01T19:20:30+01:00")


# --- SMOKE: el motor de validación funciona -------------------------------

def test_motor_acepta_alta_correcta():
    assert validacion.validar_alta(_alta(), SISTEMA, XSD_SMOKE) is True


def test_motor_acepta_anulacion_correcta():
    assert validacion.validar_anulacion(_anulacion(), SISTEMA, XSD_SMOKE) is True


def test_motor_rechaza_alta_sin_idversion():
    """Quitamos IDVersion del XML y el validador debe protestar."""
    xml_str = tx.registro_alta_xml(_alta(), SISTEMA, indent=False)
    roto = xml_str.replace("<sum1:IDVersion>1.0</sum1:IDVersion>", "", 1)
    with pytest.raises(DatosInvalidosError):
        validacion.validar_contra_xsd(roto, XSD_SMOKE)


def test_errores_devuelve_lista_vacia_si_ok():
    assert validacion.errores_alta(_alta(), SISTEMA, XSD_SMOKE) == []


def test_esquema_se_puede_reutilizar():
    esquema = validacion.cargar_esquema(XSD_SMOKE)
    assert validacion.validar_alta(_alta(), SISTEMA, esquema) is True
    assert validacion.validar_anulacion(_anulacion(), SISTEMA, esquema) is True


# --- OFICIAL: validación contra el XSD real de la AEAT --------------------

@pytest.mark.skipif(
    not XSD_OFICIAL.exists(),
    reason=f"Falta el XSD oficial en {XSD_OFICIAL} (ver tests/vectores/README.md)")
def test_xml_alta_valida_contra_xsd_oficial():
    assert validacion.validar_alta(_alta(), SISTEMA, _esquema_oficial()) is True


@pytest.mark.skipif(
    not XSD_OFICIAL.exists(),
    reason=f"Falta el XSD oficial en {XSD_OFICIAL} (ver tests/vectores/README.md)")
def test_xml_anulacion_valida_contra_xsd_oficial():
    assert validacion.validar_anulacion(_anulacion(), SISTEMA, _esquema_oficial()) is True


@pytest.mark.skipif(
    not XSD_OFICIAL.exists(),
    reason=f"Falta el XSD oficial en {XSD_OFICIAL} (ver tests/vectores/README.md)")
def test_xsd_oficial_rechaza_tipo_factura_invalido():
    """El XSD oficial debe rechazar un TipoFactura fuera de la enumeración."""
    xml_str = tx.registro_alta_xml(_alta(), SISTEMA, indent=False)
    roto = xml_str.replace("<sum1:TipoFactura>F1</sum1:TipoFactura>",
                           "<sum1:TipoFactura>ZZ</sum1:TipoFactura>", 1)
    with pytest.raises(DatosInvalidosError):
        validacion.validar_contra_xsd(roto, _esquema_oficial())
