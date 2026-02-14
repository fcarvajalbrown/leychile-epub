"""Tests para SuperirXMLGenerator.

Valida generación de XML conforme a superir_v1.xsd:
- Considerandos individuales
- Epígrafes en artículos
- Listados letrados
- Requisitos numerados con sub-items
- Anexos standalone con pendiente="true"
- Cierre (fórmula + firmante)
- Validación XSD
"""

import unittest
from pathlib import Path

from lxml import etree

from leychile_epub.superir_models import NormaSuperir
from leychile_epub.superir_structured_parser import SuperirStructuredParser
from leychile_epub.superir_xml_generator import SuperirXMLGenerator

NS = "https://superir.cl/schema/norma/v1"
NSMAP = {"n": NS}
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "superir_v1.xsd"


def _parse_xml(xml_str: str) -> etree._Element:
    """Helper: parsea XML string a elemento."""
    return etree.fromstring(xml_str.encode("utf-8"))


def _xpath(root: etree._Element, expr: str) -> list:
    """Helper: ejecuta XPath con namespace."""
    return root.xpath(expr, namespaces=NSMAP)


class TestGenerateNCG4(unittest.TestCase):
    """Tests de generación XML para NCG 4."""

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

1° Que el artículo 54° de la Ley ordena que un modelo de solicitud de inicio del Procedimiento Concursal de Reorganización se encuentre disponible en las dependencias de la Superintendencia.

2° Que, en conformidad a lo anterior, esta Superintendencia de Insolvencia y Reemprendimiento (en adelante, la "Superintendencia") dicta la siguiente:

NORMA DE CARÁCTER GENERAL

TÍTULO I
Modelo de Solicitud de Inicio del Procedimiento Concursal de Reorganización

Artículo 1°. Modelo.
En formato anexo a la presente Norma de Carácter General, se dispone un modelo de solicitud de inicio del Procedimiento Concursal de Reorganización.

TÍTULO II
Disposiciones Finales

Artículo 2°. Ámbito de aplicación.
La presente Norma de Carácter General solo tiene por objeto regular las materias que en la misma se tratan.

Artículo 3°. Términos definidos.
Los términos en mayúscula utilizados en esta Norma de Carácter General tendrán el mismo significado que a ellos se les asigna en el artículo 2° de la Ley.

Artículo 4°. Vigencia.
La presente Norma de Carácter General se dicta en mérito de los principios de continuidad de la función pública.

Anótese y publíquese.

JOSEFINA MONTENEGRO ARANEDA
Superintendenta de Insolvencia y Reemprendimiento
"""

    @classmethod
    def setUpClass(cls):
        """Parse NCG 4 y genera XML una vez."""
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(cls.NCG4_TEXTO)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_against_xsd(self):
        """XML valida contra superir_v1.xsd."""
        schema_doc = etree.parse(str(SCHEMA_PATH))
        schema = etree.XMLSchema(schema_doc)
        doc = _parse_xml(self.xml_str)
        is_valid = schema.validate(doc)
        if not is_valid:
            for error in schema.error_log:
                print(f"  Validación: {error}")
        self.assertTrue(is_valid, "XML no valida contra superir_v1.xsd")

    def test_root_element(self):
        """Elemento raíz es <norma> con atributos correctos."""
        self.assertEqual(self.root.tag, f"{{{NS}}}norma")
        self.assertEqual(self.root.get("tipo"), "Norma de Carácter General")
        self.assertEqual(self.root.get("numero"), "4")

    def test_encabezado(self):
        """Encabezado tiene identificación y organismo."""
        id_els = _xpath(self.root, "//n:encabezado/n:identificacion")
        self.assertEqual(len(id_els), 1)
        self.assertIn("4", id_els[0].text)

        org_els = _xpath(self.root, "//n:encabezado/n:organismo")
        self.assertEqual(len(org_els), 1)
        self.assertIn("SUPERINTENDENCIA", org_els[0].text)

    def test_considerandos_individuales(self):
        """Cada considerando es un elemento separado con número."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        # NCG 4 tiene 1 considerando real (el 2° era fórmula de dictación)
        self.assertEqual(len(cons), 1)
        self.assertEqual(cons[0].get("numero"), "1")

        # Cada considerando tiene al menos un párrafo
        for c in cons:
            parrafos = c.findall(f"{{{NS}}}parrafo")
            self.assertGreaterEqual(len(parrafos), 1)

    def test_formula_dictacion(self):
        """NCG 4 tiene formula_dictacion extraída."""
        formulas = _xpath(self.root, "//n:formula_dictacion")
        self.assertEqual(len(formulas), 1)
        self.assertIn("conformidad", formulas[0].text.lower())

    def test_vistos_parrafo(self):
        """Vistos contiene párrafos."""
        parrafos = _xpath(self.root, "//n:vistos/n:parrafo")
        self.assertGreaterEqual(len(parrafos), 1)
        self.assertIn("facultades", parrafos[0].text.lower())

    def test_articulo_epigrafe(self):
        """Artículos tienen atributo epigrafe."""
        arts = _xpath(self.root, "//n:articulo[@epigrafe]")
        self.assertGreaterEqual(len(arts), 3)

        epigrafes = {a.get("numero"): a.get("epigrafe") for a in arts}
        self.assertEqual(epigrafes.get("1"), "Modelo")
        self.assertEqual(epigrafes.get("2"), "Ámbito de aplicación")
        self.assertEqual(epigrafes.get("4"), "Vigencia")

    def test_cierre_formula(self):
        """Cierre tiene fórmula."""
        formulas = _xpath(self.root, "//n:cierre/n:formula")
        self.assertEqual(len(formulas), 1)
        self.assertIn("publíquese", formulas[0].text.lower())

    def test_cierre_firmante(self):
        """Cierre tiene firmante con nombre y cargo."""
        nombres = _xpath(self.root, "//n:cierre/n:firmante/n:nombre")
        cargos = _xpath(self.root, "//n:cierre/n:firmante/n:cargo")
        self.assertEqual(len(nombres), 1)
        self.assertEqual(len(cargos), 1)
        self.assertIn("MONTENEGRO", nombres[0].text)
        self.assertIn("SUPERINTENDENTA", cargos[0].text)

    def test_titulos(self):
        """Cuerpo tiene 2 títulos."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 2)
        self.assertEqual(titulos[0].get("numero"), "I")
        self.assertEqual(titulos[1].get("numero"), "II")


class TestGenerateNCG6WithListado(unittest.TestCase):
    """Tests de generación para NCG 6 (con listado letrado)."""

    NCG6_TEXTO = """REPÚBLICA DE CHILE
Ministerio de Economía, Fomento y Turismo
Superintendencia de Insolvencia y Reemprendimiento

NORMA DE CARÁCTER GENERAL N.° 6
SUPERINTENDENCIA DE INSOLVENCIA Y REEMPRENDIMIENTO

REF.: Forma de otorgar la garantía para asegurar los pagos de acreedores de primera clase.

Santiago, 8 de octubre de 2014

VISTOS

Las facultades conferidas en el artículo 75° de la Ley N.° 20.720, de Reorganización y Liquidación de Activos de Empresas y Personas (en adelante, la "Ley").

CONSIDERANDO

1° Que, el artículo 75° de la Ley dispone que en caso que no se acuerde la reorganización y se declare la liquidación de la Empresa Deudora, el acreedor prendario o hipotecario podrá percibir de la venta el monto de su respectivo crédito.

2° Que, es de la esencia de la disposición en comento, que la garantía sea de aquellas de fácil realización.

3° Que, el mencionado artículo 75° se refiere al otorgamiento de cualquier instrumento de garantía, excluyéndose toda garantía real y personal.

4° Que, en conformidad a lo anterior, esta Superintendencia dicta la siguiente:

NORMA DE CARÁCTER GENERAL

TÍTULO I

Artículo 1°. Naturaleza.
Para los efectos del artículo 75° de la Ley se entenderán como instrumentos de garantía suficientes, además de aquellos que reconozcan las leyes, los siguientes:
a) Vale vista o boleta bancaria, extendida en forma irrevocable a nombre del Deudor en liquidación, nominativa, a la vista, de una duración no inferior a dos años.
b) Póliza de seguro de caución, en los términos expuestos en el artículo 582° del Código de Comercio, tomada por el acreedor en favor del Deudor.

Artículo 2°. Monto, oportunidad y ejecución de la garantía.
Deberá estarse a lo regulado por esta Superintendencia en el instructivo correspondiente.

Artículo 3°. Extensión.
Lo dispuesto en los artículos precedentes, será también aplicable a aquellos casos en que el acreedor ejecutare su garantía al margen del Procedimiento Concursal de Liquidación.

TÍTULO II
Disposiciones finales

Artículo 4°. Ámbito de aplicación.
La presente Norma de Carácter General solo tiene por objeto regular las materias que en la misma se tratan.

Artículo 5°. Términos definidos.
Los términos en mayúscula tendrán el mismo significado que a ellos se les asigna en el artículo 2° de la Ley.

Artículo 6°. Vigencia.
La presente Norma de Carácter General se dicta en mérito de los principios de continuidad de la función pública.

Anótese y publíquese.

JOSEFINA MONTENEGRO ARANEDA
Superintendenta de Insolvencia y Reemprendimiento
"""

    @classmethod
    def setUpClass(cls):
        """Parse NCG 6 y genera XML una vez."""
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(cls.NCG6_TEXTO)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_against_xsd(self):
        """XML valida contra superir_v1.xsd."""
        schema_doc = etree.parse(str(SCHEMA_PATH))
        schema = etree.XMLSchema(schema_doc)
        is_valid = schema.validate(_parse_xml(self.xml_str))
        self.assertTrue(is_valid, "NCG 6 XML no valida contra superir_v1.xsd")

    def test_three_considerandos(self):
        """NCG 6 tiene 3 considerandos reales (el 4° era fórmula de dictación)."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 3)

    def test_listado_in_articulo_1(self):
        """Artículo 1 tiene listado con items a) y b)."""
        art1 = _xpath(self.root, "//n:articulo[@numero='1']")
        self.assertEqual(len(art1), 1)

        items = art1[0].findall(f".//{{{NS}}}item")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].get("letra"), "a")
        self.assertEqual(items[1].get("letra"), "b")
        self.assertIn("boleta bancaria", items[0].text)

    def test_six_articulos(self):
        """NCG 6 tiene 6 artículos."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 6)

    def test_titulo_ii_nombre(self):
        """Título II tiene nombre 'Disposiciones finales'."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 2)
        # Título I sin nombre
        self.assertFalse(titulos[0].get("nombre", ""))
        # Título II con nombre
        nombre_t2 = titulos[1].get("nombre", "")
        self.assertIn("Disposiciones", nombre_t2)

    def test_no_anexos(self):
        """NCG 6 no tiene anexos."""
        anexos = _xpath(self.root, "//n:anexos")
        self.assertEqual(len(anexos), 0)

    def test_epigrafe_naturaleza(self):
        """Artículo 1 tiene epígrafe 'Naturaleza'."""
        art1 = _xpath(self.root, "//n:articulo[@numero='1']")
        self.assertEqual(art1[0].get("epigrafe"), "Naturaleza")


