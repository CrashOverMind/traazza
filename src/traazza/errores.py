"""Errores tipados de Traazza.

Tener errores propios y específicos (en vez de ValueError genéricos) facilita
que quien integre la librería distinga un problema de datos de un problema de
encadenamiento, y reaccione distinto a cada uno.
"""


class TraazzaError(Exception):
    """Error base de la librería. Todo lo demás hereda de aquí."""


class DatosInvalidosError(TraazzaError):
    """Algún campo del registro falta o tiene un formato no admitido."""


class EncadenamientoError(TraazzaError):
    """La cadena de huellas se ha usado de forma incorrecta.

    Por ejemplo: marcar como 'primer registro' uno que ya tiene huella
    anterior, o intentar encadenar fuera de orden.
    """
