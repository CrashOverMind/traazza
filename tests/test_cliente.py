"""Tests del cliente de envío a la AEAT (F2.1), con transporte falso."""

import xml.etree.ElementTree as ET

import pytest

from traazza.modelos import Emisor, Cadena, SistemaInformatico, LineaDesglose
from traazza import cliente
from traazza.cliente import Cliente, Entorno, EnvioError
from traazza.errores import DatosInvalidosError

SISTEMA = SistemaInformatico("Mi Software SL", "B00000000", "MiFacturador",
                             "01", "1.0.0", "INST-001")
EMISOR = Emisor("89890001K", "Empresa Ejemplo SL")

# Respuesta OK de ejemplo (estructura tipo AEAT, namespace genérico).
RESP_OK = """<?xml version="1.0"?>
<RespuestaRegFactuSistemaFacturacion xmlns="https://ejemplo/Respuesta">
  <CSV>ABC123CSV</CSV>
  <EstadoEnvio>Correcto</EstadoEnvio>
  <RespuestaLinea>
    <IDFactura><NumSerieFactura>2024/A-1</NumSerieFactura></IDFactura>
    <Operacion><TipoOperacion>Alta</TipoOperacion></Operacion>
    <EstadoRegistro>Correcto</EstadoRegistro>
  </RespuestaLinea>
</RespuestaRegFactuSistemaFacturacion>"""

RESP_KO = """<?xml version="1.0"?>
<RespuestaRegFactuSistemaFacturacion xmlns="https://ejemplo/Respuesta">
  <EstadoEnvio>Incorrecto</EstadoEnvio>
  <RespuestaLinea>
    <IDFactura><NumSerieFactura>2024/A-1</NumSerieFactura></IDFactura>
    <EstadoRegistro>Incorrecto</EstadoRegistro>
    <CodigoErrorRegistro>1100</CodigoErrorRegistro>
    <DescripcionErrorRegistro>NIF no identificado</DescripcionErrorRegistro>
  </RespuestaLinea>
</RespuestaRegFactuSistemaFacturacion>"""


def _alta():
    c = Cadena(EMISOR)
    return [c.alta(num_serie="2024/A-1", fecha_expedicion="01-01-2024",
                   tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                   fecha_hora_huso="2024-01-01T10:00:00+01:00",
                   descripcion_operacion="Venta",
                   desglose=[LineaDesglose("111.10", "12.35", "11.12")])]


# --- Construcción del SOAP ------------------------------------------------

def test_soap_envuelve_el_registro():
    soap = cliente.construir_soap(EMISOR, _alta(), SISTEMA)
    raiz = ET.fromstring(soap)
    assert raiz.tag.endswith("}Envelope")
    locales = {h.tag.rsplit("}", 1)[-1] for h in raiz.iter()}
    assert "Body" in locales
    assert "RegFactuSistemaFacturacion" in locales
    assert "RegistroAlta" in locales


# --- Endpoints ------------------------------------------------------------

def test_url_segun_entorno_y_sello():
    assert "prewww1" in Cliente(entorno=Entorno.PRUEBAS).url
    assert "prewww10" in Cliente(entorno=Entorno.PRUEBAS, sello=True).url
    assert "www1.agenciatributaria" in Cliente(entorno=Entorno.PRODUCCION).url
    assert "www10.agenciatributaria" in Cliente(entorno=Entorno.PRODUCCION, sello=True).url


# --- Parseo de respuesta --------------------------------------------------

def test_parsea_respuesta_ok():
    resp = cliente.parsear_respuesta(RESP_OK)
    assert resp.ok and resp.estado_envio == "Correcto"
    assert resp.csv == "ABC123CSV"
    assert len(resp.lineas) == 1
    assert resp.lineas[0].num_serie == "2024/A-1"
    assert resp.lineas[0].estado == "Correcto"


def test_parsea_respuesta_ko():
    resp = cliente.parsear_respuesta(RESP_KO)
    assert not resp.ok
    assert resp.lineas[0].codigo_error == "1100"
    assert "NIF" in resp.lineas[0].descripcion_error


# --- Envío con transporte falso -------------------------------------------

def test_enviar_con_transporte_falso():
    enviado = {}

    def fake(url, soap_xml, *, cert, timeout):
        enviado["url"] = url
        enviado["soap"] = soap_xml
        return RESP_OK

    cli = Cliente(entorno=Entorno.PRUEBAS, transporte=fake)
    resp = cli.enviar(EMISOR, _alta(), SISTEMA)
    assert resp.ok
    assert "prewww1" in enviado["url"]
    assert "RegistroAlta" in enviado["soap"]


def test_reintenta_y_acaba_bien():
    intentos = {"n": 0}

    def flaky(url, soap_xml, *, cert, timeout):
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise ConnectionError("red caída")
        return RESP_OK

    cli = Cliente(transporte=flaky, reintentos=3, backoff=0)
    resp = cli.enviar(EMISOR, _alta(), SISTEMA)
    assert resp.ok and intentos["n"] == 3


def test_reintentos_agotados_lanza_envioerror():
    def siempre_falla(url, soap_xml, *, cert, timeout):
        raise ConnectionError("red caída")

    cli = Cliente(transporte=siempre_falla, reintentos=2, backoff=0)
    with pytest.raises(EnvioError):
        cli.enviar(EMISOR, _alta(), SISTEMA)


def test_sin_certificado_ni_transporte_falla():
    cli = Cliente(entorno=Entorno.PRUEBAS)  # cert=None, transporte=None
    with pytest.raises(DatosInvalidosError):
        cli.enviar(EMISOR, _alta(), SISTEMA)