class TestGenerateNCG7(unittest.TestCase):
    """Tests de generación XML para NCG 7 (requisitos + anexos standalone)."""

    @classmethod
    def setUpClass(cls):
        texto_path = Path(__file__).parent.parent / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_7.txt"
        if not texto_path.exists():
            raise unittest.SkipTest("Texto NCG 7 no disponible")

        parser = SuperirStructuredParser()
        texto = texto_path.read_text(encoding="utf-8")
        norma = parser.parse(texto)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_xsd(self):
        """NCG 7 XML valida contra superir_v1.xsd."""
        schema_doc = etree.parse(str(SCHEMA_PATH))
        schema = etree.XMLSchema(schema_doc)
        doc = etree.fromstring(self.xml_str.encode("utf-8"))
        self.assertTrue(schema.validate(doc), msg=str(schema.error_log))

    def test_five_considerandos(self):
        """NCG 7 tiene 5 considerandos."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 5)

    def test_formula_dictacion(self):
        """NCG 7 tiene fórmula de dictación."""
        fd = _xpath(self.root, "//n:formula_dictacion")
        self.assertEqual(len(fd), 1)
        self.assertIn("conformidad", fd[0].text.lower())

    def test_requisitos_in_art7(self):
        """Art 7 tiene requisitos I-V como <requisito> elements."""
        reqs = _xpath(self.root, "//n:articulo[@numero='7']/n:requisito")
        self.assertEqual(len(reqs), 5)
        numeros = [r.get("numero") for r in reqs]
        self.assertEqual(numeros, ["I", "II", "III", "IV", "V"])

    def test_requisito_ii_has_subitems(self):
        """Requisito II tiene items letrados a)-e)."""
        req_ii = _xpath(
            self.root,
            "//n:articulo[@numero='7']/n:requisito[@numero='II']"
        )
        self.assertEqual(len(req_ii), 1)
        items = _xpath(req_ii[0], "n:item")
        self.assertTrue(len(items) >= 4, f"Esperaba >=4 items, got {len(items)}")
        # Item a tiene nombre "Ingresos"
        self.assertTrue(items[0].get("nombre", ""))

    def test_requisito_ii_nombre_attribute(self):
        """Requisito II tiene atributo nombre."""
        req_ii = _xpath(
            self.root,
            "//n:articulo[@numero='7']/n:requisito[@numero='II']"
        )
        nombre = req_ii[0].get("nombre", "")
        self.assertTrue(nombre, "Requisito II debe tener nombre")

    def test_standalone_anexos(self):
        """NCG 7 tiene 4 <anexo> standalone a nivel raíz."""
        # Standalone = <anexo> directo hijo de <norma>, no dentro de <anexos>
        standalone = _xpath(self.root, "/n:norma/n:anexo")
        self.assertEqual(len(standalone), 4)

    def test_standalone_anexos_pendiente(self):
        """Todos los anexos standalone tienen pendiente='true'."""
        standalone = _xpath(self.root, "/n:norma/n:anexo")
        for anx in standalone:
            self.assertEqual(anx.get("pendiente"), "true")

    def test_standalone_anexos_numeros(self):
        """Anexos standalone tienen números I-IV."""
        standalone = _xpath(self.root, "/n:norma/n:anexo")
        numeros = [a.get("numero") for a in standalone]
        self.assertIn("I", numeros)
        self.assertIn("II", numeros)
        self.assertIn("III", numeros)
        self.assertIn("IV", numeros)

    def test_no_anexos_container(self):
        """NCG 7 no tiene <anexos> contenedor (solo standalone)."""
        container = _xpath(self.root, "//n:anexos")
        self.assertEqual(len(container), 0)

    def test_21_articulos(self):
        """NCG 7 tiene 21 artículos."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 21)


