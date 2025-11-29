"""
Tests unitarios para el módulo de configuración.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from leychile_epub.config import (
    Config,
    EpubConfig,
    LoggingConfig,
    ScraperConfig,
    get_config,
    set_config,
)


class TestScraperConfig:
    """Tests para ScraperConfig."""

    def test_default_values(self):
        """Verifica valores por defecto."""
        config = ScraperConfig()

        assert config.base_url == "https://www.leychile.cl"
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_custom_values(self):
        """Verifica valores personalizados."""
        config = ScraperConfig(timeout=60, max_retries=5)

        assert config.timeout == 60
        assert config.max_retries == 5


class TestEpubConfig:
    """Tests para EpubConfig."""

    def test_default_values(self):
        """Verifica valores por defecto."""
        config = EpubConfig()

        assert config.include_toc is True
        assert config.language == "es"
        assert "Luis Aguilera" in config.creator

    def test_custom_output_dir(self):
        """Verifica directorio de salida personalizado."""
        config = EpubConfig(output_dir="/custom/path")

        assert config.output_dir == "/custom/path"


class TestConfig:
    """Tests para Config principal."""

    def test_default_config(self):
        """Verifica configuración por defecto."""
        config = Config()

        assert isinstance(config.scraper, ScraperConfig)
        assert isinstance(config.epub, EpubConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_to_dict(self):
        """Verifica conversión a diccionario."""
        config = Config()
        data = config.to_dict()

        assert "scraper" in data
        assert "epub" in data
        assert "logging" in data
        assert data["scraper"]["timeout"] == 30

    def test_from_dict(self):
        """Verifica creación desde diccionario."""
        data = {
            "scraper": {"timeout": 120},
            "epub": {"output_dir": "/test"},
        }

        config = Config.from_dict(data)

        assert config.scraper.timeout == 120
        assert config.epub.output_dir == "/test"

    def test_save_and_load(self):
        """Verifica guardar y cargar desde archivo."""
        config = Config()
        config.scraper.timeout = 99

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config.save(f.name)

            loaded = Config.from_file(f.name)

            assert loaded.scraper.timeout == 99

            os.unlink(f.name)

    def test_from_env(self):
        """Verifica carga desde variables de entorno."""
        os.environ["LEYCHILE_TIMEOUT"] = "45"
        os.environ["LEYCHILE_OUTPUT_DIR"] = "/from/env"

        try:
            config = Config.from_env()

            assert config.scraper.timeout == 45
            assert config.epub.output_dir == "/from/env"
        finally:
            del os.environ["LEYCHILE_TIMEOUT"]
            del os.environ["LEYCHILE_OUTPUT_DIR"]


class TestGlobalConfig:
    """Tests para configuración global."""

    def test_get_config(self):
        """Verifica obtener configuración global."""
        config = get_config()

        assert isinstance(config, Config)

    def test_set_config(self):
        """Verifica establecer configuración global."""
        custom_config = Config()
        custom_config.scraper.timeout = 999

        set_config(custom_config)

        retrieved = get_config()
        assert retrieved.scraper.timeout == 999
