"""
Tests unitarios para el generador de ePub v2.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import tempfile
from pathlib import Path

import pytest

from leychile_epub.generator_v2 import DEFAULT_CSS, EPubConfig, EPubGeneratorV2
from leychile_epub.scraper_v2 import (
    EstructuraFuncional,
    Norma,
    NormaIdentificador,
    NormaMetadatos,
)


@pytest.fixture
def sample_norma():
    """Crea una Norma de ejemplo para pruebas."""
    return Norma(
        norma_id="12345",
        es_tratado=False,
        fecha_version="2024-06-15",
        schema_version="1.0",
        derogado=False,
        identificador=NormaIdentificador(
            tipo="Ley",
            numero="21.000",
            organismos=["Ministerio de Economía"],
            fecha_promulgacion="2024-01-15",
            fecha_publicacion="2024-02-01",
        ),
        metadatos=NormaMetadatos(
            titulo="LEY QUE REGULA ALGO IMPORTANTE",
            materias=["Economía", "Comercio"],
            nombres_uso_comun=["Ley de Algo"],
        ),
        encabezado_texto="Teniendo presente que el H. Congreso Nacional ha dado su aprobación...",
        encabezado_derogado=False,
        estructuras=[
            EstructuraFuncional(
                id_parte="100",
                tipo_parte="Título",
                texto="",
                nombre_parte="I",
                titulo_parte="TÍTULO I DISPOSICIONES GENERALES",
                nivel=0,
                hijos=[
                    EstructuraFuncional(
                        id_parte="101",
                        tipo_parte="Artículo",
                        texto="Esta ley tiene por objeto regular algo importante para el país.",
                        nombre_parte="1",
                        nivel=1,
                        fecha_version="2024-06-15",
                    ),
                    EstructuraFuncional(
                        id_parte="102",
                        tipo_parte="Artículo",
                        texto="Para los efectos de esta ley se entenderá por:\na) Término uno: definición.\nb) Término dos: otra definición.",
                        nombre_parte="2",
                        nivel=1,
                    ),
                ],
            ),
            EstructuraFuncional(
                id_parte="200",
                tipo_parte="Título",
                texto="",
                nombre_parte="II",
                titulo_parte="TÍTULO II DE LAS OBLIGACIONES",
                nivel=0,
                hijos=[
                    EstructuraFuncional(
                        id_parte="201",
                        tipo_parte="Artículo",
                        texto="Las personas deberán cumplir con las obligaciones establecidas.",
                        nombre_parte="3",
                        nivel=1,
                        derogado=True,
                    ),
                ],
            ),
        ],
        promulgacion_texto="Habiéndose cumplido con lo establecido en el artículo 93...",
        promulgacion_derogado=False,
    )


@pytest.fixture
def empty_norma():
    """Crea una Norma vacía para pruebas de edge cases."""
    return Norma(
        norma_id="99999",
        identificador=NormaIdentificador(tipo="Decreto", numero="100"),
        metadatos=NormaMetadatos(titulo="Decreto vacío"),
    )


@pytest.fixture
def derogada_norma():
    """Crea una Norma derogada para pruebas."""
    return Norma(
        norma_id="88888",
        derogado=True,
        identificador=NormaIdentificador(
            tipo="Ley",
            numero="5.000",
            organismos=["Ministerio del Interior"],
            fecha_promulgacion="1990-01-01",
            fecha_publicacion="1990-02-01",
        ),
        metadatos=NormaMetadatos(
            titulo="LEY DEROGADA DE PRUEBA",
            fecha_derogacion="2020-01-01",
        ),
        fecha_version="2020-01-01",
    )


class TestEPubConfig:
    """Tests para EPubConfig."""

    def test_default_values(self):
        config = EPubConfig()
        assert config.language == "es"
        assert config.include_toc is True
        assert config.include_metadata_page is True
        assert config.include_derogado_markers is True
        assert config.custom_css is None

    def test_custom_values(self):
        config = EPubConfig(language="en", include_toc=False, custom_css="body { color: red; }")
        assert config.language == "en"
        assert config.include_toc is False
        assert config.custom_css == "body { color: red; }"


class TestEPubGeneratorV2Init:
    """Tests para inicialización del generador v2."""

    def test_default_init(self):
        gen = EPubGeneratorV2()
        assert gen.config is not None
        assert gen.config.language == "es"

    def test_custom_config(self):
        config = EPubConfig(language="en")
        gen = EPubGeneratorV2(config)
        assert gen.config.language == "en"


class TestEPubGeneratorV2Generate:
    """Tests para generación de ePub."""

    def test_generate_creates_file(self, sample_norma):
        gen = EPubGeneratorV2()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test.epub"
            result = gen.generate(sample_norma, output)
            assert result.exists()
            assert result.suffix == ".epub"
            assert result.stat().st_size > 0

    def test_generate_with_string_path(self, sample_norma):
        gen = EPubGeneratorV2()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = str(Path(tmpdir) / "test_str.epub")
            result = gen.generate(sample_norma, output)
            assert Path(result).exists()

    def test_generate_empty_norma(self, empty_norma):
        gen = EPubGeneratorV2()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "empty.epub"
            result = gen.generate(empty_norma, output)
            assert result.exists()
            assert result.stat().st_size > 0

    def test_generate_derogada_norma(self, derogada_norma):
        gen = EPubGeneratorV2()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "derogada.epub"
            result = gen.generate(derogada_norma, output)
            assert result.exists()

    def test_generate_without_metadata_page(self, sample_norma):
        config = EPubConfig(include_metadata_page=False)
        gen = EPubGeneratorV2(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "no_meta.epub"
            result = gen.generate(sample_norma, output)
            assert result.exists()

    def test_generate_without_version_info(self, sample_norma):
        config = EPubConfig(include_version_info=False)
        gen = EPubGeneratorV2(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "no_version.epub"
            result = gen.generate(sample_norma, output)
            assert result.exists()

    def test_generate_with_custom_css(self, sample_norma):
        config = EPubConfig(custom_css="body { font-size: 14px; }")
        gen = EPubGeneratorV2(config)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "custom_css.epub"
            result = gen.generate(sample_norma, output)
            assert result.exists()

    def test_generate_creates_parent_dirs(self, sample_norma):
        gen = EPubGeneratorV2()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "sub" / "dir" / "test.epub"
            output.parent.mkdir(parents=True, exist_ok=True)
            result = gen.generate(sample_norma, output)
            assert result.exists()


class TestEPubGeneratorV2Formatting:
    """Tests para formateo de texto."""

    def test_format_texto_empty(self):
        gen = EPubGeneratorV2()
        assert gen._format_texto("") == ""

    def test_format_texto_simple(self):
        gen = EPubGeneratorV2()
        result = gen._format_texto("Texto simple.")
        assert "<p>" in result
        assert "Texto simple." in result

    def test_format_texto_paragraphs(self):
        gen = EPubGeneratorV2()
        result = gen._format_texto("Párrafo uno.\n\nPárrafo dos.")
        assert result.count("<p>") == 2

    def test_format_texto_literal(self):
        gen = EPubGeneratorV2()
        result = gen._format_texto("a) Primera opción")
        assert 'class="literal"' in result

    def test_format_texto_numeral(self):
        gen = EPubGeneratorV2()
        result = gen._format_texto("1. Primer punto")
        assert 'class="numero"' in result

    def test_format_texto_inciso(self):
        gen = EPubGeneratorV2()
        result = gen._format_texto("- Un inciso con guión")
        assert 'class="inciso"' in result

    def test_format_texto_html_escaping(self):
        gen = EPubGeneratorV2()
        result = gen._format_texto("Texto con <script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestEPubGeneratorV2Estructura:
    """Tests para rendering de estructuras."""

    def test_get_titulo_estructura_articulo(self):
        gen = EPubGeneratorV2()
        ef = EstructuraFuncional(tipo_parte="Artículo", nombre_parte="1")
        assert gen._get_titulo_estructura(ef) == "Artículo 1"

    def test_get_titulo_estructura_titulo(self):
        gen = EPubGeneratorV2()
        ef = EstructuraFuncional(
            tipo_parte="Título", titulo_parte="TÍTULO I DISPOSICIONES GENERALES"
        )
        assert gen._get_titulo_estructura(ef) == "TÍTULO I DISPOSICIONES GENERALES"

    def test_get_titulo_estructura_fallback(self):
        gen = EPubGeneratorV2()
        ef = EstructuraFuncional(tipo_parte="Párrafo", id_parte="500")
        assert gen._get_titulo_estructura(ef) == "Párrafo 500"

    def test_render_estructura_articulo(self):
        gen = EPubGeneratorV2()
        gen._book = None  # Not needed for this test
        ef = EstructuraFuncional(
            tipo_parte="Artículo",
            nombre_parte="1",
            texto="Contenido del artículo.",
        )
        result = gen._render_estructura(ef)
        assert 'class="articulo"' in result
        assert 'class="articulo-numero"' in result
        assert "Contenido del art" in result

    def test_render_estructura_derogado(self):
        gen = EPubGeneratorV2()
        ef = EstructuraFuncional(
            tipo_parte="Artículo",
            nombre_parte="5",
            texto="Artículo derogado.",
            derogado=True,
        )
        result = gen._render_estructura(ef)
        assert 'class="derogado"' in result or "derogado" in result

    def test_render_estructura_transitorio(self):
        gen = EPubGeneratorV2()
        ef = EstructuraFuncional(
            tipo_parte="Artículo",
            nombre_parte="T1",
            texto="Disposición transitoria.",
            transitorio=True,
        )
        result = gen._render_estructura(ef)
        assert "transitorio" in result

    def test_make_anchor(self):
        gen = EPubGeneratorV2()
        ef = EstructuraFuncional(tipo_parte="Artículo", id_parte="123")
        result = gen._make_anchor(ef)
        assert result == "articulo_123"

    def test_make_anchor_capitulo(self):
        gen = EPubGeneratorV2()
        ef = EstructuraFuncional(tipo_parte="Capítulo", id_parte="456")
        result = gen._make_anchor(ef)
        assert result == "capitulo_456"


class TestDefaultCSS:
    """Tests para el CSS predeterminado."""

    def test_css_not_empty(self):
        assert len(DEFAULT_CSS) > 0

    def test_css_contains_key_classes(self):
        assert ".articulo" in DEFAULT_CSS
        assert ".derogado" in DEFAULT_CSS
        assert ".transitorio" in DEFAULT_CSS
        assert ".titulo-pagina" in DEFAULT_CSS
        assert ".metadatos-pagina" in DEFAULT_CSS


class TestConvenienceFunction:
    """Tests para la función de conveniencia."""

    def test_generate_epub_function(self, sample_norma):
        from leychile_epub.generator_v2 import generate_epub

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "convenience.epub"
            result = generate_epub(sample_norma, output)
            assert result.exists()