class TestGenerateNCG10(unittest.TestCase):
    """Tests para NCG 10 - multi-párrafo, cierre ampliado, derogación."""

    @classmethod
    def setUpClass(cls):
        texto_path = Path(__file__).parent.parent / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_10.txt"
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_10.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="10")
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_xsd(self):
        """NCG 10 XML valida contra superir_v1.xsd."""
        schema = etree.XMLSchema(etree.parse(str(SCHEMA_PATH)))
        doc = etree.fromstring(self.xml_str.encode("utf-8"))
        self.assertTrue(schema.validate(doc), schema.error_log)

    def test_nine_articulos(self):
        """NCG 10 tiene 9 artículos."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 9)

    def test_three_considerandos(self):
        """NCG 10 tiene 3 considerandos."""
        cons = _xpath(self.root, "//n:considerando")
        self.assertEqual(len(cons), 3)

    def test_cierre_formula_ampliada(self):
        """NCG 10 tiene fórmula de cierre ampliada."""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertEqual(len(formula), 1)
        self.assertIn("notifíquese", formula[0].lower())
        self.assertIn("archívese", formula[0].lower())

    def test_firmante_hugo_sanchez(self):
        """NCG 10 firmada por Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertEqual(len(nombre), 1)
        self.assertIn("SÁNCHEZ", nombre[0])

    def test_art1_interleaved_parrafo_listado_parrafo(self):
        """Art 1 tiene patrón interleaved: párrafo → listado → párrafo."""
        art1 = _xpath(self.root, "//n:articulo[@numero='1']")[0]
        children = list(art1)
        # Debe ser: parrafo, listado, parrafo
        tags = [etree.QName(c.tag).localname for c in children]
        self.assertEqual(tags, ["parrafo", "listado", "parrafo"])

    def test_art2_four_parrafos(self):
        """Art 2 tiene 4 párrafos separados (multi-paragraph splitting)."""
        art2 = _xpath(self.root, "//n:articulo[@numero='2']")[0]
        parrafos = art2.findall(f"{{{NS}}}parrafo")
        self.assertEqual(len(parrafos), 4)

    def test_art3_three_parrafos(self):
        """Art 3 tiene 3 párrafos separados."""
        art3 = _xpath(self.root, "//n:articulo[@numero='3']")[0]
        parrafos = art3.findall(f"{{{NS}}}parrafo")
        self.assertEqual(len(parrafos), 3)

    def test_art4_four_parrafos(self):
        """Art 4 tiene 4 párrafos separados."""
        art4 = _xpath(self.root, "//n:articulo[@numero='4']")[0]
        parrafos = art4.findall(f"{{{NS}}}parrafo")
        self.assertEqual(len(parrafos), 4)

    def test_art9_derogacion(self):
        """Art 9 tiene epígrafe 'Derogación'."""
        art9 = _xpath(self.root, "//n:articulo[@numero='9']")[0]
        self.assertEqual(art9.get("epigrafe"), "Derogación")

    def test_art2_no_false_listado(self):
        """Art 2 NO tiene listado (la ref 'g)' no es item letrado)."""
        art2 = _xpath(self.root, "//n:articulo[@numero='2']")[0]
        listados = art2.findall(f"{{{NS}}}listado")
        self.assertEqual(len(listados), 0)

    def test_no_anexos(self):
        """NCG 10 no tiene anexos."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 0)

    def test_titulo_i_nombre(self):
        """Título I se llama 'Garantía de fiel desempeño'."""
        titulos = _xpath(self.root, "//n:titulo[@numero='I']")
        self.assertEqual(len(titulos), 1)
        self.assertEqual(titulos[0].get("nombre"), "Garantía de fiel desempeño")

    def test_titulo_ii_nombre(self):
        """Título II se llama 'Disposiciones finales'."""
        titulos = _xpath(self.root, "//n:titulo[@numero='II']")
        self.assertEqual(len(titulos), 1)
        self.assertEqual(titulos[0].get("nombre"), "Disposiciones finales")


class TestGenerateNCG14(unittest.TestCase):
    """Tests para NCG 14 - primera Resolución Exenta, 7 títulos, 20 artículos."""

    @classmethod
    def setUpClass(cls):
        texto_path = (
            Path(__file__).parent.parent
            / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_14.txt"
        )
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_14.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        catalog = {
            "titulo_completo": "NORMA DE CARÁCTER GENERAL N°14",
            "resolucion_exenta": "6597",
            "fecha_publicacion": "2023-08-11",
            "materias": ["Publicaciones", "Formalidades"],
            "leyes_habilitantes": ["20720"],
            "deroga": [],
            "modifica": [],
            "nombres_comunes": ["NCG de Publicaciones"],
            "categoria": "Publicación",
        }
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="14", catalog_entry=catalog)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_xsd(self):
        """NCG 14 XML valida contra superir_v1.xsd."""
        schema = etree.XMLSchema(etree.parse(str(SCHEMA_PATH)))
        doc = etree.fromstring(self.xml_str.encode("utf-8"))
        self.assertTrue(schema.validate(doc), schema.error_log)

    def test_acto_administrativo(self):
        """NCG 14 tiene acto_administrativo de Resolución Exenta N.° 6597."""
        aa = _xpath(self.root, "//n:acto_administrativo")
        self.assertEqual(len(aa), 1)
        tipo = _xpath(aa[0], "n:tipo/text()")
        self.assertEqual(tipo[0], "RESOLUCIÓN EXENTA")
        numero = _xpath(aa[0], "n:numero/text()")
        self.assertEqual(numero[0], "6597")
        materia = _xpath(aa[0], "n:materia/text()")
        self.assertIn("PUBLICACIONES", materia[0].upper())

    def test_encabezado_sin_identificacion(self):
        """Con acto_administrativo, encabezado NO tiene identificación/organismo."""
        enc = _xpath(self.root, "//n:encabezado")
        self.assertEqual(len(enc), 1)
        identificacion = _xpath(enc[0], "n:identificacion")
        self.assertEqual(len(identificacion), 0)
        organismo = _xpath(enc[0], "n:organismo")
        self.assertEqual(len(organismo), 0)
        # Pero sí tiene lugar y fecha
        lugar = _xpath(enc[0], "n:lugar")
        self.assertEqual(len(lugar), 1)

    def test_five_considerandos(self):
        """NCG 14 tiene 5 considerandos."""
        cons = _xpath(self.root, "//n:considerando")
        self.assertEqual(len(cons), 5)

    def test_resolutivo_pre_ncg(self):
        """NCG 14 tiene 1 punto resolutivo pre-NCG (APRUÉBESE)."""
        res = _xpath(self.root, "//n:resolutivo/n:punto")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].get("numero"), "1")
        self.assertIn("APRUÉBESE", res[0].text)

    def test_preambulo_ncg(self):
        """NCG 14 tiene preámbulo NCG con párrafo introductorio."""
        pre = _xpath(self.root, "//n:preambulo_ncg/n:parrafo")
        self.assertEqual(len(pre), 1)
        self.assertIn("regula las materias", pre[0].text)

    def test_seven_titulos(self):
        """NCG 14 tiene 7 títulos en cuerpo_normativo."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 7)

    def test_twenty_articulos(self):
        """NCG 14 tiene 20 artículos."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 20)

    def test_all_articulos_have_epigrafe(self):
        """Todos los 20 artículos de NCG 14 tienen epígrafe."""
        arts = _xpath(self.root, "//n:articulo")
        for art in arts:
            epigrafe = art.get("epigrafe", "")
            self.assertTrue(
                epigrafe,
                f"Art {art.get('numero')} sin epígrafe"
            )

    def test_art4_listado_abcd(self):
        """Art 4 tiene listado con items a) b) c) d)."""
        art4 = _xpath(self.root, "//n:articulo[@numero='4']")[0]
        items = _xpath(art4, "n:listado/n:item")
        self.assertEqual(len(items), 4)
        letras = [i.get("letra") for i in items]
        self.assertEqual(letras, ["a", "b", "c", "d"])

    def test_art11_three_parrafos_before_listado(self):
        """Art 11 tiene 3 párrafos antes del listado a)-f)."""
        art11 = _xpath(self.root, "//n:articulo[@numero='11']")[0]
        children = list(art11)
        tags = [etree.QName(c.tag).localname for c in children]
        # Debe ser: parrafo, parrafo, parrafo, listado
        parrafo_count = sum(1 for t in tags[:tags.index("listado")] if t == "parrafo")
        self.assertEqual(parrafo_count, 3)

    def test_art11_listado_six_items(self):
        """Art 11 tiene listado con 6 items (a-f)."""
        items = _xpath(self.root, "//n:articulo[@numero='11']/n:listado/n:item")
        self.assertEqual(len(items), 6)

    def test_art20_revocacion_clean(self):
        """Art 20 solo tiene texto de revocación (no resolutivo_final)."""
        art20 = _xpath(self.root, "//n:articulo[@numero='20']/n:parrafo")
        self.assertEqual(len(art20), 1)
        self.assertIn("Déjase sin efecto", art20[0].text)
        self.assertNotIn("PUBLÍQUESE", art20[0].text)

    def test_resolutivo_final(self):
        """NCG 14 tiene 2 puntos resolutivos finales (PUBLÍQUESE, DISPÓNGASE)."""
        rf = _xpath(self.root, "//n:resolutivo_final/n:punto")
        self.assertEqual(len(rf), 2)
        self.assertEqual(rf[0].get("numero"), "2")
        self.assertIn("PUBLÍQUESE", rf[0].text)
        self.assertEqual(rf[1].get("numero"), "3")
        self.assertIn("DISPÓNGASE", rf[1].text)

    def test_cierre_formula_con_coma(self):
        """La fórmula de cierre termina con coma (no período)."""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertTrue(formula[0].endswith(","))
        self.assertIn("ARCHÍVESE", formula[0])

    def test_firmante_hugo_sanchez(self):
        """NCG 14 firmada por Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertIn("SÁNCHEZ", nombre[0])
        cargo = _xpath(self.root, "//n:cierre/n:firmante/n:cargo/text()")
        self.assertEqual(cargo[0], "SUPERINTENDENTE DE INSOLVENCIA Y REEMPRENDIMIENTO")

    def test_distribucion(self):
        """NCG 14 tiene código de distribución PVL/PCP/CVS/POR."""
        dist = _xpath(self.root, "//n:cierre/n:distribucion/text()")
        self.assertEqual(len(dist), 1)
        self.assertEqual(dist[0], "PVL/PCP/CVS/POR")

    def test_no_standalone_anexos(self):
        """NCG 14 no tiene anexos."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 0)

    def test_titulo_i_nombre(self):
        """Título I: Del Boletín Concursal."""
        t1 = _xpath(self.root, "//n:titulo[@numero='I']")
        self.assertEqual(t1[0].get("nombre"), "Del Boletín Concursal")

    def test_titulo_vii_nombre(self):
        """Título VII: Disposiciones Finales."""
        t7 = _xpath(self.root, "//n:titulo[@numero='VII']")
        self.assertEqual(len(t7), 1)
        self.assertEqual(t7[0].get("nombre"), "Disposiciones Finales")


class TestGenerateNCG15(unittest.TestCase):
    """Tests para NCG 15 - RE 6598, juntas telemáticas, 4 títulos, 11 arts, notificación."""

    @classmethod
    def setUpClass(cls):
        texto_path = (
            Path(__file__).parent.parent
            / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_15.txt"
        )
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_15.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        catalog = {
            "titulo_completo": "NORMA DE CARÁCTER GENERAL N°15",
            "resolucion_exenta": "6598",
            "fecha_publicacion": "2023-08-11",
            "materias": ["Juntas de acreedores", "Medios tecnológicos", "Sesiones remotas"],
            "leyes_habilitantes": ["20720", "21563"],
            "deroga": [],
            "modifica": [],
            "nombres_comunes": ["NCG de Juntas Remotas"],
            "categoria": "Juntas de acreedores",
        }
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="15", catalog_entry=catalog)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_xsd(self):
        """NCG 15 XML valida contra superir_v1.xsd."""
        schema = etree.XMLSchema(etree.parse(str(SCHEMA_PATH)))
        doc = etree.fromstring(self.xml_str.encode("utf-8"))
        self.assertTrue(schema.validate(doc), schema.error_log)

    def test_acto_administrativo(self):
        """NCG 15 tiene acto_administrativo de RE N.° 6598."""
        aa = _xpath(self.root, "//n:acto_administrativo")
        self.assertEqual(len(aa), 1)
        tipo = _xpath(self.root, "//n:acto_administrativo/n:tipo/text()")
        self.assertIn("RESOLUCIÓN EXENTA", tipo[0])
        numero = _xpath(self.root, "//n:acto_administrativo/n:numero/text()")
        self.assertEqual(numero[0], "6598")

    def test_five_considerandos(self):
        """NCG 15 tiene 5 considerandos."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 5)
        self.assertEqual(cons[0].get("numero"), "1")
        self.assertEqual(cons[4].get("numero"), "5")

    def test_considerando_5_short(self):
        """Considerando 5° es breve: 'Que, atendido lo expuesto...'."""
        c5 = _xpath(self.root, "//n:considerando[@numero='5']/n:parrafo/text()")
        self.assertTrue(c5[0].startswith("Que, atendido"))

    def test_four_titulos(self):
        """NCG 15 tiene 4 títulos (I-IV)."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 4)

    def test_titulo_i_nombre(self):
        """Título I: Disposiciones comunes."""
        t1 = _xpath(self.root, "//n:titulo[@numero='I']")
        self.assertEqual(t1[0].get("nombre"), "Disposiciones comunes")

    def test_titulo_ii_nombre(self):
        """Título II: De las Juntas de Acreedores/as celebradas por medios telemáticos."""
        t2 = _xpath(self.root, "//n:titulo[@numero='II']")
        self.assertIn("Juntas de Acreedores", t2[0].get("nombre"))

    def test_titulo_iii_nombre(self):
        """Título III: De la asistencia remota..."""
        t3 = _xpath(self.root, "//n:titulo[@numero='III']")
        self.assertIn("asistencia remota", t3[0].get("nombre").lower())

    def test_titulo_iv_disposiciones_finales(self):
        """Título IV: Disposiciones Finales."""
        t4 = _xpath(self.root, "//n:titulo[@numero='IV']")
        self.assertIn("Disposiciones Finales", t4[0].get("nombre"))

    def test_eleven_articulos(self):
        """NCG 15 tiene 11 artículos."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 11)

    def test_art1_epigrafe(self):
        """Art 1° tiene epígrafe 'Ámbito de aplicación'."""
        art1 = _xpath(self.root, "//n:articulo[@numero='1']")
        self.assertEqual(art1[0].get("epigrafe"), "Ámbito de aplicación")

    def test_art2_epigrafe(self):
        """Art 2° tiene epígrafe 'Definición'."""
        art2 = _xpath(self.root, "//n:articulo[@numero='2']")
        self.assertEqual(art2[0].get("epigrafe"), "Definición")

    def test_art3_epigrafe(self):
        """Art 3° tiene epígrafe 'Requisitos técnicos'."""
        art3 = _xpath(self.root, "//n:articulo[@numero='3']")
        self.assertEqual(art3[0].get("epigrafe"), "Requisitos técnicos")

    def test_art4_no_epigrafe(self):
        """Art 4° NO tiene epígrafe."""
        art4 = _xpath(self.root, "//n:articulo[@numero='4']")
        self.assertIsNone(art4[0].get("epigrafe"))

    def test_art5_no_epigrafe(self):
        """Art 5° NO tiene epígrafe."""
        art5 = _xpath(self.root, "//n:articulo[@numero='5']")
        self.assertIsNone(art5[0].get("epigrafe"))

    def test_art11_epigrafe_vigencia(self):
        """Art 11° tiene epígrafe 'Vigencia'."""
        art11 = _xpath(self.root, "//n:articulo[@numero='11']")
        self.assertEqual(art11[0].get("epigrafe"), "Vigencia")

    def test_art3_three_parrafos(self):
        """Art 3° tiene 3 párrafos."""
        parrs = _xpath(self.root, "//n:articulo[@numero='3']/n:parrafo")
        self.assertEqual(len(parrs), 3)

    def test_art5_seven_parrafos(self):
        """Art 5° es el más extenso: 7 párrafos."""
        parrs = _xpath(self.root, "//n:articulo[@numero='5']/n:parrafo")
        self.assertEqual(len(parrs), 7)

    def test_art6_four_parrafos(self):
        """Art 6° tiene 4 párrafos."""
        parrs = _xpath(self.root, "//n:articulo[@numero='6']/n:parrafo")
        self.assertEqual(len(parrs), 4)

    def test_art7_two_parrafos(self):
        """Art 7° tiene 2 párrafos."""
        parrs = _xpath(self.root, "//n:articulo[@numero='7']/n:parrafo")
        self.assertEqual(len(parrs), 2)

    def test_resolutivo_one_punto(self):
        """NCG 15 tiene 1 punto resolutivo pre-NCG (APRUÉBASE)."""
        res = _xpath(self.root, "//n:resolutivo/n:punto")
        self.assertEqual(len(res), 1)
        self.assertIn("APRUÉBASE", res[0].text)

    def test_resolutivo_final_three_puntos(self):
        """NCG 15 tiene 3 puntos resolutivos finales (2°, 3°, 4°)."""
        rf = _xpath(self.root, "//n:resolutivo_final/n:punto")
        self.assertEqual(len(rf), 3)
        self.assertEqual(rf[0].get("numero"), "2")
        self.assertIn("PUBLÍQUESE", rf[0].text)
        self.assertEqual(rf[1].get("numero"), "3")
        self.assertIn("NOTIFÍQUESE", rf[1].text)
        self.assertEqual(rf[2].get("numero"), "4")
        self.assertIn("DISPÓNGASE", rf[2].text)

    def test_cierre_formula(self):
        """Fórmula de cierre: ANÓTESE, PUBLÍQUESE Y ARCHÍVESE,"""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertIn("ARCHÍVESE", formula[0])
        self.assertTrue(formula[0].endswith(","))

    def test_firmante_hugo_sanchez(self):
        """NCG 15 firmada por Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertIn("SÁNCHEZ", nombre[0])
        cargo = _xpath(self.root, "//n:cierre/n:firmante/n:cargo/text()")
        self.assertEqual(cargo[0], "SUPERINTENDENTE DE INSOLVENCIA Y REEMPRENDIMIENTO")

    def test_distribucion(self):
        """NCG 15 tiene código de distribución PVL/JAA/EGZ/DTC/FRR."""
        dist = _xpath(self.root, "//n:cierre/n:distribucion/text()")
        self.assertEqual(len(dist), 1)
        self.assertEqual(dist[0], "PVL/JAA/EGZ/DTC/FRR")

    def test_notificacion_destinatarios(self):
        """NCG 15 tiene notificación con destinatarios (Liquidadores y Veedores)."""
        dest = _xpath(self.root, "//n:cierre/n:notificacion/n:destinatarios/text()")
        self.assertEqual(len(dest), 1)
        self.assertIn("Liquidadores", dest[0])
        self.assertIn("Veedores", dest[0])

    def test_standalone_anexo(self):
        """NCG 15 tiene 1 anexo standalone (pendiente por ahora)."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 1)
        self.assertEqual(anexos[0].get("numero"), "I")


