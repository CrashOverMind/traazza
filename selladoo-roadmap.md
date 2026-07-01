# Roadmap · Traazza

**Qué es Traazza:** librería open-source y self-hosted para integrar Verifactu en el propio software del desarrollador (registro de facturación, huella encadenada, QR oficial, envío a la AEAT). Modelo: núcleo gratis (MIT) + reputación.

**Regla de oro (no cruzar nunca):** Traazza es una *librería/herramienta para desarrolladores*, **no un SIF que emite facturas reales bajo nuestro nombre**. Quien la usa es el "productor del SIF" y asume la declaración responsable y el art. 201 bis LGT, no nosotros. En el momento en que algo emita facturas reales en producción firmado por nosotros, paramos y replanteamos.

**Cómo se usa este roadmap:** cada tarea tiene un ID (p. ej. `F1.4`). Cada vez que avancemos, se indica el punto que se ha tocado. Es un documento vivo: se reordena o amplía según aprendamos.

Estado: `✓ hecho` · `▶ en curso` · `· pendiente`

---

## Fase 0 — Base y marca

- `F0.1` ✓ Nombre y disponibilidad — **Traazza**
- `F0.2` ✓ Posicionamiento decidido — librería, no SIF (lado seguro de la ley)
- `F0.3` ✓ Landing / index v1 — marca Traazza + modo oscuro (sistema + toggle) + responsive
- `F0.4` ✓ Nombre y dominio definidos — **Traazza** (`traazza.com` + `.es`) — `.com` principal (+ `.es` defensivo). ~15-30 €/año
- `F0.5` · Email pro (Zoho free / Cloudflare routing) + reservar handle en GitHub y redes

---

## Fase 1 — Núcleo técnico (la librería) ✓ COMPLETA

- `F1.1` ✓ Documento técnico maestro (`docs/especificacion-huella.md`), fuentes oficiales mapeadas: mapear RD 1007/2023 + Orden HAC/1177/2024 (huella, QR, XML, registro de eventos, validaciones) a las fuentes oficiales. Recopilar los **vectores/ejemplos oficiales de la AEAT**.
- `F1.2` ✓ Esqueleto del repo en Python (pyproject, MIT, tests, estructura) en Python (estructura, `pyproject`, licencia MIT, tests, CI)
- `F1.3` ✓ Modelo de registro de **alta** y **anulación** (`modelos.py`) (estructura + validaciones base)
- `F1.4` ✓ **Huella encadenada** SHA-256 implementada y funcionando (`huella.py`): implementar el hash y el encadenado exactamente como la especificación
- `F1.5` ✅ **Hito clave VALIDADO** — los 3 ejemplos oficiales AEAT (alta, alta encadenada, anulación) coinciden al carácter — validar `F1.3` + `F1.4` contra los ejemplos oficiales de la AEAT hasta que cuadren al detalle. *(El día que esto pasa, nos ganamos el "validado contra la AEAT" sin mentir.)*
- `F1.6` ✅ Generación del **QR oficial** — URL de cotejo (apartados 5-6) validada al carácter contra los ejemplos oficiales (apartados 4 y 8.1-8.4), `URL encoding` UTF-8, y render a imagen (SVG/PNG, nivel M) vía extra opcional `traazza[qr]`
- `F1.7` ✅ Registro de **anulación** — validado contra el caso 3 oficial de la AEAT
- `F1.8` ✅ XML conforme al diseño AEAT (alta + anulación; namespaces confirmados contra XSD → F1.8.1)
- `F1.8.2` ✅ Validación programática del XML contra el `SuministroInformacion.xsd` oficial (`xmlschema`)

---

## Fase 2 — Envío y modalidades ✓ COMPLETA

