"""Tests del serializador XML (F1.8).

Verifican que el XML es bien formado, sigue el orden del diseño oficial y
lleva dentro la huella validada. El URI de namespace está pendiente de
confirmar contra el XSD oficial (F1.8.1), por eso no se asierta su valor.
"""

import xml.etree.ElementTree as ET

from traazza.modelos import Emisor, Cadena, SistemaInformatico, LineaDesglose
from traazza import xml as tx

SISTEMA = SistemaInformatico(
    nombre_razon="Mi Software SL", nif="B00000000", nombre_sif="MiFacturador",
    id_sif="01", version="1.0.0", numero_instalacion="INST-001")

HUELLA_CASO1 = "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60"


def _alta_caso1():
    c = Cadena(Emisor("89890001K", "Empresa Ejemplo SL"))
    return c.alta(num_serie="12345678/G33", fecha_expedicion="01-01-2024",
                  tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                  fecha_hora_huso="2024-01-01T19:20:30+01:00",
                  descripcion_operacion="Venta de prueba",
                  desglose=[LineaDesglose(base_imponible="111.10",
                                          cuota_repercutida="12.35",
                                          tipo_impositivo="11.12")])


def test_xml_es_bien_formado():
    xml = tx.registro_alta_xml(_alta_caso1(), SISTEMA, indent=False)
    ET.fromstring(xml)  # lanza si no es válido


def test_xml_lleva_la_huella_validada():
    xml = tx.registro_alta_xml(_alta_caso1(), SISTEMA, indent=False)
    root = ET.fromstring(xml)
    ns = {"s": tx.NS_SUM1}
    assert root.find("s:Huella", ns).text == HUELLA_CASO1
    assert root.find("s:TipoHuella", ns).text == "01"


def test_xml_orden_de_campos_principales():
    """El diseño AEAT exige un orden concreto de elementos."""
    xml = tx.registro_alta_xml(_alta_caso1(), SISTEMA, indent=False)
    root = ET.fromstring(xml)
    tags = [el.tag.split("}")[-1] for el in root]
    # comprobamos la secuencia esperada de los principales
    esperado = ["IDVersion", "IDFactura", "NombreRazonEmisor", "TipoFactura",
                "DescripcionOperacion", "Desglose", "CuotaTotal", "ImporteTotal",
                "Encadenamiento", "SistemaInformatico", "FechaHoraHusoGenRegistro",
                "TipoHuella", "Huella"]
    # filtramos a los que están presentes y verificamos su orden relativo
    presentes = [t for t in tags if t in esperado]
    assert presentes == [t for t in esperado if t in presentes]


def test_anulacion_xml_bien_formado_y_con_huella():
    c = Cadena(Emisor("89890001K"))
    c.alta(num_serie="12345678/G33", fecha_expedicion="01-01-2024",
           tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
           fecha_hora_huso="2024-01-01T19:20:30+01:00")
    anul = c.anulacion(num_serie="12345679/G34", fecha_expedicion="01-01-2024",
                       fecha_hora_huso="2024-01-01T19:20:40+01:00")
    xml = tx.registro_anulacion_xml(anul, SISTEMA, indent=False)
    root = ET.fromstring(xml)
    ns = {"s": tx.NS_SUM1}
    assert root.find("s:Huella", ns).text == anul.huella


def test_registro_anterior_lleva_identidad_de_la_factura_previa():
    """El bloque RegistroAnterior debe contener los datos de la factura
    ANTERIOR (no la actual), según EncadenamientoFacturaAnteriorType del XSD."""
    c = Cadena(Emisor("89890001K", "Empresa Ejemplo SL"))
    f1 = c.alta(num_serie="12345678/G33", fecha_expedicion="01-01-2024",
                tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                fecha_hora_huso="2024-01-01T19:20:30+01:00", descripcion_operacion="Venta 1",
                desglose=[LineaDesglose(base_imponible="111.10", cuota_repercutida="12.35", tipo_impositivo="11.12")])
    f2 = c.alta(num_serie="12345679/G34", fecha_expedicion="01-01-2024",
                tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                fecha_hora_huso="2024-01-01T19:20:35+01:00", descripcion_operacion="Venta 2",
                desglose=[LineaDesglose(base_imponible="111.10", cuota_repercutida="12.35", tipo_impositivo="11.12")])
    root = ET.fromstring(tx.registro_alta_xml(f2, SISTEMA, indent=False))
    ns = {"s": tx.NS_SUM1}
    ant = root.find("s:Encadenamiento/s:RegistroAnterior", ns)
    assert ant is not None
    assert ant.find("s:IDEmisorFactura", ns).text == "89890001K"
    assert ant.find("s:NumSerieFactura", ns).text == "12345678/G33"   # la de f1
    assert ant.find("s:FechaExpedicionFactura", ns).text == "01-01-2024"
    assert ant.find("s:Huella", ns).text == f1.huella   # huella de f1


def test_alta_sin_descripcion_falla():
    import pytest
    from traazza.errores import DatosInvalidosError
    c = Cadena(Emisor("89890001K", "Empresa Ejemplo SL"))
    reg = c.alta(num_serie="A/1", fecha_expedicion="01-01-2024", tipo_factura="F1",
                 cuota_total="1.00", importe_total="2.00",
                 fecha_hora_huso="2024-01-01T10:00:00+01:00",
                 desglose=[LineaDesglose(base_imponible="2.00")])
    with pytest.raises(DatosInvalidosError):
        tx.registro_alta_xml(reg, SISTEMA)


def test_alta_sin_desglose_falla():
    import pytest
    from traazza.errores import DatosInvalidosError
    c = Cadena(Emisor("89890001K", "Empresa Ejemplo SL"))
    reg = c.alta(num_serie="A/1", fecha_expedicion="01-01-2024", tipo_factura="F1",
                 cuota_total="1.00", importe_total="2.00",
                 fecha_hora_huso="2024-01-01T10:00:00+01:00",
                 descripcion_operacion="Venta")
    with pytest.raises(DatosInvalidosError):
        tx.registro_alta_xml(reg, SISTEMA)