class TestGenerateNCG16(unittest.TestCase):
    """Tests para NCG 16 - RE 6596, exámenes de conocimientos, 2 títulos, 22 arts.

    NCG 16 valida:
    - Formato periodo "N. Que," en considerandos (distinto de "N° Que," en NCGs anteriores)
    - Items letrados con subitems romanos (Art 2°: a/b/c con i/ii/iii)
    - Items romanos puros (Art 8°: i-v, Art 11°: i-iii)
    - Listados letrados simples (Arts 4°, 13°-17°)
    """

    @classmethod
    def setUpClass(cls):
        texto_path = (
            Path(__file__).parent.parent
            / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_16.txt"
        )
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_16.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        catalog = {
            "titulo_completo": "NORMA DE CARÁCTER GENERAL N°16 - Exámenes de conocimiento para veedores y liquidadores",
            "resolucion_exenta": "6596",
            "fecha_publicacion": "2023-08-11",
            "materias": ["Exámenes de conocimiento", "Veedores", "Liquidadores"],
            "leyes_habilitantes": ["20720"],
            "deroga": [],
            "modifica": [],
            "nombres_comunes": ["NCG de Exámenes de Conocimiento"],
            "categoria": "Exámenes",
        }
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="16", catalog_entry=catalog)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_xsd(self):
        """NCG 16 XML valida contra superir_v1.xsd."""
        schema = etree.XMLSchema(etree.parse(str(SCHEMA_PATH)))
        doc = etree.fromstring(self.xml_str.encode("utf-8"))
        self.assertTrue(schema.validate(doc), schema.error_log)

    def test_acto_administrativo(self):
        """NCG 16 tiene acto_administrativo de RE N.° 6596."""
        aa = _xpath(self.root, "//n:acto_administrativo")
        self.assertEqual(len(aa), 1)
        tipo = _xpath(aa[0], "n:tipo/text()")
        self.assertEqual(tipo[0], "RESOLUCIÓN EXENTA")
        numero = _xpath(aa[0], "n:numero/text()")
        self.assertEqual(numero[0], "6596")

    def test_six_considerandos(self):
        """NCG 16 tiene 6 considerandos (formato 'N. Que,')."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 6)
        self.assertEqual(cons[0].get("numero"), "1")
        self.assertEqual(cons[5].get("numero"), "6")

    def test_considerando_starts_with_que(self):
        """Considerandos inician con 'Que,' (sin prefijo numérico)."""
        c1 = _xpath(self.root, "//n:considerando[@numero='1']/n:parrafo/text()")
        self.assertTrue(
            c1[0].startswith("Que,"),
            f"Considerando 1 no inicia con 'Que,': '{c1[0][:30]}...'"
        )
        c6 = _xpath(self.root, "//n:considerando[@numero='6']/n:parrafo/text()")
        self.assertTrue(c6[0].startswith("Que,"))

    def test_resolutivo_pre_ncg(self):
        """NCG 16 tiene 1 punto resolutivo pre-NCG (APRUÉBESE)."""
        res = _xpath(self.root, "//n:resolutivo/n:punto")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].get("numero"), "1")
        self.assertIn("APRUÉBESE", res[0].text)

    def test_preambulo_ncg(self):
        """NCG 16 tiene preámbulo NCG con texto introductorio."""
        pre = _xpath(self.root, "//n:preambulo_ncg/n:parrafo")
        self.assertEqual(len(pre), 1)
        self.assertIn("regula las materias", pre[0].text)

    def test_two_titulos(self):
        """NCG 16 tiene 2 títulos (I y II)."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 2)

    def test_titulo_i_nombre(self):
        """Título I: Exámenes de Conocimientos."""
        t1 = _xpath(self.root, "//n:titulo[@numero='I']")
        self.assertEqual(t1[0].get("nombre"), "Exámenes de Conocimientos")

    def test_titulo_ii_nombre(self):
        """Título II: Disposiciones Finales."""
        t2 = _xpath(self.root, "//n:titulo[@numero='II']")
        self.assertEqual(t2[0].get("nombre"), "Disposiciones Finales")

    def test_twenty_two_articulos(self):
        """NCG 16 tiene 22 artículos."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 22)

    def test_all_articulos_have_epigrafe(self):
        """Todos los 22 artículos de NCG 16 tienen epígrafe."""
        arts = _xpath(self.root, "//n:articulo")
        for art in arts:
            epigrafe = art.get("epigrafe", "")
            self.assertTrue(
                epigrafe,
                f"Art {art.get('numero')} sin epígrafe"
            )

    def test_art2_three_lettered_items_with_subitems(self):
        """Art 2° tiene listado con 3 items letrados (a/b/c), cada uno con subitems."""
        art2 = _xpath(self.root, "//n:articulo[@numero='2']")[0]
        items = _xpath(art2, "n:listado/n:item")
        self.assertEqual(len(items), 3)
        letras = [i.get("letra") for i in items]
        self.assertEqual(letras, ["a", "b", "c"])
        # Cada item tiene sublistado con subitems
        for item in items:
            subitems = _xpath(item, "n:sublistado/n:subitem")
            self.assertGreaterEqual(
                len(subitems), 2,
                f"Item {item.get('letra')} sin subitems suficientes"
            )

    def test_art2_item_a_nombre_veedores(self):
        """Art 2° item a) tiene nombre='Veedores Concursales'."""
        item_a = _xpath(
            self.root,
            "//n:articulo[@numero='2']/n:listado/n:item[@letra='a']"
        )[0]
        self.assertEqual(item_a.get("nombre"), "Veedores Concursales")

    def test_art2_item_b_nombre_liquidadores(self):
        """Art 2° item b) tiene nombre='Liquidadores Concursales'."""
        item_b = _xpath(
            self.root,
            "//n:articulo[@numero='2']/n:listado/n:item[@letra='b']"
        )[0]
        self.assertEqual(item_b.get("nombre"), "Liquidadores Concursales")

    def test_art2_item_c_nombre_martilleros(self):
        """Art 2° item c) tiene nombre='Martilleros Concursales'."""
        item_c = _xpath(
            self.root,
            "//n:articulo[@numero='2']/n:listado/n:item[@letra='c']"
        )[0]
        self.assertEqual(item_c.get("nombre"), "Martilleros Concursales")

    def test_art2_subitems_roman_numbers(self):
        """Art 2° subitems usan numeración romana (i, ii, iii)."""
        subitems_a = _xpath(
            self.root,
            "//n:articulo[@numero='2']/n:listado/n:item[@letra='a']/n:sublistado/n:subitem"
        )
        nums = [s.get("numero") for s in subitems_a]
        self.assertEqual(nums, ["i", "ii", "iii"])

    def test_art4_eight_items(self):
        """Art 4° tiene 8 items letrados (a-h)."""
        items = _xpath(self.root, "//n:articulo[@numero='4']/n:listado/n:item")
        self.assertEqual(len(items), 8)
        letras = [i.get("letra") for i in items]
        self.assertEqual(letras, ["a", "b", "c", "d", "e", "f", "g", "h"])

    def test_art8_five_roman_items(self):
        """Art 8° tiene 5 items romanos puros (i-v), no letrados."""
        items = _xpath(self.root, "//n:articulo[@numero='8']/n:listado/n:item")
        self.assertEqual(len(items), 5)
        nums = [i.get("numero") for i in items]
        self.assertEqual(nums, ["i", "ii", "iii", "iv", "v"])
        # No deben tener atributo "letra"
        for item in items:
            self.assertIsNone(
                item.get("letra"),
                f"Item {item.get('numero')} tiene 'letra' (debería ser 'numero')"
            )

    def test_art11_three_roman_items(self):
        """Art 11° tiene 3 items romanos (i-iii)."""
        items = _xpath(self.root, "//n:articulo[@numero='11']/n:listado/n:item")
        self.assertEqual(len(items), 3)
        nums = [i.get("numero") for i in items]
        self.assertEqual(nums, ["i", "ii", "iii"])

    def test_art13_four_items(self):
        """Art 13° tiene 4 items letrados (a-d)."""
        items = _xpath(self.root, "//n:articulo[@numero='13']/n:listado/n:item")
        self.assertEqual(len(items), 4)
        letras = [i.get("letra") for i in items]
        self.assertEqual(letras, ["a", "b", "c", "d"])

    def test_art16_seven_items(self):
        """Art 16° (Excusas) tiene 7 items letrados (a-g)."""
        items = _xpath(self.root, "//n:articulo[@numero='16']/n:listado/n:item")
        self.assertEqual(len(items), 7)
        letras = [i.get("letra") for i in items]
        self.assertEqual(letras, ["a", "b", "c", "d", "e", "f", "g"])

    def test_resolutivo_final(self):
        """NCG 16 tiene 2 puntos resolutivos finales (PUBLÍQUESE, DISPÓNGASE)."""
        rf = _xpath(self.root, "//n:resolutivo_final/n:punto")
        self.assertEqual(len(rf), 2)
        self.assertEqual(rf[0].get("numero"), "2")
        self.assertIn("PUBLÍQUESE", rf[0].text)
        self.assertEqual(rf[1].get("numero"), "3")
        self.assertIn("DISPÓNGASE", rf[1].text)

    def test_cierre_formula(self):
        """Fórmula de cierre: ANÓTESE, PUBLÍQUESE Y ARCHÍVESE,"""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertIn("ARCHÍVESE", formula[0])
        self.assertTrue(formula[0].endswith(","))

    def test_firmante_hugo_sanchez(self):
        """NCG 16 firmada por Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertIn("SÁNCHEZ", nombre[0])
        cargo = _xpath(self.root, "//n:cierre/n:firmante/n:cargo/text()")
        self.assertEqual(cargo[0], "SUPERINTENDENTE DE INSOLVENCIA Y REEMPRENDIMIENTO")

    def test_distribucion(self):
        """NCG 16 tiene código de distribución PVL/PCP/CVS/POR."""
        dist = _xpath(self.root, "//n:cierre/n:distribucion/text()")
        self.assertEqual(len(dist), 1)
        self.assertEqual(dist[0], "PVL/PCP/CVS/POR")

    def test_no_standalone_anexos(self):
        """NCG 16 no tiene anexos."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 0)


class TestGenerateNCG17(unittest.TestCase):
    """Tests para NCG 17 - RE 6595, nominación por sorteo, 3 títulos, 8 arts.

    NCG 17 valida:
    - Formato periodo "N. Que," en considerandos (igual que NCG 16)
    - Items numerados arábigos con paréntesis: 1), 2), 3) (inline en párrafo)
    - Post-listado párrafos (texto después del listado)
    - 9 considerandos (máximo hasta ahora)
    """

    @classmethod
    def setUpClass(cls):
        texto_path = (
            Path(__file__).parent.parent
            / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_17.txt"
        )
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_17.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        catalog = {
            "titulo_completo": "NORMA DE CARÁCTER GENERAL N°17 - Nominación y designación aleatoria de veedores y liquidadores",
            "resolucion_exenta": "6595",
            "fecha_publicacion": "2023-08-11",
            "materias": [
                "Nominación",
                "Designación aleatoria",
                "Veedores y liquidadores",
            ],
            "leyes_habilitantes": ["20720"],
            "deroga": [],
            "modifica": [],
            "nombres_comunes": ["NCG de Nominación Aleatoria"],
            "categoria": "Nominación",
        }
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="17", catalog_entry=catalog)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_xsd(self):
        """NCG 17 XML valida contra superir_v1.xsd."""
        schema = etree.XMLSchema(etree.parse(str(SCHEMA_PATH)))
        doc = etree.fromstring(self.xml_str.encode("utf-8"))
        self.assertTrue(schema.validate(doc), schema.error_log)

    def test_acto_administrativo(self):
        """NCG 17 tiene acto_administrativo de RE N.° 6595."""
        aa = _xpath(self.root, "//n:acto_administrativo")
        self.assertEqual(len(aa), 1)
        tipo = _xpath(aa[0], "n:tipo/text()")
        self.assertEqual(tipo[0], "RESOLUCIÓN EXENTA")
        numero = _xpath(aa[0], "n:numero/text()")
        self.assertEqual(numero[0], "6595")

    def test_nine_considerandos(self):
        """NCG 17 tiene 9 considerandos (formato 'N. Que,')."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 9)
        self.assertEqual(cons[0].get("numero"), "1")
        self.assertEqual(cons[8].get("numero"), "9")

    def test_considerando_starts_with_que(self):
        """Considerandos inician con 'Que,' (sin prefijo numérico)."""
        c1 = _xpath(self.root, "//n:considerando[@numero='1']/n:parrafo/text()")
        self.assertTrue(
            c1[0].startswith("Que,"),
            f"Considerando 1 no inicia con 'Que,': '{c1[0][:30]}...'"
        )
        c9 = _xpath(self.root, "//n:considerando[@numero='9']/n:parrafo/text()")
        self.assertTrue(c9[0].startswith("Que,"))

    def test_resolutivo_pre_ncg(self):
        """NCG 17 tiene 1 punto resolutivo pre-NCG (APRUÉBASE)."""
        res = _xpath(self.root, "//n:resolutivo/n:punto")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].get("numero"), "1")
        self.assertIn("APRUÉBASE", res[0].text)

    def test_preambulo_ncg(self):
        """NCG 17 tiene preámbulo NCG."""
        pre = _xpath(self.root, "//n:preambulo_ncg/n:parrafo")
        self.assertEqual(len(pre), 1)
        self.assertIn("regula las materias", pre[0].text)

    def test_three_titulos(self):
        """NCG 17 tiene 3 títulos (I, II, III)."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 3)

    def test_titulo_i_nombre(self):
        """Título I: Nominación mediante Sorteo ante la Superintendencia."""
        t1 = _xpath(self.root, "//n:titulo[@numero='I']")
        self.assertIn("Sorteo", t1[0].get("nombre"))

    def test_titulo_iii_disposiciones_finales(self):
        """Título III: Disposiciones Finales."""
        t3 = _xpath(self.root, "//n:titulo[@numero='III']")
        self.assertIn("Disposiciones Finales", t3[0].get("nombre"))

    def test_eight_articulos(self):
        """NCG 17 tiene 8 artículos."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 8)

    def test_all_articulos_have_epigrafe(self):
        """Todos los 8 artículos de NCG 17 tienen epígrafe."""
        arts = _xpath(self.root, "//n:articulo")
        for art in arts:
            epigrafe = art.get("epigrafe", "")
            self.assertTrue(
                epigrafe,
                f"Art {art.get('numero')} sin epígrafe"
            )

    def test_art1_three_numbered_items(self):
        """Art 1° tiene listado con 3 items numerados (1, 2, 3)."""
        items = _xpath(self.root, "//n:articulo[@numero='1']/n:listado/n:item")
        self.assertEqual(len(items), 3)
        nums = [i.get("numero") for i in items]
        self.assertEqual(nums, ["1", "2", "3"])

    def test_art1_post_listado_parrafo(self):
        """Art 1° tiene párrafo post-listado ('El sistema seleccionará...')."""
        art1 = _xpath(self.root, "//n:articulo[@numero='1']")[0]
        children = list(art1)
        tags = [etree.QName(c.tag).localname for c in children]
        # Último elemento debe ser parrafo (post-listado)
        self.assertEqual(tags[-1], "parrafo")
        last_parr = children[-1]
        self.assertIn("seleccionará", last_parr.text)

    def test_art2_three_numbered_items(self):
        """Art 2° tiene listado con 3 items numerados (1, 2, 3)."""
        items = _xpath(self.root, "//n:articulo[@numero='2']/n:listado/n:item")
        self.assertEqual(len(items), 3)
        nums = [i.get("numero") for i in items]
        self.assertEqual(nums, ["1", "2", "3"])

    def test_art2_post_listado_parrafos(self):
        """Art 2° tiene párrafos post-listado (preparación de cédulas, etc.)."""
        art2 = _xpath(self.root, "//n:articulo[@numero='2']")[0]
        children = list(art2)
        tags = [etree.QName(c.tag).localname for c in children]
        # Debe tener: parrafo(s) + listado + parrafo(s) post-listado
        self.assertIn("listado", tags)
        listado_idx = tags.index("listado")
        post_parrafos = [t for t in tags[listado_idx + 1:] if t == "parrafo"]
        self.assertGreaterEqual(len(post_parrafos), 3)

    def test_resolutivo_final(self):
        """NCG 17 tiene 2 puntos resolutivos finales (PUBLÍQUESE, DISPÓNGASE)."""
        rf = _xpath(self.root, "//n:resolutivo_final/n:punto")
        self.assertEqual(len(rf), 2)
        self.assertEqual(rf[0].get("numero"), "2")
        self.assertIn("PUBLÍQUESE", rf[0].text)
        self.assertEqual(rf[1].get("numero"), "3")
        self.assertIn("DISPÓNGASE", rf[1].text)

    def test_cierre_formula(self):
        """Fórmula de cierre: ANÓTESE, PUBLÍQUESE Y ARCHÍVESE,"""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertIn("ARCHÍVESE", formula[0])
        self.assertTrue(formula[0].endswith(","))

    def test_firmante_hugo_sanchez(self):
        """NCG 17 firmada por Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertIn("SÁNCHEZ", nombre[0])
        cargo = _xpath(self.root, "//n:cierre/n:firmante/n:cargo/text()")
        self.assertEqual(cargo[0], "SUPERINTENDENTE DE INSOLVENCIA Y REEMPRENDIMIENTO")

    def test_distribucion(self):
        """NCG 17 tiene código de distribución PVL/PCP/CVS/POR."""
        dist = _xpath(self.root, "//n:cierre/n:distribucion/text()")
        self.assertEqual(len(dist), 1)
        self.assertEqual(dist[0], "PVL/PCP/CVS/POR")

    def test_no_standalone_anexos(self):
        """NCG 17 no tiene anexos."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 0)


