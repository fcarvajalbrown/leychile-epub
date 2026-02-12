# CLAUDE.md - Contexto del Proyecto

## Qué es este proyecto

**LeyChile ePub Generator** es un paquete Python que convierte legislación chilena de la Biblioteca del Congreso Nacional (BCN) en ePubs profesionales y XML estructurado para agentes de IA.

## Comandos clave

```bash
# Instalar con dependencias de desarrollo
make install-dev

# Ejecutar tests
make test

# Tests con cobertura
make test-cov

# Linting y formateo
make lint
make format

# Verificación completa (lint + type-check + test)
make check

# Type checking
make type-check

# Generar ePub desde URL
make run URL="https://www.leychile.cl/Navegar?idNorma=242302"
```

## Arquitectura

```
src/leychile_epub/
├── scraper_v2.py      # Scraper principal (XSD-compliant) - BCNLawScraperV2
├── generator_v2.py    # Generador ePub principal - EPubGeneratorV2
├── xml_generator.py   # Generador XML para IA - LawXMLGenerator
├── scraper.py         # [DEPRECADO] Scraper v1
├── generator.py       # [DEPRECADO] Generador v1
├── config.py          # Config centralizada con dataclasses
├── exceptions.py      # Jerarquía de excepciones
├── cli.py             # CLI (leychile-epub)
├── styles.py          # CSS para ePub v1
└── text_to_xml_parser.py  # Parser texto plano → XML
```

## Convenciones

- **Python 3.10+** - Usar union types (`str | None`), no `Optional`
- **Formateo**: Black (100 chars), isort (profile black)
- **Linting**: Ruff (E, W, F, I, B, C4, UP)
- **Type checking**: mypy
- **Tests**: pytest, marca `@pytest.mark.integration` para tests con red
- **Commits**: Conventional Commits en español (feat:, fix:, chore:, etc.)

## Datos

- `biblioteca_xml/` - Biblioteca canónica de normas chilenas en XML
  - `leyes/` - Leyes ordinarias
  - `codigos/` - Códigos (Civil, Penal, Trabajo, etc.)
  - `decretos/` - DFL, DL, decretos supremos
  - `constitucion/` - Constitución Política
  - `auto_acordados/` - Auto acordados judiciales
  - `organismos/` - Normativa de organismos reguladores
    - `CMF/NCG/` - Normas CMF
    - `SUPERIR/NCG/` - NCGs SUPERIR (XML + texto + PDFs fuente)
    - `SUPERIR/Instructivo/` - Instructivos SUPERIR
- `schemas/ley_v1.xsd` - Esquema XSD para validación
- `trabajo/normas_md/` - Leyes en Markdown (borradores de trabajo, no definitivos)

## API de la BCN

- Base URL: `https://www.leychile.cl`
- XML endpoint: `/Consulta/obtxml?opt=7&idNorma={id}`
- Rate limit: 0.5s entre requests
- Namespace XML: `http://www.leychile.cl/esquemas`

## Notas importantes

- v1 (scraper.py, generator.py) está **deprecado** - siempre usar v2
- Los scrapers son context managers: `with BCNLawScraperV2() as scraper:`
- Solo se aceptan URLs de dominios `leychile.cl` y `bcn.cl`
- El XML generado se valida contra `schemas/ley_v1.xsd` automáticamente
