"""Generador XML para normas SUPERIR conforme a superir_v1.xsd.

Convierte NormaSuperir en XML validado contra el schema SUPERIR,
con considerandos individuales, epígrafes en artículos, cierre
estructurado y listados letrados.

Independiente de LawXMLGenerator (ley_v1.xsd).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.dom.minidom import parseString

from lxml import etree

from .scraper_v2 import EstructuraFuncional
from .superir_models import NormaSuperir

logger = logging.getLogger(__name__)

# Namespace
SUPERIR_NS = "https://superir.cl/schema/norma/v1"
NSMAP = {None: SUPERIR_NS}

# Schema path
SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "superir_v1.xsd"


class SuperirXMLGenerator:
    """Genera XML conforme a superir_v1.xsd desde NormaSuperir.

    Example:
        >>> gen = SuperirXMLGenerator()
        >>> xml_str = gen.generate(norma_superir)
    """

    def __init__(self, schema_path: str | Path | None = None):
        """Inicializa el generador.

        Args:
            schema_path: Ruta al XSD. Default: schemas/superir_v1.xsd.
        """
        self._schema_path = Path(schema_path) if schema_path else SCHEMA_PATH
        self._schema: etree.XMLSchema | None = None

    def _load_schema(self) -> etree.XMLSchema:
        """Carga y cachea el schema XSD."""
        if self._schema is None:
            if self._schema_path.exists():
                schema_doc = etree.parse(str(self._schema_path))
                self._schema = etree.XMLSchema(schema_doc)
            else:
                logger.warning(f"Schema no encontrado: {self._schema_path}")
        return self._schema

    def generate(self, norma: NormaSuperir) -> str:
        """Genera XML string desde NormaSuperir.

        Args:
            norma: NormaSuperir con datos estructurados.

        Returns:
            XML string validado contra superir_v1.xsd.
        """
        root = self._create_root(norma)
        self._add_acto_administrativo(root, norma)
        self._add_encabezado(root, norma)
        self._add_metadatos(root, norma)
        self._add_vistos(root, norma)
        self._add_considerandos(root, norma)
        self._add_formula_dictacion(root, norma)
        self._add_resolutivo(root, norma)
        self._add_preambulo_ncg(root, norma)
        self._add_cuerpo_normativo(root, norma)
        self._add_resolutivo_final(root, norma)
        self._add_cierre(root, norma)
        self._add_anexos(root, norma)
        self._add_standalone_anexos(root, norma)

        xml_str = self._serialize(root)

        # Validar
        self._validate(xml_str)

        return xml_str

    # ───────────────────────────────────────────────────────────────────────
    # Elemento raíz
    # ───────────────────────────────────────────────────────────────────────

    def _create_root(self, norma: NormaSuperir) -> etree._Element:
        """Crea el elemento raíz <norma>."""
        base = norma.norma_base
        attribs = {
            "tipo": base.identificador.tipo,
            "numero": base.identificador.numero,
            "organismo": "Superintendencia de Insolvencia y Reemprendimiento",
            "version": "1.0",
            "estado": "derogada" if base.derogado else "vigente",
            "generado": datetime.now(timezone.utc).isoformat(),
        }
        return etree.Element(f"{{{SUPERIR_NS}}}norma", attrib=attribs, nsmap=NSMAP)

    # ───────────────────────────────────────────────────────────────────────
    # Acto administrativo (Resolución Exenta)
    # ───────────────────────────────────────────────────────────────────────

    def _add_acto_administrativo(
        self, root: etree._Element, norma: NormaSuperir
    ) -> None:
        """Agrega <acto_administrativo> si la NCG viene envuelta en resolución."""
        if not norma.acto_administrativo:
            return
        aa = norma.acto_administrativo
        aa_el = etree.SubElement(root, f"{{{SUPERIR_NS}}}acto_administrativo")
        etree.SubElement(aa_el, f"{{{SUPERIR_NS}}}tipo").text = aa.tipo
        etree.SubElement(aa_el, f"{{{SUPERIR_NS}}}numero").text = aa.numero
        etree.SubElement(aa_el, f"{{{SUPERIR_NS}}}materia").text = aa.materia

    # ───────────────────────────────────────────────────────────────────────
    # Encabezado
    # ───────────────────────────────────────────────────────────────────────

    def _add_encabezado(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <encabezado> con identificación, organismo, referencia.

        Si hay acto_administrativo, omite identificación y organismo
        (están en el acto administrativo).
        """
        base = norma.norma_base
        enc = etree.SubElement(root, f"{{{SUPERIR_NS}}}encabezado")

        if not norma.acto_administrativo:
            # Identificación
            id_text = f"{base.identificador.tipo.upper()} N.° {base.identificador.numero}"
            etree.SubElement(enc, f"{{{SUPERIR_NS}}}identificacion").text = id_text

            # Organismo
            etree.SubElement(
                enc, f"{{{SUPERIR_NS}}}organismo"
            ).text = "SUPERINTENDENCIA DE INSOLVENCIA Y REEMPRENDIMIENTO"

            # Referencia (materia)
            if base.metadatos.materias:
                ref_text = base.metadatos.materias[0]
                if base.metadatos.titulo:
                    parts = base.metadatos.titulo.split(" - ", 1)
                    if len(parts) > 1:
                        ref_text = parts[1]
                etree.SubElement(enc, f"{{{SUPERIR_NS}}}referencia").text = ref_text

        # Lugar y fecha
        etree.SubElement(enc, f"{{{SUPERIR_NS}}}lugar").text = "SANTIAGO"

        fecha_text = base.identificador.fecha_promulgacion or base.fecha_version
        if fecha_text:
            etree.SubElement(enc, f"{{{SUPERIR_NS}}}fecha").text = fecha_text

    # ───────────────────────────────────────────────────────────────────────
    # Metadatos
    # ───────────────────────────────────────────────────────────────────────

    def _add_metadatos(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <metadatos> con materias, nombres comunes, leyes."""
        base = norma.norma_base
        meta = etree.SubElement(root, f"{{{SUPERIR_NS}}}metadatos")

        # Título
        if base.metadatos.titulo:
            etree.SubElement(meta, f"{{{SUPERIR_NS}}}titulo").text = base.metadatos.titulo

        # Resolución exenta
        if base.metadatos.numero_fuente:
            etree.SubElement(
                meta, f"{{{SUPERIR_NS}}}resolucion_exenta"
            ).text = base.metadatos.numero_fuente

        # Materias
        if base.metadatos.materias:
            materias_el = etree.SubElement(meta, f"{{{SUPERIR_NS}}}materias")
            for m in base.metadatos.materias:
                etree.SubElement(materias_el, f"{{{SUPERIR_NS}}}materia").text = m

        # Nombres comunes
        if base.metadatos.nombres_uso_comun:
            nombres_el = etree.SubElement(meta, f"{{{SUPERIR_NS}}}nombres_comunes")
            for n in base.metadatos.nombres_uso_comun:
                etree.SubElement(nombres_el, f"{{{SUPERIR_NS}}}nombre").text = n

        # Fechas
        fechas_el = etree.SubElement(meta, f"{{{SUPERIR_NS}}}fechas")
        prom = base.identificador.fecha_promulgacion
        pub = base.identificador.fecha_publicacion
        ver = base.fecha_version
        if prom:
            etree.SubElement(fechas_el, f"{{{SUPERIR_NS}}}promulgacion").text = prom
        if pub:
            etree.SubElement(fechas_el, f"{{{SUPERIR_NS}}}publicacion").text = pub
        if ver:
            etree.SubElement(fechas_el, f"{{{SUPERIR_NS}}}version").text = ver

        # Leyes referenciadas
        if base.metadatos.leyes_referenciadas:
            leyes_el = etree.SubElement(meta, f"{{{SUPERIR_NS}}}leyes_referenciadas")
            for ref in base.metadatos.leyes_referenciadas:
                # Parse "Ley 20.720" → tipo="Ley", numero="20.720"
                parts = ref.split(maxsplit=1)
                attrib = {}
                if len(parts) == 2:
                    attrib = {"tipo": parts[0], "numero": parts[1]}
                el = etree.SubElement(
                    leyes_el, f"{{{SUPERIR_NS}}}ley_ref", attrib=attrib
                )
                el.text = ref

    # ───────────────────────────────────────────────────────────────────────
    # Vistos
    # ───────────────────────────────────────────────────────────────────────

    def _add_vistos(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <vistos> con párrafos."""
        vistos_el = etree.SubElement(root, f"{{{SUPERIR_NS}}}vistos")
        texto = norma.norma_base.vistos_texto.strip()
        if texto:
            # Dividir en párrafos por líneas en blanco
            parrafos = _split_into_paragraphs(texto)
            for p in parrafos:
                etree.SubElement(vistos_el, f"{{{SUPERIR_NS}}}parrafo").text = p
        else:
            etree.SubElement(vistos_el, f"{{{SUPERIR_NS}}}parrafo").text = ""

    # ───────────────────────────────────────────────────────────────────────
    # Considerandos (individuales)
    # ───────────────────────────────────────────────────────────────────────

    def _add_considerandos(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <considerandos> con <considerando numero="N"> individuales."""
        cons_el = etree.SubElement(root, f"{{{SUPERIR_NS}}}considerandos")

        if norma.considerandos:
            for item in norma.considerandos:
                attrib = {"numero": str(item.numero)}
                c_el = etree.SubElement(
                    cons_el, f"{{{SUPERIR_NS}}}considerando", attrib=attrib
                )
                # El texto puede tener múltiples párrafos
                parrafos = _split_into_paragraphs(item.texto)
                for p in parrafos:
                    etree.SubElement(c_el, f"{{{SUPERIR_NS}}}parrafo").text = p
        else:
            # Fallback: un solo considerando con todo el texto
            c_el = etree.SubElement(
                cons_el, f"{{{SUPERIR_NS}}}considerando", attrib={"numero": "1"}
            )
            texto = norma.norma_base.considerandos_texto.strip()
            etree.SubElement(c_el, f"{{{SUPERIR_NS}}}parrafo").text = texto or ""

    # ───────────────────────────────────────────────────────────────────────
    # Fórmula de dictación
    # ───────────────────────────────────────────────────────────────────────

    def _add_formula_dictacion(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <formula_dictacion> si existe."""
        if norma.formula_dictacion:
            etree.SubElement(
                root, f"{{{SUPERIR_NS}}}formula_dictacion"
            ).text = norma.formula_dictacion

    # ───────────────────────────────────────────────────────────────────────
    # Resolutivo y preámbulo NCG (para NCGs envueltas en resolución)
    # ───────────────────────────────────────────────────────────────────────

    def _add_resolutivo(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <resolutivo> con puntos resolutivos pre-NCG."""
        if not norma.resolutivo:
            return
        res = etree.SubElement(root, f"{{{SUPERIR_NS}}}resolutivo")
        for punto in norma.resolutivo:
            p_el = etree.SubElement(
                res, f"{{{SUPERIR_NS}}}punto", attrib={"numero": punto.numero}
            )
            p_el.text = punto.texto

    def _add_preambulo_ncg(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <preambulo_ncg> con párrafos introductorios de la NCG."""
        if not norma.preambulo_ncg:
            return
        pre = etree.SubElement(root, f"{{{SUPERIR_NS}}}preambulo_ncg")
        for parrafo in norma.preambulo_ncg:
            etree.SubElement(pre, f"{{{SUPERIR_NS}}}parrafo").text = parrafo

    def _add_resolutivo_final(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <resolutivo_final> con puntos resolutivos post-NCG."""
        if not norma.resolutivo_final:
            return
        res = etree.SubElement(root, f"{{{SUPERIR_NS}}}resolutivo_final")
        for punto in norma.resolutivo_final:
            p_el = etree.SubElement(
                res, f"{{{SUPERIR_NS}}}punto", attrib={"numero": punto.numero}
            )
            p_el.text = punto.texto

    # ───────────────────────────────────────────────────────────────────────
    # Cuerpo normativo
    # ───────────────────────────────────────────────────────────────────────

    def _add_cuerpo_normativo(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <cuerpo_normativo> con títulos, capítulos y artículos."""
        estructuras = norma.norma_base.estructuras
        if not estructuras:
            return

        cuerpo = etree.SubElement(root, f"{{{SUPERIR_NS}}}cuerpo_normativo")

        for est in estructuras:
            if est.tipo_parte == "Título":
                self._add_titulo(cuerpo, est, norma)
            elif est.tipo_parte == "Artículo":
                # Artículo sin título padre
                self._add_articulo(cuerpo, est, norma)

    def _add_titulo(
        self, parent: etree._Element, titulo: EstructuraFuncional, norma: NormaSuperir
    ) -> None:
        """Agrega <titulo> con sus artículos."""
        attrib: dict[str, str] = {"numero": titulo.nombre_parte}

        # Nombre del título (opcional)
        nombre = self._extract_titulo_nombre(titulo.titulo_parte)
        if nombre:
            attrib["nombre"] = nombre

        titulo_el = etree.SubElement(parent, f"{{{SUPERIR_NS}}}titulo", attrib=attrib)

        for hijo in titulo.hijos:
            if hijo.tipo_parte == "Capítulo":
                self._add_capitulo(titulo_el, hijo, norma)
            elif hijo.tipo_parte == "Párrafo":
                self._add_parrafo_division(titulo_el, hijo, norma)
            elif hijo.tipo_parte == "Artículo":
                self._add_articulo(titulo_el, hijo, norma)

    def _add_capitulo(
        self, parent: etree._Element, capitulo: EstructuraFuncional, norma: NormaSuperir
    ) -> None:
        """Agrega <capitulo> con sus artículos."""
        attrib: dict[str, str] = {"numero": capitulo.nombre_parte}
        nombre = self._extract_titulo_nombre(capitulo.titulo_parte)
        if nombre:
            attrib["nombre"] = nombre

        cap_el = etree.SubElement(parent, f"{{{SUPERIR_NS}}}capitulo", attrib=attrib)

        for hijo in capitulo.hijos:
            if hijo.tipo_parte == "Artículo":
                self._add_articulo(cap_el, hijo, norma)

    def _add_parrafo_division(
        self, parent: etree._Element, parrafo: EstructuraFuncional, norma: NormaSuperir
    ) -> None:
        """Agrega <parrafo> como división estructural (Párrafo legal chileno).

        No confundir con <parrafo> texto (xs:string) dentro de artículos.
        Este es ParrafoDivisionType en el XSD: contiene artículos.
        """
        attrib: dict[str, str] = {"numero": parrafo.nombre_parte}
        nombre = self._extract_titulo_nombre(parrafo.titulo_parte)
        if nombre:
            attrib["nombre"] = nombre

        par_el = etree.SubElement(parent, f"{{{SUPERIR_NS}}}parrafo", attrib=attrib)

        for hijo in parrafo.hijos:
            if hijo.tipo_parte == "Artículo":
                self._add_articulo(par_el, hijo, norma)

    def _add_articulo(
        self, parent: etree._Element, articulo: EstructuraFuncional, norma: NormaSuperir
    ) -> None:
        """Agrega <articulo> con epígrafe, párrafos y listados."""
        attrib: dict[str, str] = {"numero": articulo.nombre_parte}

        # Epígrafe
        epigrafe = norma.articulos_epigrafe.get(articulo.nombre_parte, "")
        if epigrafe:
            attrib["epigrafe"] = epigrafe

        if articulo.transitorio:
            attrib["transitorio"] = "true"

        art_el = etree.SubElement(parent, f"{{{SUPERIR_NS}}}articulo", attrib=attrib)

        # Contenido estructurado (con listado/requisitos) vs texto simple
        contenido = norma.articulos_contenido.get(articulo.nombre_parte)
        if contenido:
            # Párrafos antes del listado/requisitos
            for p in contenido.parrafos:
                etree.SubElement(art_el, f"{{{SUPERIR_NS}}}parrafo").text = p

            # Listado (letrado, numerado o complejo con subitems)
            if contenido.listado:
                listado_el = etree.SubElement(art_el, f"{{{SUPERIR_NS}}}listado")
                for item in contenido.listado:
                    # Build item attributes
                    item_attrib: dict[str, str] = {}
                    if item.letra:
                        item_attrib["letra"] = item.letra
                    if item.numero:
                        item_attrib["numero"] = item.numero
                    if item.nombre:
                        item_attrib["nombre"] = item.nombre

                    item_el = etree.SubElement(
                        listado_el,
                        f"{{{SUPERIR_NS}}}item",
                        attrib=item_attrib,
                    )

                    if item.content_blocks:
                        # Interleaved content: ordered sublistados + paragraphs
                        # (NCG 20 Art 1° item A: a.1 → parrafo → a.2)
                        for p in item.parrafos:
                            etree.SubElement(
                                item_el, f"{{{SUPERIR_NS}}}parrafo"
                            ).text = p
                        for block in item.content_blocks:
                            if block.tipo == "parrafo":
                                etree.SubElement(
                                    item_el, f"{{{SUPERIR_NS}}}parrafo"
                                ).text = block.texto
                            elif block.tipo == "sublistado":
                                sub_el = etree.SubElement(
                                    item_el, f"{{{SUPERIR_NS}}}sublistado"
                                )
                                for si in block.subitems:
                                    si_attrib: dict[str, str] = {}
                                    if si.numero:
                                        si_attrib["numero"] = si.numero
                                    if si.letra:
                                        si_attrib["letra"] = si.letra
                                    si_el = etree.SubElement(
                                        sub_el,
                                        f"{{{SUPERIR_NS}}}subitem",
                                        attrib=si_attrib,
                                    )
                                    si_el.text = si.texto
                    elif item.subitems:
                        # Complex item with paragraphs + sublistado + post-parrafos
                        for p in item.parrafos:
                            etree.SubElement(
                                item_el, f"{{{SUPERIR_NS}}}parrafo"
                            ).text = p
                        sub_el2 = etree.SubElement(
                            item_el, f"{{{SUPERIR_NS}}}sublistado"
                        )
                        for si in item.subitems:
                            si_attrib2: dict[str, str] = {}
                            if si.numero:
                                si_attrib2["numero"] = si.numero
                            if si.letra:
                                si_attrib2["letra"] = si.letra
                            si_el2 = etree.SubElement(
                                sub_el2,
                                f"{{{SUPERIR_NS}}}subitem",
                                attrib=si_attrib2,
                            )
                            si_el2.text = si.texto
                        # Párrafos después del sublistado (NCG 19 Art 1° E)
                        for p in item.parrafos_post:
                            etree.SubElement(
                                item_el, f"{{{SUPERIR_NS}}}parrafo"
                            ).text = p
                    elif item.parrafos:
                        # Item with multiple paragraphs but no subitems
                        for p in item.parrafos:
                            etree.SubElement(
                                item_el, f"{{{SUPERIR_NS}}}parrafo"
                            ).text = p
                    else:
                        # Simple item: text content only
                        item_el.text = item.texto

            # Párrafos post-listado (interleaved: parrafo → listado → parrafo)
            if contenido.parrafos_post:
                for p in contenido.parrafos_post:
                    etree.SubElement(art_el, f"{{{SUPERIR_NS}}}parrafo").text = p

            # Requisitos (I, II, III...)
            if contenido.requisitos:
                for req in contenido.requisitos:
                    self._add_requisito(art_el, req)

            # Referencia a anexo
            if contenido.referencia_anexo:
                etree.SubElement(
                    art_el, f"{{{SUPERIR_NS}}}referencia_anexo"
                ).text = contenido.referencia_anexo
        elif articulo.texto:
            # Texto simple → párrafos
            parrafos = _split_into_paragraphs(articulo.texto)
            for p in parrafos:
                etree.SubElement(art_el, f"{{{SUPERIR_NS}}}parrafo").text = p

    # ───────────────────────────────────────────────────────────────────────
    # Requisitos (I, II, III...)
    # ───────────────────────────────────────────────────────────────────────

    def _add_requisito(self, parent: etree._Element, req) -> None:
        """Agrega <requisito numero="I" nombre="..."> con párrafos e items."""
        attrib: dict[str, str] = {"numero": req.numero}
        if req.nombre:
            attrib["nombre"] = req.nombre

        req_el = etree.SubElement(parent, f"{{{SUPERIR_NS}}}requisito", attrib=attrib)

        # Párrafos del requisito
        for p in req.parrafos:
            etree.SubElement(req_el, f"{{{SUPERIR_NS}}}parrafo").text = p

        # Items letrados dentro del requisito
        for item in req.items:
            self._add_requisito_item(req_el, item)

    def _add_requisito_item(self, parent: etree._Element, item) -> None:
        """Agrega <item letra="a" nombre="..."> dentro de un requisito.

        Items simples: texto directo como text content (mixed content).
        Items complejos: párrafos como sub-elementos <parrafo>.
        """
        attrib: dict[str, str] = {"letra": item.letra}
        if item.nombre:
            attrib["nombre"] = item.nombre

        item_el = etree.SubElement(parent, f"{{{SUPERIR_NS}}}item", attrib=attrib)

        if item.parrafos:
            # Item complejo con múltiples párrafos
            for p in item.parrafos:
                etree.SubElement(item_el, f"{{{SUPERIR_NS}}}parrafo").text = p
        elif item.texto:
            # Item simple - texto directo (mixed content)
            item_el.text = item.texto

    # ───────────────────────────────────────────────────────────────────────
    # Cierre
    # ───────────────────────────────────────────────────────────────────────

    def _add_cierre(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <cierre> con fórmula y firmante."""
        if not norma.cierre:
            return

        cierre_el = etree.SubElement(root, f"{{{SUPERIR_NS}}}cierre")
        etree.SubElement(
            cierre_el, f"{{{SUPERIR_NS}}}formula"
        ).text = norma.cierre.formula

        if norma.cierre.firmante:
            firm_el = etree.SubElement(cierre_el, f"{{{SUPERIR_NS}}}firmante")
            etree.SubElement(
                firm_el, f"{{{SUPERIR_NS}}}nombre"
            ).text = norma.cierre.firmante.nombre
            etree.SubElement(
                firm_el, f"{{{SUPERIR_NS}}}cargo"
            ).text = norma.cierre.firmante.cargo

        if norma.cierre.distribucion:
            etree.SubElement(
                cierre_el, f"{{{SUPERIR_NS}}}distribucion"
            ).text = norma.cierre.distribucion

        if norma.cierre.destinatarios_notificacion:
            notif_el = etree.SubElement(cierre_el, f"{{{SUPERIR_NS}}}notificacion")
            etree.SubElement(
                notif_el, f"{{{SUPERIR_NS}}}destinatarios"
            ).text = norma.cierre.destinatarios_notificacion

    # ───────────────────────────────────────────────────────────────────────
    # Anexos
    # ───────────────────────────────────────────────────────────────────────

    def _add_anexos(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <anexos> si existen."""
        base = norma.norma_base
        if not base.anexos:
            return

        anexos_el = etree.SubElement(root, f"{{{SUPERIR_NS}}}anexos")
        for i, anexo in enumerate(base.anexos, 1):
            attrib: dict[str, str] = {}
            if "numero" in anexo:
                attrib["numero"] = str(anexo["numero"])
            elif "id_parte" in anexo and anexo["id_parte"]:
                attrib["numero"] = str(anexo["id_parte"])
            else:
                attrib["numero"] = str(i)

            anx_el = etree.SubElement(
                anexos_el, f"{{{SUPERIR_NS}}}anexo", attrib=attrib
            )

            if anexo.get("titulo"):
                etree.SubElement(
                    anx_el, f"{{{SUPERIR_NS}}}titulo"
                ).text = anexo["titulo"]
            if anexo.get("texto"):
                etree.SubElement(
                    anx_el, f"{{{SUPERIR_NS}}}texto"
                ).text = anexo["texto"]

    # ───────────────────────────────────────────────────────────────────────
    # Anexos standalone (a nivel raíz)
    # ───────────────────────────────────────────────────────────────────────

    def _add_standalone_anexos(self, root: etree._Element, norma: NormaSuperir) -> None:
        """Agrega <anexo> standalone a nivel raíz (después de <anexos>).

        Estos son anexos con pendiente="true" que no se modelan en detalle.
        Ejemplo: <anexo numero="I" titulo="Modelo de presentación..." pendiente="true"/>
        """
        if not norma.anexos_standalone:
            return

        for anexo in norma.anexos_standalone:
            attrib: dict[str, str] = {}
            if anexo.numero:
                attrib["numero"] = anexo.numero
            if anexo.titulo:
                attrib["titulo"] = anexo.titulo
            if anexo.pendiente:
                attrib["pendiente"] = "true"

            etree.SubElement(root, f"{{{SUPERIR_NS}}}anexo", attrib=attrib)

    # ───────────────────────────────────────────────────────────────────────
    # Serialización y validación
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize(root: etree._Element) -> str:
        """Serializa el árbol XML a string indentado."""
        rough = etree.tostring(root, encoding="unicode", xml_declaration=False)
        dom = parseString(f'<?xml version="1.0" encoding="UTF-8"?>{rough}')
        return dom.toprettyxml(indent="  ", encoding=None)

    def _validate(self, xml_str: str) -> bool:
        """Valida XML contra superir_v1.xsd."""
        schema = self._load_schema()
        if not schema:
            logger.warning("No se puede validar: schema no disponible")
            return False

        try:
            doc = etree.fromstring(xml_str.encode("utf-8"))
            is_valid = schema.validate(doc)
            if not is_valid:
                for error in schema.error_log:
                    logger.error(f"Validación XSD: {error}")
            else:
                logger.info("  ✅ XML válido contra superir_v1.xsd")
            return is_valid
        except Exception as e:
            logger.error(f"Error validando XML: {e}")
            return False

    # ───────────────────────────────────────────────────────────────────────
    # Utilidades
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_titulo_nombre(titulo_parte: str) -> str:
        """Extrae el nombre descriptivo de un título/capítulo.

        "TÍTULO I Modelo de Solicitud..." → "Modelo de Solicitud..."
        "TÍTULO II Disposiciones Finales" → "Disposiciones Finales"
        "TÍTULO I" → "" (sin nombre)
        """
        import re

        match = re.match(
            r"(?:TÍTULO|CAPÍTULO|PÁRRAFO)\s+[IVXLCDM\d]+\s*(.*)",
            titulo_parte,
            re.IGNORECASE,
        )
        if match:
            nombre = match.group(1).strip()
            return nombre
        return ""


def _split_into_paragraphs(texto: str) -> list[str]:
    """Divide texto en párrafos por líneas en blanco o doble espacio.

    Dos modos:
    1. Texto con newlines → split por líneas en blanco (comportamiento original).
    2. Texto colapsado (sin newlines, del base parser) → split por doble espacio
       que marca los saltos de párrafo originales.

    El base parser de NCGs colapsa newlines en "  " (doble espacio). La heurística
    para detectar límites de párrafo es: periodo + doble espacio + mayúscula.
    Dentro de un mismo párrafo, las oraciones se separan con un solo espacio.
    """
    if not texto:
        return []

    # Modo 1: split por líneas en blanco
    parrafos: list[str] = []
    current: list[str] = []

    for line in texto.split("\n"):
        stripped = line.strip()
        if not stripped:
            if current:
                parrafos.append(" ".join(current))
                current = []
        else:
            current.append(stripped)

    if current:
        parrafos.append(" ".join(current))

    if len(parrafos) > 1:
        # Post-procesamiento: fusionar párrafos espurios de page breaks del PDF.
        # Si un párrafo NO termina en ".;:)" y el siguiente NO empieza con
        # mayúscula (o empieza con dígito/minúscula), es un corte de página,
        # no un párrafo real.
        merged: list[str] = [parrafos[0]]
        for p in parrafos[1:]:
            prev = merged[-1]
            # Heurística: el párrafo anterior no termina en puntuación de cierre
            # → probablemente es un page break, fusionar.
            if prev and not prev.rstrip()[-1:] in ".;:)":
                merged[-1] = prev + " " + p
            else:
                merged.append(p)
        return merged

    # Modo 2: texto colapsado → split por ". [A-Z]" (periodo + doble espacio + mayúscula)
    full_text = parrafos[0] if parrafos else texto.strip()
    parts = re.split(r"(?<=\.)\s{2}(?=[A-ZÁÉÍÓÚÑ])", full_text)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]

    return [full_text] if full_text else []
