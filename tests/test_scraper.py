"""
Tests unitarios para el scraper.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import pytest

from leychile_epub.exceptions import ValidationError
from leychile_epub.scraper import BCNLawScraper


class TestBCNLawScraper:
    """Tests para BCNLawScraper."""

    @pytest.fixture
    def scraper(self):
        """Crea una instancia del scraper."""
        return BCNLawScraper()

    def test_extract_id_norma(self, scraper):
        """Verifica extracción de ID de norma."""
        url = "https://www.leychile.cl/Navegar?idNorma=242302"

        id_norma = scraper.extract_id_norma(url)

        assert id_norma == "242302"

    def test_extract_id_norma_with_version(self, scraper):
        """Verifica extracción con versión."""
        url = "https://www.leychile.cl/Navegar?idNorma=242302&idVersion=2024-01-01"

        id_norma = scraper.extract_id_norma(url)
        id_version = scraper.extract_id_version(url)

        assert id_norma == "242302"
        assert id_version == "2024-01-01"

    def test_extract_id_norma_invalid(self, scraper):
        """Verifica URL sin ID."""
        url = "https://www.example.com/page"

        id_norma = scraper.extract_id_norma(url)

        assert id_norma is None

    def test_get_api_url(self, scraper):
        """Verifica construcción de URL de API."""
        api_url = scraper.get_api_url("242302")

        assert "242302" in api_url
        assert "obtxml" in api_url
        assert "opt=7" in api_url

    def test_classify_text_titulo(self, scraper):
        """Verifica clasificación de títulos."""
        assert scraper._classify_text("TITULO I De las disposiciones") == "titulo"
        assert scraper._classify_text("TITULO XV Otras materias") == "titulo"

    def test_classify_text_articulo(self, scraper):
        """Verifica clasificación de artículos."""
        assert scraper._classify_text("Artículo 1°.- El trabajo") == "articulo"
        assert scraper._classify_text("Artículo 25 bis") == "articulo"

    def test_classify_text_parrafo(self, scraper):
        """Verifica clasificación de párrafos."""
        assert scraper._classify_text("Párrafo 1° Del contrato") == "parrafo"
        assert scraper._classify_text("PARRAFO 2 De las obligaciones") == "parrafo"

    def test_classify_text_regular(self, scraper):
        """Verifica clasificación de texto regular."""
        assert scraper._classify_text("Este es un texto normal.") == "texto"


class TestScraperPatterns:
    """Tests para patrones de regex."""

    @pytest.fixture
    def scraper(self):
        return BCNLawScraper()

    def test_article_pattern_simple(self, scraper):
        """Verifica patrón de artículo simple."""
        match = scraper.PATTERNS["articulo"].match("Artículo 1")
        assert match is not None

    def test_article_pattern_with_bis(self, scraper):
        """Verifica patrón con bis/ter."""
        text = "Artículo 25 bis.- El empleador"
        match = scraper.PATTERNS["articulo_full"].match(text)

        assert match is not None
        assert "bis" in match.group(1).lower()

    def test_titulo_pattern(self, scraper):
        """Verifica patrón de título."""
        assert scraper.PATTERNS["titulo"].match("TITULO I")
        assert scraper.PATTERNS["titulo"].match("TITULO XV")
        assert not scraper.PATTERNS["titulo"].match("El título del documento")
