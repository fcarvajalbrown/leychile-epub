"""
Tests unitarios para el parser base de documentos SUPERIR.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""


from leychile_epub.superir_base_parser import (
    PATRON_FECHA,
    PATRON_LEY_REF,
    PATRON_PARRAFO,
    PATRON_RESOLUCION_EXENTA,
    SuperirBaseParser,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_DOC = """RESOLUCIÓN EXENTA N.° 6597
MAT.: APRUEBA LA NORMA SOBRE FORMALIDADES
DE LAS PUBLICACIONES
SANTIAGO, 11 AGOSTO 2023

VISTOS:
Lo dispuesto en la Ley N° 20.720, que Sustituye el Régimen Concursal
vigente por una Ley de Reorganización y Liquidación de Activos de
Empresas y Personas, y en la Ley N° 21.563.

CONSIDERANDO:
Que el artículo 331 de la Ley N° 20.720 faculta a esta Superintendencia
para dictar normas de carácter general.

RESUELVO:

TÍTULO I
DISPOSICIONES GENERALES

Artículo 1. Objeto. La presente norma regula las formalidades.

Artículo 2. Ámbito de aplicación. Esta norma se aplica a todos los
procedimientos concursales.

TÍTULO II
REQUISITOS ESPECÍFICOS

Artículo 3. Los interesados deberán presentar la solicitud.

Artículo transitorio. Las disposiciones de esta norma entrarán en vigencia
a contar de su publicación.

II. NOTIFÍQUESE a los interesados.
III. PUBLÍQUESE en el Boletín Concursal.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE PATRONES REGEX
# ═══════════════════════════════════════════════════════════════════════════════


class TestPatterns:
    def test_fecha_with_de(self):
        m = PATRON_FECHA.search("Santiago, 11 de agosto de 2023")
        assert m
        assert m.group(1) == "11"
        assert m.group(2) == "agosto"
        assert m.group(3) == "2023"

    def test_fecha_without_de(self):
        m = PATRON_FECHA.search("SANTIAGO, 04 SEPTIEMBRE 2024")
        assert m
        assert m.group(1) == "04"
        assert m.group(2) == "SEPTIEMBRE"
        assert m.group(3) == "2024"

    def test_resolucion_exenta(self):
        m = PATRON_RESOLUCION_EXENTA.search("RESOLUCIÓN EXENTA N.° 6597")
        assert m
        assert m.group(1) == "6597"

    def test_resolucion_exenta_sin_punto(self):
        m = PATRON_RESOLUCION_EXENTA.search("RESOLUCION EXENTA N° 22802")
        assert m
        assert m.group(1) == "22802"

    def test_ley_ref(self):
        refs = PATRON_LEY_REF.findall("Ley N° 20.720 y Ley N° 21.563")
        assert len(refs) == 2
        assert "20.720" in refs
        assert "21.563" in refs


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DEL PARSER BASE
# ═══════════════════════════════════════════════════════════════════════════════


