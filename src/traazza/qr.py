"""Generación del «QR tributario» Verifactu (F1.6).

Fuente normativa:
  - Orden HAC/1177/2024, arts. 20 y 21.
  - AEAT, "Detalle de las especificaciones técnicas del código «QR» de la
    factura y de la «URL» del servicio de cotejo o remisión de información"
    (v0.5.0, 10/12/2025).

Qué hace este módulo:
  1. NÚCLEO (sin dependencias): construir y VALIDAR la «URL» que va dentro del
     código QR, con su `URL encoding` (UTF-8) exactamente como exige la AEAT.
     Esto es lo normativo y lo que se contrasta contra los ejemplos oficiales.
  2. RENDER (extra opcional `traazza[qr]` → segno): convertir esa URL en una
     imagen QR (SVG/PNG) con nivel de corrección de errores M, como pide el
     art. 21. El núcleo NO depende de segno; el import es perezoso y, si falta,
     se lanza un error claro.

La especificación del QR usa SOLO 4 datos de la factura (apartado 6):
    nif, numserie, fecha (DD-MM-AAAA) e importe total.
Son los mismos cuatro que la persona ya tiene en su `RegistroAlta`, así que hay
un atajo (`url_desde_registro`) para no repetirlos a mano.

⚠️ El 5.º parámetro «formato=json» NUNCA debe ir en la URL del QR de la factura
   (apartado 7.2). Este módulo nunca lo añade.
"""

import re
from decimal import Decimal, InvalidOperation
from enum import Enum

from .errores import DatosInvalidosError

# --- URLs base oficiales (apartado 5) -------------------------------------
# Sistema que emite facturas VERIFICABLES (Veri*factu) → ValidarQR
# Sistema que emite facturas NO verificables           → ValidarQRNoVerifactu
_BASE_PRUEBAS = "https://prewww2.aeat.es/wlpl/TIKE-CONT/"
_BASE_PRODUCCION = "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/"


class Entorno(Enum):
    """Entorno al que apunta la URL de cotejo del QR."""
    PRUEBAS = "pruebas"        # Portal de Pruebas Externas
    PRODUCCION = "produccion"


def _url_base(entorno: Entorno, verificable: bool) -> str:
    servicio = "ValidarQR" if verificable else "ValidarQRNoVerifactu"
    raiz = _BASE_PRUEBAS if entorno == Entorno.PRUEBAS else _BASE_PRODUCCION
    return f"{raiz}{servicio}"


# --- Textos de presentación (apartado 3) ----------------------------------
# El art. 21 / apartado 3 exigen un texto que SIEMPRE precede al QR y, para
# facturas verificables, una frase justo debajo. La maquetación de la factura
# es responsabilidad de quien integra la librería; exponemos los literales
# oficiales para que no tenga que transcribirlos.
TEXTO_QR_TRIBUTARIO = "QR tributario:"
FRASE_VERIFACTU_LARGA = "Factura verificable en la sede electrónica de la AEAT"
FRASE_VERIFACTU_CORTA = "VERI*FACTU"

# Tamaño físico admitido por el art. 21 (en milímetros).
TAMANO_MIN_MM = 30
TAMANO_MAX_MM = 40

# --- Validaciones de parámetros (apartados 6 y 10) ------------------------
NUMSERIE_MAX = 60          # 2002: nº de serie excede el máximo
IMPORTE_ENTERO_MAX = 12    # 2006: importe excede el máximo

# NIF: longitud 9. No hacemos el cálculo del dígito de control (eso lo valida
# el servicio de la AEAT); solo descartamos los errores evidentes de longitud
# o caracteres, que es lo que aporta valor en cliente.
_RE_NIF = re.compile(r"^[A-Z0-9]{9}$")
_RE_FECHA = re.compile(r"^(\d{2})-(\d{2})-(\d{4})$")
_RE_IMPORTE = re.compile(r"^\d{1,12}(\.\d{1,2})?$")


