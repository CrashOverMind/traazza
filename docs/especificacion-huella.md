# Especificación técnica — mapa de la huella encadenada (F1.1)

Mapa de qué dice la norma y dónde está cada cosa, para no programar de memoria.
Fuentes primarias (sede electrónica de la AEAT) y FAQ oficiales.

## Marco legal
- **RD 1007/2023** (RRSIF): requisitos de los sistemas de facturación —
  integridad, conservación, accesibilidad, legibilidad, trazabilidad e
  inalterabilidad.
- **Orden HAC/1177/2024**: especificaciones técnicas, funcionales y de contenido
  (esquemas XML, QR, etc.).
- Calendario vigente (RD-ley 15/2025): obligación 1-ene-2027 (sociedades) y
  1-jul-2027 (resto). Fabricantes de software, obligados desde 29-jul-2025.

## La huella o «hash» (lo que implementamos en F1.4)
Confirmado en la FAQ oficial de la AEAT ("Huella o «hash»"):
- Algoritmo: **SHA-256**.
- Se calcula **solo sobre unos pocos campos** del registro, distintos según el
  tipo (alta / anulación / evento).
- La huella resultante **se almacena en el propio registro** y, además, **se
  incluye en el registro siguiente** → así se encadenan (trazabilidad).
- En sistemas NO Veri*factu, al generar un registro hay que **comprobar el
  encadenamiento del anterior**; en Veri*factu no es obligatorio comprobarlo
  (lo hace la AEAT al recibir los registros).

### Campos de la huella — registro de ALTA
Orden usado en `huella.CAMPOS_ALTA` (a validar byte a byte en F1.5):
`IDEmisorFactura, NumSerieFactura, FechaExpedicionFactura, TipoFactura,
CuotaTotal, ImporteTotal, Huella (anterior), FechaHoraHusoGenRegistro`

### Campos de la huella — registro de ANULACIÓN
`IDEmisorFacturaAnulada, NumSerieFacturaAnulada, FechaExpedicionFacturaAnulada,
Huella (anterior), FechaHoraHusoGenRegistro`

### Formato de concatenación
`Campo=valor&Campo=valor&...` → SHA-256 → hexadecimal en **mayúsculas**.
`TipoHuella = "01"` significa SHA-256.

## Estado de validación (F1.5 — VALIDADO ✅)
La implementación reproduce **al carácter** los tres ejemplos oficiales del
documento AEAT v0.1.2 (apartado 6): alta (caso 1), alta encadenada (caso 2) y
anulación (caso 3). Confirmado además:
- salida en **hexadecimal mayúsculas**, 64 caracteres;
- entrada codificada en **UTF-8**;
- importes: **los ceros a la derecha son irrelevantes** (`123.1` == `123.10`),
  por eso normalizamos a 2 decimales;
- primer registro: `Huella=` vacío y `PrimerRegistro="S"`.

## Documentos oficiales de referencia (sede AEAT, sección "Información técnica")
- Diseños de registro · WSDL · Esquemas (XSD) · Documento de validaciones y errores
- Algoritmo de la huella (hash) · Especificaciones de firma electrónica
- Características del QR · Ejemplos de declaraciones responsables
- Portal de Pruebas Externas (sandbox, requiere certificado)

## Siguiente
- `F1.5` — cerrar la validación con el ejemplo oficial.
- `F1.6` — QR (ISO/IEC 18004, lado 20–40 mm, corrección de errores nivel M; el
  QR lleva una URL de cotejo de la AEAT, **no** la huella).
- `F1.8` — XML conforme al esquema de la Orden HAC/1177/2024.

## XML del registro (F1.8 — funcional)
Estructura y orden de elementos tomados del Excel oficial de diseños de registro
("DsRegistroVeriFactu.xlsx"): hojas de alta y de anulación + bloque
«SistemaInformatico». `IDVersion = "1.0"` (L15). `TipoHuella = "01"` (L12).
Implementado en `traazza/xml.py`; produce `<RegistroAlta>` y `<RegistroAnulacion>`
con la huella validada dentro.

**F1.8.1 — VALIDADO ✅**: el `targetNamespace` del XSD oficial
(`SuministroInformacion.xsd`) coincide exactamente con el namespace de Traazza.
La revisión del XSD además corrigió un fallo: el bloque `RegistroAnterior` debe
llevar la identidad (emisor + nº + fecha + huella) de la factura **anterior**,
no de la actual (tipo `EncadenamientoFacturaAnteriorType`). Corregido y con test.

Tipos confirmados contra el XSD: `fecha` = `DD-MM-AAAA`; importes
`ImporteSgn12.2Type` (12+2, punto decimal); `Huella` máx. 64; `IdSistemaInformatico`
máx. 2; `DetalleDesglose` máx. 12; `CalificacionOperacion`/`OperacionExenta` en
choice; `Encadenamiento` = choice `PrimerRegistro`("S") | `RegistroAnterior`.

**Siguiente (F1.8.2)**: validación programática del XML contra el XSD (meter
`SuministroInformacion.xsd` en `tests/vectores/` y validar con `xmlschema`).
