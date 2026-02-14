# Guía de Conversión: Normativa SUPERIR a XML

Guía práctica para convertir instructivos, NCGs y resoluciones de la Superintendencia de Insolvencia y Reemprendimiento (SUPERIR) desde Markdown/texto a XML estructurado bajo el esquema `ley_v1`.

**Versión:** 1.0
**Fecha:** 2026-02-12
**Esquema base:** `schemas/ley_v1.xsd` (namespace `https://leychile.cl/schema/ley/v1`)

---

## 1. Principios generales

1. **Un XML por documento normativo.** Cada resolución/instructivo/NCG es un archivo independiente.
2. **Respetar el texto original.** No reescribir, no inventar datos ausentes. Si un dato no está en el texto fuente, no se agrega.
3. **Esquema compatible.** Se usa `ley_v1.xsd` como base. Los elementos extendidos (no en XSD) se documentan aquí y se proponen para `ley_v1.1`.
4. **Texto limpio.** El markdown provisto por el usuario es la fuente de verdad. Eliminar artefactos de OCR del XML anterior.
5. **Orden estable.** Respetar siempre el orden del texto original: encabezado → vistos → considerando → resuelvo → articulado → anexos → promulgación.

---

## 2. Nomenclatura de archivos

```
INST_{AÑO}_INST_{NUMERO}[_TEMA].xml     → Instructivo nuevo
INST_{AÑO}_MODIF_{TEMA}.xml             → Resolución que modifica instructivo
```

Ejemplos:
- `INST_2023_INST_HONORARIOS.xml` → Instructivo SUPERIR N° 1/2023 (Honorarios)
- `INST_2018_INST_3_HONORARIOS.xml` → Instructivo SUPERIR N° 3/2018 (Honorarios)
- `INST_2024_MODIF_HONORARIOS.xml` → Resolución que modifica instructivo de honorarios

---

## 3. Estructura del documento XML

### 3.1 Elemento raíz `<ley>`

```xml
<ley xmlns="https://leychile.cl/schema/ley/v1"
     version="1.0"
     idioma="es-CL"
     id_norma="INST-SUPERIR-{N}-{AÑO}"
     tipo="Instructivo"
     numero="{N}"
     estado="vigente|derogado|parcial"
     fecha_version="YYYY-MM-DD"
     fecha_promulgacion="YYYY-MM-DD"
     fecha_publicacion="YYYY-MM-DD"
     generado="YYYY-MM-DDTHH:MM:SS"
     fuente="Superintendencia de Insolvencia y Reemprendimiento"
     url_original="{URL_PDF_SUPERIR}">
```

**Reglas de atributos:**
- `id_norma`: Formato `INST-SUPERIR-{numero}-{año}` (ej: `INST-SUPERIR-1-2023`).
- `tipo`: `"Instructivo"` para instructivos, `"Norma de Carácter General"` para NCGs.
- `estado`:
  - `"vigente"` → norma plenamente vigente.
  - `"derogado"` → norma completamente derogada (usar con `<derogacion>` en metadatos).
  - `"parcial"` → norma parcialmente derogada o con vigencia residual/transitoria.
- Fechas: usar la fecha del acto administrativo. Si solo hay una fecha, usar esa para promulgación y publicación.

### 3.2 Estructura de hijos (orden obligatorio)

```xml
<ley ...>
  <metadatos>...</metadatos>       <!-- Siempre primero -->
  <encabezado>...</encabezado>     <!-- Preámbulo completo -->
  <contenido>...</contenido>       <!-- Articulado -->
  <anexos>...</anexos>             <!-- Opcional: anexos -->
  <promulgacion>...</promulgacion> <!-- Cierre, firmas, distribución -->
</ley>
```

---

## 4. Metadatos

### 4.1 Elementos estándar (en XSD v1)

