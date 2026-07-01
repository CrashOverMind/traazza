"""Validación de los XML contra el XSD oficial de la AEAT (F1.8.2).

Hasta ahora el XML se cotejó *a mano* campo a campo contra el diseño oficial
(F1.8/F1.8.1). Este módulo añade la validación PROGRAMÁTICA contra el esquema
XSD, para que cualquier regresión salte sola en los tests.

Diseño (consistente con el resto de Traazza):
  - El núcleo no depende de nada. La validación XSD vive detrás del extra
    opcional `traazza[xsd]` → `xmlschema`, con import perezoso y error claro
    si falta.
  - No se incluye el XSD oficial en el repo (lo publica la AEAT en su sede;
    cada quien lo descarga). Las funciones reciben la RUTA al XSD, o un
    esquema ya cargado, para poder reutilizarlo entre validaciones.

Uso típico:
    from traazza import validacion, xml
    esquema = validacion.cargar_esquema("SuministroInformacion.xsd")
    validacion.validar_alta(reg, sistema, esquema)        # lanza si no valida
    errores = validacion.errores_alta(reg, sistema, esquema)  # lista (diagnóstico)
"""

from pathlib import Path

from .errores import DatosInvalidosError

# XSD oficiales de la AEAT incluidos en el paquete (namespace tike/cont/ws),
# para poder validar sin que el usuario tenga que buscarlos.
RUTA_ESQUEMAS = Path(__file__).parent / "esquemas"
_DSIG_NS = "http://www.w3.org/2000/09/xmldsig#"
_LOCATIONS = {_DSIG_NS: str(RUTA_ESQUEMAS / "xmldsig-core-schema.xsd")}


def esquema_registros():
    """Carga el `SuministroInformacion.xsd` oficial incluido en el paquete.

    Sirve para validar un RegistroAlta/RegistroAnulacion suelto.
    """
    return cargar_esquema(RUTA_ESQUEMAS / "SuministroInformacion.xsd", locations=_LOCATIONS)


def esquema_envoltorio():
    """Carga el `SuministroLR.xsd` oficial incluido en el paquete.

    Sirve para validar el RegFactuSistemaFacturacion completo.
    """
    return cargar_esquema(RUTA_ESQUEMAS / "SuministroLR.xsd", locations=_LOCATIONS)


def _xmlschema():
    """Importa xmlschema de forma perezosa con un mensaje útil si falta."""
    try:
        import xmlschema
    except ImportError as e:  # pragma: no cover
        raise DatosInvalidosError(
            "La validación contra XSD requiere 'xmlschema'. "
            "Instala el extra:  pip install traazza[xsd]"
        ) from e
    return xmlschema


def cargar_esquema(xsd_path, *, locations=None):
    """Carga un XSD desde una ruta y devuelve el objeto esquema.

    Cárgalo una vez y reutilízalo: compilar el esquema es lo caro, validar es
    barato. Los `import`/`include` del XSD se resuelven de forma relativa a la
    ubicación del propio fichero, así que mantén juntos los XSD que se
    referencian entre sí.

    `locations` permite mapear un namespace a un XSD local cuando el `import`
    apunta a una URL externa que no quieres (o no puedes) descargar. El caso
    típico: el esquema de la AEAT importa `xmldsig` desde w3.org; como
    `ds:Signature` es opcional y la librería no lo emite, basta con apuntar ese
    namespace a un stub local:

        cargar_esquema("SuministroInformacion.xsd",
                       locations={"http://www.w3.org/2000/09/xmldsig#": "xmldsig.xsd"})
    """
    kwargs = {"locations": locations} if locations else {}
    return _xmlschema().XMLSchema(str(xsd_path), **kwargs)


def _esquema(xsd):
    """Acepta tanto una ruta/cadena como un esquema ya cargado."""
    return xsd if hasattr(xsd, "iter_errors") else cargar_esquema(xsd)


def validar_contra_xsd(xml_str: str, xsd) -> bool:
    """Valida un XML contra el XSD. Devuelve True o lanza con el detalle.

    `xsd` puede ser la ruta al fichero .xsd o un esquema ya cargado con
    `cargar_esquema`.
    """
    esquema = _esquema(xsd)
    xs = _xmlschema()
    try:
        esquema.validate(xml_str)
    except xs.XMLSchemaValidationError as e:
        raise DatosInvalidosError(f"El XML no valida contra el XSD:\n{e}") from e
    return True


def errores_contra_xsd(xml_str: str, xsd) -> list:
    """Devuelve la lista de TODOS los errores de validación (cadena vacía si OK).

    A diferencia de `validar_contra_xsd`, no se detiene en el primero: útil para
    diagnosticar de un vistazo (y reutilizable por la futura CLI, F3.2).
    """
    esquema = _esquema(xsd)
    return [str(err) for err in esquema.iter_errors(xml_str)]


# --- Atajos que serializan el registro y lo validan -----------------------

def validar_alta(reg, sistema, xsd) -> bool:
    """Serializa un RegistroAlta y lo valida contra el XSD."""
    from . import xml as _xml
    return validar_contra_xsd(_xml.registro_alta_xml(reg, sistema, indent=False), xsd)


def validar_anulacion(reg, sistema, xsd) -> bool:
    """Serializa un RegistroAnulacion y lo valida contra el XSD."""
    from . import xml as _xml
    return validar_contra_xsd(_xml.registro_anulacion_xml(reg, sistema, indent=False), xsd)


def errores_alta(reg, sistema, xsd) -> list:
    from . import xml as _xml
    return errores_contra_xsd(_xml.registro_alta_xml(reg, sistema, indent=False), xsd)


def errores_anulacion(reg, sistema, xsd) -> list:
    from . import xml as _xml
    return errores_contra_xsd(_xml.registro_anulacion_xml(reg, sistema, indent=False), xsd)


def validar_envoltorio(emisor, registros, sistema, xsd) -> bool:
    """Serializa el RegFactuSistemaFacturacion completo y lo valida contra el XSD.

    `xsd` debe ser (o cargar) el SuministroLR.xsd, que a su vez importa el
    SuministroInformacion.xsd.
    """
    from . import envoltorio as _env
    return validar_contra_xsd(_env.envoltorio_xml(emisor, registros, sistema, indent=False), xsd)
