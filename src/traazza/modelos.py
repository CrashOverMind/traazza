"""Modelos de los registros de facturación y el mecanismo de encadenado.

El cálculo de la huella usa SOLO los 8 campos que fija la AEAT (ver huella.py)
y está validado al carácter. Los campos adicionales que aparecen aquí
(descripción, desglose, sistema informático, destinatario...) son los que el
XML necesita, pero NO entran en la huella.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

from . import huella as _huella
from .errores import DatosInvalidosError


def formatear_importe(valor) -> str:
    """Importe con punto decimal y dos decimales: 123.45.

    AEAT (doc huella, pág. 6): en los campos numéricos los ceros a la derecha
    son irrelevantes (123.1 == 123.10). Normalizamos a 2 decimales con Decimal
    para no arrastrar errores de coma flotante.
    """
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise DatosInvalidosError(f"Importe no válido: {valor!r}")
    return f"{d:.2f}"


@dataclass(frozen=True)
class Emisor:
    """Quien emite la factura (obligado a expedir)."""
    nif: str
    nombre: str = ""

    def __post_init__(self):
        if not self.nif or not self.nif.strip():
            raise DatosInvalidosError("El NIF del emisor es obligatorio.")


@dataclass
class SistemaInformatico:
    """Bloque «SistemaInformatico»: identifica al SIF y a su productor.

    Obligatorio en los registros de alta y de anulación. Quien rellena estos
    datos es el PRODUCTOR del SIF (quien usa Traazza dentro de su software),
    no Traazza.
    """
    nombre_razon: str            # nombre/razón social del productor
    nif: str                     # NIF del productor
    nombre_sif: str              # nombre del SIF
    id_sif: str                  # código de 2 caracteres del SIF
    version: str                 # versión del SIF
    numero_instalacion: str      # nº de instalación (único, ver FAQ AEAT)
    solo_verifactu: str = "S"    # L4: "S" solo VERI*FACTU, "N" dual
    multi_ot: str = "N"          # L4: permite varios obligados
    indicador_multiples_ot: str = "N"  # L4: ahora mismo gestiona varios OT


@dataclass
class LineaDesglose:
    """Una línea de «DetalleDesglose» (1 a 12 por factura)."""
    base_imponible: object
    cuota_repercutida: Optional[object] = None
    tipo_impositivo: Optional[object] = None
    clave_regimen: str = "01"            # L8A (IVA) / L8B (IGIC)
    calificacion_operacion: str = "S1"   # L9 (sujeta no exenta)
    operacion_exenta: Optional[str] = None  # L10 (alternativa a calificacion)
    impuesto: Optional[str] = None       # L1; None => IVA


@dataclass
class RegistroAlta:
    """Registro de facturación de alta (una factura emitida)."""
    # --- Campos que entran en la HUELLA (los 8 oficiales) ---
    id_emisor: str
    num_serie: str
    fecha_expedicion: str        # DD-MM-AAAA
    tipo_factura: str            # L2: F1, F2, F3, R1..R5
    cuota_total: object
    importe_total: object
    fecha_hora_huso: str         # ISO 8601 con zona
    huella_anterior: str = ""
    primer_registro: bool = False
    # --- Campos adicionales que el XML necesita (NO entran en la huella) ---
    nombre_razon_emisor: str = ""
    descripcion_operacion: str = ""
    desglose: list = field(default_factory=list)   # [LineaDesglose]
    destinatario_nombre: Optional[str] = None
    destinatario_nif: Optional[str] = None
    id_version: str = "1.0"      # L15
    # Identidad del registro ANTERIOR (bloque Encadenamiento del XML).
    # Distinto de huella_anterior: el XSD exige emisor+nº+fecha del anterior.
    anterior_id_emisor: str = ""
    anterior_num_serie: str = ""
    anterior_fecha_expedicion: str = ""

    def cadena_huella(self) -> str:
        return _huella.cadena_alta(
            id_emisor=self.id_emisor,
            num_serie=self.num_serie,
            fecha_expedicion=self.fecha_expedicion,
            tipo_factura=self.tipo_factura,
            cuota_total=formatear_importe(self.cuota_total),
            importe_total=formatear_importe(self.importe_total),
            huella_anterior=self.huella_anterior,
            fecha_hora_huso=self.fecha_hora_huso,
        )

    @property
    def huella(self) -> str:
        return _huella.calcular(self.cadena_huella())


@dataclass
class RegistroAnulacion:
    """Registro de anulación (se anula una factura emitida por error)."""
    id_emisor: str
    num_serie: str
    fecha_expedicion: str
    fecha_hora_huso: str
    huella_anterior: str = ""
    primer_registro: bool = False
    id_version: str = "1.0"
    anterior_id_emisor: str = ""
    anterior_num_serie: str = ""
    anterior_fecha_expedicion: str = ""

    def cadena_huella(self) -> str:
        return _huella.cadena_anulacion(
            id_emisor=self.id_emisor,
            num_serie=self.num_serie,
            fecha_expedicion=self.fecha_expedicion,
            huella_anterior=self.huella_anterior,
            fecha_hora_huso=self.fecha_hora_huso,
        )

    @property
    def huella(self) -> str:
        return _huella.calcular(self.cadena_huella())


class Cadena:
    """Encadena registros: cada nuevo registro lleva la huella del anterior."""

    def __init__(self, emisor: Emisor):
        self.emisor = emisor
        self._ultima_huella = ""
        self._anterior = None   # (id_emisor, num_serie, fecha_expedicion)
        self._n = 0

    @property
    def ultima_huella(self) -> str:
        return self._ultima_huella

    def _siguiente(self, registro):
        registro.huella_anterior = self._ultima_huella
        registro.primer_registro = (self._n == 0)
        if self._anterior is not None:
            (registro.anterior_id_emisor,
             registro.anterior_num_serie,
             registro.anterior_fecha_expedicion) = self._anterior
        # tras calcular, este registro pasa a ser el "anterior" del siguiente
        self._ultima_huella = registro.huella
        self._anterior = (registro.id_emisor, registro.num_serie,
                          registro.fecha_expedicion)
        self._n += 1
        return registro

    def alta(self, *, num_serie, fecha_expedicion, tipo_factura,
             cuota_total, importe_total, fecha_hora_huso,
             nombre_razon_emisor="", descripcion_operacion="",
             desglose=None, destinatario_nombre=None,
             destinatario_nif=None) -> RegistroAlta:
        reg = RegistroAlta(
            id_emisor=self.emisor.nif,
            num_serie=num_serie,
            fecha_expedicion=fecha_expedicion,
            tipo_factura=tipo_factura,
            cuota_total=cuota_total,
            importe_total=importe_total,
            fecha_hora_huso=fecha_hora_huso,
            nombre_razon_emisor=nombre_razon_emisor or self.emisor.nombre,
            descripcion_operacion=descripcion_operacion,
            desglose=desglose or [],
            destinatario_nombre=destinatario_nombre,
            destinatario_nif=destinatario_nif,
        )
        return self._siguiente(reg)

    def anulacion(self, *, num_serie, fecha_expedicion,
                  fecha_hora_huso) -> RegistroAnulacion:
        reg = RegistroAnulacion(
            id_emisor=self.emisor.nif,
            num_serie=num_serie,
            fecha_expedicion=fecha_expedicion,
            fecha_hora_huso=fecha_hora_huso,
        )
        return self._siguiente(reg)
