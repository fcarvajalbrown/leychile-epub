# 💻 Referencia del CLI

El comando `leychile-epub` es la forma más sencilla de generar ePubs desde la línea de comandos.

## Uso Básico

```bash
leychile-epub [OPTIONS] [URL]
```

## Argumentos

| Argumento | Descripción |
|-----------|-------------|
| `URL` | URL de LeyChile a convertir (positional, opcional si se usa --batch) |

## Opciones

| Opción | Corta | Descripción | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Directorio de salida | `.` (actual) |
| `--batch` | `-b` | Archivo con lista de URLs | - |
| `--quiet` | `-q` | Modo silencioso | `false` |
| `--verbose` | `-v` | Modo verbose | `false` |
| `--version` | | Mostrar versión | - |
| `--help` | `-h` | Mostrar ayuda | - |

## Ejemplos

### Generar un ePub

```bash
# Forma básica
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302

# Con directorio de salida
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302 -o ./output/

# Modo silencioso (sin barra de progreso)
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302 -q

# Modo verbose (más información de debug)
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302 -v
```

### Procesamiento por Lotes

Crea un archivo `urls.txt`:

```text
https://www.leychile.cl/Navegar?idNorma=242302
https://www.leychile.cl/Navegar?idNorma=172986
https://www.leychile.cl/Navegar?idNorma=1984
```

Ejecuta:

```bash
leychile-epub --batch urls.txt -o ./biblioteca/
```

### Leyes Comunes

```bash
# Código del Trabajo
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302

# Código Civil
leychile-epub https://www.leychile.cl/Navegar?idNorma=172986

# Código Penal
leychile-epub https://www.leychile.cl/Navegar?idNorma=1984

# Ley de Tránsito (Ley 18.290)
leychile-epub https://www.leychile.cl/Navegar?idNorma=29708

# Código de Aguas
leychile-epub https://www.leychile.cl/Navegar?idNorma=5605

# Ley General de Urbanismo y Construcciones
leychile-epub https://www.leychile.cl/Navegar?idNorma=13560
```

## Formato de Salida

El archivo ePub generado incluye:

- 📑 **Portada** con título, número de ley y fecha
- 📚 **Tabla de contenidos** interactiva
- 📖 **Contenido estructurado** (títulos, capítulos, artículos)
- 🔗 **Referencias cruzadas** entre artículos
- 📇 **Índice de materias** con palabras clave
- 📋 **Metadatos** completos (autor, fecha, fuente)

## Códigos de Salida

| Código | Significado |
|--------|-------------|
| 0 | Éxito |
| 1 | Error general |
| 2 | Error de argumentos |

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `LEYCHILE_OUTPUT_DIR` | Directorio de salida por defecto | `.` |
| `LEYCHILE_TIMEOUT` | Timeout de red en segundos | `30` |
| `LEYCHILE_MAX_RETRIES` | Máximo de reintentos | `3` |
| `LEYCHILE_LOG_LEVEL` | Nivel de logging | `INFO` |

## Uso con Python -m

También puedes ejecutar el módulo directamente:

```bash
python -m leychile_epub https://www.leychile.cl/Navegar?idNorma=242302
```

Esto es útil cuando tienes múltiples instalaciones de Python.
