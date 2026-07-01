# Traazza

**Verifactu en tu código. No en el servidor de otro.**

Librería open-source (MIT) para generar los registros de facturación de **Veri\*factu**
—huella encadenada SHA-256, código QR, XML y firma— dentro de tu propio
software, sin enviar tus facturas a un tercero ni pagar una cuota por NIF.

> **Regla de oro.** Traazza es una *librería/herramienta para desarrolladores*,
> **no un SIF** que emita facturas reales en tu nombre. Quien la integra es el
> «productor del SIF» y asume la declaración responsable y el art. 201 bis LGT.

> **Estado: ALPHA.** El núcleo está validado contra material oficial de la AEAT
> (huella al carácter, XML contra los XSD oficiales), pero el envío en vivo y la
> firma con certificado cualificado son responsabilidad del integrador. Aún no
> apta para producción sin ese último tramo.

---

## Instalación

```bash
pip install traazza                 # núcleo, sin dependencias
pip install "traazza[qr]"           # + generar imágenes QR (segno)
pip install "traazza[xsd]"          # + validar contra los XSD (xmlschema)
pip install "traazza[envio]"        # + enviar a la AEAT por SOAP (requests)
pip install "traazza[firma]"        # + firma XAdES (signxml)
```

El núcleo (huella, XML, construcción del QR) **no tiene dependencias**. Cada
capacidad extra vive detrás de un módulo opcional.

---

## En 30 segundos

```python
from traazza.modelos import Emisor, Cadena, SistemaInformatico, LineaDesglose
from traazza import qr, xml, envoltorio

emisor = Emisor("89890001K", "Empresa Ejemplo SL")
sistema = SistemaInformatico(
    nombre_razon="Mi Software SL", nif="B00000000", nombre_sif="MiFacturador",
    id_sif="01", version="1.0.0", numero_instalacion="INST-001")

cadena = Cadena(emisor)
factura = cadena.alta(
    num_serie="2024/A-1", fecha_expedicion="01-01-2024", tipo_factura="F1",
    cuota_total="21.00", importe_total="121.00",
    fecha_hora_huso="2024-01-01T10:00:00+01:00",
    descripcion_operacion="Venta de prueba",
    desglose=[LineaDesglose("100.00", "21.00", "21.00")])

print(factura.huella)                         # huella SHA-256 encadenada
print(qr.url_desde_registro(factura))         # URL del QR tributario
print(xml.registro_alta_xml(factura, sistema))# XML del registro de alta
```

Cada registro que crea la `Cadena` incorpora automáticamente la huella del
anterior: así se garantiza la trazabilidad y la inalterabilidad.

> **Encadenar entre ejecuciones (producción).** Una `Cadena` nueva empieza
> vacía y marca su primer registro como «primero». En un programa real que
> arranca y para, debes **guardar la huella del último registro** (en tu base
> de datos) y arrancar la siguiente cadena desde ahí, o la AEAT devolverá el
> aviso 2007 («no debe informarse como primer registro»). El campo
> `fecha_hora_huso` es opcional: si no lo pasas, se rellena con la hora actual
> en el formato exacto que exige la AEAT (sin microsegundos, con huso).

---

## Qué sabe hacer

| Módulo         | Para qué |
|----------------|----------|
| `huella`       | Huella SHA-256 encadenada, **validada al carácter** contra los 3 ejemplos oficiales. |
| `modelos`      | Registros de **alta** y **anulación** y el encadenado (`Cadena`). |
| `qr`           | URL del **QR tributario** (validada contra los ejemplos oficiales) y render SVG/PNG nivel M. |
| `xml`          | XML de alta/anulación conforme al diseño oficial. |
| `validacion`   | Validación **contra los XSD oficiales** de la AEAT (incluidos en el paquete). |
| `envoltorio`   | `RegFactuSistemaFacturacion` (Cabecera + registros) para el envío. |
| `cliente`      | Envío **SOAP con mTLS** a la AEAT (mTLS, reintentos, idempotencia, parseo). |
| `eventos`      | Registro de eventos del sistema, encadenado SHA-256. |
| `firma`        | Firma **XAdES** (modo NO Veri\*factu). |

---

## Código QR

```python
from traazza import qr

url = qr.url_factura(nif="89890001K", numserie="2024/A-1",
                     fecha="01-01-2024", importe="121.00")
qr.guardar_qr(url, "factura.png")             # nivel de corrección M (art. 21)

# Textos oficiales para maquetar la factura:
qr.TEXTO_QR_TRIBUTARIO          # "QR tributario:"
qr.FRASE_VERIFACTU_LARGA        # "Factura verificable en la sede electrónica de la AEAT"
```

## Validar contra el XSD oficial

```python
from traazza import validacion

esquema = validacion.esquema_registros()      # SuministroInformacion.xsd (incluido)
validacion.validar_alta(factura, sistema, esquema)     # True o lanza con el detalle
```

## Enviar a la AEAT (modo Veri\*factu)

```python
from traazza.cliente import Cliente, Entorno

cli = Cliente(entorno=Entorno.PRUEBAS, cert=("cert.pem", "clave.pem"))
resp = cli.enviar(emisor, [factura], sistema)
print(resp.estado_envio, resp.csv)            # "Correcto" + CSV = aceptado
```

En modo Veri\*factu la remisión con certificado cualificado cuenta como firma
básica: **no necesitas firmar los registros**. La firma XAdES (`traazza.firma`)
solo es obligatoria en modo NO Veri\*factu.

---

## Línea de comandos

```bash
# URL del QR (y opcionalmente la imagen)
traazza qr --nif 89890001K --numserie 2024/A-1 --fecha 01-01-2024 --importe 121.00 --salida qr.png

# Huella encadenada de un lote de facturas (JSON)
traazza cadena facturas.json

# XML de los registros / envoltorio completo
traazza xml facturas.json
traazza envoltorio facturas.json

# Validar un XML contra el XSD oficial incluido
traazza validar registro.xml
traazza validar envoltorio.xml --envoltorio
```

Formato del JSON en `traazza --help` y en la cabecera de `traazza/cli.py`.

---

## Filosofía

- **Tus datos son tuyos.** Traazza corre en tu máquina; tus facturas no pasan
  por ningún servidor intermedio.
- **Núcleo sin dependencias.** Lo que exige librerías externas es opcional.
- **Validado, no prometido.** Lo que decimos que cumple, lo cumple contra el
  material oficial de la AEAT, y hay tests que lo demuestran.

## Licencia

MIT.