class TestSuperirBaseParser:
    """Tests para SuperirBaseParser usando el parser directamente."""

    def setup_method(self):
        # Usar el parser base directamente (sin subclase)
        # pero necesitamos un patrón de número
        self.parser = SuperirBaseParser()
        # Override para tests: aceptar cualquier número
        import re

        self.parser.PATRON_NUMERO = re.compile(r"N[.°º]*\s*(\d+)")
        self.parser.TIPO_NORMA = "Test"
        self.parser.ID_PREFIX = "TEST"

    def test_extract_metadata_fecha(self):
        metadata = self.parser._extract_metadata(SAMPLE_DOC)
        assert metadata.fecha_iso == "2023-08-11"
        assert "agosto" in metadata.fecha_texto

    def test_extract_metadata_resolucion(self):
        metadata = self.parser._extract_metadata(SAMPLE_DOC)
        assert metadata.resolucion_exenta == "6597"

    def test_extract_metadata_materia(self):
        metadata = self.parser._extract_metadata(SAMPLE_DOC)
        assert "FORMALIDADES" in metadata.materia.upper()
        assert "PUBLICACIONES" in metadata.materia.upper()

    def test_extract_law_references(self):
        refs = self.parser._extract_law_references(SAMPLE_DOC)
        assert "Ley 20.720" in refs
        assert "Ley 21.563" in refs

    def test_extract_dfl_references(self):
        text_with_dfl = SAMPLE_DOC + "\nD.F.L. N° 1-19.653 de 2001."
        refs = self.parser._extract_law_references(text_with_dfl)
        dfl_refs = [r for r in refs if r.startswith("DFL")]
        assert len(dfl_refs) >= 1

    def test_extract_ds_references(self):
        text_with_ds = SAMPLE_DOC + "\nDecreto Supremo N° 181 de 2022."
        refs = self.parser._extract_law_references(text_with_ds)
        assert "D.S. 181" in refs

    def test_extract_ncg_references(self):
        text_with_ncg = SAMPLE_DOC + "\nNorma de Carácter General N° 14."
        refs = self.parser._extract_law_references(text_with_ncg)
        assert "NCG 14" in refs

    def test_split_sections_vistos(self):
        sections = self.parser._split_sections(SAMPLE_DOC)
        assert "Ley N° 20.720" in sections["vistos"]

    def test_split_sections_considerando(self):
        sections = self.parser._split_sections(SAMPLE_DOC)
        assert "artículo 331" in sections["considerando"]

    def test_split_sections_body(self):
        sections = self.parser._split_sections(SAMPLE_DOC)
        assert "Artículo 1" in sections["body"]

    def test_split_sections_closing(self):
        sections = self.parser._split_sections(SAMPLE_DOC)
        assert "NOTIFÍQUESE" in sections["closing"]

    def test_parse_body_articles(self):
        sections = self.parser._split_sections(SAMPLE_DOC)
        estructuras = self.parser._parse_body(sections["body"])
        n_arts = self.parser._count_articles(estructuras)
        assert n_arts == 4  # 3 regular + 1 transitorio

    def test_parse_body_divisions(self):
        sections = self.parser._split_sections(SAMPLE_DOC)
        estructuras = self.parser._parse_body(sections["body"])
        n_divs = self.parser._count_divisions(estructuras)
        assert n_divs == 2  # 2 títulos

    def test_parse_body_transitorio(self):
        sections = self.parser._split_sections(SAMPLE_DOC)
        estructuras = self.parser._parse_body(sections["body"])
        # Find transitorio article
        transitorios = []
        for e in estructuras:
            for h in e.hijos:
                if h.transitorio:
                    transitorios.append(h)
            if e.transitorio:
                transitorios.append(e)
        assert len(transitorios) == 1
        assert transitorios[0].nombre_parte == "transitorio"

    def test_parse_full(self):
        norma = self.parser.parse(SAMPLE_DOC, url="https://example.com/test.pdf")
        assert norma.norma_id.startswith("TEST-")
        assert norma.identificador.tipo == "Test"
        assert len(norma.estructuras) > 0

    def test_parse_with_catalog(self):
        catalog = {
            "materias": ["Publicaciones", "Formalidades"],
            "nombres_comunes": ["Test NCG"],
            "resolucion_exenta": "6597",
        }
        norma = self.parser.parse(SAMPLE_DOC, catalog_entry=catalog)
        assert "Publicaciones" in norma.metadatos.materias
        assert "Formalidades" in norma.metadatos.materias
        assert "Test NCG" in norma.metadatos.nombres_uso_comun

    def test_capitalize_materia_allcaps(self):
        result = SuperirBaseParser._capitalize_materia("FORMALIDADES DE LAS PUBLICACIONES")
        assert result == "Formalidades de las publicaciones"

    def test_capitalize_materia_mixed(self):
        result = SuperirBaseParser._capitalize_materia("Formalidades de las Publicaciones")
        assert result == "Formalidades de las Publicaciones"

    def test_body_excludes_directives(self):
        sections = self.parser._split_sections(SAMPLE_DOC)
        assert "NOTIFÍQUESE" not in sections["body"]

    def test_encabezado_has_vistos_and_considerando(self):
        norma = self.parser.parse(SAMPLE_DOC)
        assert "VISTOS:" in norma.encabezado_texto
        assert "CONSIDERANDO:" in norma.encabezado_texto

    def test_disposiciones_finales_has_closing(self):
        norma = self.parser.parse(SAMPLE_DOC)
        assert "NOTIFÍQUESE" in norma.disposiciones_finales_texto
        # promulgacion_texto debe estar vacío para SUPERIR
        assert norma.promulgacion_texto == ""

    def test_vistos_texto_separated(self):
        norma = self.parser.parse(SAMPLE_DOC)
        assert norma.vistos_texto
        assert "Ley" in norma.vistos_texto

    def test_considerandos_texto_separated(self):
        norma = self.parser.parse(SAMPLE_DOC)
        assert norma.considerandos_texto
        assert "1°" in norma.considerandos_texto or "Que" in norma.considerandos_texto

    def test_fuente_populated(self):
        norma = self.parser.parse(SAMPLE_DOC)
        assert "Superintendencia" in norma.metadatos.identificacion_fuente

    def test_numero_fuente_populated(self):
        norma = self.parser.parse(SAMPLE_DOC)
        assert norma.metadatos.numero_fuente == "6597"

    def test_leyes_referenciadas_in_norma(self):
        norma = self.parser.parse(SAMPLE_DOC)
        refs = norma.metadatos.leyes_referenciadas
        assert any("20.720" in r for r in refs)
        assert any("21.563" in r for r in refs)

    def test_leyes_referenciadas_has_entries(self):
        norma = self.parser.parse(SAMPLE_DOC)
        refs = norma.metadatos.leyes_referenciadas
        assert len(refs) >= 2  # Al menos Ley 20.720 y 21.563


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE PÁRRAFO DETECTION
# ═══════════════════════════════════════════════════════════════════════════════