```xml
<metadatos>
  <titulo>INSTRUCTIVO SUPERIR N° {N}/{AÑO} - {Descripción corta}</titulo>
  <identificacion>
    <tipo>Instructivo</tipo>
    <numero>{N}</numero>
  </identificacion>
  <organismos>
    <organismo>Superintendencia de Insolvencia y Reemprendimiento</organismo>
  </organismos>
  <materias>
    <materia>{tema 1}</materia>
    <materia>{tema 2}</materia>
  </materias>
  <nombres_comunes>
    <nombre>{nombre corto 1}</nombre>
  </nombres_comunes>
  <fechas>
    <promulgacion>YYYY-MM-DD</promulgacion>
    <publicacion>YYYY-MM-DD</publicacion>
    <version>YYYY-MM-DD</version>
  </fechas>
  <fuente>Superintendencia de Insolvencia y Reemprendimiento</fuente>
  <numero_fuente>{número de resolución exenta}</numero_fuente>
  <leyes_referenciadas>
    <ley_ref>Ley 20.720</ley_ref>
    <ley_ref>DFL 1/19.653</ley_ref>
  </leyes_referenciadas>
</metadatos>
```

### 4.2 Elementos extendidos (propuestos para XSD v1.1)

Estos elementos NO están en el XSD actual pero los usamos consistentemente:

```xml
<!-- Dentro de <identificacion> -->
<resolucion>Resolución Exenta N° {NNNN}</resolucion>

<!-- Después de <leyes_referenciadas> -->
<normas_modificadas>
  <norma_modificada>{descripción de norma que este documento modifica}</norma_modificada>
</normas_modificadas>

<normas_modificatorias>
  <norma_modificatoria>{descripción de norma que modifica a este documento}</norma_modificatoria>
</normas_modificatorias>

<normas_derogadas>
  <norma_derogada>{descripción de norma que este documento deroga}</norma_derogada>
</normas_derogadas>

<derogacion>
  <derogado_por>{descripción de norma que derogó este documento}</derogado_por>
  <nota>{explicación de vigencia residual/transitoria si aplica}</nota>
</derogacion>
```

### 4.3 Reglas para materias y palabras clave

Extraer materias de:
1. **MAT.** (si existe): usar como materia principal, textual.
2. **Título del instructivo**: extraer temas.
3. **Artículos clave**: artículos sobre vigencia, ámbito, definiciones.

Materias recomendadas (vocabulario controlado SUPERIR):
- `Pago de honorarios`, `Presupuesto SUPERIR`, `Liquidadores concursales`
- `Cuenta final de administración`, `Incautación e inventario`
- `Procedimiento concursal`, `Liquidación simplificada`
- `Acción revocatoria`, `Enajenación de bienes`
- `Fianzas`, `Boletín Concursal`, `Portal de Sujetos Fiscalizados`
- `Artículo {N} Ley 20.720` (cuando el instructivo regula un artículo específico)

### 4.4 Reglas para leyes referenciadas

Extraer de VISTOS y CONSIDERANDO. Normalizar formato:
- `"Ley N.° 20.720"` → `<ley_ref>Ley 20.720</ley_ref>`
- `"D.F.L. N° 1/19.653"` → `<ley_ref>DFL 1/19.653</ley_ref>`
- `"Decreto N° 8 de..."` → `<ley_ref>Decreto 8</ley_ref>`
- `"Resolución N° 7 de 2019 de la CGR"` → `<ley_ref>Resolución CGR 7/2019</ley_ref>`

**No incluir:** oficios, circulares, instructivos internos (estos van como referencias en artículos).

---

## 5. Encabezado

El `<encabezado>` contiene **todo** el preámbulo hasta el inicio del articulado:

```
{Identificación de la resolución}
{MAT.: ...}
{Lugar y fecha}
VISTOS: {texto}
CONSIDERANDO: {texto}
RESUELVO:
{Resuelvo 1° que aprueba/ordena el instructivo}
```

**Regla clave:** El RESUELVO 1° (que aprueba el instructivo) va en el encabezado. Los RESUELVO 2°, 3°, 4° (publicación, derogación, etc.) van en `<promulgacion>`.

### 5.1 Cuándo el resuelvo va en encabezado vs. promulgación

| Contenido del resuelvo | Ubicación |
|---|---|
| `1° APRUÉBASE el siguiente Instructivo...` | `<encabezado>` (cierra el preámbulo) |
| `2° PUBLÍQUESE...` | `<promulgacion>` |
| `3° DISPÓNGASE publicación en sitio web...` | `<promulgacion>` |
| `4° DERÓGUESE...` | `<promulgacion>` |
| `ANÓTESE, NOTIFÍQUESE Y ARCHÍVESE` | `<promulgacion>` |

---

## 6. Contenido (articulado)

### 6.1 Jerarquía de divisiones

Para instructivos SUPERIR, la jerarquía típica es:

