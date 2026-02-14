"""Tests para SuperirStructuredParser.

Valida extracción de:
- Considerandos individuales numerados
- Epígrafes de artículos
- Listados letrados
- Requisitos numerados (I, II, III...) con sub-items letrados
- Anexos standalone
- Cierre (fórmula + firmante)
"""

import unittest

from leychile_epub.superir_models import (
    AnexoStandalone,
    CierreSuperir,
    ConsiderandoItem,
    ContenidoArticulo,
    Firmante,
    ItemListado,
    NormaSuperir,
    RequisitoItemModel,
    RequisitoModel,
)
from leychile_epub.superir_structured_parser import SuperirStructuredParser


class TestParseConsiderandos(unittest.TestCase):
    """Tests para parse_considerandos()."""

    def test_two_considerandos_ncg4(self):
        """NCG 4: 2 considerandos."""
        texto = (
            "1° Que el artículo 54° de la Ley ordena que un modelo de solicitud "
            "de inicio del Procedimiento Concursal de Reorganización se encuentre "
            "disponible en las dependencias de la Superintendencia.\n\n"
            "2° Que, en conformidad a lo anterior, esta Superintendencia dicta la siguiente:"
        )
        items = SuperirStructuredParser.parse_considerandos(texto)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].numero, 1)
        self.assertIn("artículo 54°", items[0].texto)
        self.assertEqual(items[1].numero, 2)
        self.assertIn("conformidad a lo anterior", items[1].texto)

    def test_four_considerandos_ncg6(self):
        """NCG 6: 4 considerandos."""
        texto = (
            "1° Que, el artículo 75° de la Ley dispone que en caso que no se acuerde "
            "la reorganización y se declare la liquidación de la Empresa Deudora.\n\n"
            "2° Que, es de la esencia de la disposición en comento, que la garantía "
            "sea de aquellas de fácil realización.\n\n"
            "3° Que, el mencionado artículo 75° se refiere al otorgamiento de cualquier "
            "instrumento de garantía.\n\n"
            "4° Que, en conformidad a lo anterior, esta Superintendencia dicta la siguiente:"
        )
        items = SuperirStructuredParser.parse_considerandos(texto)
        self.assertEqual(len(items), 4)
        self.assertEqual(items[0].numero, 1)
        self.assertEqual(items[3].numero, 4)

    def test_empty_text(self):
        """Texto vacío retorna lista vacía."""
        self.assertEqual(SuperirStructuredParser.parse_considerandos(""), [])

    def test_no_numbered_considerandos(self):
        """Texto sin numeración retorna un solo considerando."""
        texto = "Que corresponde dictar instrucciones al respecto."
        items = SuperirStructuredParser.parse_considerandos(texto)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].numero, 1)
        self.assertIn("corresponde", items[0].texto)

    def test_considerando_con_punto_degree(self):
        """Considerandos con formato '1.° Que,'."""
        texto = (
            "1.° Que, corresponde regular la materia.\n\n"
            "2.° Que, en uso de las facultades legales."
        )
        items = SuperirStructuredParser.parse_considerandos(texto)
        self.assertEqual(len(items), 2)

    def test_considerando_preserves_que_prefix(self):
        """El texto del considerando preserva 'Que,' al inicio."""
        texto = "1° Que, la Ley N.° 20.720 establece las facultades."
        items = SuperirStructuredParser.parse_considerandos(texto)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].texto.startswith("Que,"))


class TestExtractEpigrafes(unittest.TestCase):
    """Tests para _extract_epigrafes()."""

    def test_basic_epigrafes(self):
        """Extrae epígrafes de artículos."""
        from leychile_epub.scraper_v2 import EstructuraFuncional

        estructuras = [
            EstructuraFuncional(
                tipo_parte="Título",
                nombre_parte="I",
                titulo_parte="TÍTULO I",
                hijos=[
                    EstructuraFuncional(
                        tipo_parte="Artículo",
                        nombre_parte="1",
                        titulo_parte="Artículo 1. Modelo",
                        texto="En formato anexo...",
                    ),
                ],
            ),
            EstructuraFuncional(
                tipo_parte="Título",
                nombre_parte="II",
                titulo_parte="TÍTULO II Disposiciones Finales",
                hijos=[
                    EstructuraFuncional(
                        tipo_parte="Artículo",
                        nombre_parte="2",
                        titulo_parte="Artículo 2. Ámbito de aplicación",
                        texto="La presente Norma...",
                    ),
                    EstructuraFuncional(
                        tipo_parte="Artículo",
                        nombre_parte="3",
                        titulo_parte="Artículo 3",
                        texto="Sin epígrafe.",
                    ),
                ],
            ),
        ]

        epigrafes = SuperirStructuredParser._extract_epigrafes(estructuras)
        self.assertEqual(epigrafes["1"], "Modelo")
        self.assertEqual(epigrafes["2"], "Ámbito de aplicación")
        self.assertNotIn("3", epigrafes)  # Sin epígrafe

    def test_epigrafe_con_punto_degree(self):
        """Epígrafe con N.° no se trunca."""
        from leychile_epub.scraper_v2 import EstructuraFuncional

        estructuras = [
            EstructuraFuncional(
                tipo_parte="Artículo",
                nombre_parte="1",
                titulo_parte="Artículo 1. Objeto de la N.° 20.720",
                texto="El objeto...",
            ),
        ]
        epigrafes = SuperirStructuredParser._extract_epigrafes(estructuras)
        self.assertIn("1", epigrafes)


