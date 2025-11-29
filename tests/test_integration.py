"""
Tests de integración para LeyChile ePub Generator.

Estos tests hacen requests reales a la API de BCN, por lo que
pueden ser lentos y dependen de conectividad de red.

Ejecutar con: pytest tests/test_integration.py -v -m integration
"""

import tempfile
from pathlib import Path

import pytest

from leychile_epub import BCNLawScraper, Config, LawEpubGenerator
from leychile_epub.exceptions import ScraperError

# Marcar todos los tests como de integración
pytestmark = pytest.mark.integration


class TestScraperIntegration:
    """Tests de integración para el scraper."""

    @pytest.fixture
    def scraper(self):
        return BCNLawScraper()

    def test_scrape_constitucion(self, scraper):
        """Test que puede extraer la Constitución Política."""
        url = "https://www.leychile.cl/Navegar?idNorma=242302"
        law_data = scraper.scrape_law(url)

        assert law_data is not None
        assert "metadata" in law_data
        assert "content" in law_data

        metadata = law_data["metadata"]
        assert metadata.get("type") in ["Decreto", "Ley"]
        assert "100" in str(metadata.get("number", ""))

    def test_scrape_codigo_civil(self, scraper):
        """Test que puede extraer el Código Civil."""
        url = "https://www.leychile.cl/Navegar?idNorma=172986"
        law_data = scraper.scrape_law(url)

        assert law_data is not None
        assert len(law_data.get("content", [])) > 0

    def test_scrape_ley_transito(self, scraper):
        """Test que puede extraer la Ley de Tránsito."""
        url = "https://www.leychile.cl/Navegar?idNorma=29708"
        law_data = scraper.scrape_law(url)

        assert law_data is not None
        metadata = law_data.get("metadata", {})
        assert "18290" in str(metadata.get("number", "")) or "Ley" in str(metadata.get("type", ""))

    def test_scrape_invalid_url(self, scraper):
        """Test que maneja URLs inválidas correctamente."""
        with pytest.raises((ScraperError, ValueError)):
            scraper.scrape_law("https://www.leychile.cl/Navegar?idNorma=999999999")

    def test_scrape_extracts_articles(self, scraper):
        """Test que extrae artículos correctamente."""
        url = "https://www.leychile.cl/Navegar?idNorma=242302"
        law_data = scraper.scrape_law(url)

        content = law_data.get("content", [])
        articles = [item for item in content if item.get("type") == "articulo"]

        # La constitución tiene muchos artículos
        assert len(articles) > 50


class TestGeneratorIntegration:
    """Tests de integración para el generador."""

    @pytest.fixture
    def scraper(self):
        return BCNLawScraper()

    @pytest.fixture
    def generator(self):
        return LawEpubGenerator()

    def test_generate_epub_from_real_law(self, scraper, generator):
        """Test que genera un ePub real correctamente."""
        url = "https://www.leychile.cl/Navegar?idNorma=242302"
        law_data = scraper.scrape_law(url)

        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = generator.generate(law_data, output_dir=tmpdir)

            assert epub_path is not None
            assert Path(epub_path).exists()
            assert epub_path.endswith(".epub")

            # Verificar tamaño mínimo (un ePub real debe tener al menos 10KB)
            file_size = Path(epub_path).stat().st_size
            assert file_size > 10000

    def test_generate_with_custom_filename(self, scraper, generator):
        """Test que genera con nombre personalizado."""
        url = "https://www.leychile.cl/Navegar?idNorma=242302"
        law_data = scraper.scrape_law(url)

        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = generator.generate(
                law_data, output_dir=tmpdir, filename="mi_constitucion.epub"
            )

            assert "mi_constitucion.epub" in epub_path
            assert Path(epub_path).exists()

    def test_generate_multiple_laws(self, scraper, generator):
        """Test que puede generar múltiples leyes."""
        urls = [
            "https://www.leychile.cl/Navegar?idNorma=242302",
            "https://www.leychile.cl/Navegar?idNorma=29708",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            generated_files = []

            for url in urls:
                law_data = scraper.scrape_law(url)
                epub_path = generator.generate(law_data, output_dir=tmpdir)
                generated_files.append(epub_path)

            assert len(generated_files) == 2
            for path in generated_files:
                assert Path(path).exists()


class TestEndToEnd:
    """Tests end-to-end completos."""

    def test_full_workflow(self):
        """Test del flujo completo de scraping a ePub."""
        # Setup
        scraper = BCNLawScraper()
        config = Config()
        generator = LawEpubGenerator(config)

        # Scrape
        url = "https://www.leychile.cl/Navegar?idNorma=242302"
        law_data = scraper.scrape_law(url)

        # Verify law data
        assert law_data is not None
        assert "metadata" in law_data
        assert "content" in law_data
        assert len(law_data["content"]) > 0

        # Generate with progress callback
        progress_updates = []

        def track_progress(progress: float, message: str):
            progress_updates.append((progress, message))

        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = generator.generate(
                law_data, output_dir=tmpdir, progress_callback=track_progress
            )

            # Verify file
            assert Path(epub_path).exists()
            assert Path(epub_path).stat().st_size > 0

            # Verify progress was tracked
            assert len(progress_updates) > 0
            # Last progress should be 1.0 (100%)
            assert progress_updates[-1][0] == 1.0

    def test_workflow_with_custom_config(self):
        """Test con configuración personalizada."""
        config = Config()
        config.scraper.timeout = 60
        config.scraper.max_retries = 5
        config.epub.creator = "Test Suite"

        scraper = BCNLawScraper()
        generator = LawEpubGenerator(config)

        url = "https://www.leychile.cl/Navegar?idNorma=29708"
        law_data = scraper.scrape_law(url)

        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = generator.generate(law_data, output_dir=tmpdir)
            assert Path(epub_path).exists()


# Configurar pytest para que pueda filtrar por marker
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")
