"""
Tests unitarios para el generador de ePub.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import tempfile
from pathlib import Path

import pytest

from leychile_epub.exceptions import ValidationError
from leychile_epub.generator import LawEpubGenerator


class TestLawEpubGenerator:
    """Tests para LawEpubGenerator."""

    @pytest.fixture
    def generator(self):
        """Crea una instancia del generador."""
        return LawEpubGenerator()

    @pytest.fixture
    def sample_law_data(self):
        """Datos de ejemplo para pruebas."""
        return {
            "metadata": {
                "title": "Ley de Prueba",
                "type": "Ley",
                "number": "12345",
                "organism": "Ministerio de Pruebas",
                "subjects": ["Prueba", "Test"],
                "source": "Diario Oficial",
            },
            "content": [
                {
                    "type": "titulo",
                    "level": 1,
                    "text": "TITULO I De las disposiciones generales",
                },
                {
                    "type": "articulo",
                    "level": 3,
                    "title": "Artículo 1°",
                    "text": "Esta es una ley de prueba.",
                },
                {
                    "type": "articulo",
                    "level": 3,
                    "title": "Artículo 2°",
                    "text": "Véase el artículo 1°.",
                },
            ],
            "url": "https://www.leychile.cl/test",
            "id_norma": "12345",
        }

    def test_init(self, generator):
        """Verifica inicialización."""
        assert generator.config is not None
        assert generator.book is None

    def test_validate_law_data_valid(self, generator, sample_law_data):
        """Verifica validación de datos válidos."""
        # No debe lanzar excepción
        generator._validate_law_data(sample_law_data)

    def test_validate_law_data_invalid(self, generator):
        """Verifica validación de datos inválidos."""
        with pytest.raises(ValidationError):
            generator._validate_law_data({})

        with pytest.raises(ValidationError):
            generator._validate_law_data({"metadata": {}})

    def test_escape_html(self, generator):
        """Verifica escape de HTML."""
        assert generator._escape_html("<script>") == "&lt;script&gt;"
        assert generator._escape_html('"quote"') == "&quot;quote&quot;"
        assert generator._escape_html("A & B") == "A &amp; B"

    def test_extract_article_id(self, generator):
        """Verifica extracción de ID de artículo."""
        assert generator._extract_article_id("Artículo 1°") == "1"
        assert generator._extract_article_id("Artículo 25 bis") == "25bis"
        assert generator._extract_article_id("Texto normal") is None

    def test_format_section_title(self, generator):
        """Verifica formateo de títulos."""
        result = generator._format_section_title("TITULO I De las disposiciones")
        assert "<br/>" in result or "TITULO I" in result

    def test_generate_creates_file(self, generator, sample_law_data):
        """Verifica que se genera el archivo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generator.generate(sample_law_data, output_dir=tmpdir)

            assert result is not None
            assert Path(result).exists()
            assert result.endswith(".epub")

    def test_generate_with_custom_filename(self, generator, sample_law_data):
        """Verifica nombre de archivo personalizado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generator.generate(
                sample_law_data,
                output_dir=tmpdir,
                filename="mi_ley.epub",
            )

            assert "mi_ley.epub" in result


class TestCrossReferences:
    """Tests para referencias cruzadas."""

    @pytest.fixture
    def generator(self):
        gen = LawEpubGenerator()
        gen.article_ids = {
            "1": "titulo_1.xhtml#art_1",
            "2": "titulo_1.xhtml#art_2",
            "25bis": "titulo_2.xhtml#art_25bis",
        }
        return gen

    def test_add_cross_references(self, generator):
        """Verifica adición de referencias cruzadas."""
        text = "Véase el artículo 1° y el artículo 2°."
        result = generator._add_cross_references(text)

        assert 'href="titulo_1.xhtml#art_1"' in result
        assert 'class="cross-ref"' in result

    def test_cross_reference_not_found(self, generator):
        """Verifica que no se modifica si no existe el artículo."""
        text = "Véase el artículo 999°."
        result = generator._add_cross_references(text)

        # No debe contener href porque el artículo no existe
        assert "href=" not in result or "art_999" not in result


class TestArticleFormatting:
    """Tests para formateo de artículos."""

    @pytest.fixture
    def generator(self):
        gen = LawEpubGenerator()
        gen.article_ids = {}
        return gen

    def test_format_simple_article(self, generator):
        """Verifica formateo de artículo simple."""
        text = "El trabajador tiene derecho a descanso."
        result = generator._format_article_content(text)

        assert "<p>" in result

    def test_format_numbered_list(self, generator):
        """Verifica formateo de lista numerada."""
        text = "Las causales son:\n\n1° Primera causal\n\n2° Segunda causal"
        result = generator._format_article_content(text)

        assert "legal-list" in result or "<li>" in result

    def test_format_empty_text(self, generator):
        """Verifica formateo de texto vacío."""
        result = generator._format_article_content("")

        assert "<p>" in result
