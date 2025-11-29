# 🚀 Guía de Inicio Rápido

Esta guía te llevará desde cero hasta generar tu primer ePub de una ley chilena.

## Requisitos

- Python 3.10 o superior
- pip (gestor de paquetes de Python)
- Conexión a Internet (para acceder a la BCN)

## Instalación

### Opción 1: Desde PyPI (Recomendado)

```bash
pip install leychile-epub
```

### Opción 2: Desde el código fuente

```bash
git clone https://github.com/laguileracl/leychile-epub.git
cd leychile-epub
pip install -e .
```

## Tu Primer ePub

### 1. Encuentra la ley que quieres convertir

Visita [LeyChile](https://www.leychile.cl/) y busca la ley que te interesa. Copia la URL 
de la página, por ejemplo:

```
https://www.leychile.cl/Navegar?idNorma=242302
```

### 2. Genera el ePub

```bash
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302
```

### 3. ¡Listo!

Encontrarás el archivo `.epub` en tu directorio actual. Ábrelo con tu lector de ebooks 
favorito (Kindle, Kobo, Apple Books, Calibre, etc.).

## Opciones Útiles

```bash
# Especificar directorio de salida
leychile-epub URL -o ./mis_leyes/

# Modo silencioso
leychile-epub URL -q

# Modo verbose (más información)
leychile-epub URL -v

# Procesar múltiples URLs desde un archivo
leychile-epub --batch urls.txt
```

## Siguiente Paso

- Lee la [Guía del CLI](cli.md) para conocer todas las opciones
- Consulta los [Ejemplos](examples.md) para casos de uso avanzados
- Revisa la [API de Python](api.md) para integrar en tus proyectos
