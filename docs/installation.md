# 📦 Guía de Instalación

## Requisitos del Sistema

| Requisito | Versión Mínima |
|-----------|----------------|
| Python | 3.10+ |
| pip | 21.0+ |
| Sistema Operativo | Windows, macOS, Linux |

## Métodos de Instalación

### 1. Instalación desde PyPI (Recomendado)

```bash
pip install leychile-epub
```

### 2. Instalación con dependencias opcionales

```bash
# Con interfaz web (Streamlit)
pip install leychile-epub[web]

# Con herramientas de desarrollo
pip install leychile-epub[dev]

# Todo incluido
pip install leychile-epub[all]
```

### 3. Instalación desde GitHub

```bash
# Última versión estable
pip install git+https://github.com/laguileracl/leychile-epub.git

# Versión específica
pip install git+https://github.com/laguileracl/leychile-epub.git@v1.2.0
```

### 4. Instalación desde código fuente

```bash
# Clonar repositorio
git clone https://github.com/laguileracl/leychile-epub.git
cd leychile-epub

# Crear entorno virtual (recomendado)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instalar en modo editable
pip install -e .

# Con dependencias de desarrollo
pip install -e ".[dev]"
```

## Verificar Instalación

```bash
# Verificar que está instalado
leychile-epub --version

# Mostrar ayuda
leychile-epub --help

# Prueba rápida
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302
```

## Entornos Virtuales

Se recomienda usar entornos virtuales para evitar conflictos de dependencias:

### Con venv (incluido en Python)

```bash
python -m venv leychile-env
source leychile-env/bin/activate  # Windows: leychile-env\Scripts\activate
pip install leychile-epub
```

### Con conda

```bash
conda create -n leychile python=3.12
conda activate leychile
pip install leychile-epub
```

### Con poetry

```bash
poetry new mi-proyecto
cd mi-proyecto
poetry add leychile-epub
```

## Dependencias

El paquete instala automáticamente las siguientes dependencias:

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| requests | ≥2.28.0 | Cliente HTTP para la API de BCN |
| beautifulsoup4 | ≥4.11.0 | Parser HTML/XML |
| lxml | ≥4.9.0 | Parser XML de alto rendimiento |
| ebooklib | ≥0.18 | Generación de archivos ePub |

## Solución de Problemas

### Error: "No module named 'leychile_epub'"

```bash
# Asegúrate de que pip instaló en el Python correcto
python -m pip install leychile-epub
```

### Error de permisos en Linux/macOS

```bash
pip install --user leychile-epub
```

### Conflictos de dependencias

```bash
# Crear un entorno virtual limpio
python -m venv fresh-env
source fresh-env/bin/activate
pip install leychile-epub
```

## Desinstalación

```bash
pip uninstall leychile-epub
```