class TestParseListado(unittest.TestCase):
    """Tests para parsing de listados letrados."""

    def test_listado_letrado_ncg6(self):
        """NCG 6: listado con items a) y b)."""
        texto = (
            "Para los efectos del artículo 75° de la Ley se entenderán como "
            "instrumentos de garantía suficientes:\n"
            "a) Vale vista o boleta bancaria, extendida en forma irrevocable.\n"
            "b) Póliza de seguro de caución, en los términos del artículo 582°."
        )
        contenido = SuperirStructuredParser._parse_articulo_contenido(texto)
        self.assertEqual(len(contenido.parrafos), 1)
        self.assertIn("instrumentos de garantía", contenido.parrafos[0])
        self.assertEqual(len(contenido.listado), 2)
        self.assertEqual(contenido.listado[0].letra, "a")
        self.assertIn("boleta bancaria", contenido.listado[0].texto)
        self.assertEqual(contenido.listado[1].letra, "b")
        self.assertIn("Póliza de seguro", contenido.listado[1].texto)

    def test_sin_listado(self):
        """Artículo sin listado: solo párrafos."""
        texto = "La presente Norma solo tiene por objeto regular las materias."
        contenido = SuperirStructuredParser._parse_articulo_contenido(texto)
        self.assertEqual(len(contenido.parrafos), 1)
        self.assertEqual(len(contenido.listado), 0)

    def test_texto_vacio(self):
        """Texto vacío."""
        contenido = SuperirStructuredParser._parse_articulo_contenido("")
        self.assertEqual(len(contenido.parrafos), 0)
        self.assertEqual(len(contenido.listado), 0)


class TestParseCierre(unittest.TestCase):
    """Tests para parse_cierre()."""

    def test_cierre_ncg4(self):
        """NCG 4: fórmula + firmante Montenegro."""
        texto = (
            "Anótese y publíquese.\n\n"
            "JOSEFINA MONTENEGRO ARANEDA\n"
            "Superintendenta de Insolvencia y Reemprendimiento"
        )
        cierre = SuperirStructuredParser.parse_cierre(texto)
        self.assertIsNotNone(cierre)
        self.assertEqual(cierre.formula, "Anótese y publíquese.")
        self.assertIsNotNone(cierre.firmante)
        self.assertEqual(cierre.firmante.nombre, "JOSEFINA MONTENEGRO ARANEDA")
        self.assertIn("SUPERINTENDENTA", cierre.firmante.cargo)

    def test_cierre_con_directivas(self):
        """Cierre que incluye NOTIFÍQUESE antes de la fórmula."""
        texto = (
            "1°. NOTIFÍQUESE la presente resolución.\n"
            "2°. PUBLÍQUESE en el Diario Oficial.\n\n"
            "ANÓTESE Y ARCHÍVESE,\n\n"
            "HUGO SÁNCHEZ RAMÍREZ\n"
            "SUPERINTENDENTE DE INSOLVENCIA Y REEMPRENDIMIENTO"
        )
        cierre = SuperirStructuredParser.parse_cierre(texto)
        self.assertIsNotNone(cierre)
        self.assertIn("ANÓTESE", cierre.formula)
        self.assertIsNotNone(cierre.firmante)
        self.assertEqual(cierre.firmante.nombre, "HUGO SÁNCHEZ RAMÍREZ")

    def test_cierre_vacio(self):
        """Texto vacío retorna None."""
        self.assertIsNone(SuperirStructuredParser.parse_cierre(""))

    def test_cierre_sin_firmante(self):
        """Fórmula sin firmante identificable."""
        texto = "Anótese y publíquese."
        cierre = SuperirStructuredParser.parse_cierre(texto)
        self.assertIsNotNone(cierre)
        self.assertEqual(cierre.formula, "Anótese y publíquese.")
        self.assertIsNone(cierre.firmante)