class TestParrafoDetection:
    """Tests para la detección de líneas PÁRRAFO como estructura."""

    def test_patron_parrafo_matches(self):
        assert PATRON_PARRAFO.match("Párrafo I Obligaciones generales")
        assert PATRON_PARRAFO.match("PÁRRAFO II Emisión del finiquito")
        assert PATRON_PARRAFO.match("Párrafo III")

    def test_patron_parrafo_no_false_positives(self):
        assert not PATRON_PARRAFO.match("Los párrafos anteriores")
        assert not PATRON_PARRAFO.match("Artículo 1. Párrafo inicial.")

    def test_parrafo_excluded_from_article_content(self):
        """Párrafo headers should NOT appear inside article text."""
        doc = """VISTOS:
Lo dispuesto en la Ley N° 20.720.

CONSIDERANDO:
Que corresponde.

RESUELVO:

Artículo 1. El liquidador deberá cumplir.

Párrafo II Emisión del finiquito

Artículo 2. Se deberá emitir electrónicamente.

ANÓTESE Y ARCHÍVESE.
"""
        import re

        parser = SuperirBaseParser()
        parser.PATRON_NUMERO = re.compile(r"N[.°º]*\s*(\d+)")
        parser.TIPO_NORMA = "Test"
        parser.ID_PREFIX = "TEST"

        norma = parser.parse(doc)

        # Art 1 should NOT contain "Párrafo II"
        art1 = norma.estructuras[0] if norma.estructuras else None
        if art1 and art1.tipo_parte == "Artículo":
            assert "Párrafo" not in (art1.texto or "")

        # Párrafo II is now a structural element (not discarded)
        parrafos = [e for e in norma.estructuras if e.tipo_parte == "Párrafo"]
        assert len(parrafos) == 1
        assert parrafos[0].nombre_parte == "II"

        # Art 2 is a child of Párrafo II
        assert len(parrafos[0].hijos) == 1
        art2 = parrafos[0].hijos[0]
        assert art2.tipo_parte == "Artículo"
        art2_content = (art2.texto or "") + (art2.titulo_parte or "")
        assert "electrónicamente" in art2_content


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE CAPÍTULO/TÍTULO INLINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestInlineReferences:
    """Tests para referencias inline de Capítulo/Título dentro de artículos."""

    def setup_method(self):
        import re

        self.parser = SuperirBaseParser()
        self.parser.PATRON_NUMERO = re.compile(r"N[.°º]*\s*(\d+)")
        self.parser.TIPO_NORMA = "Test"
        self.parser.ID_PREFIX = "TEST"

    def test_capitulo_inline_not_treated_as_structure(self):
        """'Capítulo IV' mid-sentence should stay in article text."""
        doc = """VISTOS:
Lo dispuesto en la Ley N° 20.720.

CONSIDERANDO:
Que corresponde.

RESUELVO:

Artículo 1. El presente será aplicable a los procedimientos contemplados en el
Capítulo IV y los simplificados del Capítulo V de la Ley.

ANÓTESE Y ARCHÍVESE.
"""
        norma = self.parser.parse(doc)
        arts = [e for e in norma.estructuras if e.tipo_parte == "Artículo"]
        assert len(arts) == 1
        assert "Capítulo IV" in (arts[0].texto or "")
        assert "Capítulo V" in (arts[0].texto or "")

    def test_capitulo_as_real_structure(self):
        """Capítulo at sentence start should be a real structural element."""
        doc = """VISTOS:
Lo dispuesto en la Ley N° 20.720.

CONSIDERANDO:
Que corresponde.

RESUELVO:

TÍTULO I
Disposiciones generales

Artículo 1. Texto del artículo uno.

Capítulo I
Normas especiales

Artículo 2. Texto del artículo dos.

ANÓTESE Y ARCHÍVESE.
"""
        norma = self.parser.parse(doc)
        titulo = norma.estructuras[0]
        assert titulo.tipo_parte == "Título"
        # Should have both articles and a capítulo
        capitulos = [h for h in titulo.hijos if h.tipo_parte == "Capítulo"]
        assert len(capitulos) == 1
        assert capitulos[0].nombre_parte == "I"

    def test_unwrap_pdf_inline_capitulo(self):
        """PDF unwrapper should merge 'en el\\nCapítulo IV' into one line."""
        text = "contemplados en el\nCapítulo IV y los simplificados."
        result = SuperirBaseParser._unwrap_pdf_lines(text)
        assert "en el Capítulo IV" in result

    def test_unwrap_pdf_real_capitulo_break(self):
        """PDF unwrapper should keep Capítulo separate after sentence end."""
        text = "Texto del artículo uno.\nCapítulo II\nNormas especiales"
        result = SuperirBaseParser._unwrap_pdf_lines(text)
        # Should have a break before Capítulo
        lines = [line for line in result.split("\n") if line.strip()]
        assert any("Capítulo II" in line for line in lines)
        # First line should end with period, not be merged
        assert lines[0].strip().endswith(".")


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE VIGENCIA EN DIRECTIVAS
# ═══════════════════════════════════════════════════════════════════════════════


