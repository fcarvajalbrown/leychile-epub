# 🐍 API de Python

Esta guía documenta la API programática de LeyChile ePub Generator.

## Instalación

```bash
pip install leychile-epub
```

## Uso Básico

```python
from leychile_epub import BCNLawScraper, LawEpubGenerator

# Crear scraper y obtener datos de la ley
scraper = BCNLawScraper()
law_data = scraper.scrape_law("https://www.leychile.cl/Navegar?idNorma=242302")

# Generar ePub
generator = LawEpubGenerator()
epub_path = generator.generate(law_data, output_dir="./output")

print(f"ePub generado: {epub_path}")
```

## Clases Principales

### BCNLawScraper

Clase para extraer datos de leyes desde la Biblioteca del Congreso Nacional.

```python
from leychile_epub import BCNLawScraper

scraper = BCNLawScraper()
```

#### Métodos

##### `scrape_law(url: str) -> dict`

Extrae los datos de una ley desde su URL.

**Parámetros:**
- `url` (str): URL de LeyChile (ej: `https://www.leychile.cl/Navegar?idNorma=242302`)

**Retorna:**
- `dict`: Diccionario con los datos de la ley

**Ejemplo:**
```python
law_data = scraper.scrape_law("https://www.leychile.cl/Navegar?idNorma=242302")
print(law_data["metadata"]["title"])  # "APRUEBA LEY ORGANICA CONSTITUCIONAL..."
```

#### Estructura de Datos

```python
{
    "id_norma": "242302",
    "url": "https://www.leychile.cl/Navegar?idNorma=242302",
    "id_version": "2024-01-15",
    "metadata": {
        "title": "APRUEBA LEY ORGANICA CONSTITUCIONAL...",
        "type": "Decreto",
        "number": "100",
        "organism": "Ministerio Secretaría General de la Presidencia",
        "source": "Diario Oficial",
        "subjects": ["Constitución Política", "Derechos fundamentales"],
        "derogation_dates": ["2023-12-20", "2022-03-11"],
    },
    "content": [
        {"type": "encabezado", "text": "DECRETO 100..."},
        {"type": "titulo", "text": "TITULO I DE LOS DERECHOS..."},
        {"type": "articulo", "title": "Artículo 1", "text": "Las personas nacen..."},
        {"type": "parrafo", "text": "Párrafo 1°"},
        # ...
    ]
}
```

### LawEpubGenerator

Clase para generar archivos ePub a partir de datos de leyes.

```python
from leychile_epub import LawEpubGenerator

generator = LawEpubGenerator()
```

#### Constructor

```python
LawEpubGenerator(config: Config = None)
```

**Parámetros:**
- `config` (Config, opcional): Configuración personalizada

#### Métodos

##### `generate(law_data, output_dir=None, filename=None, progress_callback=None) -> str`

Genera un archivo ePub.

**Parámetros:**
- `law_data` (dict): Datos de la ley (resultado de `scrape_law`)
- `output_dir` (str, opcional): Directorio de salida
- `filename` (str, opcional): Nombre del archivo
- `progress_callback` (callable, opcional): Función para reportar progreso

**Retorna:**
- `str`: Ruta al archivo ePub generado

**Ejemplo:**
```python
def on_progress(progress: float, message: str):
    print(f"{progress*100:.0f}%: {message}")

epub_path = generator.generate(
    law_data,
    output_dir="./output",
    filename="mi_ley.epub",
    progress_callback=on_progress
)
```

### Config

Clase de configuración centralizada.

```python
from leychile_epub import Config

# Crear configuración por defecto
config = Config.create_default()

# Modificar configuración
config.epub.output_dir = "./mis_epubs"
config.epub.creator = "Mi Aplicación"
config.scraper.timeout = 60
config.scraper.max_retries = 5

# Usar con el generador
generator = LawEpubGenerator(config)
```

#### Atributos de Configuración

```python
# Configuración del scraper
config.scraper.timeout = 30        # Timeout en segundos
config.scraper.max_retries = 3     # Máximo de reintentos
config.scraper.retry_delay = 1.0   # Delay entre reintentos
config.scraper.rate_limit = 0.5    # Segundos entre requests

# Configuración del ePub
config.epub.output_dir = "."       # Directorio de salida
config.epub.language = "es"        # Idioma
config.epub.creator = "LeyChile ePub Generator"
config.epub.publisher = "BCN Chile"
```

## Excepciones

```python
from leychile_epub import (
    LeyChileError,      # Base para todas las excepciones
    ScraperError,       # Errores del scraper
    NetworkError,       # Errores de red
    ValidationError,    # Datos inválidos
    GeneratorError,     # Errores al generar ePub
)

try:
    law_data = scraper.scrape_law(url)
except NetworkError as e:
    print(f"Error de red: {e}")
except ScraperError as e:
    print(f"Error al extraer datos: {e}")
```

## Ejemplos Avanzados

### Procesamiento por Lotes

```python
from leychile_epub import BCNLawScraper, LawEpubGenerator
from pathlib import Path

def procesar_lotes(urls: list[str], output_dir: str = "./output"):
    scraper = BCNLawScraper()
    generator = LawEpubGenerator()
    Path(output_dir).mkdir(exist_ok=True)
    
    resultados = []
    for url in urls:
        try:
            law_data = scraper.scrape_law(url)
            epub_path = generator.generate(law_data, output_dir=output_dir)
            resultados.append({"url": url, "epub": epub_path, "status": "ok"})
        except Exception as e:
            resultados.append({"url": url, "error": str(e), "status": "error"})
    
    return resultados

# Uso
urls = [
    "https://www.leychile.cl/Navegar?idNorma=242302",
    "https://www.leychile.cl/Navegar?idNorma=172986",
]
resultados = procesar_lotes(urls)
```

### Con Barra de Progreso (tqdm)

```python
from leychile_epub import BCNLawScraper, LawEpubGenerator
from tqdm import tqdm

scraper = BCNLawScraper()
generator = LawEpubGenerator()

law_data = scraper.scrape_law(url)

with tqdm(total=100, desc="Generando ePub") as pbar:
    def update_progress(progress, message):
        pbar.update(int(progress * 100) - pbar.n)
        pbar.set_description(message)
    
    epub_path = generator.generate(law_data, progress_callback=update_progress)
```

### Configuración desde Archivo

```python
from leychile_epub import Config

# Guardar configuración
config = Config.create_default()
config.save("mi_config.json")

# Cargar configuración
config = Config.load("mi_config.json")
```

### Integración con FastAPI

```python
from fastapi import FastAPI, HTTPException
from leychile_epub import BCNLawScraper, LawEpubGenerator
from fastapi.responses import FileResponse

app = FastAPI()
scraper = BCNLawScraper()
generator = LawEpubGenerator()

@app.get("/generate")
async def generate_epub(url: str):
    try:
        law_data = scraper.scrape_law(url)
        epub_path = generator.generate(law_data, output_dir="/tmp")
        return FileResponse(epub_path, media_type="application/epub+zip")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```
