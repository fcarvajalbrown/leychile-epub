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

    def test_xml_articles_always_use_contenido(self, sample_norma):
        """Artículos siempre usan <contenido><parrafo> (punto 7 feedback)."""
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(sample_norma, tmpdir, "test_ley_p7")
            content = result.read_text(encoding="utf-8")
            # Incluso artículo simple debería tener <contenido><parrafo>
            assert "<contenido>" in content
            assert "<parrafo>" in content
            # No debería haber <texto> dentro de artículos
            root = ET.fromstring(content)
            ns = {"ley": "https://leychile.cl/schema/ley/v1"}
            for art in root.findall(".//ley:articulo", ns):
                assert art.find("ley:contenido", ns) is not None

    def test_xml_encabezado_texto_for_bcn(self, sample_norma):
        """BCN law uses <encabezado><texto>."""
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(sample_norma, tmpdir, "test_enc_bcn")
            content = result.read_text(encoding="utf-8")
            root = ET.fromstring(content)
            ns = {"ley": "https://leychile.cl/schema/ley/v1"}
            enc = root.find("ley:encabezado", ns)
            assert enc is not None
            assert enc.find("ley:texto", ns) is not None
            assert enc.find("ley:vistos", ns) is None


class TestSuperirXMLGeneration:
    """Tests para generación XML de normas SUPERIR (NCG/Instructivos)."""

    @pytest.fixture
    def superir_norma(self):
        """Crea una Norma SUPERIR de ejemplo."""
        return Norma(
            norma_id="NCG-7",
            es_tratado=False,
            fecha_version="2014-10-08",
            schema_version="1.0",
            derogado=False,
            identificador=NormaIdentificador(
                tipo="Norma de Carácter General",
                numero="7",
                organismos=["Superintendencia de Insolvencia y Reemprendimiento"],
                fecha_promulgacion="2014-10-08",
                fecha_publicacion="2014-10-08",
            ),
            metadatos=NormaMetadatos(
                titulo="NCG N°7 - Cuentas de Administración",
                materias=["Cuentas provisorias", "Liquidación"],
                conceptos=["Liquidadores", "Veedores"],
                leyes_referenciadas=["Ley 20.720", "NCG 3", "DFL 1-19.653"],
            ),
            encabezado_texto="VISTOS:\n\nLas facultades...\n\nCONSIDERANDO:\n\n1° Que...",
            vistos_texto="Las facultades conferidas en los artículos 46° y 49°.",
            considerandos_texto="1° Que el artículo 46° de la Ley dispone...",
            estructuras=[
                EstructuraFuncional(
                    id_parte="1",
                    tipo_parte="Artículo",
                    texto="Las cuentas provisorias deberán rendirse mensualmente.",
                    nombre_parte="1",
                    titulo_parte="Artículo 1. Oportunidad",
                    nivel=1,
                ),
            ],
            promulgacion_texto="",
            disposiciones_finales_texto="NOTIFÍQUESE Y PUBLÍQUESE.\n\nHUGO SÁNCHEZ",
        )

    def test_encabezado_structured(self, superir_norma):
        """SUPERIR genera <encabezado> con <vistos> y <considerandos> separados."""
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(superir_norma, tmpdir, "test_superir_enc")
            content = result.read_text(encoding="utf-8")
            root = ET.fromstring(content)
            ns = {"ley": "https://leychile.cl/schema/ley/v1"}
            enc = root.find("ley:encabezado", ns)
            assert enc is not None
            assert enc.find("ley:vistos", ns) is not None
            assert enc.find("ley:considerandos", ns) is not None
            assert enc.find("ley:texto", ns) is None
            assert "46°" in enc.find("ley:vistos", ns).text

    def test_disposiciones_finales_instead_of_promulgacion(self, superir_norma):
        """SUPERIR usa <disposiciones_finales> en vez de <promulgacion>."""
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(superir_norma, tmpdir, "test_superir_disp")
            content = result.read_text(encoding="utf-8")
            root = ET.fromstring(content)
            ns = {"ley": "https://leychile.cl/schema/ley/v1"}
            disp = root.find("ley:disposiciones_finales", ns)
            assert disp is not None
            prom = root.find("ley:promulgacion", ns)
            assert prom is None

    def test_conceptos_in_metadata(self, superir_norma):
        """Conceptos separados de materias en metadatos."""
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(superir_norma, tmpdir, "test_superir_con")
            content = result.read_text(encoding="utf-8")
            root = ET.fromstring(content)
            ns = {"ley": "https://leychile.cl/schema/ley/v1"}
            meta = root.find("ley:metadatos", ns)
            conceptos = meta.find("ley:conceptos", ns)
            assert conceptos is not None
            items = [c.text for c in conceptos.findall("ley:concepto", ns)]
            assert "Liquidadores" in items
            assert "Veedores" in items

    def test_ley_ref_structured(self, superir_norma):
        """Leyes referenciadas tienen atributos tipo y numero."""
        gen = LawXMLGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = gen.generate(superir_norma, tmpdir, "test_superir_ref")
            content = result.read_text(encoding="utf-8")
            root = ET.fromstring(content)
            ns = {"ley": "https://leychile.cl/schema/ley/v1"}
            refs = root.findall(".//ley:ley_ref", ns)
            assert len(refs) == 3
            # Ley 20.720 should have tipo and numero
            ley = refs[0]
            assert ley.get("tipo") == "Ley"
            assert ley.get("numero") == "20.720"
            # NCG 3
            ncg = refs[1]
            assert ncg.get("tipo") == "NCG"
            assert ncg.get("numero") == "3"

    def test_parse_ley_ref_patterns(self):
        """_parse_ley_ref parsea correctamente distintos tipos."""
        result = LawXMLGenerator._parse_ley_ref("Ley 20.720")
        assert result == ("Ley", "20.720")
        result = LawXMLGenerator._parse_ley_ref("DFL 1-19.653")
        assert result == ("DFL", "1-19.653")
        result = LawXMLGenerator._parse_ley_ref("NCG 7")
        assert result == ("NCG", "7")
        result = LawXMLGenerator._parse_ley_ref("D.S. 8")
        assert result == ("D.S.", "8")
        result = LawXMLGenerator._parse_ley_ref("Otro texto")
        assert result is None

    def test_version_is_1_1(self, superir_norma):
        """Schema version actualizada a 1.1."""
        gen = LawXMLGenerator()
        root = gen._create_root(superir_norma)
        assert root.get("version") == "1.1"
