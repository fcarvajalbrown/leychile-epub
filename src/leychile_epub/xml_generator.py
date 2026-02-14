"""
Generador de XML estructurado para legislación chilena.

Este módulo genera archivos XML optimizados para ser consumidos por
agentes de IA, con estructura semántica clara y metadatos completos.

El formato XML está diseñado para:
- Facilitar la comprensión por LLMs y agentes de IA
- Mantener la jerarquía legal (Libros > Títulos > Capítulos > Párrafos > Artículos)
- Preservar referencias cruzadas y contexto
- Permitir búsquedas semánticas eficientes

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.dom import minidom
from xml.etree import ElementTree as ET

from lxml import etree

from .scraper_v2 import BCNLawScraperV2, EstructuraFuncional, Norma

logger = logging.getLogger("leychile_epub.xml_generator")

# Ruta al esquema XSD
_SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "ley_v1.xsd"


class LawXMLGenerator:
    """Generador de XML estructurado para leyes chilenas.

    Genera archivos XML con estructura semántica optimizada para
    agentes de IA y procesamiento automatizado.

    Example:
        >>> from leychile_epub.xml_generator import LawXMLGenerator
        >>> generator = LawXMLGenerator()
        >>> xml_path = generator.generate_from_url(
        ...     "https://www.leychile.cl/Navegar?idNorma=172986",
        ...     output_dir="./biblioteca"
        ... )
    """

    # Mapeo de tipos de parte a nombres semánticos
    TIPO_MAPPING = {
        "libro": "libro",
        "título": "titulo",
        "titulo": "titulo",
        "capítulo": "capitulo",
        "capitulo": "capitulo",
        "párrafo": "parrafo",
        "parrafo": "parrafo",
        "artículo": "articulo",
        "articulo": "articulo",
        "disposición": "disposicion",
        "disposicion": "disposicion",
        "transitorio": "transitorio",
        "anexo": "anexo",
    }

    def __init__(self) -> None:
        """Inicializa el generador XML."""
        self.scraper = BCNLawScraperV2()
        logger.debug("LawXMLGenerator inicializado")

    def generate_from_url(
        self,
        url: str,
        output_dir: str = ".",
        filename: str | None = None,
    ) -> Path:
        """Genera un archivo XML desde una URL de LeyChile.

        Args:
            url: URL de la ley en LeyChile.
            output_dir: Directorio de salida.
            filename: Nombre del archivo (opcional).

        Returns:
            Path al archivo XML generado.
        """
        logger.info(f"Generando XML desde: {url}")

        # Obtener datos de la ley
        norma = self.scraper.scrape(url)

        # Generar XML
        return self.generate(norma, output_dir, filename)

    def generate(
        self,
        norma: Norma,
        output_dir: str = ".",
        filename: str | None = None,
    ) -> Path:
        """Genera un archivo XML desde un objeto Norma.

        Args:
            norma: Objeto Norma con los datos de la ley.
            output_dir: Directorio de salida.
            filename: Nombre del archivo (opcional).

        Returns:
            Path al archivo XML generado.
        """
        # Crear elemento raíz
        root = self._create_root(norma)

        # Agregar metadatos
        self._add_metadata(root, norma)

        # Agregar encabezado si existe
        if norma.encabezado_texto or norma.vistos_texto or norma.considerandos_texto:
            self._add_encabezado(root, norma)

        # Agregar contenido estructurado
        self._add_contenido(root, norma)

        # Agregar promulgación (BCN) o disposiciones finales (SUPERIR)
        if norma.disposiciones_finales_texto:
            self._add_disposiciones_finales(root, norma)
        elif norma.promulgacion_texto:
            self._add_promulgacion(root, norma)

        # Agregar anexos si existen
        if norma.anexos:
            self._add_anexos(root, norma)

        # Generar nombre de archivo
        output_path = self._get_output_path(norma, output_dir, filename)

        # Escribir archivo con formato bonito
        self._write_xml(root, output_path)

        logger.info(f"XML generado: {output_path}")
        return output_path

    # Tipos de norma que usan disposiciones_finales en vez de promulgación
    TIPOS_SUPERIR = {"Norma de Carácter General", "Instructivo"}

    def _is_superir(self, norma: Norma) -> bool:
        """Determina si la norma es de tipo SUPERIR."""
        return norma.identificador.tipo in self.TIPOS_SUPERIR

    def _create_root(self, norma: Norma) -> ET.Element:
        """Crea el elemento raíz del XML.

        Args:
            norma: Objeto Norma.

        Returns:
            Elemento raíz.
        """
        root = ET.Element("ley")

        # Atributos del documento
        root.set("xmlns", "https://leychile.cl/schema/ley/v1")
        root.set("version", "1.1")
        root.set("idioma", "es-CL")

        # Identificadores
        root.set("id_norma", norma.norma_id)
        root.set("tipo", norma.identificador.tipo)
        root.set("numero", norma.identificador.numero)

        # Estado
        if norma.derogado:
            root.set("estado", "derogada")
        else:
            root.set("estado", "vigente")

        # Fechas
        if norma.fecha_version:
            root.set("fecha_version", norma.fecha_version)
        if norma.identificador.fecha_promulgacion:
            root.set("fecha_promulgacion", norma.identificador.fecha_promulgacion)
        if norma.identificador.fecha_publicacion:
            root.set("fecha_publicacion", norma.identificador.fecha_publicacion)

        # Generación
        root.set("generado", datetime.now().isoformat())
        root.set("fuente", "Biblioteca del Congreso Nacional de Chile")
        root.set("url_original", norma.url_original)

        return root

    def _add_metadata(self, root: ET.Element, norma: Norma) -> None:
        """Agrega sección de metadatos.

        Args:
            root: Elemento raíz.
            norma: Objeto Norma.
        """
        metadata = ET.SubElement(root, "metadatos")

        # Título
        titulo = ET.SubElement(metadata, "titulo")
        titulo.text = norma.metadatos.titulo or norma.titulo_completo

        # Tipo y número
        tipo_numero = ET.SubElement(metadata, "identificacion")
        tipo_elem = ET.SubElement(tipo_numero, "tipo")
        tipo_elem.text = norma.identificador.tipo
        numero_elem = ET.SubElement(tipo_numero, "numero")
        numero_elem.text = norma.identificador.numero

        # Organismos
        if norma.identificador.organismos:
            organismos = ET.SubElement(metadata, "organismos")
            for org in norma.identificador.organismos:
                org_elem = ET.SubElement(organismos, "organismo")
                org_elem.text = org

        # Materias (solo temas, no entidades)
        if norma.metadatos.materias:
            materias = ET.SubElement(metadata, "materias")
            for materia in norma.metadatos.materias:
                mat_elem = ET.SubElement(materias, "materia")
                mat_elem.text = materia

        # Conceptos (entidades, instituciones, roles)
        if norma.metadatos.conceptos:
            conceptos = ET.SubElement(metadata, "conceptos")
            for concepto in norma.metadatos.conceptos:
                con_elem = ET.SubElement(conceptos, "concepto")
                con_elem.text = concepto

        # Nombres de uso común
        if norma.metadatos.nombres_uso_comun:
            nombres = ET.SubElement(metadata, "nombres_comunes")
            for nombre in norma.metadatos.nombres_uso_comun:
                nom_elem = ET.SubElement(nombres, "nombre")
                nom_elem.text = nombre

        # Fechas importantes
        fechas = ET.SubElement(metadata, "fechas")
        if norma.identificador.fecha_promulgacion:
            prom = ET.SubElement(fechas, "promulgacion")
            prom.text = norma.identificador.fecha_promulgacion
        if norma.identificador.fecha_publicacion:
            pub = ET.SubElement(fechas, "publicacion")
            pub.text = norma.identificador.fecha_publicacion
        if norma.fecha_version:
            ver = ET.SubElement(fechas, "version")
            ver.text = norma.fecha_version
        if norma.metadatos.fecha_derogacion:
            der = ET.SubElement(fechas, "derogacion")
            der.text = norma.metadatos.fecha_derogacion

        # Fuente
        if norma.metadatos.identificacion_fuente:
            fuente = ET.SubElement(metadata, "fuente")
            fuente.text = norma.metadatos.identificacion_fuente

        # Número fuente (resolución exenta)
        if norma.metadatos.numero_fuente:
            nfuente = ET.SubElement(metadata, "numero_fuente")
            nfuente.text = norma.metadatos.numero_fuente

        # Leyes referenciadas (con atributos estructurados)
        if norma.metadatos.leyes_referenciadas:
            leyes_ref = ET.SubElement(metadata, "leyes_referenciadas")
            for ref in norma.metadatos.leyes_referenciadas:
                ley_elem = ET.SubElement(leyes_ref, "ley_ref")
                ley_elem.text = ref
                # Parsear tipo y número de la referencia
                tipo_num = self._parse_ley_ref(ref)
                if tipo_num:
                    ley_elem.set("tipo", tipo_num[0])
                    ley_elem.set("numero", tipo_num[1])

        # Es tratado internacional
        if norma.es_tratado:
            tratado = ET.SubElement(metadata, "tratado")
            tratado.set("es_tratado", "true")
            if norma.metadatos.paises_tratado:
                for pais in norma.metadatos.paises_tratado:
                    pais_elem = ET.SubElement(tratado, "pais")
                    pais_elem.text = pais

    def _add_encabezado(self, root: ET.Element, norma: Norma) -> None:
        """Agrega el encabezado estructurado de la norma.

        Para normas SUPERIR genera <vistos> y <considerandos> separados.
        Para leyes BCN genera <texto> con el contenido plano.

        Args:
            root: Elemento raíz.
            norma: Objeto Norma.
        """
        encabezado = ET.SubElement(root, "encabezado")
        if norma.encabezado_derogado:
            encabezado.set("derogado", "true")

        # Si hay vistos/considerandos separados → estructura
        if norma.vistos_texto or norma.considerandos_texto:
            if norma.vistos_texto:
                vistos = ET.SubElement(encabezado, "vistos")
                vistos.text = norma.vistos_texto
            if norma.considerandos_texto:
                considerandos = ET.SubElement(encabezado, "considerandos")
                considerandos.text = norma.considerandos_texto
        elif norma.encabezado_texto:
            # Fallback: texto plano (leyes BCN)
            texto = ET.SubElement(encabezado, "texto")
            texto.text = norma.encabezado_texto

    def _add_contenido(self, root: ET.Element, norma: Norma) -> None:
        """Agrega el contenido estructurado de la ley.

        Args:
            root: Elemento raíz.
            norma: Objeto Norma.
        """
        contenido = ET.SubElement(root, "contenido")

        # Agregar estadísticas
        stats = self._calculate_stats(norma.estructuras)
        contenido.set("total_articulos", str(stats["articulos"]))
        contenido.set("total_libros", str(stats["libros"]))
        contenido.set("total_titulos", str(stats["titulos"]))
        contenido.set("total_capitulos", str(stats["capitulos"]))

        # Agregar estructuras recursivamente
        for estructura in norma.estructuras:
            self._add_estructura(contenido, estructura)

    def _add_estructura(
        self,
        parent: ET.Element,
        estructura: EstructuraFuncional,
        path: list[str] | None = None,
    ) -> None:
        """Agrega una estructura funcional recursivamente.

        Args:
            parent: Elemento padre.
            estructura: Estructura funcional a agregar.
            path: Ruta jerárquica (para contexto).
        """
        if path is None:
            path = []

        # Determinar nombre del tag
        tipo_lower = estructura.tipo_parte.lower()
        tag_name = self.TIPO_MAPPING.get(tipo_lower, "seccion")

        elem = ET.SubElement(parent, tag_name)

        # ID único
        if estructura.id_parte:
            elem.set("id", estructura.id_parte)

        # Tipo original
        elem.set("tipo_original", estructura.tipo_parte)

        # Número/nombre de la parte
        if estructura.nombre_parte:
            elem.set("numero", estructura.nombre_parte)

        # Estado
        if estructura.derogado:
            elem.set("estado", "derogado")
        if estructura.transitorio:
            elem.set("transitorio", "true")

        # Fecha de versión
        if estructura.fecha_version:
            elem.set("fecha_modificacion", estructura.fecha_version)

        # Título de la sección
        if estructura.titulo_parte:
            titulo_elem = ET.SubElement(elem, "titulo_seccion")
            titulo_elem.text = estructura.titulo_parte

        # Ruta jerárquica (contexto para IA)
        if path:
            contexto = ET.SubElement(elem, "contexto")
            contexto.text = " > ".join(path)

        # Materias específicas
        if estructura.materias:
            materias = ET.SubElement(elem, "materias")
            for materia in estructura.materias:
                mat_elem = ET.SubElement(materias, "materia")
                mat_elem.text = materia

        # Contenido textual
        if estructura.texto:
            # Para artículos, estructurar mejor el contenido
            if tag_name == "articulo":
                self._add_articulo_content(elem, estructura)
            else:
                texto_elem = ET.SubElement(elem, "texto")
                texto_elem.text = estructura.texto
        elif tag_name == "articulo":
            # Artículos sin texto: contenido vacío con nota del título
            contenido = ET.SubElement(elem, "contenido")
            if estructura.titulo_parte:
                parrafo = ET.SubElement(contenido, "parrafo")
                parrafo.text = estructura.titulo_parte

        # Procesar hijos recursivamente
        current_path = path + [self._get_display_title(estructura)]
        for hijo in estructura.hijos:
            self._add_estructura(elem, hijo, current_path)

    def _add_articulo_content(
        self, parent: ET.Element, estructura: EstructuraFuncional
    ) -> None:
        """Agrega el contenido estructurado de un artículo.

        Siempre usa <contenido> con <parrafo>/<inciso> para consistencia
        y para permitir referenciar párrafos e incisos con precisión.

        Args:
            parent: Elemento padre.
            estructura: Estructura del artículo.
        """
        texto = estructura.texto.strip()

        # Detectar si hay incisos numerados
        inciso_pattern = r"^(\d+)[°º.)\-]\s*"

        # Dividir en párrafos
        paragraphs = texto.split("\n\n")

        # Siempre usar <contenido> con <parrafo> (incluso para texto simple)
        contenido = ET.SubElement(parent, "contenido")
        inciso_num = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Verificar si es un inciso numerado
            match = re.match(inciso_pattern, para)
            if match:
                inciso_num += 1
                inciso = ET.SubElement(contenido, "inciso")
                inciso.set("numero", str(inciso_num))
                inciso.text = re.sub(inciso_pattern, "", para).strip()
            else:
                parrafo = ET.SubElement(contenido, "parrafo")
                parrafo.text = para

        # Detectar referencias a otros artículos
        refs = self._extract_references(texto)
        if refs:
            referencias = ET.SubElement(parent, "referencias")
            for ref in refs:
                ref_elem = ET.SubElement(referencias, "ref")
                ref_elem.set("articulo", ref)

    def _extract_references(self, texto: str) -> list[str]:
        """Extrae referencias a otros artículos.

        Args:
            texto: Texto a analizar.

        Returns:
            Lista de referencias encontradas.
        """
        pattern = r"art[íi]culo\s+(\d+(?:\s*(?:bis|ter|qu[aá]ter|quinquies|sexies|septies|octies|nonies|decies))?)"
        matches = re.findall(pattern, texto, re.IGNORECASE)
        return list({m.lower().replace(" ", "") for m in matches})

    def _add_promulgacion(self, root: ET.Element, norma: Norma) -> None:
        """Agrega el texto de promulgación (leyes BCN).

        Args:
            root: Elemento raíz.
            norma: Objeto Norma.
        """
        promulgacion = ET.SubElement(root, "promulgacion")
        if norma.promulgacion_derogado:
            promulgacion.set("derogado", "true")
        promulgacion.text = norma.promulgacion_texto

    def _add_disposiciones_finales(self, root: ET.Element, norma: Norma) -> None:
        """Agrega las disposiciones finales (normas SUPERIR).

        Reemplaza <promulgacion> para NCG e Instructivos, con el nombre
        semántico correcto: notificación, vigencia, publicación, etc.

        Args:
            root: Elemento raíz.
            norma: Objeto Norma.
        """
        disp = ET.SubElement(root, "disposiciones_finales")
        texto = ET.SubElement(disp, "texto")
        texto.text = norma.disposiciones_finales_texto

    @staticmethod
    def _parse_ley_ref(ref: str) -> tuple[str, str] | None:
        """Parsea una referencia a norma en tipo y número.

        Args:
            ref: String como "Ley 20.720", "DFL 1-19.653", "NCG 7", "D.S. 8".

        Returns:
            Tupla (tipo, numero) o None si no se puede parsear.
        """
        patterns = [
            (r"^Ley\s+(.+)$", "Ley"),
            (r"^DFL\s+(.+)$", "DFL"),
            (r"^D\.S\.\s+(.+)$", "D.S."),
            (r"^NCG\s+(.+)$", "NCG"),
        ]
        for pattern, tipo in patterns:
            match = re.match(pattern, ref)
            if match:
                return (tipo, match.group(1))
        return None

    def _add_anexos(self, root: ET.Element, norma: Norma) -> None:
        """Agrega los anexos de la ley.

        Args:
            root: Elemento raíz.
            norma: Objeto Norma.
        """
        anexos_elem = ET.SubElement(root, "anexos")

        for i, anexo in enumerate(norma.anexos, 1):
            anexo_elem = ET.SubElement(anexos_elem, "anexo")
            anexo_elem.set("numero", str(i))

            if anexo.get("id_parte"):
                anexo_elem.set("id", anexo["id_parte"])
            if anexo.get("derogado"):
                anexo_elem.set("estado", "derogado")

            if anexo.get("titulo"):
                titulo = ET.SubElement(anexo_elem, "titulo")
                titulo.text = anexo["titulo"]

            if anexo.get("materias"):
                materias = ET.SubElement(anexo_elem, "materias")
                for materia in anexo["materias"]:
                    mat_elem = ET.SubElement(materias, "materia")
                    mat_elem.text = materia

            if anexo.get("texto"):
                texto = ET.SubElement(anexo_elem, "texto")
                texto.text = anexo["texto"]

    def _get_display_title(self, estructura: EstructuraFuncional) -> str:
        """Obtiene el título para mostrar de una estructura.

        Args:
            estructura: Estructura funcional.

        Returns:
            Título para mostrar.
        """
        if estructura.titulo_parte:
            return estructura.titulo_parte
        elif estructura.nombre_parte:
            return f"{estructura.tipo_parte} {estructura.nombre_parte}"
        else:
            return estructura.tipo_parte

    def _calculate_stats(
        self, estructuras: list[EstructuraFuncional]
    ) -> dict[str, int]:
        """Calcula estadísticas del contenido.

        Args:
            estructuras: Lista de estructuras.

        Returns:
            Diccionario con conteos.
        """
        stats = {"articulos": 0, "libros": 0, "titulos": 0, "capitulos": 0}

        def count_recursive(items: list[EstructuraFuncional]) -> None:
            for item in items:
                tipo = item.tipo_parte.lower()
                if "artículo" in tipo or "articulo" in tipo:
                    stats["articulos"] += 1
                elif "libro" in tipo:
                    stats["libros"] += 1
                elif "título" in tipo or "titulo" in tipo:
                    stats["titulos"] += 1
                elif "capítulo" in tipo or "capitulo" in tipo:
                    stats["capitulos"] += 1

                count_recursive(item.hijos)

        count_recursive(estructuras)
        return stats

    def _get_output_path(
        self, norma: Norma, output_dir: str, filename: str | None
    ) -> Path:
        """Genera la ruta de salida.

        Args:
            norma: Objeto Norma.
            output_dir: Directorio de salida.
            filename: Nombre de archivo opcional.

        Returns:
            Ruta completa del archivo.
        """
        dir_path = Path(output_dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        if filename:
            name = filename if filename.endswith(".xml") else f"{filename}.xml"
        else:
            # Generar nombre seguro
            tipo = norma.identificador.tipo.replace(" ", "_")
            numero = norma.identificador.numero.replace(" ", "_").replace("/", "-")
            name = f"{tipo}_{numero}.xml"

        return dir_path / name

    def _validate_xml(self, root: ET.Element) -> list[str]:
        """Valida el XML generado contra el esquema XSD.

        Args:
            root: Elemento raíz del XML.

        Returns:
            Lista de errores de validación (vacía si es válido).
        """
        if not _SCHEMA_PATH.exists():
            logger.warning(f"Esquema XSD no encontrado en {_SCHEMA_PATH}, saltando validación")
            return []

        try:
            xml_str = ET.tostring(root, encoding="unicode")
            lxml_doc = etree.fromstring(xml_str.encode("utf-8"))
            schema_doc = etree.parse(str(_SCHEMA_PATH))
            schema = etree.XMLSchema(schema_doc)

            if schema.validate(lxml_doc):
                logger.debug("XML válido según esquema XSD")
                return []

            errors = [str(e) for e in schema.error_log]
            logger.warning(f"Validación XSD: {len(errors)} errores encontrados")
            for error in errors[:5]:
                logger.warning(f"  XSD: {error}")
            return errors

        except Exception as e:
            logger.warning(f"Error durante validación XSD: {e}")
            return [str(e)]

    def _write_xml(self, root: ET.Element, output_path: Path) -> None:
        """Escribe el XML con formato legible.

        Args:
            root: Elemento raíz.
            output_path: Ruta del archivo.
        """
        # Validar contra XSD (no bloquea la escritura, solo advierte)
        self._validate_xml(root)

        # Convertir a string
        xml_str = ET.tostring(root, encoding="unicode")

        # Formatear con indentación
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ", encoding="utf-8")

        # Escribir archivo
        with open(output_path, "wb") as f:
            f.write(pretty_xml)


class BibliotecaXMLGenerator:
    """Generador de biblioteca de leyes en XML.

    Genera múltiples archivos XML y un índice de la biblioteca.

    Example:
        >>> from leychile_epub.xml_generator import BibliotecaXMLGenerator
        >>> biblioteca = BibliotecaXMLGenerator()
        >>> biblioteca.generate(
        ...     leyes=LEYES_COMERCIALES,
        ...     output_dir="./biblioteca/comercial",
        ...     nombre="Biblioteca de Derecho Comercial"
        ... )
    """

    # Leyes predefinidas por categoría
    LEYES_BASICAS = {
        "codigo_civil": {
            "url": "https://www.leychile.cl/Navegar?idNorma=172986",
            "nombre": "Código Civil",
            "descripcion": "Código Civil de la República de Chile",
        },
        "codigo_comercio": {
            "url": "https://www.leychile.cl/Navegar?idNorma=1974",
            "nombre": "Código de Comercio",
            "descripcion": "Código de Comercio de la República de Chile",
        },
        "ley_consumidor": {
            "url": "https://www.leychile.cl/Navegar?idNorma=61438",
            "nombre": "Ley 19.496",
            "descripcion": "Ley de Protección de los Derechos de los Consumidores",
        },
        "ley_insolvencia": {
            "url": "https://www.leychile.cl/Navegar?idNorma=1058072",
            "nombre": "Ley 20.720",
            "descripcion": "Ley de Reorganización y Liquidación de Empresas y Personas",
        },
    }

    def __init__(self) -> None:
        """Inicializa el generador de biblioteca."""
        self.generator = LawXMLGenerator()
        logger.debug("BibliotecaXMLGenerator inicializado")

    def generate(
        self,
        leyes: dict[str, dict[str, str]] | None = None,
        output_dir: str = "./biblioteca_legal",
        nombre: str = "Biblioteca Legal Chilena",
        generar_indice: bool = True,
    ) -> dict[str, Any]:
        """Genera una biblioteca de leyes en XML.

        Args:
            leyes: Diccionario de leyes a incluir. Si es None, usa LEYES_BASICAS.
            output_dir: Directorio de salida.
            nombre: Nombre de la biblioteca.
            generar_indice: Si genera archivo de índice.

        Returns:
            Diccionario con resultados de la generación.
        """
        if leyes is None:
            leyes = self.LEYES_BASICAS

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        resultados: dict[str, Any] = {
            "nombre": nombre,
            "directorio": str(output_path),
            "fecha_generacion": datetime.now().isoformat(),
            "leyes": [],
            "exitosas": 0,
            "fallidas": 0,
        }

        logger.info(f"Generando biblioteca: {nombre}")
        logger.info(f"Total de leyes: {len(leyes)}")

        for key, info in leyes.items():
            logger.info(f"Procesando: {info['nombre']}")

            try:
                xml_path = self.generator.generate_from_url(
                    url=info["url"],
                    output_dir=str(output_path),
                    filename=key,
                )

                resultados["leyes"].append({
                    "clave": key,
                    "nombre": info["nombre"],
                    "descripcion": info.get("descripcion", ""),
                    "url": info["url"],
                    "archivo": xml_path.name,
                    "estado": "exitoso",
                })
                resultados["exitosas"] += 1
                logger.info(f"  ✓ Generado: {xml_path.name}")

            except Exception as e:
                resultados["leyes"].append({
                    "clave": key,
                    "nombre": info["nombre"],
                    "url": info["url"],
                    "estado": "fallido",
                    "error": str(e),
                })
                resultados["fallidas"] += 1
                logger.error(f"  ✗ Error: {e}")

        # Generar índice
        if generar_indice:
            indice_path = self._generate_index(resultados, output_path)
            resultados["indice"] = str(indice_path)
            logger.info(f"Índice generado: {indice_path}")

        logger.info(
            f"Biblioteca completada: {resultados['exitosas']} exitosas, "
            f"{resultados['fallidas']} fallidas"
        )

        return resultados

    def _generate_index(self, resultados: dict[str, Any], output_dir: Path) -> Path:
        """Genera el archivo de índice de la biblioteca.

        Args:
            resultados: Resultados de la generación.
            output_dir: Directorio de salida.

        Returns:
            Ruta al archivo de índice.
        """
        root = ET.Element("biblioteca")
        root.set("xmlns", "https://leychile.cl/schema/biblioteca/v1")
        root.set("version", "1.0")

        # Metadatos de la biblioteca
        meta = ET.SubElement(root, "metadatos")

        nombre = ET.SubElement(meta, "nombre")
        nombre.text = resultados["nombre"]

        fecha = ET.SubElement(meta, "fecha_generacion")
        fecha.text = resultados["fecha_generacion"]

        total = ET.SubElement(meta, "total_leyes")
        total.text = str(len(resultados["leyes"]))

        fuente = ET.SubElement(meta, "fuente")
        fuente.text = "Biblioteca del Congreso Nacional de Chile"

        # Uso recomendado para IA
        uso = ET.SubElement(meta, "uso_ia")
        uso.text = (
            "Esta biblioteca está optimizada para ser consumida por agentes de IA. "
            "Cada archivo XML contiene una ley con estructura jerárquica completa, "
            "metadatos detallados y referencias cruzadas entre artículos."
        )

        # Lista de leyes
        leyes_elem = ET.SubElement(root, "leyes")

        for ley in resultados["leyes"]:
            if ley["estado"] == "exitoso":
                ley_elem = ET.SubElement(leyes_elem, "ley")
                ley_elem.set("clave", ley["clave"])
                ley_elem.set("archivo", ley["archivo"])

                nombre_elem = ET.SubElement(ley_elem, "nombre")
                nombre_elem.text = ley["nombre"]

                if ley.get("descripcion"):
                    desc = ET.SubElement(ley_elem, "descripcion")
                    desc.text = ley["descripcion"]

                url_elem = ET.SubElement(ley_elem, "url_fuente")
                url_elem.text = ley["url"]

        # Escribir archivo
        output_path = output_dir / "indice.xml"

        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ", encoding="utf-8")

        with open(output_path, "wb") as f:
            f.write(pretty_xml)

        return output_path


# Función de conveniencia
def generate_law_xml(
    url: str,
    output_dir: str = ".",
    filename: str | None = None,
) -> Path:
    """Genera un XML de ley desde una URL.

    Args:
        url: URL de LeyChile.
        output_dir: Directorio de salida.
        filename: Nombre del archivo (opcional).

    Returns:
        Path al archivo generado.
    """
    generator = LawXMLGenerator()
    return generator.generate_from_url(url, output_dir, filename)


def generate_library(
    output_dir: str = "./biblioteca_legal",
    leyes: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Genera una biblioteca de leyes en XML.

    Args:
        output_dir: Directorio de salida.
        leyes: Diccionario de leyes (usa predefinidas si es None).

    Returns:
        Resultados de la generación.
    """
    biblioteca = BibliotecaXMLGenerator()
    return biblioteca.generate(leyes=leyes, output_dir=output_dir)
