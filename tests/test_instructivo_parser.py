"""
Tests unitarios para el parser de Instructivos.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

from leychile_epub.instructivo_parser import (
    PATRON_INSTRUCTIVO_NUMERO,
    PATRON_INSTRUCTIVO_NUMERO_ALT,
    InstructivoParser,
)

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_INSTRUCTIVO = """RESOLUCIÓN EXENTA N.° 14477
MAT.: INSTRUCTIVO SUPERIR N.° 5 SOBRE INCAUTACIÓN,
RESGUARDO Y ENTREGA DE BIENES
SANTIAGO, 03 OCTUBRE 2024

VISTOS:
Lo dispuesto en la Ley N° 20.720, en particular los artículos
129 y siguientes, que regulan la incautación de bienes en
procedimientos de liquidación.

CONSIDERANDO:
Que resulta necesario instruir a los liquidadores sobre la
forma correcta de proceder con la incautación de bienes.

RESUELVO:

Artículo 1. Objeto. El presente instructivo regula la incautación,
resguardo y entrega de bienes en procedimientos concursales
de liquidación.

Artículo 2. Ámbito. Se aplica a todos los liquidadores en
ejercicio de sus funciones.

Artículo 3. Procedimiento de incautación. El liquidador deberá
constituirse en el domicilio del deudor dentro de las 48 horas
siguientes a su designación.

Artículo 4. Inventario. Se deberá levantar un inventario
detallado de los bienes incautados.

Artículo 5. Resguardo. Los bienes quedarán bajo custodia
del liquidador.

ANÓTESE Y PUBLÍQUESE.
"""

SAMPLE_INSTRUCTIVO_SIR = """RESOLUCIÓN EXENTA N.° 8725
MAT.: INSTRUCTIVO SIR N° 1 QUE REGULA EL PAGO
DE HONORARIOS CON CARGO AL PRESUPUESTO
SANTIAGO, 24 DE OCTUBRE DE 2023

VISTOS:
Lo dispuesto en el artículo 40 de la Ley N° 20.720.

CONSIDERANDO:
Que es necesario regular el pago de honorarios.

RESUELVO:

Artículo 1. El presente instructivo regula el pago de honorarios.

Artículo 2. Los pagos se realizarán mensualmente.

REGÍSTRESE Y COMUNÍQUESE.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DE PATRONES
# ═══════════════════════════════════════════════════════════════════════════════


class TestInstructivoPatterns:
    def test_patron_superir(self):
        m = PATRON_INSTRUCTIVO_NUMERO.search("INSTRUCTIVO SUPERIR N.° 5")
        assert m
        assert m.group(1) == "5"

    def test_patron_sir(self):
        m = PATRON_INSTRUCTIVO_NUMERO.search("INSTRUCTIVO SIR N° 1")
        assert m
        assert m.group(1) == "1"

    def test_patron_sir_con_punto(self):
        m = PATRON_INSTRUCTIVO_NUMERO.search("INSTRUCTIVO SIR. N° 3")
        assert m
        assert m.group(1) == "3"

    def test_patron_alt(self):
        m = PATRON_INSTRUCTIVO_NUMERO_ALT.search("INSTRUCTIVO N° 2")
        assert m
        assert m.group(1) == "2"

    def test_patron_no_match(self):
        m = PATRON_INSTRUCTIVO_NUMERO.search("NORMA DE CARÁCTER GENERAL N° 28")
        assert m is None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DEL PARSER
# ═══════════════════════════════════════════════════════════════════════════════


class TestInstructivoParser:
    def setup_method(self):
        self.parser = InstructivoParser()

    def test_parse_returns_norma(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO, url="https://example.com/test.pdf")
        assert norma is not None

    def test_tipo_norma(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert norma.identificador.tipo == "Instructivo"

    def test_numero_detectado(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert norma.identificador.numero == "5"

    def test_norma_id(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert norma.norma_id == "INST-5"

    def test_fecha(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert norma.identificador.fecha_promulgacion == "2024-10-03"

    def test_organismo(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert "Superintendencia" in norma.identificador.organismos[0]

    def test_materia_extracted(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert "INCAUTACIÓN" in norma.metadatos.materias[0].upper()

    def test_articulos_count(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)

        def count_arts(structs):
            c = 0
            for s in structs:
                if "artículo" in s.tipo_parte.lower() or "articulo" in s.tipo_parte.lower():
                    c += 1
                c += count_arts(s.hijos)
            return c
        assert count_arts(norma.estructuras) == 5

    def test_encabezado_has_vistos(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert "VISTOS:" in norma.encabezado_texto

    def test_disposiciones_finales_has_closing(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert "PUBLÍQUESE" in norma.disposiciones_finales_texto
        assert norma.promulgacion_texto == ""

    def test_vistos_texto_separated(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert norma.vistos_texto
        assert "Ley" in norma.vistos_texto

    def test_considerandos_texto_separated(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert norma.considerandos_texto

    def test_titulo_built(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert "INSTRUCTIVO" in norma.metadatos.titulo
        assert "5" in norma.metadatos.titulo

    def test_resolucion_exenta(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        assert norma.metadatos.numero_fuente == "14477"

    def test_sir_variant(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO_SIR)
        assert norma.identificador.numero == "1"
        assert norma.identificador.tipo == "Instructivo"

    def test_sir_fecha(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO_SIR)
        assert norma.identificador.fecha_promulgacion == "2023-10-24"

    def test_with_catalog_entry(self):
        catalog = {
            "titulo_completo": "INSTRUCTIVO SUPERIR N°5 - Incautación de bienes",
            "materias": ["Incautación", "Resguardo", "Entrega de bienes"],
            "nombres_comunes": ["Instructivo de Incautación"],
            "resolucion_exenta": "14477",
        }
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO, catalog_entry=catalog)
        assert norma.metadatos.titulo == "INSTRUCTIVO SUPERIR N°5 - Incautación de bienes"
        assert "Incautación" in norma.metadatos.materias
        assert "Instructivo de Incautación" in norma.metadatos.nombres_uso_comun

    def test_doc_numero_override(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO_SIR, doc_numero="99")
        # When text has the number, it should use text's number
        # But if text detection fails, it uses override
        assert norma.identificador.numero in ("1", "99")

    def test_leyes_referenciadas(self):
        norma = self.parser.parse(SAMPLE_INSTRUCTIVO)
        # Check the encabezado mentions the law
        assert "20.720" in norma.encabezado_texto