```
<contenido>
  <titulo>           → "Título I", "Título II", etc.
    <articulo>       → "Artículo 1°", "Artículo 2°", etc.
```

No hay libros ni capítulos típicamente. Si un instructivo tiene secciones internas sin título/capítulo explícito, usar artículos directamente bajo `<contenido>`.

### 6.2 Elemento `<titulo>`

```xml
<titulo id="{N}" tipo_original="Título" numero="{romano}">
  <titulo_seccion>Título {N}: {nombre}</titulo_seccion>
  <articulo ...>...</articulo>
</titulo>
```

### 6.3 Elemento `<articulo>`

```xml
<articulo id="{N_secuencial}" tipo_original="Artículo" numero="{N}">
  <titulo_seccion>Artículo {N}°[: {subtítulo si existe}]</titulo_seccion>
  <contexto>{jerarquía padre}</contexto>
  <texto>{contenido del artículo}</texto>
  <referencias>
    <ref articulo="{N}" [ley="{norma externa}"] [norma="{instructivo}"]/>
  </referencias>
</articulo>
```

### 6.4 Texto de artículos: párrafos y listas

El contenido va en `<texto>` como texto plano con párrafos separados por líneas en blanco.

**Preservar la estructura original:**
- Párrafos separados por `\n\n` (doble salto de línea).
- Listas numeradas `1)`, `2)`, etc. preservar como texto plano dentro del artículo.
- Listas con letras `a)`, `b)`, `c)` preservar como texto plano.
- No fragmentar artículos largos artificialmente.

**Cuándo usar `<contenido>` estructurado vs. `<texto>`:**
- **Preferir `<texto>`** para instructivos SUPERIR. Es más simple, legible, y suficiente para artículos que son texto corrido con listas inline.
- **Usar `<contenido>` con `<parrafo>/<inciso>`** solo para leyes/códigos con estructura de incisos formales numerados tipo `1°) ...`.

### 6.5 Referencias dentro de artículos

```xml
<referencias>
  <!-- Referencia a artículo de la Ley 20.720 (por defecto) -->
  <ref articulo="40"/>

  <!-- Referencia a artículo de otra ley -->
  <ref articulo="59" ley="Ley 19.880"/>

  <!-- Referencia a artículo de un código -->
  <ref articulo="1699" ley="Código Civil"/>

  <!-- Referencia a artículo del mismo instructivo -->
  <ref articulo="4" norma="presente Instructivo"/>
</referencias>
```

**Reglas de extracción de referencias:**
1. Extraer solo artículos mencionados **explícitamente** en el texto: `"artículo 40"`, `"artículos 163 y siguientes"`.
2. Para `"artículos X y siguientes"`, registrar solo el artículo X.
3. Para `"artículo 8 N° 6 del Código Tributario"`, usar `<ref articulo="8" ley="Código Tributario"/>`.
4. No duplicar: si un artículo se menciona múltiples veces, una sola entrada.
5. No inventar: si no hay referencia explícita a artículos, no agregar `<referencias>`.

**Qué NO se extrae como `<ref>`:**
- Oficios (ej: `"Oficio Superir N° 14006"`) → se preservan en el texto, no como ref.
- Circulares (ej: `"Circular N° 64 del SII"`) → se preservan en el texto.
- Instituciones (ej: `"Servicio de Registro Civil"`) → no son referencias normativas.

---

## 7. Anexos

### 7.1 Estructura

```xml
<anexos>
  <anexo id="{N}" numero="{N}" titulo="{título del anexo}">
    <seccion id="{N}" numero="{N}" titulo="{título de sección}">
      <texto>{contenido de la sección}</texto>
    </seccion>
  </anexo>
</anexos>
```

**Nota:** El XSD actual define `<anexo>` con `titulo`, `materias`, `texto`. Las `<seccion>` dentro de anexos son una extensión que proponemos para v1.1.

### 7.2 Referencias a imágenes

Si el markdown contiene indicaciones de imágenes (`> Aquí iba la imagen: ...`), simplemente omitirlas del XML. No crear elementos especiales para placeholders de imágenes — el texto explicativo alrededor ya provee el contexto necesario.

---

## 8. Promulgación

Contiene los resuelvo finales (publicación, derogación) y el cierre formal:

```xml
<promulgacion>2° PUBLÍQUESE la presente resolución en el Diario Oficial.

3° DISPÓNGASE como medida de publicidad...

4° DERÓGUESE el Instructivo Superir N° 3 de 16 de noviembre de 2018...

ANÓTESE, NOTIFÍQUESE Y ARCHÍVESE,
{iniciales}

DISTRIBUCIÓN:
{destinatarios}</promulgacion>
```

---

## 9. Vigencia y derogación

### 9.1 Estados posibles

| Estado | Significado | Cuándo usar |
|---|---|---|
| `vigente` | Norma plenamente en vigor | Norma activa sin derogación |
| `derogado` | Norma completamente derogada | Otra norma la derogó expresamente |
| `parcial` | Vigencia parcial/residual | Derogada pero con cláusula transitoria que mantiene vigencia para casos anteriores |

### 9.2 Reglas de determinación de vigencia (solo desde el texto)

1. **Cláusula de vigencia explícita**: `"comenzará a regir a contar de..."` → `fecha_version` y `<fechas><version>`.
2. **Cláusula de derogación**: `"Derógase..."` → el documento derogado pasa a `estado="derogado"` desde la fecha de vigencia del derogador.
3. **Vigencia residual**: Si dice `"No obstante, continuarán vigentes para regular solicitudes anteriores..."` → el derogado queda como `estado="derogado"` (no parcial) pero con `<derogacion><nota>` explicando la vigencia residual. Se usa "derogado" porque la norma ya no genera nuevos efectos jurídicos.
4. **Disposiciones transitorias**: Si un artículo transitorio establece aplicabilidad diferenciada por fecha, documentar en `<derogacion><nota>`.

### 9.3 Relaciones entre documentos

Cuando el documento A deroga B:
- En A: `<normas_derogadas><norma_derogada>B</norma_derogada></normas_derogadas>`
- En B: `<derogacion><derogado_por>A</derogado_por><nota>...</nota></derogacion>`

Cuando el documento A modifica B:
- En A: `<normas_modificadas><norma_modificada>B</norma_modificada></normas_modificadas>`
- En B: `<normas_modificatorias><norma_modificatoria>A</norma_modificatoria></normas_modificatorias>`

### 9.4 Cadena de honorarios (ejemplo concreto)

```
Instructivo SIR N° 1/2015 (art. 16)
  ← sustituido por → Instructivo SUPERIR N° 1/2018
    ← sustituido por → Instructivo SUPERIR N° 3/2018
      ← derogado por → Instructivo SUPERIR N° 1/2023 (Res 8725)
        ← texto refundido → Res 9074/2023
          ← modificado por → Res 2549/2024 (tema notarios)
```

---

## 10. Detección de efectos jurídicos

### 10.1 Verbos resolutivos

| Verbo | Efecto | Qué registrar |
|---|---|---|
| `APRUÉBASE` | Crea norma nueva | Es el contenido principal |
| `DERÓGUESE` | Elimina norma anterior | `<normas_derogadas>` en este + `<derogacion>` en el derogado |
| `SUSTITÚYASE` | Reemplaza artículo/norma | `<normas_modificadas>` |
| `REEMPLÁZASE` | Reemplaza texto | `<normas_modificadas>` |
| `ELIMÍNASE` | Borra parte de norma | `<normas_modificadas>` |
| `AGRÉGASE` | Añade texto/artículo | `<normas_modificadas>` |
| `PUBLÍQUESE` | Ordena publicación | Se registra en `<promulgacion>` |
| `DISPÓNGASE` | Ordena acción | Se registra en `<promulgacion>` |

### 10.2 Detección en CONSIDERANDO

Los considerandos a menudo contienen información clave para vigencia:
- `"esta Superintendencia dictó la Resolución Exenta N° ..."` → referencia a norma anterior.
- `"es necesario modificar..."` → indica que este documento modifica otro.
- `"la Ley N° 21.563 establece que..."` → contexto legal del cambio.

---

## 11. Validaciones del XML generado

### 11.1 Checklist obligatorio

- [ ] `id_norma` tiene formato correcto (`INST-SUPERIR-{N}-{AÑO}`).
- [ ] `numero` coincide con el número real del instructivo.
- [ ] `estado` refleja la vigencia real.
- [ ] Artículos tienen `id` secuencial y `numero` correcto.
- [ ] Cada artículo tiene `<contexto>` con su jerarquía padre.
- [ ] `<titulo_seccion>` en cada título y artículo.
- [ ] `total_articulos` y `total_titulos` son correctos en `<contenido>`.
- [ ] El texto no tiene artefactos de OCR.
- [ ] Los resuelvo de publicación/derogación están en `<promulgacion>`, no en `<contenido>`.
- [ ] Las `<leyes_referenciadas>` coinciden con lo mencionado en VISTOS/CONSIDERANDO.

