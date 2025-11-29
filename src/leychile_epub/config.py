"""
Configuración centralizada para LeyChile ePub Generator.

Este módulo maneja todas las configuraciones del paquete,
incluyendo valores por defecto, validación y carga desde archivos.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ScraperConfig:
    """Configuración del scraper de la BCN.

    Attributes:
        base_url: URL base de la API de la BCN.
        xml_endpoint: Endpoint para obtener XML de normas.
        timeout: Timeout en segundos para las solicitudes HTTP.
        max_retries: Número máximo de reintentos en caso de error.
        retry_delay: Segundos de espera entre reintentos.
        user_agent: User-Agent para las solicitudes HTTP.
        rate_limit_delay: Segundos entre solicitudes para evitar rate limiting.
    """

    base_url: str = "https://www.leychile.cl"
    xml_endpoint: str = "/Consulta/obtxml"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    user_agent: str = "LeyChile-ePub-Generator/1.1.0 (https://github.com/laguileracl/leychile-epub)"
    rate_limit_delay: float = 0.5


@dataclass
class EpubConfig:
    """Configuración del generador de ePub.

    Attributes:
        output_dir: Directorio de salida por defecto.
        include_toc: Incluir tabla de contenidos.
        include_index: Incluir índice de palabras clave.
        include_metadata: Incluir metadatos completos.
        include_cover: Incluir portada.
        language: Idioma del ePub (código ISO).
        creator: Nombre del creador por defecto.
        publisher: Editorial por defecto.
    """

    output_dir: str = "."
    include_toc: bool = True
    include_index: bool = True
    include_metadata: bool = True
    include_cover: bool = True
    language: str = "es"
    creator: str = "Luis Aguilera Arteaga"
    publisher: str = "LeyChile ePub Generator"


@dataclass
class LoggingConfig:
    """Configuración del sistema de logging.

    Attributes:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: Formato de los mensajes de log.
        file: Archivo de log (None para solo consola).
        console: Habilitar logging a consola.
    """

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    console: bool = True


@dataclass
class Config:
    """Configuración principal del paquete.

    Agrupa todas las configuraciones en una sola clase.
    Permite cargar/guardar desde archivos JSON y variables de entorno.

    Attributes:
        scraper: Configuración del scraper.
        epub: Configuración del generador de ePub.
        logging: Configuración del sistema de logging.

    Example:
        >>> config = Config()
        >>> config.scraper.timeout = 60
        >>> config.epub.output_dir = "./mis_libros"
        >>> config.save("mi_config.json")
    """

    scraper: ScraperConfig = field(default_factory=ScraperConfig)
    epub: EpubConfig = field(default_factory=EpubConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        """Carga configuración desde un archivo JSON.

        Args:
            path: Ruta al archivo de configuración.

        Returns:
            Instancia de Config con los valores cargados.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            json.JSONDecodeError: Si el archivo no es JSON válido.
        """
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Crea configuración desde un diccionario.

        Args:
            data: Diccionario con la configuración.

        Returns:
            Instancia de Config con los valores del diccionario.
        """
        config = cls()

        if "scraper" in data:
            for key, value in data["scraper"].items():
                if hasattr(config.scraper, key):
                    setattr(config.scraper, key, value)

        if "epub" in data:
            for key, value in data["epub"].items():
                if hasattr(config.epub, key):
                    setattr(config.epub, key, value)

        if "logging" in data:
            for key, value in data["logging"].items():
                if hasattr(config.logging, key):
                    setattr(config.logging, key, value)

        return config

    @classmethod
    def from_env(cls) -> "Config":
        """Carga configuración desde variables de entorno.

        Variables de entorno soportadas:
            - LEYCHILE_TIMEOUT: Timeout del scraper
            - LEYCHILE_OUTPUT_DIR: Directorio de salida
            - LEYCHILE_LOG_LEVEL: Nivel de logging
            - LEYCHILE_LOG_FILE: Archivo de log

        Returns:
            Instancia de Config con valores de variables de entorno.
        """
        config = cls()

        # Scraper config
        if timeout := os.getenv("LEYCHILE_TIMEOUT"):
            config.scraper.timeout = int(timeout)
        if max_retries := os.getenv("LEYCHILE_MAX_RETRIES"):
            config.scraper.max_retries = int(max_retries)

        # ePub config
        if output_dir := os.getenv("LEYCHILE_OUTPUT_DIR"):
            config.epub.output_dir = output_dir
        if creator := os.getenv("LEYCHILE_CREATOR"):
            config.epub.creator = creator

        # Logging config
        if log_level := os.getenv("LEYCHILE_LOG_LEVEL"):
            config.logging.level = log_level.upper()
        if log_file := os.getenv("LEYCHILE_LOG_FILE"):
            config.logging.file = log_file

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario.

        Returns:
            Diccionario con toda la configuración.
        """
        return {
            "scraper": {
                "base_url": self.scraper.base_url,
                "xml_endpoint": self.scraper.xml_endpoint,
                "timeout": self.scraper.timeout,
                "max_retries": self.scraper.max_retries,
                "retry_delay": self.scraper.retry_delay,
                "user_agent": self.scraper.user_agent,
                "rate_limit_delay": self.scraper.rate_limit_delay,
            },
            "epub": {
                "output_dir": self.epub.output_dir,
                "include_toc": self.epub.include_toc,
                "include_index": self.epub.include_index,
                "include_metadata": self.epub.include_metadata,
                "include_cover": self.epub.include_cover,
                "language": self.epub.language,
                "creator": self.epub.creator,
                "publisher": self.epub.publisher,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file": self.logging.file,
                "console": self.logging.console,
            },
        }

    def save(self, path: str | Path) -> None:
        """Guarda la configuración en un archivo JSON.

        Args:
            path: Ruta donde guardar el archivo.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def setup_logging(self) -> logging.Logger:
        """Configura el sistema de logging según la configuración.

        Returns:
            Logger configurado para el paquete.
        """
        logger = logging.getLogger("leychile_epub")
        logger.setLevel(getattr(logging, self.logging.level))

        # Limpiar handlers existentes
        logger.handlers.clear()

        formatter = logging.Formatter(self.logging.format)

        # Handler de consola
        if self.logging.console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Handler de archivo
        if self.logging.file:
            file_handler = logging.FileHandler(self.logging.file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger


# Configuración por defecto global
_default_config: Optional[Config] = None


def get_config() -> Config:
    """Obtiene la configuración global.

    Returns:
        Instancia de Config global.
    """
    global _default_config
    if _default_config is None:
        _default_config = Config.from_env()
    return _default_config


def set_config(config: Config) -> None:
    """Establece la configuración global.

    Args:
        config: Nueva configuración a usar globalmente.
    """
    global _default_config
    _default_config = config
