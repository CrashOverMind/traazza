"""Interfaz de línea de comandos de Traazza (F3.2).

Uso rápido:
    traazza qr --nif 89890001K --numserie 2024/A-1 --fecha 01-01-2024 --importe 121.00
    traazza cadena facturas.json
    traazza xml facturas.json
    traazza envoltorio facturas.json
    traazza validar registro.xml

Formato del JSON de facturas (para cadena/xml/envoltorio):

    {
      "emisor":  {"nif": "89890001K", "nombre": "Empresa Ejemplo SL"},
      "sistema": {"nombre_razon": "Mi Software SL", "nif": "B00000000",
                  "nombre_sif": "MiFacturador", "id_sif": "01",
                  "version": "1.0.0", "numero_instalacion": "INST-001"},
      "facturas": [
        {"tipo": "alta", "num_serie": "2024/A-1", "fecha_expedicion": "01-01-2024",
         "tipo_factura": "F1", "cuota_total": "21.00", "importe_total": "121.00",
         "fecha_hora_huso": "2024-01-01T10:00:00+01:00",
         "descripcion_operacion": "Venta",
         "desglose": [{"base_imponible": "100.00", "cuota_repercutida": "21.00",
                       "tipo_impositivo": "21.00"}]},
        {"tipo": "anulacion", "num_serie": "2024/A-0",
         "fecha_expedicion": "01-01-2024",
         "fecha_hora_huso": "2024-01-01T10:05:00+01:00"}
      ]
    }
"""

import argparse
import json
import sys

from . import qr as _qr
from . import xml as _xml
from . import envoltorio as _env
from . import validacion as _val
from .modelos import Emisor, Cadena, SistemaInformatico, LineaDesglose
from .errores import TraazzaError


def _cargar_json(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def _construir(datos):
    """De un dict JSON a (emisor, sistema, lista_de_registros encadenados)."""
    emisor = Emisor(datos["emisor"]["nif"], datos["emisor"].get("nombre", ""))
    s = datos["sistema"]
    sistema = SistemaInformatico(
        nombre_razon=s["nombre_razon"], nif=s["nif"], nombre_sif=s["nombre_sif"],
        id_sif=s["id_sif"], version=s["version"], numero_instalacion=s["numero_instalacion"])
    cadena = Cadena(emisor)
    registros = []
    for f in datos["facturas"]:
        if f.get("tipo", "alta") == "anulacion":
            reg = cadena.anulacion(num_serie=f["num_serie"],
                                   fecha_expedicion=f["fecha_expedicion"],
                                   fecha_hora_huso=f["fecha_hora_huso"])
        else:
            desglose = [LineaDesglose(**linea) for linea in f.get("desglose", [])]
            reg = cadena.alta(
                num_serie=f["num_serie"], fecha_expedicion=f["fecha_expedicion"],
                tipo_factura=f["tipo_factura"], cuota_total=f["cuota_total"],
                importe_total=f["importe_total"], fecha_hora_huso=f["fecha_hora_huso"],
                descripcion_operacion=f.get("descripcion_operacion", ""),
                desglose=desglose)
        registros.append(reg)
    return emisor, sistema, registros


# --- Comandos --------------------------------------------------------------

def cmd_qr(args):
    entorno = _qr.Entorno.PRODUCCION if args.produccion else _qr.Entorno.PRUEBAS
    url = _qr.url_factura(nif=args.nif, numserie=args.numserie, fecha=args.fecha,
                          importe=args.importe, entorno=entorno,
                          verificable=not args.no_verificable)
    print(url)
    if args.salida:
        _qr.guardar_qr(url, args.salida)
        print(f"QR guardado en {args.salida}", file=sys.stderr)
    return 0


def cmd_cadena(args):
    _, _, registros = _construir(_cargar_json(args.json))
    print(f"{'#':>2}  {'tipo':<10} {'num_serie':<16} huella")
    for i, reg in enumerate(registros):
        tipo = type(reg).__name__.replace("Registro", "")
        print(f"{i:>2}  {tipo:<10} {reg.num_serie:<16} {reg.huella}")
    return 0


def cmd_xml(args):
    from .modelos import RegistroAlta
    _, sistema, registros = _construir(_cargar_json(args.json))
    if args.indice is not None:
        registros = [registros[args.indice]]
    salida = []
    for reg in registros:
        if isinstance(reg, RegistroAlta):
            salida.append(_xml.registro_alta_xml(reg, sistema))
        else:
            salida.append(_xml.registro_anulacion_xml(reg, sistema))
    print("\n\n".join(salida))
    return 0


def cmd_envoltorio(args):
    emisor, sistema, registros = _construir(_cargar_json(args.json))
    print(_env.envoltorio_xml(emisor, registros, sistema))
    return 0


def cmd_validar(args):
    with open(args.xml, "r", encoding="utf-8") as f:
        contenido = f.read()
    if args.xsd:
        esquema = _val.cargar_esquema(args.xsd)
    elif args.envoltorio:
        esquema = _val.esquema_envoltorio()
    else:
        esquema = _val.esquema_registros()
    errores = _val.errores_contra_xsd(contenido, esquema)
    if not errores:
        print("✓ VÁLIDO contra el XSD oficial")
        return 0
    print("✗ NO válido:")
    for e in errores:
        print("  -", e.split("\n")[0])
    return 1


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="traazza",
        description="Herramientas Verifactu: huella, QR, XML y validación.")
    sub = p.add_subparsers(dest="comando", required=True)

    q = sub.add_parser("qr", help="Genera la URL del QR (y opcionalmente la imagen).")
    q.add_argument("--nif", required=True)
    q.add_argument("--numserie", required=True)
    q.add_argument("--fecha", required=True, help="DD-MM-AAAA")
    q.add_argument("--importe", required=True)
    q.add_argument("--salida", help="ruta PNG/SVG donde guardar el QR")
    q.add_argument("--produccion", action="store_true", help="usar URL de producción")
    q.add_argument("--no-verificable", action="store_true", help="modo NO Veri*factu")
    q.set_defaults(func=cmd_qr)

    c = sub.add_parser("cadena", help="Muestra la huella encadenada de cada factura.")
    c.add_argument("json", help="fichero JSON de facturas")
    c.set_defaults(func=cmd_cadena)

    x = sub.add_parser("xml", help="Genera el XML de los registros.")
    x.add_argument("json", help="fichero JSON de facturas")
    x.add_argument("--indice", type=int, help="solo el registro N (0 = primero)")
    x.set_defaults(func=cmd_xml)

    e = sub.add_parser("envoltorio", help="Genera el RegFactuSistemaFacturacion completo.")
    e.add_argument("json", help="fichero JSON de facturas")
    e.set_defaults(func=cmd_envoltorio)

    v = sub.add_parser("validar", help="Valida un XML contra el XSD oficial incluido.")
    v.add_argument("xml", help="fichero XML a validar")
    v.add_argument("--envoltorio", action="store_true",
                   help="validar como RegFactuSistemaFacturacion (SuministroLR.xsd)")
    v.add_argument("--xsd", help="usar un XSD propio en vez del incluido")
    v.set_defaults(func=cmd_validar)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except TraazzaError as ex:
        print(f"Error: {ex}", file=sys.stderr)
        return 2
    except FileNotFoundError as ex:
        print(f"No se encuentra el fichero: {ex.filename}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
