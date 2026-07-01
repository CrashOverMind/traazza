# tests/vectores/

Vectores y esquemas oficiales de la AEAT para los tests.

## XSD para F1.8.2 (validación programática) — ✅ en su sitio

```
tests/vectores/
├── SuministroInformacion.xsd      ← oficial: define RegistroAlta / RegistroAnulacion
├── xmldsig-core-schema.xsd        ← stub local de xmldsig (ds:Signature, opcional)
└── _smoke/registro_smoke.xsd      ← esquema de humo (NO oficial), prueba el motor
```

El `SuministroInformacion.xsd` importa el esquema de firma `xmldsig` desde
w3.org. Como `ds:Signature` es opcional y la librería no lo emite, ese import
se redirige a `xmldsig-core-schema.xsd` (un stub local) vía el parámetro
`locations` de `validacion.cargar_esquema`, de modo que el esquema compila sin
acceso a la red. La firma XAdES real, si llega, es cosa de Fase 2.

`test_validacion.py` valida el XML generado (alta y anulación) contra el
esquema oficial y comprueba además que rechaza datos fuera de norma.

## Fase 2 — ✅ envoltorio validado contra el XSD oficial

- `SuministroLR.xsd` (envoltorio `RegFactuSistemaFacturacion` + `Cabecera`):
  **oficial** (namespace `tike/cont/ws`), importa el `SuministroInformacion.xsd`
  oficial. El envoltorio completo de Traazza valida contra él.

> ⚠️ Ojo: existe un `SuministroLR.xsd` homónimo del **SII** (namespace
> `ssii/fact/ws`) con libros de IVA (FacturasEmitidas/Recibidas, etc.). Ese NO
> es el de Veri*factu. El correcto es el de `tike/cont/ws` con
> `RegFactuSistemaFacturacion`.