class TestGenerateNCG18(unittest.TestCase):
    """Tests para NCG 18 - RE 6599, objeción cuenta final, 4 títulos, 12 arts.

    NCG 18 valida:
    - Primera NCG que revoca una Resolución Exenta (no otra NCG)
    - 4 títulos temáticos (no solo I+Disposiciones finales)
    - Arts 1-8 sin epígrafe, solo Arts 9-12 con epígrafe
    - Considerando 5° con 2 párrafos (primer multi-párrafo)
    - Sin preambulo_ncg (a diferencia de NCGs 14-17)
    - 3 resolutivo_final (PUBLÍQUESE, NOTIFÍQUESE, DISPÓNGASE)
    - Notificación con destinatarios en cierre
    - Distribución incluye 3 tipos de fiscalizados
    """

    @classmethod
    def setUpClass(cls):
        texto_path = (
            Path(__file__).parent.parent
            / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_18.txt"
        )
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_18.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        catalog = {
            "titulo_completo": "NORMA DE CARÁCTER GENERAL N°18 - Objeción de la cuenta final de administración",
            "resolucion_exenta": "6599",
            "fecha_publicacion": "2023-08-11",
            "materias": [
                "Objeción cuenta final",
                "Cuenta final de administración",
                "Liquidación",
            ],
            "leyes_habilitantes": ["20720", "21563"],
            "deroga": [],
            "modifica": [],
            "nombres_comunes": ["NCG de Objeción Cuenta Final"],
            "categoria": "Liquidación",
        }
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="18", catalog_entry=catalog)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_xsd(self):
        """NCG 18 XML valida contra superir_v1.xsd."""
        schema = etree.XMLSchema(etree.parse(str(SCHEMA_PATH)))
        doc = etree.fromstring(self.xml_str.encode("utf-8"))
        self.assertTrue(schema.validate(doc), schema.error_log)

    def test_acto_administrativo(self):
        """NCG 18 tiene acto_administrativo de RE N.° 6599."""
        aa = _xpath(self.root, "//n:acto_administrativo")
        self.assertEqual(len(aa), 1)
        tipo = _xpath(aa[0], "n:tipo/text()")
        self.assertEqual(tipo[0], "RESOLUCIÓN EXENTA")
        numero = _xpath(aa[0], "n:numero/text()")
        self.assertEqual(numero[0], "6599")

    def test_six_considerandos(self):
        """NCG 18 tiene 6 considerandos."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 6)
        self.assertEqual(cons[0].get("numero"), "1")
        self.assertEqual(cons[5].get("numero"), "6")

    def test_considerando_starts_with_que(self):
        """Considerandos inician con 'Que,' (sin prefijo numérico)."""
        c1 = _xpath(self.root, "//n:considerando[@numero='1']/n:parrafo/text()")
        self.assertTrue(
            c1[0].startswith("Que,"),
            f"Considerando 1 no inicia con 'Que,': '{c1[0][:30]}...'"
        )

    def test_considerando_5_two_parrafos(self):
        """Considerando 5° tiene 2 párrafos (primer multi-párrafo en NCGs)."""
        c5_parrafos = _xpath(
            self.root, "//n:considerando[@numero='5']/n:parrafo"
        )
        self.assertEqual(len(c5_parrafos), 2)
        self.assertIn("artículo 281", c5_parrafos[0].text)
        self.assertIn("Lo anterior", c5_parrafos[1].text)

    def test_resolutivo_pre_ncg(self):
        """NCG 18 tiene 1 punto resolutivo pre-NCG (APRUÉBASE)."""
        res = _xpath(self.root, "//n:resolutivo/n:punto")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].get("numero"), "1")
        self.assertIn("APRUÉBASE", res[0].text)

    def test_no_preambulo_ncg(self):
        """NCG 18 NO tiene preámbulo NCG (a diferencia de NCGs 14-17)."""
        pre = _xpath(self.root, "//n:preambulo_ncg")
        self.assertEqual(len(pre), 0)

    def test_four_titulos(self):
        """NCG 18 tiene 4 títulos (I, II, III, IV)."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 4)
        nums = [t.get("numero") for t in titulos]
        self.assertEqual(nums, ["I", "II", "III", "IV"])

    def test_titulo_i_name(self):
        """Título I: materias relativas a la objeción de la cuenta final."""
        t1 = _xpath(self.root, "//n:titulo[@numero='I']")
        self.assertIn("objeción", t1[0].get("nombre").lower())

    def test_titulo_ii_name(self):
        """Título II: Obligaciones del Liquidador, publicaciones Boletín."""
        t2 = _xpath(self.root, "//n:titulo[@numero='II']")
        self.assertIn("Boletín Concursal", t2[0].get("nombre"))

    def test_titulo_iv_disposiciones_finales(self):
        """Título IV: Disposiciones finales."""
        t4 = _xpath(self.root, "//n:titulo[@numero='IV']")
        self.assertIn("Disposiciones finales", t4[0].get("nombre"))

    def test_twelve_articulos(self):
        """NCG 18 tiene 12 artículos."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 12)

    def test_arts_1_to_8_no_epigrafe(self):
        """Arts 1° a 8° carecen de epígrafe formal."""
        for num in range(1, 9):
            art = _xpath(self.root, f"//n:articulo[@numero='{num}']")
            self.assertEqual(len(art), 1)
            epigrafe = art[0].get("epigrafe", "")
            self.assertFalse(
                epigrafe,
                f"Art {num} tiene epígrafe inesperado: '{epigrafe}'"
            )

    def test_arts_9_to_12_have_epigrafe(self):
        """Arts 9° a 12° tienen epígrafe."""
        expected = {
            "9": "Ámbito de aplicación",
            "10": "Cómputo de plazos",
            "11": "Revocación",
            "12": "Vigencia",
        }
        for num, ep in expected.items():
            art = _xpath(self.root, f"//n:articulo[@numero='{num}']")
            self.assertEqual(len(art), 1)
            self.assertEqual(art[0].get("epigrafe"), ep)

    def test_art1_two_parrafos(self):
        """Art 1° tiene 2 párrafos (objeciones + insistencias)."""
        parrs = _xpath(self.root, "//n:articulo[@numero='1']/n:parrafo")
        self.assertEqual(len(parrs), 2)

    def test_art2_references_portal(self):
        """Art 2° referencia Portal Mi Superir con ClaveÚnica."""
        parrs = _xpath(self.root, "//n:articulo[@numero='2']/n:parrafo")
        texto_completo = " ".join(p.text for p in parrs)
        self.assertIn("Portal Mi Superir", texto_completo)
        self.assertIn("Clave Única", texto_completo)

    def test_art5_two_parrafos(self):
        """Art 5° tiene 2 párrafos (no 3 — page break fusionado)."""
        parrs = _xpath(self.root, "//n:articulo[@numero='5']/n:parrafo")
        self.assertEqual(len(parrs), 2)
        # Primer párrafo debe contener "artículo 52" (fusionado)
        self.assertIn("artículo 52", parrs[0].text)

    def test_art8_two_parrafos(self):
        """Art 8° tiene 2 párrafos (no 3 — page break fusionado)."""
        parrs = _xpath(self.root, "//n:articulo[@numero='8']/n:parrafo")
        self.assertEqual(len(parrs), 2)
        # Primer párrafo debe contener "presente Norma" (fusionado)
        self.assertIn("presente Norma", parrs[0].text)

    def test_art9_three_parrafos(self):
        """Art 9° tiene 3 párrafos (ámbito de aplicación extendido)."""
        parrs = _xpath(self.root, "//n:articulo[@numero='9']/n:parrafo")
        self.assertEqual(len(parrs), 3)

    def test_art9_references_modulo_comunicacion(self):
        """Art 9° referencia Módulo de Comunicación Directa."""
        parrs = _xpath(self.root, "//n:articulo[@numero='9']/n:parrafo")
        texto_completo = " ".join(p.text for p in parrs)
        self.assertIn("Módulo de Comunicación Directa", texto_completo)

    def test_art11_revocacion_re_11902(self):
        """Art 11° revoca RE N.° 11902 de 2018 (no otra NCG)."""
        parrs = _xpath(self.root, "//n:articulo[@numero='11']/n:parrafo")
        self.assertIn("11902", parrs[0].text)
        self.assertIn("2018", parrs[0].text)

    def test_art12_vigencia(self):
        """Art 12° tiene 2 párrafos (vigencia + régimen transitorio)."""
        parrs = _xpath(self.root, "//n:articulo[@numero='12']/n:parrafo")
        self.assertEqual(len(parrs), 2)

    def test_resolutivo_final_three_points(self):
        """NCG 18 tiene 3 resolutivo_final (PUBLÍQUESE, NOTIFÍQUESE, DISPÓNGASE)."""
        rf = _xpath(self.root, "//n:resolutivo_final/n:punto")
        self.assertEqual(len(rf), 3)
        self.assertEqual(rf[0].get("numero"), "2")
        self.assertIn("PUBLÍQUESE", rf[0].text)
        self.assertEqual(rf[1].get("numero"), "3")
        self.assertIn("NOTIFÍQUESE", rf[1].text)
        self.assertEqual(rf[2].get("numero"), "4")
        self.assertIn("DISPÓNGASE", rf[2].text)

    def test_cierre_formula(self):
        """Fórmula de cierre: ANÓTESE, PUBLÍQUESE Y ARCHÍVESE,"""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertIn("ARCHÍVESE", formula[0])

    def test_firmante_hugo_sanchez(self):
        """NCG 18 firmada por Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertIn("SÁNCHEZ", nombre[0])
        cargo = _xpath(self.root, "//n:cierre/n:firmante/n:cargo/text()")
        self.assertEqual(
            cargo[0], "SUPERINTENDENTE DE INSOLVENCIA Y REEMPRENDIMIENTO"
        )

    def test_distribucion(self):
        """NCG 18 tiene código de distribución PVL/JAA/EGZ/DTC/FRR."""
        dist = _xpath(self.root, "//n:cierre/n:distribucion/text()")
        self.assertEqual(len(dist), 1)
        self.assertEqual(dist[0], "PVL/JAA/EGZ/DTC/FRR")

    def test_notificacion_with_destinatarios(self):
        """NCG 18 tiene notificación con 3 destinatarios."""
        notif = _xpath(self.root, "//n:cierre/n:notificacion/n:destinatarios/text()")
        self.assertEqual(len(notif), 1)
        self.assertIn("Liquidadores/as", notif[0])
        self.assertIn("Veedores/as", notif[0])
        self.assertIn("Martilleros/as", notif[0])

    def test_no_standalone_anexos(self):
        """NCG 18 no tiene anexos."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 0)


class TestGenerateNCG19(unittest.TestCase):
    """Tests de generación XML para NCG 19 — Certificado de deudas y DJ reorganización.

    NCG 19 es la primera que:
    - Tiene items letrados mayúsculas A.- a G.- (Art 1°)
    - Item E contiene subitems letrados a), b) + párrafos post-sublistado
    - Solo 4 artículos en 3 títulos
    - No revoca NCG anterior (materia nueva)
    - Contiene 2 Anexos (formularios-espejo: I con auditor, II con DJ)
    - Distribución 6 iniciales: PVL/JAA/EGZ/DTC/RAA/MLS
    """

    @classmethod
    def setUpClass(cls):
        texto_path = (
            Path(__file__).parent.parent
            / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_19.txt"
        )
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_19.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        catalog = {
            "titulo_completo": "NORMA DE CARÁCTER GENERAL N°19 - Certificación y declaración jurada en procedimiento de reorganización",
            "resolucion_exenta": "6600",
            "fecha_publicacion": "2023-08-11",
            "materias": [
                "Certificado estado deudas",
                "Declaración jurada reorganización",
                "Reorganización",
            ],
            "leyes_habilitantes": ["20720", "21563"],
            "deroga": [],
            "modifica": [],
            "nombres_comunes": ["NCG de Certificado de Deudas"],
            "categoria": "Reorganización",
        }
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="19", catalog_entry=catalog)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_against_xsd(self):
        """XML valida contra superir_v1.xsd."""
        schema_doc = etree.parse(str(SCHEMA_PATH))
        schema = etree.XMLSchema(schema_doc)
        doc = _parse_xml(self.xml_str)
        is_valid = schema.validate(doc)
        if not is_valid:
            for error in schema.error_log:
                print(f"  Validación: {error}")
        self.assertTrue(is_valid, "XML no valida contra superir_v1.xsd")

    def test_acto_administrativo_re_6600(self):
        """Acto administrativo es RE 6600."""
        tipo = _xpath(self.root, "//n:acto_administrativo/n:tipo/text()")
        self.assertEqual(tipo, ["RESOLUCIÓN EXENTA"])
        num = _xpath(self.root, "//n:acto_administrativo/n:numero/text()")
        self.assertEqual(num, ["6600"])

    def test_six_considerandos(self):
        """NCG 19 tiene 6 considerandos."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 6)

    def test_considerandos_start_with_que(self):
        """Cada considerando empieza con 'Que,'."""
        for i in range(1, 7):
            text = _xpath(
                self.root,
                f"//n:considerando[@numero='{i}']/n:parrafo/text()",
            )
            self.assertTrue(
                text[0].startswith("Que,"),
                f"Considerando {i} no empieza con 'Que,': {text[0][:40]}",
            )

    def test_considerando_6_formula_dictacion(self):
        """Considerando 6° es la fórmula de dictación (atendido lo expuesto)."""
        text = _xpath(
            self.root,
            "//n:considerando[@numero='6']/n:parrafo/text()",
        )
        self.assertIn("atendido lo expuesto", text[0])

    def test_one_resolutivo_pre_ncg(self):
        """1 punto resolutivo (APRUÉBASE)."""
        res = _xpath(self.root, "//n:resolutivo/n:punto")
        self.assertEqual(len(res), 1)
        self.assertIn("APRUÉBASE", res[0].text)

    def test_no_preambulo_ncg(self):
        """NCG 19 no tiene preámbulo NCG."""
        pre = _xpath(self.root, "//n:preambulo_ncg")
        self.assertEqual(len(pre), 0)

    def test_three_titulos(self):
        """3 títulos: I, II, III."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 3)
        nums = [t.get("numero") for t in titulos]
        self.assertEqual(nums, ["I", "II", "III"])

    def test_titulo_i_name(self):
        """Título I es sobre certificado de deudas por auditor."""
        t1 = _xpath(self.root, "//n:titulo[@numero='I']")[0]
        self.assertIn("Certificado del Estado de Deudas", t1.get("nombre"))

    def test_titulo_ii_name(self):
        """Título II es sobre DJ en reorganización simplificada."""
        t2 = _xpath(self.root, "//n:titulo[@numero='II']")[0]
        self.assertIn("Reorganización Simplificada", t2.get("nombre"))

    def test_titulo_iii_disposiciones_finales(self):
        """Título III es 'Disposiciones Finales'."""
        t3 = _xpath(self.root, "//n:titulo[@numero='III']")[0]
        self.assertIn("Disposiciones Finales", t3.get("nombre"))

    def test_four_articulos(self):
        """4 artículos totales."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 4)

    def test_art1_epigrafe_requisitos(self):
        """Art 1° tiene epígrafe 'Requisitos'."""
        art1 = _xpath(self.root, "//n:articulo[@numero='1']")[0]
        self.assertEqual(art1.get("epigrafe"), "Requisitos")

    def test_art1_intro_parrafo(self):
        """Art 1° tiene 1 párrafo introductorio antes del listado."""
        art1 = _xpath(self.root, "//n:articulo[@numero='1']")[0]
        parrafos = _xpath(art1, "n:parrafo/text()")
        self.assertTrue(len(parrafos) >= 1)
        self.assertIn("Según lo establecido", parrafos[0])

    def test_art1_listado_seven_items(self):
        """Art 1° tiene listado con 7 items (A-G)."""
        items = _xpath(self.root, "//n:articulo[@numero='1']/n:listado/n:item")
        self.assertEqual(len(items), 7)
        letras = [it.get("letra") for it in items]
        self.assertEqual(letras, ["A", "B", "C", "D", "E", "F", "G"])

    def test_art1_item_a_single_text(self):
        """Item A es simple (texto directo, page break merged)."""
        item_a = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='A']",
        )[0]
        # Item A debería tener texto directo (page break "numeral/4" merged)
        text = item_a.text or ""
        parrafos = _xpath(item_a, "n:parrafo/text()")
        # Puede ser texto directo o párrafos, lo importante es que
        # el contenido complete incluye "individualización" y "artículo 56"
        full = text + " ".join(parrafos)
        self.assertIn("individualización", full)

    def test_art1_item_b_two_parrafos(self):
        """Item B tiene 2 párrafos (detalle pasivos + aclaratorio)."""
        item_b = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='B']",
        )[0]
        parrafos = _xpath(item_b, "n:parrafo/text()")
        self.assertEqual(len(parrafos), 2)
        self.assertIn("detalle de los pasivos", parrafos[0])
        self.assertIn("acreedores laborales y previsionales", parrafos[1])

    def test_art1_item_e_complex_with_subitems(self):
        """Item E tiene subitems letrados a), b)."""
        item_e = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='E']",
        )[0]
        subitems = _xpath(item_e, "n:sublistado/n:subitem")
        self.assertEqual(len(subitems), 2)
        self.assertEqual(subitems[0].get("letra"), "a")
        self.assertEqual(subitems[1].get("letra"), "b")

    def test_art1_item_e_intro_parrafos(self):
        """Item E tiene párrafos introductorios antes del sublistado."""
        item_e = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='E']",
        )[0]
        # Los párrafos antes del sublistado
        all_parrafos = _xpath(item_e, "n:parrafo/text()")
        self.assertTrue(len(all_parrafos) >= 2)
        self.assertIn("Hechos Posteriores", all_parrafos[0])

    def test_art1_item_e_post_sublistado_parrafos(self):
        """Item E tiene párrafos después del sublistado."""
        item_e = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='E']",
        )[0]
        all_parrafos = _xpath(item_e, "n:parrafo/text()")
        # Debe haber párrafos después del sublistado con "Estos hechos"
        post_texts = [p for p in all_parrafos if "Estos hechos" in p]
        self.assertTrue(len(post_texts) >= 1, "Faltan párrafos post-sublistado en item E")

    def test_art1_item_f_two_parrafos(self):
        """Item F tiene 2 párrafos."""
        item_f = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='F']",
        )[0]
        parrafos = _xpath(item_f, "n:parrafo/text()")
        self.assertEqual(len(parrafos), 2)
        self.assertIn("Informe final", parrafos[0])

    def test_art2_no_epigrafe(self):
        """Art 2° no tiene epígrafe."""
        art2 = _xpath(self.root, "//n:articulo[@numero='2']")[0]
        self.assertIsNone(art2.get("epigrafe"))

    def test_art2_references_anexo_ii(self):
        """Art 2° referencia el Anexo II."""
        art2_text = _xpath(self.root, "//n:articulo[@numero='2']/n:parrafo/text()")
        full = " ".join(art2_text)
        self.assertIn("Anexo II", full)

    def test_art3_epigrafe_ambito(self):
        """Art 3° tiene epígrafe 'Ámbito de aplicación'."""
        art3 = _xpath(self.root, "//n:articulo[@numero='3']")[0]
        self.assertEqual(art3.get("epigrafe"), "Ámbito de aplicación")

    def test_art4_epigrafe_vigencia(self):
        """Art 4° tiene epígrafe 'Vigencia'."""
        art4 = _xpath(self.root, "//n:articulo[@numero='4']")[0]
        self.assertEqual(art4.get("epigrafe"), "Vigencia")

    def test_art4_references_ley_21563(self):
        """Art 4° referencia la Ley 21.563."""
        art4_text = _xpath(self.root, "//n:articulo[@numero='4']/n:parrafo/text()")
        full = " ".join(art4_text)
        self.assertIn("21.563", full)

    def test_three_resolutivo_final(self):
        """3 puntos resolutivos finales."""
        puntos = _xpath(self.root, "//n:resolutivo_final/n:punto")
        self.assertEqual(len(puntos), 3)

    def test_resolutivo_final_publiquese(self):
        """Punto 2° es PUBLÍQUESE."""
        p2 = _xpath(self.root, "//n:resolutivo_final/n:punto[@numero='2']")[0]
        self.assertIn("PUBLÍQUESE", p2.text)

    def test_resolutivo_final_notifiquese(self):
        """Punto 3° es NOTIFÍQUESE."""
        p3 = _xpath(self.root, "//n:resolutivo_final/n:punto[@numero='3']")[0]
        self.assertIn("NOTIFÍQUESE", p3.text)

    def test_resolutivo_final_dispongase(self):
        """Punto 4° es DISPÓNGASE."""
        p4 = _xpath(self.root, "//n:resolutivo_final/n:punto[@numero='4']")[0]
        self.assertIn("DISPÓNGASE", p4.text)

    def test_cierre_formula(self):
        """Fórmula de cierre."""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertIn("ANÓTESE", formula[0])

    def test_firmante_hugo_sanchez(self):
        """Firmante es Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertEqual(nombre, ["HUGO SÁNCHEZ RAMÍREZ"])

    def test_distribucion_six_initials(self):
        """Distribución PVL/JAA/EGZ/DTC/RAA/MLS (6 iniciales)."""
        dist = _xpath(self.root, "//n:cierre/n:distribucion/text()")
        self.assertEqual(dist, ["PVL/JAA/EGZ/DTC/RAA/MLS"])

    def test_notificacion_veedores(self):
        """Notificación solo a Veedores/as."""
        notif = _xpath(self.root, "//n:cierre/n:notificacion/n:destinatarios/text()")
        self.assertEqual(len(notif), 1)
        self.assertIn("Veedores/as", notif[0])

    def test_two_standalone_anexos(self):
        """2 anexos standalone (I y II)."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 2)
        nums = [a.get("numero") for a in anexos]
        self.assertEqual(nums, ["I", "II"])

    def test_no_spurious_anexo_c(self):
        """No hay anexo espurio 'c' (bug PATRON_ANEXO_NUMS con IGNORECASE)."""
        anexos = _xpath(self.root, "//n:anexo")
        nums = [a.get("numero") for a in anexos]
        self.assertNotIn("c", nums)
        self.assertNotIn("C", nums)


