"""Traazza · Verifactu en tu código.

Librería open-source para generar registros de facturación Verifactu
(huella encadenada, XML y QR tributario) dentro de tu propio software,
sin enviar tus facturas a un tercero.

Núcleo de huella: VALIDADO al carácter contra los tres ejemplos oficiales de
la AEAT (doc v0.1.2). El XML sigue el diseño oficial; los namespaces están
pendientes de confirmar contra el XSD (F1.8.1). Estado: ALPHA.
"""

from .modelos import (
    Emisor, RegistroAlta, RegistroAnulacion, Cadena,
    SistemaInformatico, LineaDesglose, formatear_importe,
)
from . import huella
from . import xml
from . import qr
from . import validacion
from . import envoltorio
from . import cliente
from . import eventos
from . import firma
from .errores import TraazzaError, DatosInvalidosError, EncadenamientoError

__version__ = "0.0.1"

__all__ = [
    "Emisor", "RegistroAlta", "RegistroAnulacion", "Cadena",
    "SistemaInformatico", "LineaDesglose", "formatear_importe",
    "huella", "xml", "qr", "validacion", "envoltorio", "cliente", "eventos", "firma",
    "TraazzaError", "DatosInvalidosError", "EncadenamientoError",
    "__version__",
]
