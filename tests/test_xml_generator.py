"""
Tests unitarios para el generador de XML.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import tempfile
from xml.etree import ElementTree as ET

import pytest

from leychile_epub.scraper_v2 import (
    EstructuraFuncional,
    Norma,
    NormaIdentificador,
    NormaMetadatos,
)
from leychile_epub.xml_generator import LawXMLGenerator


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
            titulo="LEY QUE REGULA ALGO",
            materias=["Economía"],
        ),
        encabezado_texto="Teniendo presente que el H. Congreso...",
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
                        texto="Esta ley tiene por objeto regular algo.",
                        nombre_parte="1",
                        nivel=1,
                    ),
                    EstructuraFuncional(
                        id_parte="102",
                        tipo_parte="Artículo",
                        texto="Definiciones.\n\n1) Término uno.\n\n2) Término dos.",
                        nombre_parte="2",
                        nivel=1,
                    ),
                ],
            ),
        ],
        promulgacion_texto="Habiéndose cumplido con lo establecido...",
        promulgacion_derogado=False,
    )


class TestLawXMLGeneratorInit:
    """Tests para inicialización del generador."""

    def test_init(self):
        gen = LawXMLGenerator()
        assert gen.scraper is not None

    def test_tipo_mapping(self):
        gen = LawXMLGenerator()
        assert gen.TIPO_MAPPING["artículo"] == "articulo"
        assert gen.TIPO_MAPPING["título"] == "titulo"
        assert gen.TIPO_MAPPING["libro"] == "libro"
        assert gen.TIPO_MAPPING["capítulo"] == "capitulo"


class TestCreateRoot:
    """Tests para _create_root."""

    def test_root_tag(self, sample_norma):
        gen = LawXMLGenerator()
        root = gen._create_root(sample_norma)
        assert root.tag == "ley"

    def test_root_attributes(self, sample_norma):
        gen = LawXMLGenerator()
        root = gen._create_root(sample_norma)
        assert root.get("id_norma") == "12345"
        assert root.get("tipo") == "Ley"
        assert root.get("numero") == "21.000"
        assert root.get("estado") == "vigente"

    def test_root_derogada(self, sample_norma):
        sample_norma.derogado = True
        gen = LawXMLGenerator()
        root = gen._create_root(sample_norma)
        assert root.get("estado") == "derogada"


class TestCalculateStats:
    """Tests para _calculate_stats."""

    def test_empty(self):
        gen = LawXMLGenerator()
        stats = gen._calculate_stats([])
        assert stats == {"articulos": 0, "libros": 0, "titulos": 0, "capitulos": 0}

    def test_counts_articles(self, sample_norma):
        gen = LawXMLGenerator()
        stats = gen._calculate_stats(sample_norma.estructuras)
        assert stats["articulos"] == 2
        assert stats["titulos"] == 1

    def test_counts_nested(self):
        gen = LawXMLGenerator()
        estructuras = [
            EstructuraFuncional(
                tipo_parte="Libro",
                nombre_parte="I",
                hijos=[
                    EstructuraFuncional(
                        tipo_parte="Título",
                        nombre_parte="I",
                        hijos=[
                            EstructuraFuncional(
                                tipo_parte="Capítulo",
                                nombre_parte="I",
                                hijos=[
                                    EstructuraFuncional(
                                        tipo_parte="Artículo",
                                        nombre_parte="1",
                                        texto="Texto.",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ]
        stats = gen._calculate_stats(estructuras)
        assert stats["libros"] == 1
        assert stats["titulos"] == 1
        assert stats["capitulos"] == 1
        assert stats["articulos"] == 1


class TestGetDisplayTitle:
    """Tests para _get_display_title."""

    def test_with_titulo_parte(self):
        gen = LawXMLGenerator()
        ef = EstructuraFuncional(
            tipo_parte="Título",
            titulo_parte="TÍTULO I DISPOSICIONES GENERALES",
        )
        assert gen._get_display_title(ef) == "TÍTULO I DISPOSICIONES GENERALES"

    def test_with_nombre_parte(self):
        gen = LawXMLGenerator()
        ef = EstructuraFuncional(tipo_parte="Artículo", nombre_parte="5")
        assert gen._get_display_title(ef) == "Artículo 5"

    def test_fallback(self):
        gen = LawXMLGenerator()
        ef = EstructuraFuncional(tipo_parte="Párrafo")
        assert gen._get_display_title(ef) == "Párrafo"


class TestExtractReferences:
    """Tests para _extract_references."""

    def test_single_reference(self):
        gen = LawXMLGenerator()
        refs = gen._extract_references("Ver artículo 5 de esta ley.")
        assert "5" in refs

    def test_multiple_references(self):
        gen = LawXMLGenerator()
        refs = gen._extract_references("Según el artículo 3 y artículo 7.")
        assert "3" in refs
        assert "7" in refs

    def test_no_references(self):
        gen = LawXMLGenerator()
        refs = gen._extract_references("Texto sin referencias.")
        assert refs == []

    def test_bis_reference(self):
        gen = LawXMLGenerator()
        refs = gen._extract_references("Conforme al artículo 5 bis.")
        assert "5bis" in refs


class TestGetOutputPath:
    """Tests para _get_output_path."""

    def test_with_filename(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen._get_output_path(sample_norma, tmpdir, "mi_ley")
            assert path.name == "mi_ley.xml"

    def test_with_xml_extension(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen._get_output_path(sample_norma, tmpdir, "mi_ley.xml")
            assert path.name == "mi_ley.xml"

    def test_auto_name(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = gen._get_output_path(sample_norma, tmpdir, None)
            assert path.name == "Ley_21.000.xml"


class TestGenerate:
    """Tests para generate (generación completa)."""

    def test_generates_xml_file(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(sample_norma, tmpdir, "test_ley")
            assert result.exists()
            assert result.suffix == ".xml"
            assert result.stat().st_size > 0

    def test_xml_is_valid(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(sample_norma, tmpdir, "test_ley")
            content = result.read_text(encoding="utf-8")
            # Should be valid XML (tag includes namespace)
            root = ET.fromstring(content)
            assert root.tag.endswith("ley")

    def test_xml_has_metadata(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(sample_norma, tmpdir, "test_ley")
            content = result.read_text(encoding="utf-8")
            assert "metadatos" in content
            assert "LEY QUE REGULA ALGO" in content

    def test_xml_has_articles(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(sample_norma, tmpdir, "test_ley")
            content = result.read_text(encoding="utf-8")
            assert "articulo" in content
            assert 'numero="1"' in content
            assert 'numero="2"' in content

    def test_xml_has_encabezado(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(sample_norma, tmpdir, "test_ley")
            content = result.read_text(encoding="utf-8")
            assert "encabezado" in content

    def test_xml_has_promulgacion(self, sample_norma):
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(sample_norma, tmpdir, "test_ley")
            content = result.read_text(encoding="utf-8")
            assert "promulgacion" in content