### 11.2 Errores comunes a evitar

1. **No crear "capítulos" espurios.** Si el texto dice "Capítulo VI de la Ley" como referencia, no crear un `<capitulo>` — es una referencia, no una división del instructivo.
2. **No mezclar resuelvo con articulado.** Los resuelvo 2°, 3°, 4° no son artículos del instructivo.
3. **No truncar artículos.** Si un artículo tiene 10 numerales, todos deben estar completos.
4. **No poner el Anexo dentro de `<contenido>`.** Va en `<anexos>` o, si el XSD no lo soporta bien, en `<promulgacion>`.

---

## 12. Extensiones propuestas para XSD v1.1

### 12.1 Nuevos elementos en MetadatosType

```xml
<!-- Número de resolución que aprueba la norma -->
<xs:element name="resolucion" type="xs:string" minOccurs="0"/>

<!-- Normas que este documento modifica -->
<xs:element name="normas_modificadas" minOccurs="0">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="norma_modificada" type="xs:string" maxOccurs="unbounded"/>
    </xs:sequence>
  </xs:complexType>
</xs:element>

<!-- Normas que modifican este documento -->
<xs:element name="normas_modificatorias" minOccurs="0">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="norma_modificatoria" type="xs:string" maxOccurs="unbounded"/>
    </xs:sequence>
  </xs:complexType>
</xs:element>

<!-- Normas que este documento deroga -->
<xs:element name="normas_derogadas" minOccurs="0">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="norma_derogada" type="xs:string" maxOccurs="unbounded"/>
    </xs:sequence>
  </xs:complexType>
</xs:element>

<!-- Info de derogación (para documentos derogados) -->
<xs:element name="derogacion" minOccurs="0">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="derogado_por" type="xs:string"/>
      <xs:element name="nota" type="xs:string" minOccurs="0"/>
    </xs:sequence>
  </xs:complexType>
</xs:element>
```

### 12.2 Atributo `ley` en RefType

```xml
<xs:attribute name="ley" type="xs:string">
  <xs:annotation>
    <xs:documentation>Ley o código externo al que pertenece el artículo referenciado.</xs:documentation>
  </xs:annotation>
</xs:attribute>
```

### 12.3 Secciones en AnexoType

```xml
<xs:element name="seccion" minOccurs="0" maxOccurs="unbounded">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="texto" type="xs:string"/>
    </xs:sequence>
    <xs:attribute name="id" type="xs:string"/>
    <xs:attribute name="numero" type="xs:string"/>
    <xs:attribute name="titulo" type="xs:string"/>
  </xs:complexType>
</xs:element>
```

### 12.4 Estado "derogado" en EstadoType

Agregar a la enumeración:
```xml
<xs:enumeration value="derogado">
  <xs:annotation>
    <xs:documentation>Norma derogada (puede tener vigencia residual documentada en metadatos).</xs:documentation>
  </xs:annotation>
</xs:enumeration>
```

---

## 13. Resumen operativo (para agente/humano)

Al recibir un texto Markdown de una norma SUPERIR:

1. **Identificar tipo**: instructivo nuevo, resolución modificatoria, NCG.
2. **Determinar archivo destino**: buscar si ya existe en `biblioteca_xml/organismos/SUPERIR/`.
3. **Extraer metadatos**: número, fecha, materia, resolución, leyes referenciadas.
4. **Separar bloques**: encabezado (hasta RESUELVO 1°), articulado, anexos, cierre.
5. **Estructurar articulado**: títulos → artículos, con texto limpio y párrafos separados.
6. **Extraer referencias**: artículos mencionados en cada artículo, con ley/norma cuando aplique.
7. **Determinar vigencia**: buscar cláusulas de derogación, vigencia, transitorios.
8. **Actualizar relaciones**: si este documento deroga/modifica otro, actualizar ambos XMLs.
9. **Validar**: checklist de la sección 11.

---

*Documento generado para el proyecto LeyChile ePub Generator*
*Basado en análisis de Instructivos SUPERIR N° 3/2018 y N° 1/2023*
