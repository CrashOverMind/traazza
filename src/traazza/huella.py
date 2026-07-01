"""Cálculo de la huella o «hash» de los registros de facturación Verifactu.

Fuente normativa:
  - RD 1007/2023 y Orden HAC/1177/2024.
  - AEAT, "Algoritmo de cálculo de codificación de la huella o hash de los
    registros" (documento técnico de la sede electrónica).

Lo que la norma fija (confirmado en las FAQ oficiales de la AEAT):
  - El algoritmo es SHA-256.
  - La huella se calcula sobre unos pocos campos concretos del registro,
    concatenados en un orden fijo con el formato `Campo=valor&Campo=valor&...`.
  - La huella del registro ANTERIOR entra en el cálculo del registro actual:
    así se encadenan (trazabilidad e inalterabilidad).
  - El resultado es una cadena hexadecimal en mayúsculas.

VALIDADO (F1.5): el orden de campos, el formato y la salida coinciden AL
CARÁCTER con los 3 ejemplos oficiales de la AEAT (alta, alta encadenada y
anulación).
"""

import hashlib

# Orden EXACTO de campos para el registro de ALTA (validado en F1.5).
CAMPOS_ALTA = (
    "IDEmisorFactura",
    "NumSerieFactura",
    "FechaExpedicionFactura",
    "TipoFactura",
    "CuotaTotal",
    "ImporteTotal",
    "Huella",                     # huella del registro anterior (vacía si es el primero)
    "FechaHoraHusoGenRegistro",
)

# Orden EXACTO de campos para el registro de ANULACIÓN.
CAMPOS_ANULACION = (
    "IDEmisorFacturaAnulada",
    "NumSerieFacturaAnulada",
    "FechaExpedicionFacturaAnulada",
    "Huella",
    "FechaHoraHusoGenRegistro",
)

# Tipo de huella según la AEAT: "01" = SHA-256.
TIPO_HUELLA_SHA256 = "01"


def construir_cadena(pares):
    """Concatena pares (campo, valor) con el formato `Campo=valor&...`.

    Recibe una lista de tuplas para garantizar el orden; un dict no nos
    daría la garantía de orden que la norma exige.
    """
    return "&".join(f"{campo}={'' if valor is None else valor}" for campo, valor in pares)


def calcular(cadena: str) -> str:
    """Devuelve el SHA-256 de la cadena, en hexadecimal MAYÚSCULAS.

    La AEAT representa la huella en hexadecimal en mayúsculas (validado al
    carácter contra los ejemplos oficiales, F1.5).
    """
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest().upper()


def cadena_alta(*, id_emisor, num_serie, fecha_expedicion, tipo_factura,
                cuota_total, importe_total, huella_anterior, fecha_hora_huso):
    """Construye la cadena a hashear para un registro de ALTA."""
    pares = [
        ("IDEmisorFactura", id_emisor),
        ("NumSerieFactura", num_serie),
        ("FechaExpedicionFactura", fecha_expedicion),
        ("TipoFactura", tipo_factura),
        ("CuotaTotal", cuota_total),
        ("ImporteTotal", importe_total),
        ("Huella", huella_anterior or ""),
        ("FechaHoraHusoGenRegistro", fecha_hora_huso),
    ]
    return construir_cadena(pares)


def cadena_anulacion(*, id_emisor, num_serie, fecha_expedicion,
                     huella_anterior, fecha_hora_huso):
    """Construye la cadena a hashear para un registro de ANULACIÓN."""
    pares = [
        ("IDEmisorFacturaAnulada", id_emisor),
        ("NumSerieFacturaAnulada", num_serie),
        ("FechaExpedicionFacturaAnulada", fecha_expedicion),
        ("Huella", huella_anterior or ""),
        ("FechaHoraHusoGenRegistro", fecha_hora_huso),
    ]
    return construir_cadena(pares)
