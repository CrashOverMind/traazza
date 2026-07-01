"""Registro de eventos del sistema (F2.2) — helper opcional.

El Reglamento (RD 1007/2023) obliga al SIF a llevar un «registro de eventos»
que deje traza de hechos relevantes (arranque, generación de registros,
exportaciones, incidencias, etc.). Traazza ofrece aquí una utilidad ligera y
encadenada para ayudar al integrador a cumplirlo; igual que con la facturación,
quien decide qué registrar y dónde conservarlo es el productor del SIF.

Los eventos se encadenan con la misma función de huella SHA-256 que los
registros de facturación: cada evento incorpora la huella del anterior, de modo
que el log es a prueba de manipulación (no se puede borrar/alterar un evento sin
romper la cadena).

NOTA: los tipos y el detalle exacto de cada evento deben ajustarse a la lista
oficial de eventos de la AEAT cuando se publique la versión definitiva; esta
estructura cubre el mecanismo (encadenado + sellado temporal + serialización).
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum

from . import huella as _huella


class TipoEvento(str, Enum):
    INICIO_OPERACION = "InicioOperacion"
    FIN_OPERACION = "FinOperacion"
    GENERACION_REGISTRO = "GeneracionRegistroFacturacion"
    EXPORTACION = "Exportacion"
    DETECCION_ANOMALIA = "DeteccionAnomalia"
    INCIDENCIA = "Incidencia"
    RESTAURACION_COPIA = "RestauracionCopiaSeguridad"
    LANZAMIENTO_VERIFACTU = "LanzamientoModoVerifactu"
    PARADA_VERIFACTU = "ParadaModoVerifactu"


@dataclass
class Evento:
    tipo: TipoEvento
    detalle: str = ""
    marca_tiempo: str = ""        # ISO 8601 con zona
    huella_anterior: str = ""
    huella: str = ""

    def cadena_huella(self) -> str:
        # Mismo estilo clave=valor & que la huella de facturación.
        return (
            f"Tipo={self.tipo.value}"
            f"&Detalle={self.detalle}"
            f"&MarcaTiempo={self.marca_tiempo}"
            f"&HuellaAnterior={self.huella_anterior}"
        )


class RegistroEventos:
    """Log de eventos append-only y encadenado por huella SHA-256."""

    def __init__(self):
        self._eventos = []
        self._ultima_huella = ""

    @property
    def eventos(self) -> list:
        return list(self._eventos)

    @property
    def ultima_huella(self) -> str:
        return self._ultima_huella

    def registrar(self, tipo: TipoEvento, detalle: str = "",
                  marca_tiempo: str = None) -> Evento:
        """Añade un evento al log, encadenándolo con el anterior."""
        if marca_tiempo is None:
            marca_tiempo = datetime.now(timezone.utc).isoformat()
        ev = Evento(tipo=tipo, detalle=detalle, marca_tiempo=marca_tiempo,
                    huella_anterior=self._ultima_huella)
        ev.huella = _huella.calcular(ev.cadena_huella())
        self._ultima_huella = ev.huella
        self._eventos.append(ev)
        return ev

    def verificar(self) -> bool:
        """Recalcula toda la cadena y comprueba que nadie la ha manipulado."""
        anterior = ""
        for ev in self._eventos:
            if ev.huella_anterior != anterior:
                return False
            esperada = _huella.calcular(ev.cadena_huella())
            if ev.huella != esperada:
                return False
            anterior = ev.huella
        return True

    def a_dicts(self) -> list:
        """Vuelca el log a una lista de dicts (para serializar a JSON/CSV)."""
        out = []
        for ev in self._eventos:
            d = asdict(ev)
            d["tipo"] = ev.tipo.value
            out.append(d)
        return out