class TestVigenciaDirective:
    """Tests para detección de 'II. VIGENCIA' como directiva resolutiva."""

    def setup_method(self):
        import re

        self.parser = SuperirBaseParser()
        self.parser.PATRON_NUMERO = re.compile(r"N[.°º]*\s*(\d+)")
        self.parser.TIPO_NORMA = "Test"
        self.parser.ID_PREFIX = "TEST"

    def test_vigencia_excluded_from_body(self):
        """'II. VIGENCIA' should be in disposiciones_finales, not body."""
        doc = """RESOLUCIÓN EXENTA N.° 16245
MAT.: APRUEBA INSTRUCTIVO
SANTIAGO, 04 NOVIEMBRE 2024

VISTOS:
Las facultades de la Ley N° 20.720.

CONSIDERANDO:
Que corresponde.

RESUELVO:

I. APRUÉBASE el siguiente Instructivo:

Artículo 1. El liquidador deberá cumplir.

II. VIGENCIA. El presente instructivo rige desde su notificación.

III. NOTIFÍQUESE a los liquidadores.

ANÓTESE Y ARCHÍVESE.
"""
        norma = self.parser.parse(doc)

        # Art 1 should NOT contain "VIGENCIA"
        arts = [e for e in norma.estructuras if e.tipo_parte == "Artículo"]
        assert len(arts) == 1
        for art in arts:
            assert "VIGENCIA" not in (art.texto or "")

        # Disposiciones finales should contain VIGENCIA
        assert "VIGENCIA" in norma.disposiciones_finales_texto

    def test_arabic_numeral_directive(self):
        """'2°. NOTIFÍQUESE' (Arabic numeral) should be in disposiciones_finales."""
        doc = """RESOLUCIÓN EXENTA N.° 13139
MAT.: APRUEBA INSTRUCTIVO
SANTIAGO, 05 SEPTIEMBRE 2024

VISTOS:
Las facultades de la Ley N° 20.720.

CONSIDERANDO:
Que corresponde.

RESUELVO:

1° APRUÉBASE el siguiente Instructivo:

Artículo 1. Los sujetos fiscalizados deberán informar.

Artículo 2. Vigencia. El presente Instructivo rige desde su notificación.

2°. NOTIFÍQUESE la presente resolución a los Sujetos Fiscalizados.

3°. PUBLÍQUESE la presente resolución en el Diario Oficial.

ANÓTESE Y ARCHÍVESE.
"""
        norma = self.parser.parse(doc)

        # Art 2 should NOT contain "NOTIFÍQUESE" or "PUBLÍQUESE"
        arts = [e for e in norma.estructuras if e.tipo_parte == "Artículo"]
        assert len(arts) == 2
        art2_text = arts[1].texto or ""
        assert "NOTIFÍQUESE" not in art2_text
        assert "PUBLÍQUESE" not in art2_text

        # Disposiciones finales should contain NOTIFÍQUESE
        assert "NOTIFÍQUESE" in norma.disposiciones_finales_texto
        assert "PUBLÍQUESE" in norma.disposiciones_finales_texto

    def test_dejase_sin_efecto_directive(self):
        """'2°. DÉJASE SIN EFECTO' should be in disposiciones_finales, not in articles."""
        doc = """RESOLUCIÓN EXENTA N.° 12473
MAT.: APRUEBA INSTRUCTIVO
SANTIAGO, 26 AGOSTO 2024

VISTOS:
Las facultades de la Ley N° 20.720.

CONSIDERANDO:
Que corresponde.

RESUELVO:

1° APRUÉBASE el siguiente Instructivo:

Artículo 1. Los veedores deberán observar lo siguiente.

Artículo 2. Vigencia. El presente Instructivo rige desde su notificación.

2°. DÉJASE SIN EFECTO el Oficio Superir N.° 2542 de 6 de junio de 2016.

3°. NOTIFÍQUESE la presente resolución.

4°. PUBLÍQUESE en el Diario Oficial.

ANÓTESE Y ARCHÍVESE.
"""
        norma = self.parser.parse(doc)

        # Art 2 should NOT contain "DÉJASE"
        arts = [e for e in norma.estructuras if e.tipo_parte == "Artículo"]
        assert len(arts) == 2
        art2_text = arts[1].texto or ""
        assert "DÉJASE" not in art2_text

        # Disposiciones finales should contain DÉJASE
        assert "DÉJASE SIN EFECTO" in norma.disposiciones_finales_texto
        assert "NOTIFÍQUESE" in norma.disposiciones_finales_texto


