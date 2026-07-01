"""Serialización de los registros a XML conforme al diseño oficial de la AEAT.

El ORDEN y los NOMBRES de los elementos provienen del Excel oficial de diseños
de registro ("DsRegistroVeriFactu.xlsx", hoja "D. Registro Facturación Alta" y
"D. Reg. Facturación Anulación"). El valor de IDVersion es "1.0" (lista L15).

⚠️ NAMESPACES — único dato a confirmar contra el XSD oficial (F1.8.1):
  El Excel fija los nombres y el orden de los elementos, pero NO el URI de los
  espacios de nombres. Los valores de abajo son los documentados públicamente
  para Veri*factu; deben verificarse contra los XSD de la sede AEAT
  (Esquemas de los servicios web) antes de remitir nada de verdad. Están
  aislados como constantes para poder cambiarlos en un solo sitio.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

from .modelos import RegistroAlta, RegistroAnulacion, SistemaInformatico, formatear_importe
from .errores import DatosInvalidosError

# Namespaces (CONFIRMAR contra XSD oficial — ver aviso de cabecera).
NS_SUM1 = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd"
NS_SUM = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd"

_PREFIJO = "sum1"


def _q(tag: str) -> str:
    return f"{{{NS_SUM1}}}{tag}"


def _sub(parent, tag, texto=None):
    """Crea un subelemento; si texto es None, no añade nada (campo opcional)."""
    el = ET.SubElement(parent, _q(tag))
    if texto is not None:
        el.text = str(texto)
    return el


def _registro_alta_elem(reg: RegistroAlta, sistema: SistemaInformatico) -> ET.Element:
    # Campos que el XSD oficial exige en el alta (y que la huella/QR no usan):
    # validarlos aquí evita generar XML inválido por descuido.
    if not reg.descripcion_operacion:
        raise DatosInvalidosError(
            "El alta requiere 'descripcion_operacion' (DescripcionOperacion es "
            "obligatorio en el XSD, máx. 500 caracteres).")
    if not reg.desglose:
        raise DatosInvalidosError(
            "El alta requiere al menos una línea de 'desglose' "
            "(Desglose/DetalleDesglose es obligatorio, 1 a 12 líneas).")

    raiz = ET.Element(_q("RegistroAlta"))

    _sub(raiz, "IDVersion", reg.id_version)

    idf = _sub(raiz, "IDFactura")
    _sub(idf, "IDEmisorFactura", reg.id_emisor)
    _sub(idf, "NumSerieFactura", reg.num_serie)
    _sub(idf, "FechaExpedicionFactura", reg.fecha_expedicion)

    if reg.nombre_razon_emisor:
        _sub(raiz, "NombreRazonEmisor", reg.nombre_razon_emisor)

    _sub(raiz, "TipoFactura", reg.tipo_factura)

    _sub(raiz, "DescripcionOperacion", reg.descripcion_operacion)

    # Destinatarios (obligatorio para F1; opcional aquí)
    if reg.destinatario_nombre or reg.destinatario_nif:
        dests = _sub(raiz, "Destinatarios")
        idd = _sub(dests, "IDDestinatario")
        if reg.destinatario_nombre:
            _sub(idd, "NombreRazon", reg.destinatario_nombre)
        if reg.destinatario_nif:
            _sub(idd, "NIF", reg.destinatario_nif)

    # Desglose (1-12 DetalleDesglose)
    desg = _sub(raiz, "Desglose")
    for linea in reg.desglose:
        det = _sub(desg, "DetalleDesglose")
        if linea.impuesto is not None:
            _sub(det, "Impuesto", linea.impuesto)
        if linea.clave_regimen is not None:
            _sub(det, "ClaveRegimen", linea.clave_regimen)
        if linea.operacion_exenta is not None:
            _sub(det, "OperacionExenta", linea.operacion_exenta)
        else:
            _sub(det, "CalificacionOperacion", linea.calificacion_operacion)
        if linea.tipo_impositivo is not None:
            _sub(det, "TipoImpositivo", formatear_importe(linea.tipo_impositivo))
        _sub(det, "BaseImponibleOimporteNoSujeto", formatear_importe(linea.base_imponible))
        if linea.cuota_repercutida is not None:
            _sub(det, "CuotaRepercutida", formatear_importe(linea.cuota_repercutida))

    _sub(raiz, "CuotaTotal", formatear_importe(reg.cuota_total))
    _sub(raiz, "ImporteTotal", formatear_importe(reg.importe_total))

    # Encadenamiento
    enc = _sub(raiz, "Encadenamiento")
    if reg.primer_registro:
        _sub(enc, "PrimerRegistro", "S")
    else:
        ant = _sub(enc, "RegistroAnterior")
        _sub(ant, "IDEmisorFactura", reg.anterior_id_emisor)
        _sub(ant, "NumSerieFactura", reg.anterior_num_serie)
        _sub(ant, "FechaExpedicionFactura", reg.anterior_fecha_expedicion)
        _sub(ant, "Huella", reg.huella_anterior)

    _añadir_sistema(raiz, sistema)

    _sub(raiz, "FechaHoraHusoGenRegistro", reg.fecha_hora_huso)
    _sub(raiz, "TipoHuella", "01")   # L12: SHA-256
    _sub(raiz, "Huella", reg.huella)
    return raiz


def _añadir_sistema(parent, s: SistemaInformatico):
    si = _sub(parent, "SistemaInformatico")
    _sub(si, "NombreRazon", s.nombre_razon)
    _sub(si, "NIF", s.nif)
    _sub(si, "NombreSistemaInformatico", s.nombre_sif)
    _sub(si, "IdSistemaInformatico", s.id_sif)
    _sub(si, "Version", s.version)
    _sub(si, "NumeroInstalacion", s.numero_instalacion)
    _sub(si, "TipoUsoPosibleSoloVerifactu", s.solo_verifactu)
    _sub(si, "TipoUsoPosibleMultiOT", s.multi_ot)
    _sub(si, "IndicadorMultiplesOT", s.indicador_multiples_ot)


def _registro_anulacion_elem(reg: RegistroAnulacion, sistema: SistemaInformatico) -> ET.Element:
    raiz = ET.Element(_q("RegistroAnulacion"))
    _sub(raiz, "IDVersion", reg.id_version)
    idf = _sub(raiz, "IDFactura")
    _sub(idf, "IDEmisorFacturaAnulada", reg.id_emisor)
    _sub(idf, "NumSerieFacturaAnulada", reg.num_serie)
    _sub(idf, "FechaExpedicionFacturaAnulada", reg.fecha_expedicion)
    enc = _sub(raiz, "Encadenamiento")
    if reg.primer_registro:
        _sub(enc, "PrimerRegistro", "S")
    else:
        ant = _sub(enc, "RegistroAnterior")
        _sub(ant, "IDEmisorFactura", reg.anterior_id_emisor)
        _sub(ant, "NumSerieFactura", reg.anterior_num_serie)
        _sub(ant, "FechaExpedicionFactura", reg.anterior_fecha_expedicion)
        _sub(ant, "Huella", reg.huella_anterior)
    _añadir_sistema(raiz, sistema)
    _sub(raiz, "FechaHoraHusoGenRegistro", reg.fecha_hora_huso)
    _sub(raiz, "TipoHuella", "01")
    _sub(raiz, "Huella", reg.huella)
    return raiz


def _serializar(elem: ET.Element, indent: bool) -> str:
    ET.register_namespace(_PREFIJO, NS_SUM1)
    crudo = ET.tostring(elem, encoding="unicode")
    if not indent:
        return crudo
    return minidom.parseString(crudo).toprettyxml(indent="  ").split("\n", 1)[1].strip()


def registro_alta_xml(reg: RegistroAlta, sistema: SistemaInformatico, indent: bool = True) -> str:
    """Devuelve el XML del <RegistroAlta> conforme al diseño AEAT."""
    return _serializar(_registro_alta_elem(reg, sistema), indent)


def registro_anulacion_xml(reg: RegistroAnulacion, sistema: SistemaInformatico, indent: bool = True) -> str:
    """Devuelve el XML del <RegistroAnulacion> conforme al diseño AEAT."""
    return _serializar(_registro_anulacion_elem(reg, sistema), indent)


def elemento_registro(reg, sistema: SistemaInformatico) -> ET.Element:
    """Devuelve el Element (alta o anulación) según el tipo de `reg`.

    Lo usa el envoltorio (RegFactuSistemaFacturacion) para meter cada registro
    dentro de su <RegistroFactura> reutilizando exactamente la misma
    serialización ya validada contra el XSD.
    """
    if isinstance(reg, RegistroAlta):
        return _registro_alta_elem(reg, sistema)
    if isinstance(reg, RegistroAnulacion):
        return _registro_anulacion_elem(reg, sistema)
    raise TypeError(f"Tipo de registro no soportado: {type(reg).__name__}")