def _validar_nif(nif: str) -> str:
    if not nif:
        raise DatosInvalidosError("Falta el parámetro 'nif' (NIF del obligado a expedir). [1001]")
    nif = nif.strip().upper()
    if not _RE_NIF.match(nif):
        raise DatosInvalidosError(f"El NIF tiene un formato erróneo o no es válido: {nif!r}. [2001]")
    return nif


def _validar_numserie(numserie: str) -> str:
    if not numserie:
        raise DatosInvalidosError("Falta el parámetro 'numserie' (nº de serie + nº de factura). [1002]")
    if len(numserie) > NUMSERIE_MAX:
        raise DatosInvalidosError(
            f"El número de serie excede el máximo de {NUMSERIE_MAX} caracteres. [2002]")
    # Solo se admiten caracteres ASCII imprimibles (códigos 32..126).
    for ch in numserie:
        if not (32 <= ord(ch) <= 126):
            raise DatosInvalidosError(
                f"El número de serie contiene caracteres no permitidos: {ch!r}. [2003]")
    return numserie


def _validar_fecha(fecha: str) -> str:
    if not fecha:
        raise DatosInvalidosError("Falta el parámetro 'fecha' (fecha de expedición). [1003]")
    m = _RE_FECHA.match(fecha)
    if not m:
        raise DatosInvalidosError(
            f"La fecha de expedición debe tener el formato DD-MM-AAAA: {fecha!r}. [2004]")
    dia, mes, anio = (int(x) for x in m.groups())
    # Comprobación de fecha real (rechaza 31-02, 00-00, etc.).
    from datetime import date
    try:
        date(anio, mes, dia)
    except ValueError:
        raise DatosInvalidosError(
            f"La fecha de expedición no es una fecha válida: {fecha!r}. [2004]")
    return fecha


def _normalizar_importe(importe) -> str:
    """Devuelve el importe como cadena válida para el QR.

    - Si llega como str con formato válido, se respeta TAL CUAL (la AEAT admite
      1 o 2 decimales: el ejemplo oficial usa `241.4`).
    - Si llega como número/Decimal, se normaliza a 2 decimales con punto.
    """
    if importe is None or importe == "":
        raise DatosInvalidosError("Falta el parámetro 'importe' (importe total). [1004]")

    if isinstance(importe, str):
        candidato = importe.strip()
        if not _RE_IMPORTE.match(candidato):
            raise DatosInvalidosError(
                f"El importe tiene un formato incorrecto (use '.' como separador): {importe!r}. [2005]")
        entero = candidato.split(".")[0]
        if len(entero) > IMPORTE_ENTERO_MAX:
            raise DatosInvalidosError(
                f"El importe excede el máximo de {IMPORTE_ENTERO_MAX} dígitos enteros. [2006]")
        return candidato

    try:
        d = Decimal(str(importe))
    except (InvalidOperation, ValueError):
        raise DatosInvalidosError(f"El importe tiene un formato incorrecto: {importe!r}. [2005]")
    texto = f"{d:.2f}"
    entero = texto.split(".")[0].lstrip("-")
    if len(entero) > IMPORTE_ENTERO_MAX:
        raise DatosInvalidosError(
            f"El importe excede el máximo de {IMPORTE_ENTERO_MAX} dígitos enteros. [2006]")
    return texto


def _encode(valor: str) -> str:
    """`URL encoding` (UTF-8) de un valor, idéntico a la referencia de la AEAT.

    El documento oficial (apartado 4.1, pág. 9) publica como referencia un
    `codificarQR` en Java que usa `java.net.URLEncoder.encode(param, "UTF-8")`
    (codificación `application/x-www-form-urlencoded`). Reproducimos su
    semántica EXACTA para casar byte a byte con esa referencia:

      - se dejan sin codificar letras, dígitos y `. - * _`
      - el espacio se codifica como `+`
      - el resto se percent-codifica en UTF-8 (incluido `~` → `%7E`)

    Esto reproduce el ejemplo del apartado 4 (`12345678&G33` → `12345678%26G33`)
    y los del apartado 8. Difiere del percent-encoding RFC 3986 solo en espacio,
    `*` y `~`; en esos casos el servicio de la AEAT decodifica ambas formas al
    mismo valor, pero igualar la referencia evita cualquier discusión.
    """
    out = []
    for ch in valor:
        if ch.isalnum() or ch in ".-*_":
            out.append(ch)
        elif ch == " ":
            out.append("+")
        else:
            out.append("".join(f"%{b:02X}" for b in ch.encode("utf-8")))
    return "".join(out)


