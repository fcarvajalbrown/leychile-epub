"""
Parser base para documentos normativos de la SUPERIR.

Módulo compartido que contiene la lógica común de parsing para
Normas de Carácter General (NCG) e Instructivos de la
Superintendencia de Insolvencia y Reemprendimiento.

Estructura canónica de documentos SUPERIR:
  ENCABEZADO (tipo, número, fecha, materia)
  VISTOS / VISTO
  CONSIDERANDO
  RESUELVO (explícito en docs modernos, implícito en antiguos)
  CUERPO (Títulos > Capítulos > Artículos)
  CIERRE (firmas)
  ANEXOS (si existen)

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import logging
import re
from dataclasses import dataclass, field

from .scraper_v2 import (
    EstructuraFuncional,
    Norma,
    NormaIdentificador,
    NormaMetadatos,
)

logger = logging.getLogger("leychile_epub.superir_parser")

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

ORGANISMO = "Superintendencia de Insolvencia y Reemprendimiento"

# Meses en español → número
MESES_ES: dict[str, str] = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "setiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}

# ═══════════════════════════════════════════════════════════════════════════════
# PATRONES REGEX COMPARTIDOS
# ═══════════════════════════════════════════════════════════════════════════════

# Encabezado
PATRON_FECHA = re.compile(
    r"Santiago,?\s*(\d{1,2})\s+(?:de\s+)?(\w+)\s+(?:de\s+)?(\d{4})",
    re.IGNORECASE,
)
PATRON_MATERIA = re.compile(r"^MAT\.?\s*:\.?\s*(.+)$", re.MULTILINE | re.IGNORECASE)
PATRON_REFERENCIA = re.compile(r"^REF\.?\s*:\.?\s*(.+)$", re.MULTILINE | re.IGNORECASE)
PATRON_RESOLUCION_EXENTA = re.compile(
    r"RESOLUCI[ÓO]N\s+EXENTA\s+N[.°º]*\s*(\d+)",
    re.IGNORECASE,
)

# Secciones principales
PATRON_VISTOS = re.compile(r"^VISTOS?\s*:?\s*$|^VISTOS?\s*:", re.MULTILINE)
PATRON_CONSIDERANDO = re.compile(r"^CONSIDERANDO\s*:?\s*$|^CONSIDERANDO\s*:", re.MULTILINE)
PATRON_RESUELVO = re.compile(r"^RESUELVO\s*:?\s*$|^RESUELVO\s*:", re.MULTILINE)
PATRON_CIERRE = re.compile(
    r"^(AN[OÓ]TESE|REG[IÍ]STRESE|COMUN[IÍ]QUESE|PUBL[IÍ]QUESE)",
    re.MULTILINE | re.IGNORECASE,
)
PATRON_DIRECTIVA_RESOLUTIVA = re.compile(
    r"^(?:[IVX]+|\d+°?)\.\s*(NOTIF[ÍI]QUESE|PUBL[ÍI]QUESE|DER[ÓO]GUENSE|DISP[ÓO]NGASE|"
    r"AN[ÓO]TESE|REG[ÍI]STRESE|COMUN[ÍI]QUESE|ARCH[ÍI]VESE|D[ÉE]JASE|VIGENCIA)",
    re.MULTILINE | re.IGNORECASE,
)

# Estructura del cuerpo
PATRON_TITULO = re.compile(
    r"^T[ÍI]TULO\s+([IVXLCDM]+|\d+)\s*[:\-.]?\s*(.*)$",
    re.MULTILINE | re.IGNORECASE,
)
PATRON_CAPITULO = re.compile(
    r"^CAP[ÍI]TULO\s+([IVXLCDM]+|\d+)\s*[:\-.]?\s*(.*)$",
    re.MULTILINE | re.IGNORECASE,
)
PATRON_ARTICULO = re.compile(
    r"^Art[ií]culo\s+(\d+)[°º.]?\s*[:\-.]?\s*(.*?)$",
    re.MULTILINE,
)
PATRON_ARTICULO_TRANSITORIO = re.compile(
    r"^Art[ií]culo\s+transitorio",
    re.MULTILINE | re.IGNORECASE,
)

# Referencias a leyes y normas
PATRON_LEY_REF = re.compile(
    r"Ley\s+N[°º.]*\s*([\d.]+)",
    re.IGNORECASE,
)
PATRON_DFL_REF = re.compile(
    r"D\.?F\.?L\.?\s+N[°º.]*\s*([\d\-./]+)",
    re.IGNORECASE,
)
PATRON_DS_REF = re.compile(
    r"(?:Decreto\s+Supremo|D\.?S\.?)\s+N[°º.]*\s*(\d+)",
    re.IGNORECASE,
)
PATRON_NCG_REF = re.compile(
    r"(?:Norma\s+de\s+Car[áa]cter\s+General|NCG)\s+N[°º.]*\s*(\d+)",
    re.IGNORECASE,
)
PATRON_PARRAFO = re.compile(
    r"^P[ÁA]RRAFO\s+([IVXLCDM]+|\d+)\s*[:\-.]?\s*(.*)$",
    re.MULTILINE | re.IGNORECASE,
)
PATRON_DEROGACION = re.compile(
    r"(?:der[óo]g(?:a|ase|ese|uen)|dej(?:a|ese)\s+sin\s+efecto|queda\s+derogada)",
    re.IGNORECASE,
)

# Nivel jerárquico de cada tipo de división
NIVEL_JERARQUIA = {
    "Título": 0,
    "Párrafo": 1,
    "Capítulo": 1,
    "Artículo": 2,
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS DE METADATOS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SuperirDocMetadata:
    """Metadatos extraídos del encabezado de un documento SUPERIR."""

    numero: str = ""
    fecha_iso: str = ""
    fecha_texto: str = ""
    materia: str = ""
    referencia: str = ""
    resolucion_exenta: str = ""
    leyes_referenciadas: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# PARSER BASE
# ═══════════════════════════════════════════════════════════════════════════════


class SuperirBaseParser:
    """Parser base para documentos normativos de la SUPERIR.

    Contiene la lógica compartida para parsing de NCGs e Instructivos:
    - Extracción de metadatos (fecha, resolución, materia)
    - División en secciones (VISTOS, CONSIDERANDO, cuerpo, cierre)
    - Parsing de cuerpo normativo (títulos, capítulos, artículos)
    - Extracción de referencias a leyes

    Las subclases deben implementar el patrón de número de documento
    y la construcción del título.
    """

    # Patrón para extraer el número del documento (override en subclases)
    PATRON_NUMERO: re.Pattern[str] = re.compile(r"$^")  # nunca matchea

    # Tipo de norma para el XML
    TIPO_NORMA: str = ""

    # Prefijo para IDs
    ID_PREFIX: str = ""

    def parse(
        self,
        texto: str,
        url: str = "",
        doc_numero: str = "",
        catalog_entry: dict | None = None,
    ) -> Norma:
        """Parsea un texto de documento SUPERIR y retorna un objeto Norma.

        Args:
            texto: Texto completo del documento.
            url: URL de origen del PDF.
            doc_numero: Número del documento (override si no se detecta).
            catalog_entry: Metadatos adicionales del catálogo.

        Returns:
            Objeto Norma con toda la estructura parseada.
        """
        catalog = catalog_entry or {}

        # 1. Extraer metadatos del encabezado
        metadata = self._extract_metadata(texto)
        if doc_numero and not metadata.numero:
            metadata.numero = doc_numero

        # Enriquecer con datos del catálogo
        self._enrich_from_catalog(metadata, catalog)

        logger.info(f"Parseando {self.TIPO_NORMA} N°{metadata.numero}...")
        logger.info(f"  {metadata.materia[:60]}...")

        # 2. Extraer referencias a leyes del texto completo
        metadata.leyes_referenciadas = self._extract_law_references(texto)

        # Filtrar auto-referencias (ej: NCG que se menciona a sí misma)
        self_ref = f"{self.ID_PREFIX} {metadata.numero}"
        metadata.leyes_referenciadas = [
            r for r in metadata.leyes_referenciadas if r != self_ref
        ]

        # 3. Dividir en secciones
        sections = self._split_sections(texto)

        # 4. Parsear el cuerpo normativo
        estructuras = []
        if sections.get("body"):
            estructuras = self._parse_body(sections["body"])

        # 5. Almacenar VISTOS y CONSIDERANDO por separado (encabezado estructurado)
        vistos_texto = sections.get("vistos", "")
        considerandos_texto = sections.get("considerando", "")

        # Encabezado combinado (retrocompatibilidad)
        encabezado_parts = []
        if vistos_texto:
            encabezado_parts.append(f"VISTOS:\n\n{vistos_texto}")
        if considerandos_texto:
            encabezado_parts.append(f"CONSIDERANDO:\n\n{considerandos_texto}")
        encabezado_texto = "\n\n".join(encabezado_parts)

        # 6. Construir disposiciones finales (cierre normativo SUPERIR)
        disp_finales_parts = []
        if sections.get("resuelvo_intro"):
            disp_finales_parts.append(f"RESUELVO:\n\n{sections['resuelvo_intro']}")
        if sections.get("closing"):
            disp_finales_parts.append(sections["closing"])
        disposiciones_finales_texto = "\n\n".join(disp_finales_parts)

        # 7. Materias y conceptos (separados según taxonomía)
        materias = list(catalog.get("materias", []))
        if not materias and metadata.materia:
            materias.append(metadata.materia)
        conceptos = list(catalog.get("conceptos", []))

        # 8. Nombres de uso común
        nombres_comunes = list(catalog.get("nombres_comunes", []))

        # 9. Fuente
        fuente = "Superintendencia de Insolvencia y Reemprendimiento"

        # 10. Construir objeto Norma
        norma_id = f"{self.ID_PREFIX}-{metadata.numero}"
        norma = Norma(
            norma_id=norma_id,
            es_tratado=False,
            fecha_version=metadata.fecha_iso,
            schema_version="1.0",
            derogado=False,
            identificador=NormaIdentificador(
                tipo=self.TIPO_NORMA,
                numero=metadata.numero,
                organismos=[ORGANISMO],
                fecha_promulgacion=metadata.fecha_iso,
                fecha_publicacion=catalog.get("fecha_publicacion", metadata.fecha_iso),
            ),
            metadatos=NormaMetadatos(
                titulo=self._build_titulo(metadata, catalog),
                materias=materias,
                conceptos=conceptos,
                nombres_uso_comun=nombres_comunes,
                identificacion_fuente=fuente,
                numero_fuente=metadata.resolucion_exenta,
                leyes_referenciadas=metadata.leyes_referenciadas,
            ),
            encabezado_texto=encabezado_texto,
            encabezado_derogado=False,
            vistos_texto=vistos_texto,
            considerandos_texto=considerandos_texto,
            estructuras=estructuras,
            promulgacion_texto="",
            promulgacion_derogado=False,
            disposiciones_finales_texto=disposiciones_finales_texto,
            url_original=url,
        )

        # 11. Parsear y agregar anexos
        if sections.get("anexos_raw"):
            parsed_anexos = self._parse_anexos(sections["anexos_raw"])
            for anexo in parsed_anexos:
                norma.anexos.append({
                    "titulo": anexo["titulo"],
                    "texto": anexo["texto"],
                    "materias": [],
                    "id_parte": "",
                    "derogado": False,
                })
            if parsed_anexos:
                logger.info(f"  Anexos encontrados: {len(parsed_anexos)}")

        # Estadísticas
        n_arts = self._count_articles(estructuras)
        n_divs = self._count_divisions(estructuras)
        logger.info(
            f"  Parseado: {n_arts} artículos, {n_divs} divisiones, "
            f"encabezado={len(encabezado_texto):,} chars, "
            f"cuerpo={len(sections.get('body', '')):,} chars"
        )
        if metadata.leyes_referenciadas:
            logger.info(f"  Leyes referenciadas: {', '.join(metadata.leyes_referenciadas)}")

        return norma

    # ───────────────────────────────────────────────────────────────────────
    # Métodos a implementar por subclases
    # ───────────────────────────────────────────────────────────────────────

    def _build_titulo(self, metadata: SuperirDocMetadata, catalog: dict) -> str:
        """Construye el título completo del documento. Override en subclases."""
        return f"{self.TIPO_NORMA} N°{metadata.numero}"

    def _enrich_from_catalog(self, metadata: SuperirDocMetadata, catalog: dict) -> None:
        """Enriquece metadatos con datos del catálogo. Override en subclases."""
        if not metadata.resolucion_exenta and catalog.get("resolucion_exenta"):
            metadata.resolucion_exenta = catalog["resolucion_exenta"]

    # ───────────────────────────────────────────────────────────────────────
    # Extracción de metadatos
    # ───────────────────────────────────────────────────────────────────────

    def _extract_metadata(self, texto: str) -> SuperirDocMetadata:
        """Extrae metadatos del encabezado del documento."""
        metadata = SuperirDocMetadata()
        header = texto[:3000]

        # Número del documento
        match = self.PATRON_NUMERO.search(header)
        if match:
            metadata.numero = match.group(1)

        # Resolución Exenta
        match = PATRON_RESOLUCION_EXENTA.search(header)
        if match:
            metadata.resolucion_exenta = match.group(1)

        # Fecha
        match = PATRON_FECHA.search(header)
        if match:
            dia = match.group(1).zfill(2)
            mes_nombre = match.group(2).lower()
            anio = match.group(3)
            metadata.fecha_texto = f"{dia} de {mes_nombre} de {anio}"
            mes = MESES_ES.get(mes_nombre, "01")
            metadata.fecha_iso = f"{anio}-{mes}-{dia}"

        # Materia (MAT: o MAT.:) — puede ser multi-línea
        match = PATRON_MATERIA.search(header)
        if match:
            mat_text = match.group(1).strip()
            mat_text = self._extract_multiline_field(header[match.end() :], mat_text)
            metadata.materia = mat_text

        # Referencia (REF:) — alternativa a MAT en documentos antiguos
        if not metadata.materia:
            match = PATRON_REFERENCIA.search(header)
            if match:
                mat_text = match.group(1).strip()
                mat_text = self._extract_multiline_field(header[match.end() :], mat_text)
                metadata.materia = mat_text

        return metadata

    def _extract_multiline_field(self, rest: str, initial: str) -> str:
        """Extrae un campo multi-línea (MAT, REF) hasta encontrar un delimitador."""
        parts = [initial]
        consecutive_empty = 0
        for line in rest.split("\n"):
            line_s = line.strip()
            if not line_s:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    break
                continue
            consecutive_empty = 0
            if re.match(r"(SANTIAGO|VISTOS?|CONSIDERANDO|RESUELVO)", line_s, re.IGNORECASE):
                break
            if PATRON_FECHA.match(line_s):
                break
            parts.append(line_s)
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def _extract_law_references(self, texto: str) -> list[str]:
        """Extrae referencias a leyes, DFL, decretos supremos y NCGs del texto."""
        # Buscar en VISTOS + CONSIDERANDO (generalmente primeros 10000 chars)
        search_area = texto[:10000]
        refs: list[str] = []
        seen: set[str] = set()

        def _add(prefix: str, num: str) -> None:
            key = f"{prefix} {num}"
            if key not in seen:
                seen.add(key)
                refs.append(key)

        # Leyes (deduplicar variantes con/sin punto: "20.720" y "20720")
        ley_nums_seen: set[str] = set()
        for match in PATRON_LEY_REF.finditer(search_area):
            raw = match.group(1).rstrip(".")
            ley_num = raw.replace(".", "")
            if len(ley_num) >= 4 and ley_num not in ley_nums_seen:
                ley_nums_seen.add(ley_num)
                # Preferir formato con punto si existe
                display = raw if "." in raw else f"{ley_num[:2]}.{ley_num[2:]}"
                _add("Ley", display)

        # D.F.L.
        for match in PATRON_DFL_REF.finditer(search_area):
            _add("DFL", match.group(1).rstrip("."))

        # Decretos Supremos
        for match in PATRON_DS_REF.finditer(search_area):
            _add("D.S.", match.group(1))

        # NCGs referenciadas (excluyendo la propia norma)
        for match in PATRON_NCG_REF.finditer(search_area):
            _add("NCG", match.group(1))

        return refs

    # ───────────────────────────────────────────────────────────────────────
    # División en secciones
    # ───────────────────────────────────────────────────────────────────────

    def _split_sections(self, texto: str) -> dict[str, str]:
        """Divide el texto en secciones estructurales.

        Returns:
            Diccionario con claves: header, vistos, considerando,
            resuelvo_intro, body, closing.
        """
        sections: dict[str, str] = {
            "header": "",
            "vistos": "",
            "considerando": "",
            "resuelvo_intro": "",
            "body": "",
            "closing": "",
        }

        pos_vistos = PATRON_VISTOS.search(texto)
        pos_considerando = PATRON_CONSIDERANDO.search(texto)
        pos_resuelvo = PATRON_RESUELVO.search(texto)
        pos_first_article = PATRON_ARTICULO.search(texto)
        pos_cierre = PATRON_CIERRE.search(texto)

        # Header: todo antes de VISTOS
        if pos_vistos:
            sections["header"] = texto[: pos_vistos.start()].strip()
        elif pos_first_article:
            sections["header"] = texto[: pos_first_article.start()].strip()

        # VISTOS
        if pos_vistos and pos_considerando:
            sections["vistos"] = texto[pos_vistos.end() : pos_considerando.start()].strip()
        elif pos_vistos and pos_resuelvo:
            sections["vistos"] = texto[pos_vistos.end() : pos_resuelvo.start()].strip()

        # CONSIDERANDO
        if pos_considerando:
            end = None
            if pos_resuelvo:
                end = pos_resuelvo.start()
            elif pos_first_article:
                end = pos_first_article.start()
            if end:
                sections["considerando"] = texto[pos_considerando.end() : end].strip()

        # Buscar primer TÍTULO o primer artículo
        pos_first_titulo = PATRON_TITULO.search(texto)
        pos_body_start = pos_first_article

        if pos_first_titulo and pos_first_article:
            if pos_first_titulo.start() < pos_first_article.start():
                body_zone_start = 0
                if pos_resuelvo:
                    body_zone_start = pos_resuelvo.end()
                elif pos_considerando:
                    body_zone_start = pos_considerando.end()
                if pos_first_titulo.start() >= body_zone_start:
                    pos_body_start = pos_first_titulo

        # RESUELVO intro
        if pos_resuelvo and pos_body_start:
            intro = texto[pos_resuelvo.end() : pos_body_start.start()].strip()
            if intro:
                sections["resuelvo_intro"] = intro

        # Directivas resolutivas
        pos_directivas = PATRON_DIRECTIVA_RESOLUTIVA.search(texto)

        pos_fin_body = None
        if pos_directivas and pos_body_start:
            if pos_directivas.start() > pos_body_start.start():
                pos_fin_body = pos_directivas.start()
        if pos_fin_body is None and pos_cierre:
            if not pos_body_start or pos_cierre.start() > pos_body_start.start():
                pos_fin_body = pos_cierre.start()

        # Body
        if pos_body_start:
            if pos_fin_body:
                sections["body"] = texto[pos_body_start.start() : pos_fin_body].strip()
            else:
                sections["body"] = texto[pos_body_start.start() :].strip()

        # Closing
        closing_start = pos_fin_body or (pos_cierre.start() if pos_cierre else None)
        if closing_start:
            raw_closing = texto[closing_start:].strip()
            sections["closing"] = self._clean_closing(raw_closing)

        # Fallback
        if not sections["body"] and not pos_vistos and not pos_considerando:
            sections["body"] = texto.strip()
            logger.warning("No se detectaron secciones VISTOS/CONSIDERANDO. Tratando todo como cuerpo.")

        # Extraer anexos del texto completo (después del cuerpo)
        annex_match = re.search(
            r"^ANEXO\s+[NIVX\d]",
            texto,
            re.MULTILINE | re.IGNORECASE,
        )
        if annex_match:
            annex_start = annex_match.start()
            # Solo capturar si está después del inicio del cuerpo
            if not pos_body_start or annex_start > pos_body_start.start():
                sections["anexos_raw"] = texto[annex_start:].strip()

        # Unwrap PDF line breaks in all text sections
        for key in ("vistos", "considerando", "resuelvo_intro", "body", "closing"):
            if sections.get(key):
                sections[key] = self._unwrap_pdf_lines(sections[key])

        return sections

    # ───────────────────────────────────────────────────────────────────────
    # Limpieza de texto extraído de PDF
    # ───────────────────────────────────────────────────────────────────────

    _PATRON_NEW_UNIT = re.compile(
        r"^(?:"
        r"\d{1,2}\.?[°º]?\.?\s|"  # Ítems numerados: 1° 2. 3.° etc.
        r"[a-z][.)]\s|"  # Ítems con letra: a. b) etc.
        r"[IVXLCDM]+[.)]\s|"  # Ítems con romano: I. II) etc.
        r"Art[ií]culo\s|"  # Inicio de artículo
        r"T[ÍI]TULO\s|"  # Título
        r"CAP[ÍI]TULO\s|"  # Capítulo
        r"P[ÁA]RRAFO\s|"  # Párrafo
        r"NORMA\s+DE\s+CAR[ÁA]CTER|"  # Norma de Carácter General
        r"VISTOS?\s*:|"  # VISTOS
        r"CONSIDERANDO\s*:|"  # CONSIDERANDO
        r"RESUELVO\s*:|"  # RESUELVO
        r"AN[OÓ]TESE|"  # Cierre
        r"PUBL[IÍ]QUESE|"  # Cierre
        r"REG[IÍ]STRESE|"  # Cierre
        r"COMUN[IÍ]QUESE"  # Cierre
        r")",
        re.IGNORECASE,
    )

    @classmethod
    def _is_new_unit_start(cls, line: str) -> bool:
        """Detecta si una línea inicia un nuevo elemento estructural."""
        return bool(cls._PATRON_NEW_UNIT.match(line))

    @classmethod
    def _unwrap_pdf_lines(cls, text: str) -> str:
        """Une líneas cortadas por el formato de columna del PDF.

        Los PDFs legales tienen ancho de columna fijo (~70-80 chars), lo que
        produce saltos de línea en medio de oraciones. Esta función:
        1. Une líneas consecutivas que forman parte del mismo párrafo.
        2. Preserva quiebres intencionales: líneas vacías, ítems numerados,
           encabezados de sección, inicio de artículos.
        3. Inserta líneas vacías entre párrafos detectados (. + Mayúscula)
           para que el XML generator los separe en <parrafo> distintos.
        """
        if not text:
            return text

        lines = text.split("\n")
        result: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Línea vacía = quiebre de párrafo
            if not stripped:
                result.append("")
                continue

            # Si hay línea previa no vacía, decidir si unir o separar
            if result and result[-1]:
                prev = result[-1].rstrip()

                starts_new_para = False

                # Nuevo elemento estructural → siempre separar
                # SALVO que la línea previa termine en preposición/artículo
                # (referencia inline: "contemplados en el\nCapítulo IV...")
                if cls._is_new_unit_start(stripped):
                    if prev and re.search(
                        r"\b(?:el|la|los|las|del|al|en|de|un|una)\s*$",
                        prev,
                        re.IGNORECASE,
                    ):
                        result[-1] = prev + " " + stripped
                        continue
                    starts_new_para = True
                # Terminador de oración + mayúscula → nuevo párrafo
                elif prev and prev[-1] in ".;:" and stripped[0].isupper():
                    starts_new_para = True

                if starts_new_para:
                    # Insertar línea vacía si no hay una ya
                    if result[-1] != "":
                        result.append("")
                    result.append(stripped)
                    continue

                # Continuación: unir con la línea anterior
                result[-1] = prev + " " + stripped
                continue

            result.append(stripped)

        return "\n".join(result)

    @staticmethod
    def _clean_closing(raw: str) -> str:
        """Limpia el texto de cierre eliminando artefactos de PDF.

        Elimina:
        - Números de página sueltos al final
        - Iniciales de funcionarios (PVL/PCP/CVS/POR)
        - Secciones DISTRIBUCION
        - Contenido de ANEXOS (se separan aparte)
        """
        lines = raw.split("\n")
        clean_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Cortar en DISTRIBUCION
            if re.match(r"^DISTRIBUCI[OÓ]N\s*:", stripped, re.IGNORECASE):
                break

            # Cortar en ANEXO (inicio de sección de anexos)
            if re.match(r"^ANEXO\s+[NIVX\d]", stripped, re.IGNORECASE):
                break

            clean_lines.append(line)

        # Eliminar líneas finales vacías, números de página e iniciales
        while clean_lines:
            last = clean_lines[-1].strip()
            if not last:
                clean_lines.pop()
                continue
            # Número de página suelto
            if re.match(r"^\d{1,3}$", last):
                clean_lines.pop()
                continue
            # Iniciales de funcionarios (PVL/PCP/CVS/POR)
            if re.match(r"^[A-Z]{2,4}(?:/[A-Z]{2,4})+$", last):
                clean_lines.pop()
                continue
            break

        return "\n".join(clean_lines).strip()

    # ───────────────────────────────────────────────────────────────────────
    # Parseo de Anexos
    # ───────────────────────────────────────────────────────────────────────

    _PATRON_ANEXO = re.compile(
        r"^ANEXO\s+([NIVXLCDM]+|\d+)",
        re.IGNORECASE | re.MULTILINE,
    )

    @classmethod
    def _parse_anexos(cls, raw_text: str) -> list[dict[str, str]]:
        """Parsea el texto de anexos en una lista de diccionarios.

        Detecta múltiples anexos (ANEXO I, ANEXO II, etc.) y extrae
        su título y texto para cada uno.

        Returns:
            Lista de dicts con keys: titulo, texto, numero.
        """
        if not raw_text:
            return []

        # Encontrar todas las posiciones de inicio de ANEXO
        matches = list(cls._PATRON_ANEXO.finditer(raw_text))
        if not matches:
            return []

        anexos: list[dict[str, str]] = []
        for i, match in enumerate(matches):
            numero = match.group(1).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)

            chunk = raw_text[start:end].strip()

            # Extraer título: primera línea completa (puede incluir "DE LA NCG...")
            lines = chunk.split("\n")
            titulo_lines: list[str] = []
            text_start_idx = 0

            for j, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    text_start_idx = j + 1
                    break
                titulo_lines.append(stripped)
                text_start_idx = j + 1

            titulo = " ".join(titulo_lines)
            texto = "\n".join(lines[text_start_idx:]).strip()

            # Limpiar artefactos finales del texto del anexo
            texto_lines = texto.split("\n")
            while texto_lines:
                last = texto_lines[-1].strip()
                if not last or re.match(r"^\d{1,3}$", last):
                    texto_lines.pop()
                    continue
                if re.match(r"^[A-Z]{2,4}(?:/[A-Z]{2,4})+$", last):
                    texto_lines.pop()
                    continue
                break
            texto = "\n".join(texto_lines).strip()

            anexos.append({
                "titulo": titulo,
                "texto": texto,
                "numero": numero,
            })

        return anexos

    # ───────────────────────────────────────────────────────────────────────
    # Parseo del cuerpo normativo
    # ───────────────────────────────────────────────────────────────────────

    def _parse_body(self, texto: str) -> list[EstructuraFuncional]:
        """Parsea el cuerpo normativo en estructuras funcionales jerárquicas."""
        lines = texto.split("\n")
        root_structures: list[EstructuraFuncional] = []

        current_titulo: EstructuraFuncional | None = None
        current_capitulo: EstructuraFuncional | None = None
        current_article: EstructuraFuncional | None = None
        article_lines: list[str] = []
        article_counter = 0
        division_counter = 0
        pending_titulo_desc: str | None = None

        def finalize_article():
            nonlocal current_article, article_lines
            if current_article and article_lines:
                texto_completo = "\n".join(article_lines).strip()
                current_article.texto = texto_completo

                if current_article.titulo_parte == f"Artículo {current_article.nombre_parte}":
                    texto_flat = " ".join(texto_completo.split("\n")[:3])
                    # Exigir \s+ después del "." para no romper en "N.°", "D.S.", etc.
                    titulo_match = re.match(
                        r"^([A-ZÁÉÍÓÚÑ](?:[^.]|\.(?=[°º])){1,100})\.\s+",
                        texto_flat,
                    )
                    if titulo_match:
                        art_titulo = titulo_match.group(1).strip()
                        current_article.titulo_parte = (
                            f"Artículo {current_article.nombre_parte}. {art_titulo}"
                        )
                        remaining = texto_flat[titulo_match.end() :].strip()
                        if remaining:
                            full_text = " ".join(texto_completo.split("\n"))
                            pos = full_text.find(remaining)
                            if pos >= 0:
                                current_article.texto = full_text[pos:]

                article_lines = []

        def get_parent() -> EstructuraFuncional | None:
            return current_capitulo or current_titulo

        def add_to_parent(elem: EstructuraFuncional):
            parent = get_parent()
            if parent:
                parent.hijos.append(elem)
            else:
                root_structures.append(elem)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                if current_article:
                    article_lines.append("")
                continue

            if pending_titulo_desc is not None:
                if (
                    not PATRON_TITULO.match(stripped)
                    and not PATRON_CAPITULO.match(stripped)
                    and not PATRON_ARTICULO.match(stripped)
                    and not PATRON_ARTICULO_TRANSITORIO.match(stripped)
                ):
                    if current_titulo:
                        current_titulo.titulo_parte += f" {stripped}"
                    # Seguir capturando si la línea termina en preposición/artículo
                    if not re.search(r"\b(?:de|del|la|las|los|el|en|y|para|por|al|a)\s*$", stripped, re.IGNORECASE):
                        pending_titulo_desc = None
                    continue
                pending_titulo_desc = None

            # ─── PÁRRAFO (división legal chilena, equivalente estructural a Capítulo) ───
            match_parrafo = PATRON_PARRAFO.match(stripped)
            if match_parrafo:
                # Detectar referencia inline: "dispuesto en el\nPárrafo 2 del Título 3"
                if current_article and article_lines:
                    last_text = ""
                    for al in reversed(article_lines):
                        if al.strip():
                            last_text = al.strip()
                            break
                    if last_text and last_text[-1] not in ".;:":
                        article_lines.append(stripped)
                        continue
                finalize_article()
                current_article = None
                division_counter += 1

                numero = match_parrafo.group(1)
                descripcion = match_parrafo.group(2).strip()

                current_capitulo = EstructuraFuncional(
                    id_parte=str(division_counter),
                    tipo_parte="Párrafo",
                    nombre_parte=numero,
                    titulo_parte=stripped if descripcion else f"PÁRRAFO {numero}",
                    nivel=1,
                )

                if current_titulo:
                    current_titulo.hijos.append(current_capitulo)
                else:
                    root_structures.append(current_capitulo)

                if not descripcion:
                    for j in range(i + 1, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        if (
                            next_line
                            and not PATRON_ARTICULO.match(next_line)
                            and not PATRON_TITULO.match(next_line)
                            and not PATRON_CAPITULO.match(next_line)
                            and not PATRON_PARRAFO.match(next_line)
                        ):
                            current_capitulo.titulo_parte += f" {next_line}"
                            lines[j] = ""
                            break
                continue

            # ─── TÍTULO ───
            match_titulo = PATRON_TITULO.match(stripped)
            if match_titulo:
                # Detectar referencia inline (misma lógica que Capítulo)
                if current_article and article_lines:
                    last_text = ""
                    for al in reversed(article_lines):
                        if al.strip():
                            last_text = al.strip()
                            break
                    if last_text and last_text[-1] not in ".;:":
                        article_lines.append(stripped)
                        continue
                finalize_article()
                current_article = None
                current_capitulo = None
                division_counter += 1

                numero = match_titulo.group(1)
                descripcion = match_titulo.group(2).strip()

                current_titulo = EstructuraFuncional(
                    id_parte=str(division_counter),
                    tipo_parte="Título",
                    nombre_parte=numero,
                    titulo_parte=stripped if descripcion else f"TÍTULO {numero}",
                    nivel=0,
                )
                root_structures.append(current_titulo)

                if not descripcion:
                    pending_titulo_desc = numero
                continue

            # ─── CAPÍTULO ───
            match_cap = PATRON_CAPITULO.match(stripped)
            if match_cap:
                # Detectar referencia inline: "contemplados en el\nCapítulo IV"
                # Si estamos dentro de un artículo y la última línea no termina
                # con terminador de oración, esto es una referencia, no estructura.
                if current_article and article_lines:
                    last_text = ""
                    for al in reversed(article_lines):
                        if al.strip():
                            last_text = al.strip()
                            break
                    if last_text and last_text[-1] not in ".;:":
                        article_lines.append(stripped)
                        continue
                finalize_article()
                current_article = None
                division_counter += 1

                numero = match_cap.group(1)
                descripcion = match_cap.group(2).strip()

                current_capitulo = EstructuraFuncional(
                    id_parte=str(division_counter),
                    tipo_parte="Capítulo",
                    nombre_parte=numero,
                    titulo_parte=stripped if descripcion else f"CAPÍTULO {numero}",
                    nivel=1,
                )

                if current_titulo:
                    current_titulo.hijos.append(current_capitulo)
                else:
                    root_structures.append(current_capitulo)

                if not descripcion:
                    for j in range(i + 1, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        if (
                            next_line
                            and not PATRON_ARTICULO.match(next_line)
                            and not PATRON_TITULO.match(next_line)
                            and not PATRON_CAPITULO.match(next_line)
                        ):
                            current_capitulo.titulo_parte += f" {next_line}"
                            lines[j] = ""
                            break
                continue

            # ─── ARTÍCULO TRANSITORIO ───
            if PATRON_ARTICULO_TRANSITORIO.match(stripped):
                finalize_article()
                article_counter += 1

                current_article = EstructuraFuncional(
                    id_parte=str(article_counter),
                    tipo_parte="Artículo",
                    nombre_parte="transitorio",
                    titulo_parte="Artículo Transitorio",
                    nivel=2,
                    transitorio=True,
                )
                article_lines = []
                resto = re.sub(
                    r"^Art[ií]culo\s+transitorio[°º.]?\s*[:\-.]?\s*",
                    "",
                    stripped,
                    flags=re.IGNORECASE,
                )
                if resto.strip():
                    article_lines.append(resto.strip())
                add_to_parent(current_article)
                continue

            # ─── ARTÍCULO ───
            match_art = PATRON_ARTICULO.match(stripped)
            if match_art:
                finalize_article()
                article_counter += 1

                numero = match_art.group(1)
                resto = match_art.group(2).strip()

                art_titulo = ""
                art_first_text = resto
                # Exigir \s+ después del "." para no romper en "N.°", "D.S.", etc.
                titulo_match = re.match(
                    r"^([A-ZÁÉÍÓÚÑ](?:[^.]|\.(?=[°º])){1,80})\.\s+[:\-]?\s*(.*)",
                    resto,
                    re.DOTALL,
                )
                if titulo_match:
                    art_titulo = titulo_match.group(1).strip()
                    art_first_text = titulo_match.group(2).strip()

                titulo_parte = f"Artículo {numero}"
                if art_titulo:
                    titulo_parte = f"Artículo {numero}. {art_titulo}"

                current_article = EstructuraFuncional(
                    id_parte=str(article_counter),
                    tipo_parte="Artículo",
                    nombre_parte=numero,
                    titulo_parte=titulo_parte,
                    nivel=2,
                )
                article_lines = []
                if art_first_text:
                    article_lines.append(art_first_text)

                add_to_parent(current_article)
                continue

            # ─── TEXTO REGULAR ───
            if current_article:
                article_lines.append(stripped)

        finalize_article()
        return root_structures

    # ───────────────────────────────────────────────────────────────────────
    # Utilidades
    # ───────────────────────────────────────────────────────────────────────

    def _count_articles(self, estructuras: list[EstructuraFuncional]) -> int:
        """Cuenta artículos recursivamente."""
        count = 0
        for e in estructuras:
            if "artículo" in e.tipo_parte.lower() or "articulo" in e.tipo_parte.lower():
                count += 1
            count += self._count_articles(e.hijos)
        return count

    def _count_divisions(self, estructuras: list[EstructuraFuncional]) -> int:
        """Cuenta divisiones (no artículos) recursivamente."""
        count = 0
        for e in estructuras:
            if "artículo" not in e.tipo_parte.lower() and "articulo" not in e.tipo_parte.lower():
                count += 1
            count += self._count_divisions(e.hijos)
        return count

    @staticmethod
    def _capitalize_materia(materia: str) -> str:
        """Capitaliza una materia: si está en mayúsculas, solo primera letra mayúscula."""
        if materia == materia.upper():
            return materia.capitalize()
        return materia