class TestFullParseNCG4(unittest.TestCase):
    """Test de integración: parse completo de NCG 4."""

    NCG4_TEXTO = """REPÚBLICA DE CHILE
Ministerio de Economía, Fomento y Turismo
Superintendencia de Insolvencia y Reemprendimiento

NORMA DE CARÁCTER GENERAL N.° 4
SUPERINTENDENCIA DE INSOLVENCIA Y REEMPRENDIMIENTO

REF.: Modelo de solicitud de inicio de Procedimiento Concursal de Reorganización.

Santiago, 5 de septiembre de 2014

VISTOS

Las facultades conferidas en el artículo 54° de la Ley N.° 20.720, sobre Reorganización y Liquidación de Activos de Empresas y Personas (en adelante, la "Ley").

CONSIDERANDO

1° Que el artículo 54° de la Ley ordena que un modelo de solicitud de inicio del Procedimiento Concursal de Reorganización se encuentre disponible en las dependencias de la Superintendencia de Insolvencia y Reemprendimiento, en su sitio web y en las dependencias de los tribunales con competencia en Procedimientos Concursales, disponiendo adicionalmente que dicho modelo será regulado por medio de la dictación de una Norma de Carácter General por parte de esta Superintendencia.

2° Que, en conformidad a lo anterior, esta Superintendencia de Insolvencia y Reemprendimiento (en adelante, la "Superintendencia") dicta la siguiente:

NORMA DE CARÁCTER GENERAL

TÍTULO I
Modelo de Solicitud de Inicio del Procedimiento Concursal de Reorganización

Artículo 1°. Modelo.
En formato anexo a la presente Norma de Carácter General, se dispone un modelo de solicitud de inicio del Procedimiento Concursal de Reorganización.

TÍTULO II
Disposiciones Finales

Artículo 2°. Ámbito de aplicación.
La presente Norma de Carácter General solo tiene por objeto regular las materias que en la misma se tratan para los Procedimientos Concursales de Reorganización regulados en la Ley.

Artículo 3°. Términos definidos.
Los términos en mayúscula utilizados en esta Norma de Carácter General tendrán el mismo significado que a ellos se les asigna en el artículo 2° de la Ley.

Artículo 4°. Vigencia.
La presente Norma de Carácter General se dicta en mérito de los principios de continuidad de la función pública, de eficiencia y eficacia consagrados en los artículos 3°, 5° y 8° de la Ley N.° 18.575.

Anótese y publíquese.

JOSEFINA MONTENEGRO ARANEDA
Superintendenta de Insolvencia y Reemprendimiento
"""

    def test_full_parse_produces_norma_superir(self):
        """Parse completo produce NormaSuperir válida."""
        parser = SuperirStructuredParser()
        norma = parser.parse(self.NCG4_TEXTO)

        # Tipo correcto
        self.assertIsInstance(norma, NormaSuperir)
        self.assertIsNotNone(norma.norma_base)

        # 1 considerando (el 2° era la fórmula de dictación, se extrae)
        self.assertEqual(len(norma.considerandos), 1)
        self.assertEqual(norma.considerandos[0].numero, 1)

        # Fórmula de dictación extraída del último "considerando"
        self.assertTrue(norma.formula_dictacion)
        self.assertIn("conformidad", norma.formula_dictacion.lower())

        # Epígrafes
        self.assertEqual(norma.articulos_epigrafe.get("1"), "Modelo")
        self.assertEqual(norma.articulos_epigrafe.get("2"), "Ámbito de aplicación")
        self.assertEqual(norma.articulos_epigrafe.get("3"), "Términos definidos")
        self.assertEqual(norma.articulos_epigrafe.get("4"), "Vigencia")

        # Cierre
        self.assertIsNotNone(norma.cierre)
        self.assertIn("publíquese", norma.cierre.formula.lower())
        self.assertIsNotNone(norma.cierre.firmante)
        self.assertEqual(norma.cierre.firmante.nombre, "JOSEFINA MONTENEGRO ARANEDA")

    def test_norma_base_compatible(self):
        """La Norma base tiene datos correctos."""
        parser = SuperirStructuredParser()
        norma = parser.parse(self.NCG4_TEXTO)
        base = norma.norma_base

        self.assertEqual(base.identificador.tipo, "Norma de Carácter General")
        self.assertEqual(base.identificador.numero, "4")
        self.assertIn("Ley 20.720", base.metadatos.leyes_referenciadas)

        # Artículos en estructura
        arts = []
        for e in base.estructuras:
            for h in e.hijos:
                if h.tipo_parte == "Artículo":
                    arts.append(h)
        self.assertEqual(len(arts), 4)


