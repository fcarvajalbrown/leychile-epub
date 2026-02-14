"""
Tests unitarios para el parser de NCG.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import pytest

from leychile_epub.ncg_parser import (
    NCGParser,
    extract_ncg_number_from_url,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_NCG_TEXT = """RESOLUCIÓN EXENTA N.° 6597
MAT.: APRUEBA LA NORMA DE CARÁCTER GENERAL N.° 14
SOBRE FORMALIDADES DE LAS PUBLICACIONES
SANTIAGO, 11 AGOSTO 2023
VISTOS:
Las facultades que me confiere la Ley N.° 20.720.
CONSIDERANDO:
1° Que la Superintendencia tiene atribuciones.
2° Que es necesario regular.
RESUELVO:
I. APRUÉBESE la siguiente Norma de Carácter General:
NORMA DE CARÁCTER GENERAL N.° 14
TÍTULO I
DISPOSICIONES GENERALES
Artículo 1. Objeto. La presente norma tiene por objeto regular las publicaciones.
Artículo 2. Ámbito de aplicación. Esta norma se aplica a todos los
procedimientos concursales vigentes en el territorio nacional.
TÍTULO II
ASPECTOS GENERALES
Artículo 3. Definiciones. Para los efectos de esta norma se entenderá por:
a) Boletín Concursal: medio electrónico de publicación.
b) Publicación: acto de difusión de información.
Artículo 4. Plazo. Las publicaciones deberán efectuarse dentro del plazo
de 5 días hábiles contados desde el artículo 6 de esta ley.
II. NOTIFÍQUESE la presente resolución.
III. PUBLÍQUESE en el Diario Oficial.
ANÓTESE, COMUNÍQUESE Y PUBLÍQUESE.
HUGO SÁNCHEZ
SUPERINTENDENTE
"""

SAMPLE_NCG_SIMPLE = """SUPERINTENDENCIA DE INSOLVENCIA Y REEMPRENDIMIENTO
NCG N°25
Santiago, 13 de octubre de 2023
MAT.: APRUEBA NORMA SOBRE USO DE PLATAFORMA
VISTOS:
Lo dispuesto en la Ley N.° 20.720.
CONSIDERANDO:
1° Que es necesario regular el uso de la plataforma.
RESUELVO:
Artículo 1. La plataforma se utilizará para todo trámite.
Artículo 2. Los usuarios deberán registrarse previamente.
ANÓTESE Y ARCHÍVESE.
"""

SAMPLE_NCG_NO_RESUELVO = """SUPERINTENDENCIA DE INSOLVENCIA Y REEMPRENDIMIENTO
NCG N°10
Santiago, 31 de diciembre de 2019
REF.: Modifica NCG N°1 sobre garantía
VISTO:
Las facultades legales.
CONSIDERANDO:
Que es necesario modificar.
Artículo 1. Modificación. Se modifica el artículo 3.
Artículo 2. Vigencia. Rige desde su publicación.
ANÓTESE.
"""


@pytest.fixture
def parser():
    return NCGParser()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: extract_ncg_number_from_url
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractNCGNumber:
    def test_standard_url(self):
        url = "https://www.superir.gob.cl/wp-content/uploads/2025/12/NCG-N°28.pdf"
        assert extract_ncg_number_from_url(url) == "28"

    def test_url_with_underscore(self):
        url = "https://example.com/NCG_N7_Contenidos.pdf"
        assert extract_ncg_number_from_url(url) == "7"

    def test_url_without_ncg(self):
        url = "https://example.com/RES_NUM_6597_ANO_2023.pdf"
        assert extract_ncg_number_from_url(url) == ""

    def test_url_with_encoded_chars(self):
        url = "https://example.com/NORMA-N%C2%B010.pdf"
        # After URL decoding this becomes NORMA-N°10
        assert extract_ncg_number_from_url(url) == ""  # %C2%B0 not decoded


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: NCGParser._extract_metadata
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractMetadata:
    def test_ncg_number(self, parser):
        meta = parser._extract_metadata(SAMPLE_NCG_TEXT)
        assert meta.numero == "14"

    def test_ncg_number_simple(self, parser):
        meta = parser._extract_metadata(SAMPLE_NCG_SIMPLE)
        assert meta.numero == "25"

    def test_date_with_de(self, parser):
        meta = parser._extract_metadata(SAMPLE_NCG_SIMPLE)
        assert meta.fecha_iso == "2023-10-13"

    def test_date_without_de(self, parser):
        meta = parser._extract_metadata(SAMPLE_NCG_TEXT)
        assert meta.fecha_iso == "2023-08-11"

    def test_materia_multiline(self, parser):
        meta = parser._extract_metadata(SAMPLE_NCG_TEXT)
        assert "APRUEBA LA NORMA DE CARÁCTER GENERAL" in meta.materia
        assert "FORMALIDADES" in meta.materia

    def test_referencia_as_materia(self, parser):
        meta = parser._extract_metadata(SAMPLE_NCG_NO_RESUELVO)
        assert "Modifica NCG" in meta.materia

    def test_no_metadata(self, parser):
        meta = parser._extract_metadata("Texto sin metadatos legales.")
        assert meta.numero == ""
        assert meta.fecha_iso == ""
        assert meta.materia == ""


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: NCGParser._split_sections
# ═══════════════════════════════════════════════════════════════════════════════


class TestSplitSections:
    def test_all_sections_present(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        assert sections["vistos"]
        assert sections["considerando"]
        assert sections["body"]
        assert sections["closing"]

    def test_vistos_content(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        assert "Ley N.° 20.720" in sections["vistos"]

    def test_considerando_content(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        assert "atribuciones" in sections["considerando"]

    def test_body_has_articles(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        assert "Artículo 1" in sections["body"]
        assert "Artículo 4" in sections["body"]

    def test_closing_has_directive(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        assert "NOTIFÍQUESE" in sections["closing"]

    def test_body_excludes_directives(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        assert "II. NOTIFÍQUESE" not in sections["body"]

    def test_no_resuelvo(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_NO_RESUELVO)
        assert sections["body"]
        assert "Artículo 1" in sections["body"]

    def test_visto_singular(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_NO_RESUELVO)
        assert sections["vistos"]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: NCGParser._parse_body
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseBody:
    def test_article_count(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        estructuras = parser._parse_body(sections["body"])
        total = parser._count_articles(estructuras)
        assert total == 4

    def test_division_count(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        estructuras = parser._parse_body(sections["body"])
        total = parser._count_divisions(estructuras)
        assert total == 2  # TÍTULO I y TÍTULO II

    def test_titulo_hierarchy(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        estructuras = parser._parse_body(sections["body"])
        # Los dos primeros elementos deben ser Títulos
        assert estructuras[0].tipo_parte == "Título"
        assert estructuras[1].tipo_parte == "Título"

    def test_articles_under_titulos(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        estructuras = parser._parse_body(sections["body"])
        titulo1 = estructuras[0]
        assert len(titulo1.hijos) == 2  # Art 1 y 2
        assert titulo1.hijos[0].tipo_parte == "Artículo"

    def test_article_text(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        estructuras = parser._parse_body(sections["body"])
        art1 = estructuras[0].hijos[0]
        assert "regular las publicaciones" in art1.texto

    def test_article_references(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_TEXT)
        estructuras = parser._parse_body(sections["body"])
        # Artículo 4 menciona "artículo 6"
        titulo2 = estructuras[1]
        art4 = titulo2.hijos[1]  # Art 4 bajo Título II
        assert "artículo 6" in art4.texto

    def test_flat_structure(self, parser):
        sections = parser._split_sections(SAMPLE_NCG_SIMPLE)
        estructuras = parser._parse_body(sections["body"])
        # Sin títulos, artículos directos
        assert len(estructuras) == 2
        assert estructuras[0].tipo_parte == "Artículo"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS: NCGParser.parse (integración)
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseIntegration:
    def test_returns_norma(self, parser):
        norma = parser.parse(SAMPLE_NCG_TEXT)
        assert norma is not None
        assert norma.norma_id == "NCG-14"

    def test_norma_tipo(self, parser):
        norma = parser.parse(SAMPLE_NCG_TEXT)
        assert norma.identificador.tipo == "Norma de Carácter General"

    def test_norma_organismo(self, parser):
        norma = parser.parse(SAMPLE_NCG_TEXT)
        assert "Superintendencia" in norma.identificador.organismos[0]

    def test_norma_fecha(self, parser):
        norma = parser.parse(SAMPLE_NCG_TEXT)
        assert norma.fecha_version == "2023-08-11"
        assert norma.identificador.fecha_promulgacion == "2023-08-11"

    def test_norma_encabezado(self, parser):
        norma = parser.parse(SAMPLE_NCG_TEXT)
        assert "VISTOS:" in norma.encabezado_texto
        assert "CONSIDERANDO:" in norma.encabezado_texto

    def test_norma_estructuras(self, parser):
        norma = parser.parse(SAMPLE_NCG_TEXT)
        assert len(norma.estructuras) > 0

    def test_norma_disposiciones_finales(self, parser):
        norma = parser.parse(SAMPLE_NCG_TEXT)
        assert norma.disposiciones_finales_texto
        assert norma.promulgacion_texto == ""

    def test_override_ncg_numero(self, parser):
        norma = parser.parse("Texto sin metadata.", ncg_numero="99")
        assert norma.norma_id == "NCG-99"

    def test_article_titles_extracted(self, parser):
        norma = parser.parse(SAMPLE_NCG_TEXT)
        art1 = norma.estructuras[0].hijos[0]
        assert "Objeto" in art1.titulo_parte

    def test_simple_ncg(self, parser):
        norma = parser.parse(SAMPLE_NCG_SIMPLE)
        assert norma.norma_id == "NCG-25"
        assert norma.fecha_version == "2023-10-13"
        assert len(norma.estructuras) == 2

    def test_no_resuelvo_ncg(self, parser):
        norma = parser.parse(SAMPLE_NCG_NO_RESUELVO, ncg_numero="10")
        assert norma.norma_id == "NCG-10"
        assert len(norma.estructuras) >= 2