- `F2.1` ✅ **Cliente de envío a la AEAT** — envoltorio `RegFactuSistemaFacturacion` (`envoltorio.py`) + cliente SOAP (`cliente.py`): endpoints pruebas/producción (cert y sello), mTLS, reintentos con backoff, idempotencia (la AEAT deduplica → reintentar no duplica) y parseo de respuesta (EstadoEnvio, CSV, líneas con estado/código/descr.). Probado con transporte falso (construcción, parseo OK/KO, reintentos, falta de cert). *El envío en vivo necesita tu certificado + red a la AEAT.*
- `F2.2` ✅ **Registro de eventos** (`eventos.py`) — log append-only encadenado con SHA-256 (mismo mecanismo que la facturación), con verificación de integridad y volcado a dicts. Tipos de evento a afinar contra la lista oficial cuando se publique.
- `F2.3` ✅ Modo **NO Veri*factu** — QR no verificable y flag `TipoUsoPosibleSoloVerifactu=N` ya soportados; **firma XAdES** (`firma.py`, extra `traazza[firma]` sobre `signxml`): firma enveloped del registro (la `ds:Signature` cae como último hijo, justo donde la admite el XSD), soporta XAdES-BES y XAdES-EPES con política, y verificación. Probado en round-trip con certificado autofirmado de test (la aceptación por la AEAT necesita certificado cualificado real). *La política de firma oficial de Veri*factu, si la AEAT la exige, se pasa como `politica`.*

---

## Fase 3 — Experiencia de desarrollador (DX) ◀ en curso

- `F3.1` ✅ README copy-paste — instalación, quickstart, tabla de módulos, ejemplos de QR/validación/envío/CLI.
- `F3.2` ✅ **CLI** `traazza` — `qr`, `cadena`, `xml`, `envoltorio`, `validar` (contra los XSD oficiales **incluidos en el paquete**). Trabaja con un JSON de facturas.
- `F3.3` ◐ Publicar en **PyPI** — el wheel se construye bien (incluye el comando `traazza`, los XSD y el entry point). Pendiente el `twine upload` con tu cuenta y fijar versión semver.
- `F3.4` ✅ **Suite de tests pública** — 78 tests en verde.

---

## Fase 4 — Web pública y observabilidad

- `F4.1` · Desplegar la landing en el **VPS de Contabo** (HTTPS automático + hardening básico: SSH solo clave, ufw, fail2ban, auto-updates)
- `F4.2` · Sitio de **documentación** online
- `F4.3` · **Analíticas self-hosted (Umami)** — saber visitas/tráfico real, 0 € y on-brand
- `F4.4` · **Playground/diagnóstico** online: pegas un JSON y ves huella, QR, XML y errores

---

## Fase 5 — Reputación, contenido y SEO

- `F5.1` · **Base pública de errores de la AEAT** (causa probable + solución) — imán SEO
- `F5.2` · Artículos técnicos clave: "Verifactu para desarrolladores", "Verifactu ≠ factura electrónica B2B", "Cómo diseñar el encadenado sin romper tu ERP"
- `F5.3` · Presencia y E-E-A-T/GEO: GitHub activo, issues respondidos, autoría visible
- `F5.4` · **Changelog normativo**: mantener la librería y la web al día con cambios de la AEAT

---

## Fase 6 — Sostenibilidad (sin vender humo)

- `F6.1` · GitHub Sponsors / donaciones
- `F6.2` · *(Opcional, más adelante)* capa "Pro" de herramientas dev — **solo si hay tracción real** y sin cruzar a productor de SIF ni a asesoría de cumplimiento
- `F6.3` · Revisión de la **condición dura**: si en un plazo razonable no hay interés real, mantener el open-source pero no forzar negocio

---

### Dónde estamos ahora
Cerrados: **`F0.1`–`F0.4`**, **Fase 1 completa**, **Fase 2 completa** (`F2.1`, `F2.2`, `F2.3`).
- Huella, XML y QR: validados al carácter / contra el XSD oficial (ver Fase 1).
- Envío: envoltorio `RegFactuSistemaFacturacion` + cliente SOAP (mTLS, reintentos, idempotencia, parseo). El **envoltorio completo valida contra el `SuministroLR.xsd` oficial** (que importa el `SuministroInformacion.xsd` oficial). Ambos XSD oficiales en `tests/vectores/`.
- Alta: `DescripcionOperacion` y `Desglose` ahora son obligatorios al generar el XML (no se puede producir un alta inválida por descuido).
- Eventos: log encadenado SHA-256 con verificación de integridad.
- Firma: XAdES enveloped (BES/EPES) con verificación, probada en round-trip.
- **71 tests en verde.**

**Pendientes / a cotejar con material oficial:**
- Envío en vivo contra el entorno de pruebas de la AEAT con certificado (no ejecutable sin cert/red).
- Política de firma oficial de Veri*factu (identificador + hash) si la AEAT la exige.
- Endpoints SOAP y namespaces: cotejar contra el WSDL oficial antes de producción.
