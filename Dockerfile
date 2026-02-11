# Multi-stage Dockerfile para LeyChile ePub Generator
# Soporta tanto CLI como Web (Streamlit)

# === Stage 1: Base ===
FROM python:3.12-slim AS base

LABEL maintainer="Luis Aguilera Arteaga <luis@aguilera.cl>"
LABEL description="Generador de ePub para legislación chilena"
LABEL org.opencontainers.image.source="https://github.com/laguileracl/leychile-epub"

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends libxml2 libxslt1.1 && \
    rm -rf /var/lib/apt/lists/*

# Copiar solo lo necesario para instalar dependencias
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
COPY app.py ./

# === Stage 2: CLI ===
FROM base AS cli

RUN pip install --no-cache-dir .

# Crear directorio de salida
RUN mkdir -p /output

ENTRYPOINT ["leychile-epub"]
CMD ["--help"]

# === Stage 3: Web (Streamlit) ===
FROM base AS web

RUN pip install --no-cache-dir ".[web]"

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
