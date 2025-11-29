# Changelog

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

## [1.3.0] - 2024-11-29

### Agregado
- **Documentación completa** en `docs/`
  - Guía de inicio rápido (`quickstart.md`)
  - Guía de instalación (`installation.md`)
  - Referencia del CLI (`cli.md`)
  - Documentación de API Python (`api.md`)
  - Ejemplos de uso (`examples.md`)
  - Guía de desarrollo (`development.md`)
- **Tests de integración** (`test_integration.py`)
  - Tests end-to-end con requests reales a BCN
  - Tests de múltiples leyes (Constitución, Código Civil, etc.)
- **MANIFEST.in** para distribución correcta del paquete
- Más ejemplos de código en la documentación

### Mejorado
- Documentación más detallada para contribuidores
- Ejemplos de integración con Flask, FastAPI, etc.

## [1.2.0] - 2024-11-29

### Agregado
- **GitHub Actions CI/CD** - Automatización completa
  - CI pipeline: tests en Python 3.10-3.13, linting, type checking
  - Release pipeline: publicación automática a PyPI con trusted publishing
  - Codecov integration para cobertura de código
- **Makefile** con comandos de desarrollo comunes
  - `make test`, `make lint`, `make format`, `make check`, etc.
- **Pre-commit hooks** para calidad de código automática
  - Black, isort, ruff, mypy integrados
- **Badges** actualizados en README (CI status, PyPI, code style)

### Cambiado
- Todo el código formateado con Black e isort
- Configuración de linting unificada con Ruff

## [1.1.0] - 2024-11-29

### Agregado
- **Nueva arquitectura de paquete Python** siguiendo estándares modernos (src layout)
- Sistema de configuración centralizada con `Config` dataclass
- Excepciones personalizadas para mejor manejo de errores
- Type hints completos en todo el código
- Soporte para `py.typed` (PEP 561)
- Suite de tests con pytest (35 tests)
- Comando `leychile-epub` instalable via pip
- Soporte para `python -m leychile_epub`
- Modo verbose (`-v`) en CLI
- Funcionalidad de callback de progreso en el generador
- Logging estructurado con niveles configurables

### Cambiado
- **BREAKING**: Importaciones cambian de `from bcn_scraper import ...` a `from leychile_epub import ...`
- Reestructuración completa del proyecto como paquete Python instalable
- pyproject.toml modernizado con herramientas de desarrollo (ruff, mypy, black, isort)
- README.md actualizado con nueva documentación de API

### Eliminado
- Archivos obsoletos: `app.py`, `main.py`, `requirements.txt`
- Dependencia de archivos sueltos en raíz del proyecto

### Mejorado
- Retry automático con backoff exponencial en el scraper
- Rate limiting para evitar sobrecargar la API de BCN
- Sistema de caché para requests repetidos
- Mejor manejo de errores de red y parsing
- CSS premium mejorado con soporte para dark mode

## [1.0.0] - 2024-11-29

### Agregado
- Scraper para la API XML de la Biblioteca del Congreso Nacional (BCN)
- Generador de ePub con formato premium y estilos profesionales
- Interfaz web con Streamlit para uso interactivo
- Clasificación automática de tipos de normas (leyes, códigos, decretos, etc.)
- Tabla de contenidos interactiva en los ePub generados
- Índice de palabras clave
- Sistema de referencias cruzadas
- Metadatos completos en los ePub (autor, fecha, identificadores)
- Atribución automática al creador del documento

### Características del ePub
- Portada personalizada con información de la norma
- Estilos CSS profesionales para lectura cómoda
- Navegación jerárquica (títulos, capítulos, artículos)
- Compatible con todos los lectores de ePub estándar
- Optimizado para e-readers (Kindle, Kobo, etc.)

---

## Tipos de Cambios

- `Agregado` para nuevas funcionalidades
- `Cambiado` para cambios en funcionalidades existentes
- `Obsoleto` para funcionalidades que serán eliminadas próximamente
- `Eliminado` para funcionalidades eliminadas
- `Corregido` para corrección de bugs
- `Seguridad` para vulnerabilidades

[Unreleased]: https://github.com/laguileracl/leychile-epub/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/laguileracl/leychile-epub/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/laguileracl/leychile-epub/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/laguileracl/leychile-epub/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/laguileracl/leychile-epub/releases/tag/v1.0.0