class TestParseRequisitos(unittest.TestCase):
    """Tests para parsing de requisitos (I.-, II.-, etc.)."""

    def test_requisitos_inline_detected(self):
        """Requisitos con doble espacio como separador (texto colapsado)."""
        contenido = SuperirStructuredParser._parse_articulo_contenido(
            "Cumpliendo además con los siguientes requisitos:  "
            "I.- Tener una carátula.  "
            "II.- Contener el detalle de los ingresos:  "
            "a) Ingresos totales.  "
            "b) Egresos totales.  "
            "III.- Incluir un balance general."
        )
        self.assertEqual(len(contenido.requisitos), 3)
        self.assertEqual(contenido.requisitos[0].numero, "I")
        self.assertEqual(contenido.requisitos[1].numero, "II")
        self.assertEqual(contenido.requisitos[2].numero, "III")

    def test_requisito_with_subitems(self):
        """Requisito II debe tener items letrados a), b)."""
        contenido = SuperirStructuredParser._parse_articulo_contenido(
            "Requisitos:  "
            "I.- Tener algo.  "
            "II.- Detalle:  a) Primer item.  b) Segundo item.  "
            "III.- Balance."
        )
        req_ii = contenido.requisitos[1]
        self.assertEqual(req_ii.numero, "II")
        self.assertEqual(len(req_ii.items), 2)
        self.assertEqual(req_ii.items[0].letra, "a")
        self.assertEqual(req_ii.items[1].letra, "b")

    def test_requisito_intro_parrafos(self):
        """Texto antes del primer requisito es párrafo de intro."""
        contenido = SuperirStructuredParser._parse_articulo_contenido(
            "Las cuentas se confeccionarán cumpliendo:  "
            "I.- Carátula.  II.- Detalle."
        )
        self.assertTrue(len(contenido.parrafos) >= 1)
        self.assertIn("confeccionarán", contenido.parrafos[0])

    def test_requisito_without_subitems(self):
        """Requisito simple sin items letrados tiene solo párrafos."""
        contenido = SuperirStructuredParser._parse_articulo_contenido(
            "Intro:  I.- Requisito simple sin sub-items."
        )
        self.assertEqual(len(contenido.requisitos), 1)
        self.assertEqual(len(contenido.requisitos[0].items), 0)
        self.assertTrue(len(contenido.requisitos[0].parrafos) >= 1)

    def test_no_listado_when_requisitos_present(self):
        """Cuando hay requisitos, los items a) b) no generan listado separado."""
        contenido = SuperirStructuredParser._parse_articulo_contenido(
            "Intro:  I.- Primer req:  a) Item A.  b) Item B.  II.- Segundo."
        )
        self.assertEqual(len(contenido.listado), 0)
        self.assertEqual(len(contenido.requisitos), 2)

    def test_requisito_item_with_nombre(self):
        """Items letrados con nombre: 'a) Ingresos: detalle...'."""
        from leychile_epub.superir_structured_parser import _parse_requisito_item

        item = _parse_requisito_item("a", "Ingresos: Deberá detallarse cada cuenta.")
        self.assertEqual(item.letra, "a")
        self.assertEqual(item.nombre, "Ingresos")
        self.assertIn("Deberá", item.texto)


class TestParseNCG7Requisitos(unittest.TestCase):
    """Tests de integración con texto real de NCG 7, Art 7."""

    def test_ncg7_art7_five_requisitos(self):
        """NCG 7, Art 7: 5 requisitos (I-V) detectados desde texto real."""
        from pathlib import Path

        texto_path = Path("biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_7.txt")
        if not texto_path.exists():
            self.skipTest("Texto NCG 7 no disponible")

        parser = SuperirStructuredParser()
        texto = texto_path.read_text(encoding="utf-8")
        norma = parser.parse(texto)

        # Art 7 debe tener contenido estructurado con requisitos
        self.assertIn("7", norma.articulos_contenido)
        contenido = norma.articulos_contenido["7"]
        self.assertEqual(len(contenido.requisitos), 5)

        # Requisito I
        self.assertEqual(contenido.requisitos[0].numero, "I")
        # Requisito II con items a)-e)
        req_ii = contenido.requisitos[1]
        self.assertEqual(req_ii.numero, "II")
        self.assertTrue(len(req_ii.items) >= 4)
        # Requisito V
        self.assertEqual(contenido.requisitos[4].numero, "V")

    def test_ncg7_standalone_anexos(self):
        """NCG 7: 4 anexos standalone detectados."""
        from pathlib import Path

        texto_path = Path("biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_7.txt")
        if not texto_path.exists():
            self.skipTest("Texto NCG 7 no disponible")

        parser = SuperirStructuredParser()
        texto = texto_path.read_text(encoding="utf-8")
        norma = parser.parse(texto)

        self.assertEqual(len(norma.anexos_standalone), 4)
        numeros = [a.numero for a in norma.anexos_standalone]
        self.assertIn("I", numeros)
        self.assertIn("IV", numeros)
        for a in norma.anexos_standalone:
            self.assertTrue(a.pendiente)


if __name__ == "__main__":
    unittest.main()
