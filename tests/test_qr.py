"""Tests del QR tributario (F1.6).

Vectores tomados al carácter del documento oficial de la AEAT
"Especificaciones técnicas del código «QR»" (v0.5.0):
  - Apartado 4: ejemplo de URL encoding (`12345678&G33` → `12345678%26G33`).
  - Apartado 8.1–8.4: URLs válidas de pruebas/producción, verificable y no.
"""

import pytest

from traazza.modelos import Emisor, Cadena, LineaDesglose
from traazza import qr
from traazza.qr import Entorno
from traazza.errores import DatosInvalidosError


# --- URL: vectores oficiales al carácter ----------------------------------

def test_url_encoding_apartado_4():
    """El `&` dentro de numserie debe codificarse como %26 (ejemplo oficial)."""
    url = qr.url_factura(
        nif="89890001K", numserie="12345678&G33",
        fecha="01-01-2024", importe="241.4",
        entorno=Entorno.PRUEBAS, verificable=True)
    assert url == (
        "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR"
        "?nif=89890001K&numserie=12345678%26G33&fecha=01-01-2024&importe=241.4")


def test_url_8_1_pruebas_verificable():
    url = qr.url_factura(
        nif="89890001K", numserie="12345678-G33",
        fecha="01-09-2024", importe="241.4",
        entorno=Entorno.PRUEBAS, verificable=True)
    assert url == (
        "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR"
        "?nif=89890001K&numserie=12345678-G33&fecha=01-09-2024&importe=241.4")


def test_url_8_2_pruebas_no_verificable():
    url = qr.url_factura(
        nif="89890001K", numserie="12345678-G33",
        fecha="01-09-2024", importe="241.4",
        entorno=Entorno.PRUEBAS, verificable=False)
    assert url == (
        "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu"
        "?nif=89890001K&numserie=12345678-G33&fecha=01-09-2024&importe=241.4")


def test_url_8_3_produccion_verificable():
    url = qr.url_factura(
        nif="89890001K", numserie="12345678-G33",
        fecha="01-09-2024", importe="241.4",
        entorno=Entorno.PRODUCCION, verificable=True)
    assert url == (
        "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR"
        "?nif=89890001K&numserie=12345678-G33&fecha=01-09-2024&importe=241.4")


def test_url_8_4_produccion_no_verificable():
    url = qr.url_factura(
        nif="89890001K", numserie="12345678-G33",
        fecha="01-09-2024", importe="241.4",
        entorno=Entorno.PRODUCCION, verificable=False)
    assert url == (
        "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu"
        "?nif=89890001K&numserie=12345678-G33&fecha=01-09-2024&importe=241.4")


# --- numserie con `/` (caso del test de XML) ------------------------------

def test_numserie_con_barra_se_codifica():
    url = qr.url_factura(
        nif="89890001K", numserie="12345678/G33",
        fecha="01-01-2024", importe="123.45")
    assert "numserie=12345678%2FG33" in url


def test_encoding_identico_a_la_referencia_java():
    """Casa byte a byte con java.net.URLEncoder (apartado 4.1): espacio->'+',
    se preservan '* . - _', y '~' se percent-codifica."""
    assert qr._encode("FRA 2024/001") == "FRA+2024%2F001"
    assert qr._encode("A*B") == "A*B"
    assert qr._encode("A~B") == "A%7EB"
    assert qr._encode("12345678&G33") == "12345678%26G33"


# --- Importe: número vs cadena --------------------------------------------

def test_importe_numerico_se_normaliza_a_2_decimales():
    url = qr.url_factura(nif="89890001K", numserie="A1",
                         fecha="01-01-2024", importe=241.4)
    assert "importe=241.40" in url


def test_importe_cadena_se_respeta():
    url = qr.url_factura(nif="89890001K", numserie="A1",
                         fecha="01-01-2024", importe="241.4")
    assert "importe=241.4" in url


# --- Validaciones (códigos de error apartado 10) --------------------------

@pytest.mark.parametrize("nif", ["", "891K", "89890001KX", "8989 001K"])
def test_nif_invalido(nif):
    with pytest.raises(DatosInvalidosError):
        qr.url_factura(nif=nif, numserie="A1", fecha="01-01-2024", importe="10.00")


def test_numserie_demasiado_largo():
    with pytest.raises(DatosInvalidosError):
        qr.url_factura(nif="89890001K", numserie="X" * 61,
                       fecha="01-01-2024", importe="10.00")


def test_numserie_caracter_no_imprimible():
    with pytest.raises(DatosInvalidosError):
        qr.url_factura(nif="89890001K", numserie="A\n1",
                       fecha="01-01-2024", importe="10.00")


@pytest.mark.parametrize("fecha", ["2024-01-01", "1-1-2024", "31-02-2024", ""])
def test_fecha_invalida(fecha):
    with pytest.raises(DatosInvalidosError):
        qr.url_factura(nif="89890001K", numserie="A1", fecha=fecha, importe="10.00")


@pytest.mark.parametrize("importe", ["7,2", "10.123", "abc", ""])
def test_importe_invalido(importe):
    with pytest.raises(DatosInvalidosError):
        qr.url_factura(nif="89890001K", numserie="A1",
                       fecha="01-01-2024", importe=importe)


def test_importe_excede_enteros():
    with pytest.raises(DatosInvalidosError):
        qr.url_factura(nif="89890001K", numserie="A1",
                       fecha="01-01-2024", importe="1234567890123.00")


# --- Atajo desde un registro de alta --------------------------------------

def test_url_desde_registro():
    c = Cadena(Emisor("89890001K", "Empresa Ejemplo SL"))
    reg = c.alta(num_serie="12345678-G33", fecha_expedicion="01-09-2024",
                 tipo_factura="F1", cuota_total="41.40", importe_total="241.40",
                 fecha_hora_huso="2024-09-01T19:20:30+01:00")
    url = qr.url_desde_registro(reg, entorno=Entorno.PRUEBAS)
    assert url == (
        "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR"
        "?nif=89890001K&numserie=12345678-G33&fecha=01-09-2024&importe=241.40")


# --- Render a imagen (extra opcional) -------------------------------------

def test_qr_svg_nivel_M():
    url = qr.url_factura(nif="89890001K", numserie="A1",
                         fecha="01-01-2024", importe="10.00")
    svg = qr.qr_svg(url)
    assert svg.lstrip().startswith("<svg")
    # nivel de corrección de errores M (art. 21)
    assert qr.codigo_qr(url).error == "M"


def test_qr_png_devuelve_bytes_png():
    url = qr.url_factura(nif="89890001K", numserie="A1",
                         fecha="01-01-2024", importe="10.00")
    png = qr.qr_png(url)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
