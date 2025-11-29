# 🔧 Guía de Desarrollo

Esta guía está dirigida a desarrolladores que quieran contribuir al proyecto.

## Configuración del Entorno

### 1. Clonar el Repositorio

```bash
git clone https://github.com/laguileracl/leychile-epub.git
cd leychile-epub
```

### 2. Crear Entorno Virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Instalar Dependencias de Desarrollo

```bash
pip install -e ".[dev]"
```

### 4. Instalar Pre-commit Hooks

```bash
pre-commit install
```

## Estructura del Proyecto

```
leychile-epub/
├── src/leychile_epub/      # Código fuente principal
│   ├── __init__.py         # Exports públicos y versión
│   ├── __main__.py         # Entry point para python -m
│   ├── cli.py              # Interfaz de línea de comandos
│   ├── config.py           # Configuración centralizada
│   ├── exceptions.py       # Excepciones personalizadas
│   ├── generator.py        # Generador de ePub
│   ├── scraper.py          # Scraper para BCN
│   ├── styles.py           # Estilos CSS
│   └── py.typed            # Marker para type hints
│
├── tests/                   # Tests unitarios
│   ├── test_config.py
│   ├── test_scraper.py
│   └── test_generator.py
│
├── docs/                    # Documentación
│
├── .github/                 # GitHub Actions y templates
│   ├── workflows/
│   │   ├── ci.yml          # Pipeline de CI
│   │   └── release.yml     # Pipeline de release
│   └── ISSUE_TEMPLATE/
│
├── pyproject.toml           # Configuración del proyecto
├── Makefile                 # Comandos de desarrollo
└── .pre-commit-config.yaml  # Pre-commit hooks
```

## Comandos de Desarrollo

Usa el Makefile para tareas comunes:

```bash
# Ver todos los comandos disponibles
make help

# Instalar en modo desarrollo
make install-dev

# Ejecutar tests
make test

# Ejecutar tests con cobertura
make test-cov

# Ejecutar linting
make lint

# Formatear código
make format

# Verificar formato
make format-check

# Type checking
make type-check

# Ejecutar todas las verificaciones
make check

# Limpiar archivos temporales
make clean

# Construir paquete
make build
```

## Tests

### Ejecutar Tests

```bash
# Todos los tests
pytest tests/ -v

# Tests específicos
pytest tests/test_scraper.py -v

# Con cobertura
pytest tests/ --cov=src/leychile_epub --cov-report=html

# Solo tests rápidos
pytest tests/ -v -x --tb=short
```

### Escribir Tests

```python
# tests/test_ejemplo.py
import pytest
from leychile_epub import BCNLawScraper

class TestBCNLawScraper:
    def test_extract_id_norma(self):
        scraper = BCNLawScraper()
        url = "https://www.leychile.cl/Navegar?idNorma=242302"
        id_norma = scraper._extract_id_norma(url)
        assert id_norma == "242302"
    
    def test_invalid_url(self):
        scraper = BCNLawScraper()
        with pytest.raises(ValueError):
            scraper._extract_id_norma("invalid-url")

# Fixtures
@pytest.fixture
def scraper():
    return BCNLawScraper()

@pytest.fixture
def sample_law_data():
    return {
        "metadata": {"title": "Test", "type": "Ley", "number": "123"},
        "content": [],
    }
```

## Linting y Formateo

### Black (Formateo)

```bash
# Formatear todo
black src/ tests/

# Verificar sin modificar
black --check src/ tests/
```

### isort (Imports)

```bash
# Ordenar imports
isort src/ tests/

# Verificar
isort --check-only src/ tests/
```

### Ruff (Linting)

```bash
# Verificar
ruff check src/ tests/

# Auto-fix
ruff check --fix src/ tests/
```

### mypy (Type Checking)

```bash
mypy src/leychile_epub
```

## Git Workflow

### Feature Branch

```bash
# Crear branch desde develop
git checkout develop
git pull origin develop
git checkout -b feature/mi-feature

# Hacer cambios
# ...

# Commit
git add .
git commit -m "feat: descripción del cambio"

# Push
git push origin feature/mi-feature

# Crear PR en GitHub
```

### Conventional Commits

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: nueva funcionalidad
fix: corrección de bug
docs: cambios en documentación
style: cambios de formato (no afectan lógica)
refactor: refactorización de código
test: agregar o modificar tests
chore: cambios de mantenimiento
```

Ejemplos:

```bash
git commit -m "feat: agregar soporte para decretos supremos"
git commit -m "fix: corregir parsing de artículos bis"
git commit -m "docs: actualizar ejemplos de API"
git commit -m "test: agregar tests para generator"
```

## Releases

### Proceso de Release

1. **Actualizar versión** en:
   - `src/leychile_epub/__init__.py`
   - `pyproject.toml`

2. **Actualizar CHANGELOG.md**

3. **Crear PR** de develop a main

4. **Merge y tag**:
   ```bash
   git checkout main
   git merge develop
   git tag v1.x.0
   git push origin main --tags
   ```

5. **Crear Release** en GitHub (esto dispara la publicación a PyPI)

## Arquitectura

### Flujo de Datos

```
URL → BCNLawScraper → law_data (dict) → LawEpubGenerator → .epub
```

### Principios de Diseño

1. **Separación de responsabilidades**: Scraper extrae, Generator genera
2. **Configuración centralizada**: Config class para todos los settings
3. **Excepciones específicas**: Jerarquía clara de errores
4. **Type hints**: Todo el código está tipado
5. **Logging**: Logging estructurado para debugging

### Agregar Nueva Funcionalidad

1. **Crear branch** desde develop
2. **Escribir tests** primero (TDD)
3. **Implementar** la funcionalidad
4. **Documentar** en docstrings y docs/
5. **Actualizar** CHANGELOG.md
6. **Crear PR** con descripción clara

## Recursos

- [Documentación de ebooklib](https://ebooklib.readthedocs.io/)
- [BeautifulSoup4 Docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [ePub Specification](https://www.w3.org/publishing/epub3/epub-overview.html)
- [Python Packaging Guide](https://packaging.python.org/)