class TestArticleTitleNGrado:
    """Tests para que el regex de título de artículo no rompa en 'N.°'."""

    def setup_method(self):
        import re

        self.parser = SuperirBaseParser()
        self.parser.PATRON_NUMERO = re.compile(r"N[.°º]*\s*(\d+)")
        self.parser.TIPO_NORMA = "Test"
        self.parser.ID_PREFIX = "TEST"

    def test_article_title_not_broken_at_n_grado(self):
        """'Ley N.° 20.720' should not be split into title/content at 'N.'."""
        doc = """RESOLUCIÓN EXENTA N.° 13139
MAT.: APRUEBA INSTRUCTIVO
SANTIAGO, 05 SEPTIEMBRE 2024

VISTOS:
Las facultades de la Ley N° 20.720.

CONSIDERANDO:
Que corresponde.

RESUELVO:

Artículo 8°. En virtud de lo previsto en el artículo 337 de la Ley N.° 20.720, se interpreta la voz notoria insolvencia.

Artículo 9°. En virtud del artículo 337 de la Ley N.° 20.720, se interpreta la voz inhabilidad sobreviniente.

ANÓTESE Y ARCHÍVESE.
"""
        norma = self.parser.parse(doc)

        arts = [e for e in norma.estructuras if e.tipo_parte == "Artículo"]
        assert len(arts) == 2

        # Art 8: title should be just "Artículo 8", not "Artículo 8. ...Ley N"
        assert arts[0].titulo_parte == "Artículo 8"
        # Content should contain "N.° 20.720" intact
        assert "N.° 20.720" in (arts[0].texto or "")

        # Art 9: same
        assert arts[1].titulo_parte == "Artículo 9"
        assert "N.° 20.720" in (arts[1].texto or "")

    def test_short_article_title_still_detected(self):
        """Short titles like 'Responsabilidad.' should still be detected."""
        doc = """RESOLUCIÓN EXENTA N.° 13139
MAT.: APRUEBA INSTRUCTIVO
SANTIAGO, 05 SEPTIEMBRE 2024

VISTOS:
Las facultades de la Ley N° 20.720.

CONSIDERANDO:
Que corresponde.

RESUELVO:

Artículo 13°. Responsabilidad. De conformidad al artículo 338.

Artículo 14°. Vigencia. El presente Instructivo rige desde notificación.

ANÓTESE Y ARCHÍVESE.
"""
        norma = self.parser.parse(doc)

        arts = [e for e in norma.estructuras if e.tipo_parte == "Artículo"]
        assert len(arts) == 2

        # Art 13 should have "Responsabilidad" as part of title
        assert "Responsabilidad" in arts[0].titulo_parte
        # Art 14 should have "Vigencia" as part of title
        assert "Vigencia" in arts[1].titulo_parte