class TestGenerateNCG20(unittest.TestCase):
    """Tests de generación XML para NCG 20 — Informe estado cumplimiento ARJ.

    NCG 20 es la primera que:
    - Tiene items letrados mayúsculas sin dash: A. (no A.-)
    - Item A tiene subitems alfanuméricos intercalados a.1), a.2)
      con párrafos intermedios (content_blocks)
    - Art 2° usa items romanos i-vi (incluye vi, no cubierto antes)
    - 7 anexos con numeración compuesta: I-A, I-B, II, III, IV, V-A, V-B
    - Distribución 6 iniciales: PVL/JAA/EGZ/DTC/RAA/SCP
    """

    @classmethod
    def setUpClass(cls):
        texto_path = (
            Path(__file__).parent.parent
            / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_20.txt"
        )
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_20.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        catalog = {
            "titulo_completo": "NORMA DE CARÁCTER GENERAL N°20 - Informe sobre estado de cumplimiento del Acuerdo de Reorganización Judicial",
            "resolucion_exenta": "6617",
            "fecha_publicacion": "2023-08-11",
            "materias": [
                "Informe cumplimiento ARJ",
                "Interventor/a",
                "Reorganización",
            ],
            "leyes_habilitantes": ["20720", "21563"],
            "deroga": [],
            "modifica": [],
            "nombres_comunes": ["NCG de Informe Cumplimiento ARJ"],
            "categoria": "Reorganización",
        }
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="20", catalog_entry=catalog)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_against_xsd(self):
        """XML valida contra superir_v1.xsd."""
        schema_doc = etree.parse(str(SCHEMA_PATH))
        schema = etree.XMLSchema(schema_doc)
        doc = _parse_xml(self.xml_str)
        is_valid = schema.validate(doc)
        if not is_valid:
            for error in schema.error_log:
                print(f"  Validación: {error}")
        self.assertTrue(is_valid, "XML no valida contra superir_v1.xsd")

    def test_acto_administrativo_re_6617(self):
        """Acto administrativo es RE 6617."""
        num = _xpath(self.root, "//n:acto_administrativo/n:numero/text()")
        self.assertEqual(num, ["6617"])

    def test_four_considerandos(self):
        """NCG 20 tiene 4 considerandos."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 4)

    def test_two_titulos(self):
        """2 títulos: I y II."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 2)
        nums = [t.get("numero") for t in titulos]
        self.assertEqual(nums, ["I", "II"])

    def test_six_articulos(self):
        """6 artículos totales."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 6)

    def test_art1_epigrafe(self):
        """Art 1° tiene epígrafe."""
        art1 = _xpath(self.root, "//n:articulo[@numero='1']")[0]
        self.assertIsNotNone(art1.get("epigrafe"))

    def test_art1_six_uppercase_items(self):
        """Art 1° tiene 6 items letrados mayúsculas A-F."""
        items = _xpath(self.root, "//n:articulo[@numero='1']/n:listado/n:item")
        self.assertEqual(len(items), 6)
        letras = [it.get("letra") for it in items]
        self.assertEqual(letras, ["A", "B", "C", "D", "E", "F"])

    def test_art1_item_a_has_two_sublistados(self):
        """Item A tiene 2 sublistados (a.1 y a.2 intercalados)."""
        item_a = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='A']",
        )[0]
        sublists = _xpath(item_a, "n:sublistado")
        self.assertEqual(len(sublists), 2)

    def test_art1_item_a_subitem_a1(self):
        """Item A sublistado 1 tiene subitem a.1."""
        item_a = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='A']",
        )[0]
        sublists = _xpath(item_a, "n:sublistado")
        subs_1 = _xpath(sublists[0], "n:subitem")
        self.assertEqual(len(subs_1), 1)
        self.assertEqual(subs_1[0].get("numero"), "a.1")

    def test_art1_item_a_subitem_a2(self):
        """Item A sublistado 2 tiene subitem a.2."""
        item_a = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='A']",
        )[0]
        sublists = _xpath(item_a, "n:sublistado")
        subs_2 = _xpath(sublists[1], "n:subitem")
        self.assertEqual(len(subs_2), 1)
        self.assertEqual(subs_2[0].get("numero"), "a.2")

    def test_art1_item_a_intermediate_parrafo(self):
        """Item A tiene párrafo intermedio entre sublistados."""
        item_a = _xpath(
            self.root,
            "//n:articulo[@numero='1']/n:listado/n:item[@letra='A']",
        )[0]
        # Content should be: parrafos intro, sublistado a.1, parrafo, sublistado a.2
        all_parrafos = _xpath(item_a, "n:parrafo/text()")
        # At least 2 parrafos (intro + intermediate)
        self.assertGreaterEqual(len(all_parrafos), 2)

    def test_art2_epigrafe_documentacion(self):
        """Art 2° tiene epígrafe 'Documentación'."""
        art2 = _xpath(self.root, "//n:articulo[@numero='2']")[0]
        self.assertEqual(art2.get("epigrafe"), "Documentación")

    def test_art2_six_roman_items(self):
        """Art 2° tiene 6 items romanos i-vi."""
        items = _xpath(self.root, "//n:articulo[@numero='2']/n:listado/n:item")
        self.assertEqual(len(items), 6)
        nums = [it.get("numero") for it in items]
        self.assertEqual(nums, ["i", "ii", "iii", "iv", "v", "vi"])

    def test_art2_item_vi_flujo_caja(self):
        """Item vi es 'Flujo de caja'."""
        items = _xpath(self.root, "//n:articulo[@numero='2']/n:listado/n:item")
        last = items[-1]
        self.assertEqual(last.get("numero"), "vi")
        self.assertIn("Flujo de caja", last.text)

    def test_seven_compound_anexos(self):
        """7 anexos con numeración compuesta."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 7)
        nums = [a.get("numero") for a in anexos]
        self.assertEqual(nums, ["I-A", "I-B", "II", "III", "IV", "V-A", "V-B"])

    def test_anexo_ia_titulo(self):
        """Anexo I-A tiene título con 'Indicadores Financieros'."""
        ia = _xpath(self.root, "//n:anexo[@numero='I-A']")[0]
        self.assertIn("Indicadores Financieros", ia.get("titulo", ""))

    def test_anexo_vb_titulo(self):
        """Anexo V-B tiene título con 'comparativo'."""
        vb = _xpath(self.root, "//n:anexo[@numero='V-B']")[0]
        self.assertIn("comparativo", ia_titulo := vb.get("titulo", "").lower())

    def test_three_resolutivo_final(self):
        """3 puntos resolutivos finales."""
        puntos = _xpath(self.root, "//n:resolutivo_final/n:punto")
        self.assertEqual(len(puntos), 3)

    def test_cierre_formula(self):
        """Fórmula de cierre con ANÓTESE."""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertIn("ANÓTESE", formula[0])

    def test_firmante_hugo_sanchez(self):
        """Firmante es Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertEqual(nombre, ["HUGO SÁNCHEZ RAMÍREZ"])

    def test_distribucion_with_scp(self):
        """Distribución incluye SCP (variante nueva)."""
        dist = _xpath(self.root, "//n:cierre/n:distribucion/text()")
        self.assertIn("SCP", dist[0])

    def test_notificacion_veedores(self):
        """Notificación solo a Veedores/as."""
        notif = _xpath(self.root, "//n:cierre/n:notificacion/n:destinatarios/text()")
        self.assertIn("Veedores/as", notif[0])


class TestGenerateNCG22(unittest.TestCase):
    """Tests de generación XML para NCG 22 — Liquidación Voluntaria Simplificada.

    NCG 22 es la más extensa y compleja de todas las procesadas:
    - 10 artículos en 3 títulos
    - 7 considerandos (5° empieza con "Asimismo" en vez de "Que,")
    - Art 4° tiene items letrados a-g (formato "a." sin paréntesis)
    - Art 6° tiene estructura compleja: items a-i con subitems alfanuméricos
      embebidos (a.1-a.6, b.1-b.8, f.1-f.5, g.1-g.2, h.1)
    - 12 anexos standalone con numeración arábiga: 1, 2-A, 2-B, 3-11
    - RE 6619, firmante Hugo Sánchez Ramírez
    - Distribución PVL/JAA/EGZ/CBP/DTC/FRC
    - Destinatarios: solo Liquidadores/as
    """

    @classmethod
    def setUpClass(cls):
        texto_path = (
            Path(__file__).parent.parent
            / "biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_22.txt"
        )
        if not texto_path.exists():
            raise unittest.SkipTest("NCG_22.txt no encontrado")
        texto = texto_path.read_text(encoding="utf-8")
        catalog = {
            "titulo_completo": "NORMA DE CARÁCTER GENERAL N°22 - Plataforma electrónica para enajenación de activos en liquidación",
            "resolucion_exenta": "6619",
            "fecha_publicacion": "2023-08-11",
            "materias": [
                "Plataforma electrónica",
                "Enajenación de activos",
                "Liquidación",
            ],
            "leyes_habilitantes": ["20720", "21563"],
            "deroga": [],
            "modifica": [],
            "nombres_comunes": ["NCG de Enajenación de Activos"],
            "categoria": "Liquidación",
        }
        parser = SuperirStructuredParser()
        cls.norma = parser.parse(texto, doc_numero="22", catalog_entry=catalog)
        gen = SuperirXMLGenerator()
        cls.xml_str = gen.generate(cls.norma)
        cls.root = _parse_xml(cls.xml_str)

    def test_validates_against_xsd(self):
        """XML valida contra superir_v1.xsd."""
        schema_doc = etree.parse(str(SCHEMA_PATH))
        schema = etree.XMLSchema(schema_doc)
        doc = _parse_xml(self.xml_str)
        is_valid = schema.validate(doc)
        if not is_valid:
            for error in schema.error_log:
                print(f"  Validación: {error}")
        self.assertTrue(is_valid, "XML no valida contra superir_v1.xsd")

    def test_acto_administrativo_re_6619(self):
        """Acto administrativo es RE 6619."""
        num = _xpath(self.root, "//n:acto_administrativo/n:numero/text()")
        self.assertEqual(num, ["6619"])

    def test_seven_considerandos(self):
        """NCG 22 tiene 7 considerandos."""
        cons = _xpath(self.root, "//n:considerandos/n:considerando")
        self.assertEqual(len(cons), 7)

    def test_considerando_5_asimismo(self):
        """Considerando 5° empieza con 'Asimismo' (no 'Que,')."""
        c5 = _xpath(
            self.root,
            "//n:considerandos/n:considerando[@numero='5']/n:parrafo/text()",
        )
        self.assertTrue(c5[0].startswith("Asimismo"))

    def test_considerando_4_separate_from_5(self):
        """Considerando 4° no contiene el texto del 5°."""
        c4 = _xpath(
            self.root,
            "//n:considerandos/n:considerando[@numero='4']/n:parrafo/text()",
        )
        for p in c4:
            self.assertNotIn("Asimismo", p)

    def test_three_titulos(self):
        """3 títulos: I, II, III."""
        titulos = _xpath(self.root, "//n:cuerpo_normativo/n:titulo")
        self.assertEqual(len(titulos), 3)
        nums = [t.get("numero") for t in titulos]
        self.assertEqual(nums, ["I", "II", "III"])

    def test_titulo_i_nombre(self):
        """Título I: DE LA ACREDITACIÓN."""
        t1 = _xpath(self.root, "//n:cuerpo_normativo/n:titulo[@numero='I']")[0]
        self.assertIn("ACREDITACIÓN", t1.get("nombre", ""))

    def test_titulo_iii_disposiciones_finales(self):
        """Título III: DISPOSICIONES FINALES."""
        t3 = _xpath(self.root, "//n:cuerpo_normativo/n:titulo[@numero='III']")[0]
        self.assertIn("DISPOSICIONES FINALES", t3.get("nombre", ""))

    def test_ten_articulos(self):
        """10 artículos totales."""
        arts = _xpath(self.root, "//n:articulo")
        self.assertEqual(len(arts), 10)

    def test_art4_epigrafe(self):
        """Art 4° tiene epígrafe 'Antecedentes que se deben acompañar'."""
        art4 = _xpath(self.root, "//n:articulo[@numero='4']")[0]
        self.assertIn("Antecedentes", art4.get("epigrafe", ""))

    def test_art4_seven_items_a_to_g(self):
        """Art 4° tiene 7 items letrados a-g."""
        items = _xpath(self.root, "//n:articulo[@numero='4']/n:listado/n:item")
        self.assertEqual(len(items), 7)
        letras = [it.get("letra") for it in items]
        self.assertEqual(letras, ["a", "b", "c", "d", "e", "f", "g"])

    def test_art6_no_epigrafe(self):
        """Art 6° no tiene epígrafe."""
        art6 = _xpath(self.root, "//n:articulo[@numero='6']")[0]
        ep = art6.get("epigrafe")
        self.assertTrue(ep is None or ep == "")

    def test_art6_nine_items_a_to_i(self):
        """Art 6° tiene 9 items letrados a-i."""
        items = _xpath(self.root, "//n:articulo[@numero='6']/n:listado/n:item")
        self.assertEqual(len(items), 9)
        letras = [it.get("letra") for it in items]
        self.assertEqual(letras, ["a", "b", "c", "d", "e", "f", "g", "h", "i"])

    def test_art6_item_a_mentions_subitems(self):
        """Art 6° item a) contiene subitems a.1 a a.6 en su texto."""
        item_a = _xpath(
            self.root,
            "//n:articulo[@numero='6']/n:listado/n:item[@letra='a']",
        )[0]
        # Los subitems a.1 - a.6 están embebidos en el texto del item
        texto = item_a.text or ""
        self.assertIn("a.1", texto)
        self.assertIn("a.6", texto)

    def test_art6_item_b_mentions_subitems(self):
        """Art 6° item b) contiene subitems b.1 a b.8 en su texto."""
        item_b = _xpath(
            self.root,
            "//n:articulo[@numero='6']/n:listado/n:item[@letra='b']",
        )[0]
        texto = item_b.text or ""
        self.assertIn("b.1", texto)
        self.assertIn("b.8", texto)

    def test_art10_vigencia_clean(self):
        """Art 10° solo tiene texto de vigencia, sin resolutivo final."""
        art10 = _xpath(self.root, "//n:articulo[@numero='10']")[0]
        parrafos = _xpath(art10, "n:parrafo/text()")
        for p in parrafos:
            self.assertNotIn("PUBLÍQUESE", p)
            self.assertNotIn("NOTIFÍQUESE", p)
            self.assertNotIn("DISPÓNGASE", p)

    def test_three_resolutivo_final(self):
        """3 puntos resolutivos finales (2°, 3°, 4°)."""
        puntos = _xpath(self.root, "//n:resolutivo_final/n:punto")
        self.assertEqual(len(puntos), 3)
        nums = [p.get("numero") for p in puntos]
        self.assertEqual(nums, ["2", "3", "4"])

    def test_resolutivo_final_publiquese(self):
        """Punto 2° es PUBLÍQUESE."""
        p2 = _xpath(self.root, "//n:resolutivo_final/n:punto[@numero='2']")[0]
        self.assertTrue(p2.text.startswith("PUBLÍQUESE"))

    def test_resolutivo_final_notifiquese(self):
        """Punto 3° es NOTIFÍQUESE."""
        p3 = _xpath(self.root, "//n:resolutivo_final/n:punto[@numero='3']")[0]
        self.assertTrue(p3.text.startswith("NOTIFÍQUESE"))

    def test_resolutivo_final_dispongase(self):
        """Punto 4° es DISPÓNGASE."""
        p4 = _xpath(self.root, "//n:resolutivo_final/n:punto[@numero='4']")[0]
        self.assertTrue(p4.text.startswith("DISPÓNGASE"))

    def test_cierre_formula(self):
        """Fórmula de cierre con ANÓTESE."""
        formula = _xpath(self.root, "//n:cierre/n:formula/text()")
        self.assertIn("ANÓTESE", formula[0])
        self.assertIn("ARCHÍVESE", formula[0])

    def test_firmante_hugo_sanchez(self):
        """Firmante es Hugo Sánchez Ramírez."""
        nombre = _xpath(self.root, "//n:cierre/n:firmante/n:nombre/text()")
        self.assertEqual(nombre, ["HUGO SÁNCHEZ RAMÍREZ"])

    def test_firmante_cargo_superintendente(self):
        """Cargo es Superintendente."""
        cargo = _xpath(self.root, "//n:cierre/n:firmante/n:cargo/text()")
        self.assertIn("SUPERINTENDENTE", cargo[0])

    def test_distribucion_pvl_jaa(self):
        """Distribución PVL/JAA/EGZ/CBP/DTC/FRC."""
        dist = _xpath(self.root, "//n:cierre/n:distribucion/text()")
        self.assertEqual(dist, ["PVL/JAA/EGZ/CBP/DTC/FRC"])

    def test_notificacion_liquidadores(self):
        """Notificación solo a Liquidadores/as."""
        notif = _xpath(self.root, "//n:cierre/n:notificacion/n:destinatarios/text()")
        self.assertIn("Liquidadores/as", notif[0])

    def test_twelve_anexos_standalone(self):
        """12 anexos standalone (1, 2-A, 2-B, 3-11)."""
        anexos = _xpath(self.root, "//n:anexo")
        self.assertEqual(len(anexos), 12)
        nums = [a.get("numero") for a in anexos]
        self.assertEqual(
            nums,
            ["1", "2-A", "2-B", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
        )

    def test_anexo_1_declaracion_jurada(self):
        """Anexo 1 es Modelo de Declaración Jurada."""
        a1 = _xpath(self.root, "//n:anexo[@numero='1']")[0]
        self.assertIn("Declaración Jurada", a1.get("titulo", ""))

    def test_anexo_2a_empresa_deudora(self):
        """Anexo 2-A es solicitud empresa deudora."""
        a2a = _xpath(self.root, "//n:anexo[@numero='2-A']")[0]
        self.assertIn("empresa deudora", a2a.get("titulo", ""))

    def test_anexo_2b_persona_deudora(self):
        """Anexo 2-B es solicitud persona deudora."""
        a2b = _xpath(self.root, "//n:anexo[@numero='2-B']")[0]
        self.assertIn("persona deudora", a2b.get("titulo", ""))

    def test_anexo_11_completitud(self):
        """Anexo 11 es declaración jurada de completitud."""
        a11 = _xpath(self.root, "//n:anexo[@numero='11']")[0]
        self.assertIn("completos y fehacientes", a11.get("titulo", ""))

    def test_all_anexos_pendiente(self):
        """Todos los anexos están marcados como pendiente."""
        anexos = _xpath(self.root, "//n:anexo")
        for a in anexos:
            self.assertEqual(a.get("pendiente"), "true", f"Anexo {a.get('numero')} no pendiente")


if __name__ == "__main__":
    unittest.main()