def url_factura(*, nif, numserie, fecha, importe,
                entorno: Entorno = Entorno.PRODUCCION,
                verificable: bool = True) -> str:
    """Construye la «URL» de cotejo que va DENTRO del código QR.

    Valida los 4 parámetros obligatorios (apartado 6) y aplica el `URL
    encoding` exigido. El orden de parámetros es el del documento oficial:
    nif, numserie, fecha, importe.

    Lanza `DatosInvalidosError` (con el código de error AEAT entre corchetes)
    si algún parámetro no cumple. NO añade nunca el parámetro `formato`.
    """
    nif = _validar_nif(nif)
    numserie = _validar_numserie(numserie)
    fecha = _validar_fecha(fecha)
    importe = _normalizar_importe(importe)

    base = _url_base(entorno, verificable)
    return (
        f"{base}?nif={_encode(nif)}"
        f"&numserie={_encode(numserie)}"
        f"&fecha={_encode(fecha)}"
        f"&importe={_encode(importe)}"
    )


def url_desde_registro(reg, *, entorno: Entorno = Entorno.PRODUCCION,
                       verificable: bool = True) -> str:
    """Atajo: construye la URL del QR a partir de un `RegistroAlta`.

    Toma nif (id_emisor), numserie (num_serie), fecha (fecha_expedicion) e
    importe (importe_total) directamente del registro de alta.
    """
    return url_factura(
        nif=reg.id_emisor,
        numserie=reg.num_serie,
        fecha=reg.fecha_expedicion,
        importe=reg.importe_total,
        entorno=entorno,
        verificable=verificable,
    )


# --- Render a imagen (extra opcional: traazza[qr] → segno) -----------------
_NIVEL_CORRECCION = "m"   # art. 21: nivel M (medio), obligatorio.


def _segno():
    """Importa segno de forma perezosa con un mensaje útil si falta."""
    try:
        import segno
    except ImportError as e:  # pragma: no cover
        raise DatosInvalidosError(
            "La generación de la imagen QR requiere 'segno'. "
            "Instala el extra:  pip install traazza[qr]"
        ) from e
    return segno


def codigo_qr(url: str):
    """Devuelve el objeto QR (segno.QRCode) de una URL, con nivel M.

    Con él puedes guardar o serializar a tu gusto:
        qr = codigo_qr(url)
        qr.save("factura.png", scale=8, border=4)
        qr.save("factura.svg", scale=8)
    """
    return _segno().make(url, error=_NIVEL_CORRECCION)


def qr_svg(url: str, *, scale: int = 8, border: int = 4) -> str:
    """Devuelve el QR como cadena SVG (ideal para incrustar en facturas HTML/PDF).

    `border` es la zona de silencio en módulos. El estándar ISO exige un mínimo
    de 4 módulos; la AEAT recomienda ~6 mm de blanco alrededor (apartado 3): a
    40x40 mm eso se cumple sobradamente con el borde por defecto.
    """
    import io
    buf = io.BytesIO()
    codigo_qr(url).save(buf, kind="svg", scale=scale, border=border, xmldecl=False)
    return buf.getvalue().decode("utf-8")


def qr_png(url: str, *, scale: int = 8, border: int = 4) -> bytes:
    """Devuelve el QR como bytes PNG."""
    import io
    buf = io.BytesIO()
    codigo_qr(url).save(buf, kind="png", scale=scale, border=border)
    return buf.getvalue()


def guardar_qr(url: str, ruta: str, *, scale: int = 8, border: int = 4) -> None:
    """Guarda el QR en disco; el formato se deduce de la extensión de `ruta`."""
    codigo_qr(url).save(ruta, scale=scale, border=border)
