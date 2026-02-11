"""
Tests unitarios para el scraper v2.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import pytest

from leychile_epub.exceptions import ValidationError
from leychile_epub.scraper_v2 import BCNLawScraperV2, BCNXMLParser, Norma


class TestBCNLawScraperV2:
    """Tests para BCNLawScraperV2."""

    @pytest.fixture
    def scraper(self):
        return BCNLawScraperV2()

    def test_extract_id_norma(self, scraper):
        url = "https://www.leychile.cl/Navegar?idNorma=242302"
        assert scraper.extract_id_norma(url) == "242302"

    def test_extract_id_norma_bcn_domain(self, scraper):
        url = "https://www.bcn.cl/leychile/navegar?idNorma=242302"
        assert scraper.extract_id_norma(url) == "242302"

    def test_extract_id_norma_with_version(self, scraper):
        url = "https://www.leychile.cl/Navegar?idNorma=242302&idVersion=2024-01-01"
        assert scraper.extract_id_norma(url) == "242302"
        assert scraper.extract_id_version(url) == "2024-01-01"

    def test_extract_id_norma_no_id(self, scraper):
        url = "https://www.leychile.cl/Navegar"
        assert scraper.extract_id_norma(url) is None

    def test_extract_id_norma_invalid_domain(self, scraper):
        url = "https://www.example.com/page?idNorma=123"
        with pytest.raises(ValidationError, match="Dominio no permitido"):
            scraper.extract_id_norma(url)

    def test_extract_id_norma_invalid_scheme(self, scraper):
        url = "ftp://www.leychile.cl/Navegar?idNorma=242302"
        with pytest.raises(ValidationError, match="HTTP o HTTPS"):
            scraper.extract_id_norma(url)

    def test_get_xml_url(self, scraper):
        url = scraper.get_xml_url("242302")
        assert "242302" in url
        assert "obtxml" in url
        assert "opt=7" in url

    def test_context_manager(self):
        with BCNLawScraperV2() as scraper:
            assert scraper.session is not None
        # Session should be closed after exiting context

    def test_close(self):
        scraper = BCNLawScraperV2()
        scraper.close()
        # Should not raise


class TestBCNXMLParser:
    """Tests para BCNXMLParser."""

    def test_parser_init(self):
        parser = BCNXMLParser()
        assert parser.ns == {"lc": "http://www.leychile.cl/esquemas"}

    def test_get_text_none(self):
        parser = BCNXMLParser()
        assert parser._get_text(None) == ""


class TestNormaDataclass:
    """Tests para la dataclass Norma."""

    def test_titulo_completo_with_titulo(self):
        norma = Norma(
            metadatos=__import__(
                "leychile_epub.scraper_v2", fromlist=["NormaMetadatos"]
            ).NormaMetadatos(titulo="Mi Título"),
        )
        assert norma.titulo_completo == "Mi Título"

    def test_titulo_completo_fallback(self):
        from leychile_epub.scraper_v2 import NormaIdentificador

        norma = Norma(
            identificador=NormaIdentificador(tipo="Ley", numero="123"),
        )
        assert norma.titulo_completo == "Ley 123"

    def test_nombre_archivo(self):
        from leychile_epub.scraper_v2 import NormaIdentificador

        norma = Norma(
            identificador=NormaIdentificador(tipo="Decreto Ley", numero="3.500"),
        )
        assert norma.nombre_archivo == "Decreto_Ley_3.500"
