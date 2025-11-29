# 📚 LeyChile ePub Generator

[![CI](https://github.com/laguileracl/leychile-epub/actions/workflows/ci.yml/badge.svg)](https://github.com/laguileracl/leychile-epub/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/leychile-epub.svg)](https://badge.fury.io/py/leychile-epub)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](CONTRIBUTING.md)

> 🇨🇱 Generador de libros electrónicos (ePub) a partir de la legislación chilena oficial de la Biblioteca del Congreso Nacional.

**Convierte cualquier ley, decreto o norma chilena en un libro electrónico profesional** listo para leer en tu Kindle, Kobo, iPad o cualquier e-reader.

[English](#english) | [Español](#español)

---

## 📖 Tabla de Contenidos

- [✨ Características](#-características)
- [🚀 Inicio Rápido](#-inicio-rápido)
- [📦 Instalación](#-instalación)
- [💻 Uso](#-uso)
  - [Línea de Comandos (CLI)](#línea-de-comandos-cli)
  - [Interfaz Web](#interfaz-web)
  - [Como Biblioteca Python](#como-biblioteca-python)
- [📋 Ejemplos](#-ejemplos)
- [🏗️ Arquitectura](#️-arquitectura)
- [🤝 Contribuir](#-contribuir)
- [📄 Licencia](#-licencia)
- [👤 Autor](#-autor)

---

## ✨ Características

### 🎯 Funcionalidades Principales

- **Scraping Inteligente**: Extrae datos directamente de la API XML oficial de la BCN
- **ePub Profesional**: Genera libros electrónicos con formato premium
- **Múltiples Interfaces**: CLI, Web (Streamlit) y API Python
- **Procesamiento por Lotes**: Convierte múltiples normas de una vez

### 📱 Características del ePub Generado

| Característica | Descripción |
|----------------|-------------|
| 📑 **Portada Personalizada** | Incluye título, tipo de norma y fecha de publicación |
| 📚 **Tabla de Contenidos** | Navegación interactiva por títulos, capítulos y artículos |
| 🎨 **Estilos Profesionales** | CSS optimizado para lectura cómoda |
| 🔗 **Referencias Cruzadas** | Links internos entre artículos relacionados |
| 📇 **Índice de Palabras Clave** | Búsqueda rápida de términos importantes |
| 📋 **Metadatos Completos** | Autor, fecha, identificadores estándar |
| ✅ **Compatibilidad Universal** | Funciona en Kindle, Kobo, Apple Books, etc. |

### 📜 Tipos de Normas Soportadas

- ✅ Leyes
- ✅ Decretos Ley (DL)
- ✅ Decretos con Fuerza de Ley (DFL)
- ✅ Decretos Supremos
- ✅ Códigos (Civil, Penal, del Trabajo, etc.)
- ✅ Constitución Política
- ✅ Reglamentos
- ✅ Y más...

---

## 🚀 Inicio Rápido

```bash
# Clonar el repositorio
git clone https://github.com/laguileracl/leychile-epub.git
cd leychile-epub

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instalar el paquete
pip install -e .

# Generar tu primer ePub
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302
```

¡Listo! Encontrarás el archivo ePub generado en tu directorio.

---

## 📦 Instalación

### Requisitos

- Python 3.10 o superior
- pip (gestor de paquetes de Python)

### Instalación Paso a Paso

1. **Clona el repositorio**
   ```bash
   git clone https://github.com/laguileracl/leychile-epub.git
   cd leychile-epub
   ```

2. **Crea un entorno virtual** (recomendado)
   ```bash
   python -m venv .venv
   
   # En macOS/Linux:
   source .venv/bin/activate
   
   # En Windows:
   .venv\Scripts\activate
   ```

3. **Instala el paquete**
   ```bash
   # Instalación básica
   pip install -e .
   
   # Con dependencias de desarrollo
   pip install -e ".[dev]"
   
   # Con interfaz web (Streamlit)
   pip install -e ".[web]"
   ```

### Dependencias

| Paquete | Versión | Descripción |
|---------|---------|-------------|
| `requests` | ≥2.28 | Cliente HTTP para la API de BCN |
| `beautifulsoup4` | ≥4.11 | Parser HTML/XML |
| `lxml` | ≥4.9 | Parser XML de alto rendimiento |
| `ebooklib` | ≥0.18 | Generación de archivos ePub |
| `streamlit` | ≥1.28 | Interfaz web (opcional) |

---

## 💻 Uso

### Línea de Comandos (CLI)

La forma más directa de usar el generador:

```bash
# Generar ePub de una ley específica
leychile-epub https://www.leychile.cl/Navegar?idNorma=61438

# También funciona con python -m
python -m leychile_epub https://www.leychile.cl/Navegar?idNorma=61438

# Especificar directorio de salida
leychile-epub https://www.leychile.cl/Navegar?idNorma=61438 -o ./mis_leyes/

# Modo silencioso (sin output en consola)
leychile-epub https://www.leychile.cl/Navegar?idNorma=61438 -q

# Modo verbose (más información)
leychile-epub https://www.leychile.cl/Navegar?idNorma=61438 -v

# Procesar múltiples URLs desde un archivo
leychile-epub --batch urls.txt -o ./output/

# Ver versión
leychile-epub --version
```

#### Opciones del CLI

| Opción | Corta | Descripción |
|--------|-------|-------------|
| `--output` | `-o` | Directorio de salida para los ePub |
| `--batch` | `-b` | Archivo con lista de URLs (una por línea) |
| `--quiet` | `-q` | Modo silencioso |
| `--verbose` | `-v` | Modo verbose |
| `--version` | | Mostrar versión |
| `--help` | `-h` | Mostrar ayuda |

### Interfaz Web

Para una experiencia más visual:

```bash
python main.py --web
# o directamente:
streamlit run app.py
```

Esto abrirá una interfaz web en `http://localhost:8501` con:
- Campo para ingresar URLs
- Vista previa del contenido
- Opciones de personalización
- Descarga directa del ePub

> **Nota**: La interfaz web requiere Streamlit, que puede no ser compatible con Python 3.14+

### Como Biblioteca Python

Integra el generador en tus propios proyectos:

```python
from leychile_epub import BCNLawScraper, LawEpubGenerator

# Inicializar scraper
scraper = BCNLawScraper()

# Obtener datos de una ley
url = "https://www.leychile.cl/Navegar?idNorma=61438"
law_data = scraper.scrape_law(url)

if law_data:
    # Generar ePub
    generator = LawEpubGenerator()
    epub_path = generator.generate(law_data, output_dir="./output")
    print(f"ePub generado: {epub_path}")
```

#### API del Scraper

```python
from leychile_epub import BCNLawScraper

scraper = BCNLawScraper()

# Obtener datos de una ley
law_data = scraper.scrape_law(url)

# Estructura de law_data:
{
    "id_norma": "61438",
    "url": "https://...",
    "id_version": "2024-01-15",
    "metadata": {
        "title": "Ley 18700",
        "type": "Ley",
        "number": "18700",
        "organism": "Ministerio del Interior",
        "source": "Diario Oficial",
        "subjects": ["Elecciones", "Votación"],
        "derogation_dates": [...],
    },
    "content": [
        {"type": "titulo", "text": "TITULO I..."},
        {"type": "articulo", "title": "Artículo 1", "text": "..."},
        ...
    ]
}
```

#### API del Generador

```python
from leychile_epub import LawEpubGenerator, Config

# Configuración personalizada
config = Config.create_default()
config.epub.output_dir = "./mis_epubs"
config.epub.creator = "Mi Aplicación"

# Generar ePub
generator = LawEpubGenerator(config)
epub_path = generator.generate(
    law_data,
    output_dir="./output",      # Directorio de salida
    filename="mi_ley.epub",     # Nombre del archivo
    progress_callback=lambda p, msg: print(f"{p*100:.0f}%: {msg}")
)
```

---

## 📋 Ejemplos

### Leyes Populares

```bash
# Código del Trabajo
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302

# Código Civil
leychile-epub https://www.leychile.cl/Navegar?idNorma=172986

# Código Penal
leychile-epub https://www.leychile.cl/Navegar?idNorma=1984

# Constitución Política
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302

# Ley de Tránsito
leychile-epub https://www.leychile.cl/Navegar?idNorma=29708

# Código de Aguas
leychile-epub https://www.leychile.cl/Navegar?idNorma=5605
```

### Procesamiento por Lotes

Crea un archivo `leyes.txt`:
```
https://www.leychile.cl/Navegar?idNorma=242302
https://www.leychile.cl/Navegar?idNorma=172986
https://www.leychile.cl/Navegar?idNorma=1984
```

Ejecuta:
```bash
leychile-epub --batch leyes.txt -o ./biblioteca_legal/
```

### Uso Programático Avanzado

```python
from leychile_epub import BCNLawScraper, LawEpubGenerator
from pathlib import Path

def crear_biblioteca_legal(urls: list[str], output_dir: str = "./biblioteca"):
    """Crea una biblioteca de ePubs a partir de múltiples URLs."""
    scraper = BCNLawScraper()
    generator = LawEpubGenerator()
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    resultados = []
    for url in urls:
        try:
            law_data = scraper.scrape_law(url)
            if law_data:
                epub_path = generator.generate(law_data, output_dir=str(output_path))
                resultados.append({"url": url, "epub": epub_path, "status": "success"})
            else:
                resultados.append({"url": url, "status": "no_data"})
        except Exception as e:
            resultados.append({"url": url, "status": "error", "error": str(e)})
    
    return resultados

# Uso
urls = [
    "https://www.leychile.cl/Navegar?idNorma=242302",
    "https://www.leychile.cl/Navegar?idNorma=172986",
]
resultados = crear_biblioteca_legal(urls)
```

---

## 🏗️ Arquitectura

```
leychile-epub/
│
├── � src/leychile_epub/      # Paquete principal
│   ├── __init__.py            # Exports públicos
│   ├── __main__.py            # Entry point para python -m
│   ├── cli.py                 # Interfaz de línea de comandos
│   ├── config.py              # Configuración centralizada
│   ├── exceptions.py          # Excepciones personalizadas
│   ├── generator.py           # Generador de ePub
│   ├── scraper.py             # Scraper para la API de BCN
│   ├── styles.py              # Estilos CSS premium
│   └── py.typed               # Soporte para type checking
│
├── 📁 tests/                   # Tests unitarios
│   ├── test_config.py         # Tests de configuración
│   ├── test_scraper.py        # Tests del scraper
│   └── test_generator.py      # Tests del generador
│
├── 📁 docs/                    # Documentación adicional
│
├── 📄 pyproject.toml          # Configuración del proyecto
├── 📄 README.md               # Este archivo
├── 📄 CONTRIBUTING.md         # Guía de contribución
├── 📄 CODE_OF_CONDUCT.md      # Código de conducta
├── 📄 CHANGELOG.md            # Historial de cambios
├── 📄 LICENSE                 # Licencia MIT
└── 📄 SECURITY.md             # Política de seguridad
```

### Flujo de Datos

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────┐
│  URL BCN    │────▶│  BCNScraper  │────▶│ EpubGenerator  │────▶│  .epub   │
│  (input)    │     │  (extract)   │     │  (transform)   │     │ (output) │
└─────────────┘     └──────────────┘     └────────────────┘     └──────────┘
                           │                      │
                           ▼                      ▼
                    ┌──────────────┐     ┌────────────────┐
                    │  XML API     │     │  CSS Styles    │
                    │  BCN Chile   │     │  Templates     │
                    └──────────────┘     └────────────────┘
```

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Este es un proyecto open source creado para la comunidad.

### Formas de Contribuir

- 🐛 **Reportar bugs**: Abre un [Issue](https://github.com/laguileracl/leychile-epub/issues)
- 💡 **Sugerir mejoras**: Comparte tus ideas
- 📝 **Mejorar documentación**: Ayuda a otros usuarios
- 🔧 **Enviar código**: Haz un Pull Request

Lee la [Guía de Contribución](CONTRIBUTING.md) para más detalles.

### Desarrollo

```bash
# Clonar tu fork
git clone https://github.com/TU_USUARIO/leychile-epub.git
cd leychile-epub

# Crear branch para tu feature
git checkout -b feature/mi-mejora

# Hacer cambios y commit
git add .
git commit -m "feat: agregar mi mejora"

# Push y crear PR
git push origin feature/mi-mejora
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

---

## 👤 Autor

**Luis Aguilera Arteaga**

- 📧 Email: luis@aguilera.cl
- 🐙 GitHub: [@laguileracl](https://github.com/laguileracl)
- 🇨🇱 Chile

### Créditos

- [Biblioteca del Congreso Nacional de Chile](https://www.bcn.cl/) por proveer acceso público a la legislación
- Todos los [contribuidores](https://github.com/laguileracl/leychile-epub/contributors) del proyecto

---

## 🌟 Star History

Si este proyecto te es útil, ¡considera darle una ⭐ en GitHub!

---

<h2 id="english">🇺🇸 English</h2>

# LeyChile ePub Generator

> Convert Chilean legislation from the National Congress Library into professional eBooks (ePub format).

This tool scrapes Chilean laws, decrees, and regulations from the official BCN (Biblioteca del Congreso Nacional) API and generates high-quality ePub files compatible with all major e-readers.

### Quick Start

```bash
git clone https://github.com/laguileracl/leychile-epub.git
cd leychile-epub
python -m venv .venv && source .venv/bin/activate
pip install -e .
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302
```

### Features

- 📚 Scrapes from official BCN XML API
- 📱 Generates professional ePub files
- 🎨 Premium styling and formatting
- 📑 Interactive table of contents
- 🔗 Cross-references between articles
- 📇 Keyword index
- ✅ Compatible with Kindle, Kobo, Apple Books, etc.

For full documentation, see the Spanish section above.

---

<p align="center">
  Made with ❤️ in Chile 🇨🇱
</p>
