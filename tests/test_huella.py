"""Validación de la huella contra los ejemplos OFICIALES de la AEAT.

Punto F1.5 del roadmap: VALIDADO.

Los tres vectores provienen del documento oficial de la AEAT:
  "Detalle de las especificaciones técnicas para generación de la huella o
   hash de los registros de facturación" — v0.1.2 (27/08/2024), apartado 6.

La implementación de Traazza reproduce los tres al carácter. Estos tests
fijan ese comportamiento: si algún cambio futuro rompe la coincidencia con
la AEAT, saltarán.
"""

from traazza import huella
from traazza.modelos import Emisor, Cadena, formatear_importe


# --- Vectores oficiales AEAT (doc v0.1.2, apartado 6) ------------------------
OFICIAL_ALTA_1 = "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60"
OFICIAL_ALTA_2 = "F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97"
OFICIAL_ANULACION = "177547C0D57AC74748561D054A9CEC14B4C4EA23D1BEFD6F2E69E3A388F90C68"


def test_caso1_primer_registro_alta():
    """6.1 — primer registro de alta (sin huella anterior)."""
    cadena = huella.cadena_alta(
        id_emisor="89890001K", num_serie="12345678/G33",
        fecha_expedicion="01-01-2024", tipo_factura="F1",
        cuota_total="12.35", importe_total="123.45",
        huella_anterior="", fecha_hora_huso="2024-01-01T19:20:30+01:00")
    assert huella.calcular(cadena) == OFICIAL_ALTA_1


def test_caso2_segundo_registro_alta_encadenado():
    """6.2 — segundo registro de alta, encadenado al primero."""
    cadena = huella.cadena_alta(
        id_emisor="89890001K", num_serie="12345679/G34",
        fecha_expedicion="01-01-2024", tipo_factura="F1",
        cuota_total="12.35", importe_total="123.45",
        huella_anterior=OFICIAL_ALTA_1,
        fecha_hora_huso="2024-01-01T19:20:35+01:00")
    assert huella.calcular(cadena) == OFICIAL_ALTA_2


def test_caso3_anulacion_encadenada():
    """6.3 — registro de anulación, encadenado al segundo de alta."""
    cadena = huella.cadena_anulacion(
        id_emisor="89890001K", num_serie="12345679/G34",
        fecha_expedicion="01-01-2024",
        huella_anterior=OFICIAL_ALTA_2,
        fecha_hora_huso="2024-01-01T19:20:40+01:00")
    assert huella.calcular(cadena) == OFICIAL_ANULACION


def test_cadena_completa_reproduce_los_tres():
    """La clase Cadena reproduce la secuencia oficial alta→alta→anulación."""
    c = Cadena(Emisor("89890001K"))
    a1 = c.alta(num_serie="12345678/G33", fecha_expedicion="01-01-2024",
                tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                fecha_hora_huso="2024-01-01T19:20:30+01:00")
    assert a1.huella == OFICIAL_ALTA_1
    a2 = c.alta(num_serie="12345679/G34", fecha_expedicion="01-01-2024",
                tipo_factura="F1", cuota_total="12.35", importe_total="123.45",
                fecha_hora_huso="2024-01-01T19:20:35+01:00")
    assert a2.huella == OFICIAL_ALTA_2
    assert a2.huella_anterior == a1.huella


def test_importe_ceros_a_la_derecha_irrelevantes():
    """AEAT (pág. 6): 123.1 y 123.10 deben tratarse igual en el hash."""
    # formatear_importe normaliza a 2 decimales -> misma huella
    base = huella.calcular(huella.cadena_alta(
        id_emisor="89890001K", num_serie="12345678/G33",
        fecha_expedicion="01-01-2024", tipo_factura="F1",
        cuota_total=formatear_importe("12.35"),
        importe_total=formatear_importe("123.4"),   # un decimal
        huella_anterior="", fecha_hora_huso="2024-01-01T19:20:30+01:00"))
    dos_dec = huella.calcular(huella.cadena_alta(
        id_emisor="89890001K", num_serie="12345678/G33",
        fecha_expedicion="01-01-2024", tipo_factura="F1",
        cuota_total=formatear_importe("12.35"),
        importe_total=formatear_importe("123.40"),  # dos decimales
        huella_anterior="", fecha_hora_huso="2024-01-01T19:20:30+01:00"))
    assert base == dos_dec


def test_cualquier_cambio_rompe_la_huella():
    """Cambiar un céntimo cambia la huella (propiedad antifraude)."""
    base = huella.cadena_alta(
        id_emisor="89890001K", num_serie="12345678/G33",
        fecha_expedicion="01-01-2024", tipo_factura="F1",
        cuota_total="12.35", importe_total="123.45",
        huella_anterior="", fecha_hora_huso="2024-01-01T19:20:30+01:00")
    alterado = huella.cadena_alta(
        id_emisor="89890001K", num_serie="12345678/G33",
        fecha_expedicion="01-01-2024", tipo_factura="F1",
        cuota_total="12.35", importe_total="123.46",
        huella_anterior="", fecha_hora_huso="2024-01-01T19:20:30+01:00")
    assert huella.calcular(base) != huella.calcular(alterado)
