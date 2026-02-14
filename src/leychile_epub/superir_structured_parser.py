"""Parser estructurado para normas SUPERIR (NCGs e Instructivos).

Extiende SuperirBaseParser para extraer semántica detallada:
- Considerandos individuales numerados
- Epígrafes de artículos separados
- Cierre con fórmula y firmante
- Listados letrados dentro de artículos

Produce NormaSuperir que envuelve Norma y agrega campos estructurados
para generación de XML conforme a superir_v1.xsd.
"""

from __future__ import annotations

import logging
import re

from .ncg_parser import NCGParser
from .scraper_v2 import EstructuraFuncional, Norma
from .superir_base_parser import SuperirBaseParser
from .superir_models import (
    ActoAdministrativo,
    AnexoStandalone,
    CierreSuperir,
    ConsiderandoItem,
    ContenidoArticulo,
    Firmante,
    ItemContentBlock,
    ItemListado,
    NormaSuperir,
    SubitemModel,
    PuntoResolutivo,
    RequisitoItemModel,
    RequisitoModel,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# PATRONES
# ═══════════════════════════════════════════════════════════════════════════════

# Considerandos: "1° Que," / "1º Que," / "1° Que " / "1.° Que," / "1. Que,"
# NCGs 4-15 usan "N° Que,", NCGs 16-17 usan "N. Que," (período sin grado).
# NCG 22: considerando 5° empieza con "Asimismo," en vez de "Que,".
PATRON_CONSIDERANDO_NUM = re.compile(
    r"^(\d+)[.°º]+\s+(?:[Qq]ue[,\s]|Asimismo[,\s])",
    re.MULTILINE,
)

# Artículo con epígrafe: "Artículo 1. Modelo." o "Artículo 1°. Modelo."
# Grupo 1 = número, Grupo 2 = epígrafe (puede estar vacío)
PATRON_ARTICULO_EPIGRAFE = re.compile(
    r"Art[ií]culo\s+(\d+(?:\s*bis|\s*ter)?)[°º.]?\.\s+"
    r"([A-ZÁÉÍÓÚÑ](?:[^.]|\.(?=[°º])){1,80})\.\s+",
    re.IGNORECASE,
)

# Items letrados: "a)" o "a." al inicio de línea O precedido por doble espacio
# (el base parser colapsa newlines en doble espacio).
# Requiere doble espacio para evitar falsos positivos como "artículos 2 g) y 5".
PATRON_ITEM_LETRADO = re.compile(
    r"(?:^|\s{2})([a-z])[.)]\s+",
    re.MULTILINE,
)

# Items con numerales romanos minúsculos: "i.", "ii.", "iii.", "iv.", "v.", "vi."
# Usados como subitems dentro de items letrados (NCG 16 Art 2°) o como
# items top-level (NCG 16 Arts 8° y 11°, NCG 20 Art 2°).
# NCG 20 tiene items sin espacio después del punto: "iii.Libros", "iv.Balance".
# Lookahead [A-Za-záéíóúñÁÉÍÓÚÑ] evita matches en texto como "i.e." o "iv.".
PATRON_ITEM_ROMANO = re.compile(
    r"(?:^|\s{2})(i{1,3}|iv|vi{0,3})[.]\s*(?=[A-Za-záéíóúñÁÉÍÓÚÑ])",
    re.MULTILINE,
)

# Items numerados arábigos: "1.", "2.", "3." o "1)", "2)", "3)"
# Usados en NCG 17 Art 1° y 2° como listados de requisitos simples.
# Se distingue de considerandos porque los considerandos usan "1°" o "1. Que,".
# Soporta 3 contextos de detección:
# - Inicio de línea (^)
# - Después de doble espacio (newline colapsado por base parser)
# - Después de ". " o ": " (inline dentro de párrafo, NCG 17 Arts 1° y 2°)
PATRON_ITEM_NUMERADO = re.compile(
    r"(?:^|(?<=\s\s)|(?<=\.\s)|(?<=:\s))(\d+)[.)]\s+(?=[A-Z])",
    re.MULTILINE,
)

# Fórmula de cierre: "Anótese y publíquese." o "ANÓTESE Y PUBLÍQUESE,"
PATRON_FORMULA_CIERRE = re.compile(
    r"(An[óo]tese\b.*?)(?:\n|$)",
    re.IGNORECASE,
)

# Fórmula de dictación: "Que, en conformidad a lo anterior, ...dicta la siguiente:"
# Captura incluyendo el terminador ":"
PATRON_FORMULA_DICTACION = re.compile(
    r"(Que,?\s+en\s+conformidad\s+a\s+lo\s+anterior.*?(?:dicta\s+la\s+siguiente|siguiente\s+norma).*?[.:])\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Items letrados mayúsculas: "A.-", "B.-" o "A.", "B." (sin guion).
# Usados en NCGs 19-20 Art 1° como listado de primer nivel.
# Se distinguen de requisitos romanos (I.-, II.-) porque la secuencia incluye
# letras NO válidas en numerales romanos (A, B, E, F, G, etc.).
# NCG 19 usa formato "A.- ", NCG 20 usa "A. " (dash opcional).
PATRON_ITEM_LETRADO_MAYUS = re.compile(
    r"(?:^|\s{2})([A-Z])\.(?:-|–)?\s+",
    re.MULTILINE,
)

# Subitems alfanuméricos: "a.1)", "a.2)", "b.1)" etc.
# Usados en NCG 20 Art 1° item A: subitems con numeración compuesta.
# Cada subitem puede estar en su propio <sublistado> con párrafos intermedios.
# Formato "letra.dígito)" es suficientemente específico para usar \s+ en vez de \s{2}.
# En el texto colapsado, a.1) puede aparecer tras ". " (sentence boundary).
PATRON_SUBITEM_ALFANUM = re.compile(
    r"(?:^|\s+)([a-z]\.\d+)\)\s+",
    re.MULTILINE,
)

# Requisitos: "I.-", "II.-", "III.-" al inicio de línea O precedido por 2+ espacios.
# El base parser colapsa newlines en espacios dobles, así que soportamos ambos formatos.
# Solo captura el marcador, no el texto completo (el texto se extrae entre marcadores).
PATRON_REQUISITO = re.compile(
    r"(?:^|\s{2})([IVXLCDM]+)\.\-\s+",
    re.MULTILINE,
)

# Referencia a anexo: "En el Anexo I...", "conforme a los Anexos II, III y IV"
PATRON_REFERENCIA_ANEXO = re.compile(
    r"^(?:En\s+el\s+Anexo|conforme\s+(?:a\s+los|al)\s+Anexo)",
    re.IGNORECASE,
)

# Números de anexo referenciados en texto: "Anexo I", "Anexos II, III y IV"
# Soporta numeración compuesta: "Anexo I-A", "Anexo V-B" (NCG 20).
PATRON_ANEXO_NUMS = re.compile(
    r"Anexo[s]?\s+([IVXLCDM\d]+(?:-[A-Z])?\b(?:\s*,\s*[IVXLCDM\d]+(?:-[A-Z])?\b)*(?:\s+y\s+[IVXLCDM\d]+(?:-[A-Z])?\b)?)",
    re.IGNORECASE,
)

# Anexo con título entre comillas (resolutivo): Anexo I-A "Indicadores..."
# Soporta comillas ASCII (") y Unicode (\u201c \u201d).
# Soporta prefijo "N.°" opcional: Anexo N.° 1 "Modelo..." (NCG 22).
# Números: romanos (I-A), arábigos (1), arábigos compuestos (2 A, 2 B).
PATRON_ANEXO_CON_TITULO = re.compile(
    r'Anexo\s+(?:N\.?\s*[°º]?\s*)?(\d+(?:\s*[A-Z])?|[IVXLCDM]+(?:-[A-Z])?)\s+["\u201c]([^"\u201d]+)["\u201d]',
    re.IGNORECASE,
)

# Firmante: línea en mayúsculas seguida de línea con cargo
PATRON_FIRMANTE = re.compile(
    r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,})$\s*^(.+(?:Superintendente|Superintendenta).*)$",
    re.MULTILINE | re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PATRONES RESOLUCIÓN EXENTA (NCGs envueltas desde 2023)
# ═══════════════════════════════════════════════════════════════════════════════

# Detectar Resolución Exenta en primeras líneas
PATRON_RESOLUCION_EXENTA = re.compile(
    r"RESOLUCI[ÓO]N\s+EXENTA\s+N\.?\s*[°º]?\s*(\d+)",
    re.IGNORECASE,
)

# Sección RESUELVO: / RESUELVO
# NCGs 14-17 usan "RESUELVO:", NCG 18 usa "RESUELVO" sin dos puntos.
PATRON_RESUELVO = re.compile(
    r"^RESUELVO\s*:?\s*$",
    re.MULTILINE,
)

# Punto resolutivo: "1° APRUÉBESE...", "2° PUBLÍQUESE...", "1. APRUÉBESE..."
# NCGs 16-17 usan "N." (período) en vez de "N°" (grado).
PATRON_PUNTO_RESOLUTIVO = re.compile(
    r"(?:^|\n)\s*(\d+)[.°º]\s+([A-ZÁÉÍÓÚÑ])",
    re.MULTILINE,
)

# Encabezado de NCG dentro de Resolución Exenta
PATRON_NCG_HEADER = re.compile(
    r"^NORMA\s+DE\s+CAR[ÁA]CTER\s+GENERAL\s+N\.?\s*[°º]?\s*(\d+)",
    re.MULTILINE | re.IGNORECASE,
)

# Código de distribución: "PVL/PCP/CVS/POR"
PATRON_DISTRIBUCION = re.compile(
    r"^([A-Z]{2,4}(?:/[A-Z]{2,4})+)\s*$",
    re.MULTILINE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PARSER ESTRUCTURADO
# ═══════════════════════════════════════════════════════════════════════════════


class SuperirStructuredParser:
    """Parser que produce NormaSuperir con campos estructurados.

    Usa composición: delega el parsing base a NCGParser (o cualquier
    SuperirBaseParser subclass) y luego enriquece el resultado con
    considerandos individuales, epígrafes, listados y cierre.

    Example:
        >>> parser = SuperirStructuredParser()
        >>> norma_superir = parser.parse(texto, url="https://...")
    """

    def __init__(self, base_parser: SuperirBaseParser | None = None):
        """Inicializa con un parser base.

        Args:
            base_parser: Parser base para delegación. Default: NCGParser.
        """
        self._base_parser = base_parser or NCGParser()

    def parse(
        self,
        texto: str,
        url: str = "",
        doc_numero: str = "",
        catalog_entry: dict | None = None,
    ) -> NormaSuperir:
        """Parsea texto y retorna NormaSuperir con campos estructurados.

        Args:
            texto: Texto completo de la norma.
            url: URL de origen.
            doc_numero: Número de la norma (override).
            catalog_entry: Metadatos del catálogo.

        Returns:
            NormaSuperir con Norma base + campos estructurados.
        """
        # 0. Detectar Resolución Exenta y extraer componentes wrapper
        acto_admin = _extract_acto_administrativo(texto)
        resolutivo: list[PuntoResolutivo] = []
        preambulo_ncg: list[str] = []
        resolutivo_final: list[PuntoResolutivo] = []
        distribucion = ""

        if acto_admin:
            resolutivo, preambulo_ncg = _extract_resolutivo_y_preambulo(texto)
            resolutivo_final = _extract_resolutivo_final(texto)
            distribucion = _extract_distribucion(texto)
            logger.info(
                f"  Resolución Exenta N.° {acto_admin.numero}: "
                f"{len(resolutivo)} resolutivo, "
                f"{len(preambulo_ncg)} preámbulo, "
                f"{len(resolutivo_final)} resolutivo_final"
            )

        # 1. Parsing base - adaptar argumentos según tipo de parser
        if isinstance(self._base_parser, NCGParser):
            norma_base = self._base_parser.parse(
                texto, url=url, ncg_numero=doc_numero, catalog_entry=catalog_entry
            )
        else:
            norma_base = self._base_parser.parse(
                texto, url=url, doc_numero=doc_numero, catalog_entry=catalog_entry
            )

        # 2. Extraer considerandos individuales y fórmula de dictación
        considerandos = self.parse_considerandos(norma_base.considerandos_texto)
        formula_dictacion = self._extract_formula_dictacion(considerandos)

        # 3. Extraer epígrafes de artículos
        articulos_epigrafe = self._extract_epigrafes(norma_base.estructuras)

        # 4. Extraer contenido estructurado (listados letrados)
        articulos_contenido = self._extract_contenido_estructurado(norma_base.estructuras)

        # 5. Extraer cierre
        cierre = self.parse_cierre(norma_base.disposiciones_finales_texto)

        # 5a. Para RE: el base parser puede producir cierre mal formado
        # (disposiciones_finales_texto contiene el RESUELVO, no el cierre).
        # Fallback: extraer cierre directamente del texto raw.
        if acto_admin:
            cierre_raw = _extract_cierre_from_raw(texto)
            if cierre_raw:
                cierre = cierre_raw

        # 5b. Agregar distribución y destinatarios al cierre si es Resolución Exenta
        if distribucion and cierre:
            cierre.distribucion = distribucion
        if acto_admin and cierre:
            destinatarios = _extract_destinatarios_notificacion(texto)
            if destinatarios:
                cierre.destinatarios_notificacion = destinatarios

        # 5c. Limpiar resolutivo_final del texto del último artículo
        # (el base parser absorbe "2° PUBLÍQUESE..." como texto del art. final)
        if resolutivo_final:
            _clean_resolutivo_from_articles(norma_base.estructuras, resolutivo_final)

        # 6. Detectar anexos standalone
        anexos_standalone = self._detect_standalone_anexos(
            norma_base, articulos_contenido, resolutivo
        )

        norma_superir = NormaSuperir(
            norma_base=norma_base,
            considerandos=considerandos,
            cierre=cierre,
            articulos_epigrafe=articulos_epigrafe,
            articulos_contenido=articulos_contenido,
            formula_dictacion=formula_dictacion,
            anexos_standalone=anexos_standalone,
            acto_administrativo=acto_admin,
            resolutivo=resolutivo,
            preambulo_ncg=preambulo_ncg,
            resolutivo_final=resolutivo_final,
        )

        logger.info(
            f"  Estructurado: {len(considerandos)} considerandos, "
            f"{len(articulos_epigrafe)} epígrafes, "
            f"formula_dictacion={'sí' if formula_dictacion else 'no'}, "
            f"cierre={'sí' if cierre else 'no'}, "
            f"anexos_standalone={len(anexos_standalone)}"
        )

        return norma_superir

    # ───────────────────────────────────────────────────────────────────────
    # Considerandos individuales
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def parse_considerandos(texto: str) -> list[ConsiderandoItem]:
        """Separa el texto de considerandos en items individuales.

        Detecta el patrón "N° Que," para delimitar cada considerando.

        Args:
            texto: Texto completo de la sección CONSIDERANDO.

        Returns:
            Lista de ConsiderandoItem numerados.
        """
        if not texto or not texto.strip():
            return []

        matches = list(PATRON_CONSIDERANDO_NUM.finditer(texto))

        if not matches:
            # Sin numeración: un solo considerando
            cleaned = texto.strip()
            if cleaned:
                return [ConsiderandoItem(numero=1, texto=cleaned)]
            return []

        items: list[ConsiderandoItem] = []
        for i, match in enumerate(matches):
            numero = int(match.group(1))
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(texto)

            # Texto completo del considerando (incluye "Que,")
            item_texto = texto[start:end].strip()

            # Quitar el prefijo "N° Que," / "N.° Que," / "N. Que,"
            # NCGs 4-15 usan "N°" o "N.°", NCGs 16-17 usan "N." (período).
            item_texto = re.sub(
                r"^\d+[.°º]+\s+",
                "",
                item_texto,
            ).strip()

            if item_texto:
                items.append(ConsiderandoItem(numero=numero, texto=item_texto))

        return items

    # ───────────────────────────────────────────────────────────────────────
    # Fórmula de dictación
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_formula_dictacion(
        considerandos: list[ConsiderandoItem],
    ) -> str:
        """Extrae la fórmula de dictación del último considerando.

        La fórmula de dictación es el texto transitorio entre los
        considerandos y el cuerpo normativo, típicamente:
        "Que, en conformidad a lo anterior, se dicta la siguiente:"

        Dos casos posibles:
        1. El último "considerando" ES enteramente la fórmula (NCGs 4, 6)
           → se extrae y el considerando se ELIMINA de la lista.
        2. La fórmula es un párrafo final del último considerando (NCG 7)
           → se extrae y el considerando conserva su texto previo.

        También limpia residuos de encabezados estructurales que el
        base parser captura dentro de los considerandos
        (NORMA DE CARÁCTER GENERAL, TÍTULO I, etc.).

        Args:
            considerandos: Lista de considerandos (se modifica in-place).

        Returns:
            Texto de la fórmula de dictación, o "" si no se detecta.
        """
        if not considerandos:
            return ""

        last = considerandos[-1]
        texto = last.texto

        # Primero limpiar residuos de encabezados del texto
        clean_text = texto
        for pattern in (
            r"\s*NORMA\s+DE\s+CAR[ÁA]CTER\s+GENERAL.*$",
            r"\s*T[ÍI]TULO\s+[IVXLCDM]+.*$",
        ):
            clean_text = re.sub(pattern, "", clean_text, flags=re.IGNORECASE | re.DOTALL)
        clean_text = clean_text.strip()
        last.texto = clean_text

        # Buscar la fórmula de dictación
        match = PATRON_FORMULA_DICTACION.search(clean_text)
        formula = ""
        if match:
            formula = match.group(1).strip()
            # Quitar la fórmula del texto del considerando
            remaining = clean_text[: match.start()].strip()
            last.texto = remaining

            # Si el considerando queda vacío, era enteramente la fórmula → eliminarlo
            if not remaining:
                considerandos.pop()
        else:
            # Fallback: buscar "NORMA DE CARÁCTER GENERAL" como residuo
            residuo_idx = clean_text.upper().find("NORMA DE CARÁCTER GENERAL")
            if residuo_idx < 0:
                residuo_idx = clean_text.upper().find("NORMA DE CARACTER GENERAL")
            if residuo_idx >= 0:
                last.texto = clean_text[:residuo_idx].strip()

        return formula

    # ───────────────────────────────────────────────────────────────────────
    # Epígrafes de artículos
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_epigrafes(
        estructuras: list[EstructuraFuncional],
    ) -> dict[str, str]:
        """Extrae epígrafes de los títulos de artículos.

        Un artículo con titulo_parte "Artículo 1. Modelo" tiene
        epígrafe "Modelo".

        Args:
            estructuras: Jerarquía de EstructuraFuncional del parser base.

        Returns:
            Diccionario {numero_articulo: epigrafe}.
        """
        epigrafes: dict[str, str] = {}

        def recurse(items: list[EstructuraFuncional]) -> None:
            for item in items:
                if item.tipo_parte == "Artículo" and item.titulo_parte:
                    # "Artículo N. Epígrafe" → extraer epígrafe
                    match = re.match(
                        r"Art[ií]culo\s+\S+\.\s+(.*)",
                        item.titulo_parte,
                        re.IGNORECASE,
                    )
                    if match:
                        epigrafe = match.group(1).strip().rstrip(".")
                        if epigrafe:
                            epigrafes[item.nombre_parte] = epigrafe
                recurse(item.hijos)

        recurse(estructuras)
        return epigrafes

    # ───────────────────────────────────────────────────────────────────────
    # Contenido estructurado (listados letrados)
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_contenido_estructurado(
        estructuras: list[EstructuraFuncional],
    ) -> dict[str, ContenidoArticulo]:
        """Extrae contenido estructurado de artículos con listados o requisitos.

        Detecta items letrados (a), b), c)) y requisitos (I.-, II.-)
        dentro del texto de artículos.

        Args:
            estructuras: Jerarquía de EstructuraFuncional del parser base.

        Returns:
            Diccionario {numero_articulo: ContenidoArticulo} solo para
            artículos con estructura especial (listados, requisitos).
        """
        contenidos: dict[str, ContenidoArticulo] = {}

        def recurse(items: list[EstructuraFuncional]) -> None:
            for item in items:
                if item.tipo_parte == "Artículo" and item.texto:
                    contenido = SuperirStructuredParser._parse_articulo_contenido(
                        item.texto
                    )
                    if contenido.listado or contenido.requisitos:
                        contenidos[item.nombre_parte] = contenido
                recurse(item.hijos)

        recurse(estructuras)
        return contenidos

    @staticmethod
    def _parse_articulo_contenido(texto: str) -> ContenidoArticulo:
        """Parsea el texto de un artículo en párrafos, listados y requisitos.

        Prioridad de detección:
        1. Requisitos (I.-, II.-) - si presentes, items letrados internos
           son sub-items del requisito, no listado independiente.
        2. Listados letrados (a), b)) con posibles subitems romanos.
        3. Items numerados arábigos (1., 2., 3.) - para NCGs con listados
           numerados (ej: NCG 17).
        4. Items romanos puros (i., ii., iii.) - cuando no hay items
           letrados padre (ej: NCG 16 Art 8°).
        5. Párrafos planos - sin estructura especial.

        Args:
            texto: Texto del artículo (sin título/epígrafe).

        Returns:
            ContenidoArticulo con párrafos, listados, requisitos
            y referencia_anexo separados.
        """
        contenido = ContenidoArticulo()

        if not texto:
            return contenido

        # 1a. Detectar items letrados mayúsculas (A.-, B.-, C.-, etc.)
        # Formato idéntico a requisitos (X.-) pero con letras alfabéticas.
        # Distinguimos de requisitos romanos (I, II, III) verificando si hay
        # letras que NO son válidas en numerales romanos.
        upper_items = list(PATRON_ITEM_LETRADO_MAYUS.finditer(texto))
        if upper_items:
            identifiers = {m.group(1) for m in upper_items}
            roman_chars = {"I", "V", "X", "L", "C", "D", "M"}
            non_roman = identifiers - roman_chars
            if non_roman:
                # Al menos una letra no es numeral romano → items alfabéticos
                return SuperirStructuredParser._parse_with_uppercase_listado(
                    texto, upper_items
                )

        # 1b. Detectar requisitos (I.-, II.-, etc.)
        req_matches = list(PATRON_REQUISITO.finditer(texto))
        if req_matches:
            return SuperirStructuredParser._parse_with_requisitos(texto, req_matches)

        # 2. Detectar items letrados (a), b), etc.)
        lettered = list(PATRON_ITEM_LETRADO.finditer(texto))
        is_genuine_lettered = bool(lettered)

        if lettered:
            # Filtrar falsos positivos: si TODOS los items letrados detectados
            # son caracteres que también son numerales romanos (i, v), y el
            # patrón romano detecta MÁS matches (ii, iii, iv además de i, v),
            # son items romanos disfrazados de letrados — dejar que paso 4
            # los resuelva. Afecta NCG 16 Arts 8° y 11°.
            roman_single_chars = {"i", "v"}
            all_roman_like = all(
                m.group(1) in roman_single_chars for m in lettered
            )
            if all_roman_like:
                roman_check = list(PATRON_ITEM_ROMANO.finditer(texto))
                if len(roman_check) > len(lettered):
                    is_genuine_lettered = False

        if is_genuine_lettered:
            # Verificar si hay subitems romanos dentro de algún item letrado
            roman = list(PATRON_ITEM_ROMANO.finditer(texto))
            has_subitems = False
            if roman:
                # Si hay romanos Y el primer romano viene después del primer letrado,
                # son subitems. Si el primer romano viene antes, es falso positivo
                # (ej: "artículo 11° número iii)" no es un sub-item).
                first_roman_pos = roman[0].start()
                first_letter_pos = lettered[0].start()
                last_letter_pos = lettered[-1].start()
                if first_letter_pos < first_roman_pos < last_letter_pos + 500:
                    has_subitems = True

            if has_subitems:
                # Filtrar items letrados que son realmente romanos (i, v)
                # para que solo los genuinos (a, b, c...) sean padres.
                # Afecta NCG 16 Art 2°: "a) Veedores... i. subitem...".
                roman_chars = {"i", "v"}
                genuine_parents = [
                    m for m in lettered if m.group(1) not in roman_chars
                ]
                if genuine_parents:
                    return SuperirStructuredParser._parse_with_subitems(
                        texto, genuine_parents, roman
                    )
            return SuperirStructuredParser._parse_with_listado(
                texto, lettered, attr_name="letra"
            )

        # 3. Detectar items numerados arábigos (1., 2., 3.)
        numbered = list(PATRON_ITEM_NUMERADO.finditer(texto))
        if numbered:
            return SuperirStructuredParser._parse_with_listado(
                texto, numbered, attr_name="numero"
            )

        # 4. Detectar items romanos puros (i., ii., iii., iv., v.)
        roman_top = list(PATRON_ITEM_ROMANO.finditer(texto))
        if roman_top:
            return SuperirStructuredParser._parse_with_listado(
                texto, roman_top, attr_name="numero"
            )

        # 5. Sin estructura especial: solo párrafos
        for parrafo in _split_parrafos(texto):
            contenido.parrafos.append(parrafo)
        return contenido

    @staticmethod
    def _parse_with_listado(
        texto: str, items: list[re.Match], attr_name: str = "letra"
    ) -> ContenidoArticulo:
        """Parsea artículo con listado simple (letrado, numerado o romano).

        Soporta interleaved: párrafo → listado → párrafo (post-listado).
        attr_name determina si los items usan 'letra' o 'numero'.
        """
        contenido = ContenidoArticulo()

        # Texto antes del primer item → párrafos
        pre_text = texto[: items[0].start()].strip()
        if pre_text:
            for parrafo in _split_parrafos(pre_text):
                contenido.parrafos.append(parrafo)

        # Items del listado
        for i, match in enumerate(items):
            identifier = match.group(1)
            start = match.start()
            end = items[i + 1].start() if i + 1 < len(items) else len(texto)
            item_texto = texto[start:end].strip()
            # Remover el marcador del inicio (letra, número o romano)
            item_texto = re.sub(
                r"^(?:[a-z][.)]\s+|\d+[.)]\s+|(?:i{1,3}|iv|vi{0,3})[.]\s*)",
                "",
                item_texto,
            ).strip()

            # Para el último item: detectar texto post-listado
            if i == len(items) - 1 and item_texto:
                item_texto, post_text = _split_last_item_post_listado(item_texto)

                if post_text:
                    for parrafo in _split_parrafos(post_text):
                        contenido.parrafos_post.append(parrafo)

            if item_texto:
                kwargs = {attr_name: identifier, "texto": item_texto}
                contenido.listado.append(ItemListado(**kwargs))

        return contenido

    @staticmethod
    def _parse_with_subitems(
        texto: str,
        lettered: list[re.Match],
        roman: list[re.Match],
    ) -> ContenidoArticulo:
        """Parsea artículo con items letrados que contienen subitems romanos.

        Patrón (NCG 16 Art 2°):
            a) [Nombre:] Texto introductorio
               i. Subitem 1...
               ii. Subitem 2...
            b) [Nombre:] Texto introductorio
               i. Subitem 1...
        """
        contenido = ContenidoArticulo()

        # Texto antes del primer item letrado → párrafos
        pre_text = texto[: lettered[0].start()].strip()
        if pre_text:
            for parrafo in _split_parrafos(pre_text):
                contenido.parrafos.append(parrafo)

        for i, let_match in enumerate(lettered):
            letra = let_match.group(1)
            let_start = let_match.start()
            let_end = lettered[i + 1].start() if i + 1 < len(lettered) else len(texto)
            item_block = texto[let_start:let_end].strip()
            # Remover marcador letra
            item_block = re.sub(r"^[a-z][.)]\s+", "", item_block).strip()

            # Buscar subitems romanos dentro de este bloque de item
            sub_matches = list(PATRON_ITEM_ROMANO.finditer(item_block))

            if sub_matches:
                # Texto antes del primer subitem → párrafo introductorio
                intro_text = item_block[: sub_matches[0].start()].strip()
                item_parrafos = []
                nombre = ""

                if intro_text:
                    # Intentar extraer nombre: "Para el caso de los [Nombre], ..."
                    nombre_match = re.match(
                        r"(?:Para\s+el\s+caso\s+de\s+los\s+)([^,]+),\s*(.*)",
                        intro_text,
                        re.IGNORECASE,
                    )
                    if nombre_match:
                        nombre = nombre_match.group(1).strip()
                        rest = nombre_match.group(2).strip()
                        if rest:
                            # Capitalize first letter
                            rest = rest[0].upper() + rest[1:] if rest else rest
                            item_parrafos.append(rest)
                    else:
                        item_parrafos.append(intro_text)

                # Parsear subitems
                subitems = []
                for j, sub_match in enumerate(sub_matches):
                    sub_num = sub_match.group(1)
                    sub_start = sub_match.start()
                    sub_end = (
                        sub_matches[j + 1].start()
                        if j + 1 < len(sub_matches)
                        else len(item_block)
                    )
                    sub_texto = item_block[sub_start:sub_end].strip()
                    sub_texto = re.sub(
                        r"^(?:i{1,3}|iv|vi{0,3})[.]\s*", "", sub_texto
                    ).strip()
                    if sub_texto:
                        subitems.append(SubitemModel(numero=sub_num, texto=sub_texto))

                contenido.listado.append(
                    ItemListado(
                        letra=letra,
                        nombre=nombre,
                        parrafos=item_parrafos,
                        subitems=subitems,
                    )
                )
            else:
                # Item letrado simple sin subitems
                contenido.listado.append(ItemListado(letra=letra, texto=item_block))

        return contenido

    @staticmethod
    def _parse_with_uppercase_listado(
        texto: str,
        items: list[re.Match],
    ) -> ContenidoArticulo:
        """Parsea artículo con items letrados mayúsculas (A.-, B.-, etc.).

        Soporta:
        - Items simples (solo texto)
        - Items multi-párrafo (párrafos separados por \\n\\n dentro del item)
        - Items complejos con subitems letrados minúsculas a), b) y
          párrafos post-sublistado (NCG 19 Art 1° E).
        - Items complejos con subitems alfanuméricos a.1), a.2) y
          párrafos intermedios intercalados (NCG 20 Art 1° A).

        Patrón: NCG 19 Art 1° (items A.– a G.–), NCG 20 Art 1° (A. a F.).
        """
        contenido = ContenidoArticulo()

        # Texto antes del primer item → párrafos
        pre_text = texto[: items[0].start()].strip()
        if pre_text:
            for parrafo in _split_parrafos(pre_text):
                contenido.parrafos.append(parrafo)

        for i, match in enumerate(items):
            letra = match.group(1)
            start = match.start()
            end = items[i + 1].start() if i + 1 < len(items) else len(texto)
            item_block = texto[start:end].strip()
            # Remover marcador "X.- " o "X. " (dash/en-dash opcional)
            item_block = re.sub(r"^[A-Z]\.(?:-|–)?\s+", "", item_block).strip()

            # ── Paso 1: Buscar subitems alfanuméricos (a.1, a.2, b.1...) ──
            alfanum_subs = list(PATRON_SUBITEM_ALFANUM.finditer(item_block))
            if alfanum_subs:
                contenido.listado.append(
                    _parse_item_with_alfanum_subitems(letra, item_block, alfanum_subs)
                )
                continue

            # ── Paso 2: Buscar subitems letrados (a), b), c)...) ──
            # Solo considerar matches que forman secuencia alfabética contigua
            # desde 'a': a), b), c)... para evitar falsos positivos como i), ii)
            # que son items informativos dentro de párrafos (NCG 19 Art 1° E).
            all_sub_matches = list(PATRON_ITEM_LETRADO.finditer(item_block))
            sub_matches: list[re.Match] = []  # type: ignore[type-arg]
            expected_letter = "a"
            for sm in all_sub_matches:
                if sm.group(1) == expected_letter:
                    sub_matches.append(sm)
                    expected_letter = chr(ord(expected_letter) + 1)
                else:
                    break

            if sub_matches:
                # Item complejo: párrafos intro + subitems + párrafos post
                intro_text = item_block[: sub_matches[0].start()].strip()
                item_parrafos = []
                if intro_text:
                    item_parrafos = _split_parrafos(intro_text)

                # Calcular fin del último subitem real.
                # Buscamos el primer \n\n después del último subitem para
                # separar el contenido del subitem del texto posterior.
                # Esto evita que text post-sublistado sea absorbido por
                # el último subitem (NCG 19 Art 1° E: texto entre b) e i)).
                last_sm = sub_matches[-1]
                next_break = item_block.find("\n\n", last_sm.end())
                if next_break == -1:
                    last_sub_text_end = len(item_block)
                else:
                    last_sub_text_end = next_break

                post_text = item_block[last_sub_text_end:].strip()

                # Parsear subitems de la secuencia contigua
                subitems = []
                for j, sm in enumerate(sub_matches):
                    sub_letra = sm.group(1)
                    sm_start = sm.start()
                    sm_end = (
                        sub_matches[j + 1].start()
                        if j + 1 < len(sub_matches)
                        else last_sub_text_end
                    )
                    sub_texto = item_block[sm_start:sm_end].strip()
                    # Remover marcador "x) " o "x. "
                    sub_texto = re.sub(
                        r"^[a-z][.)]\s+", "", sub_texto
                    ).strip()
                    if sub_texto:
                        subitems.append(
                            SubitemModel(letra=sub_letra, texto=sub_texto)
                        )

                # Parsear párrafos post-sublistado
                parrafos_post = []
                if post_text:
                    parrafos_post = _split_parrafos(post_text)

                contenido.listado.append(
                    ItemListado(
                        letra=letra,
                        parrafos=item_parrafos,
                        subitems=subitems,
                        parrafos_post=parrafos_post,
                    )
                )
            else:
                # Item simple o multi-párrafo
                parrafos = _split_parrafos(item_block)
                if len(parrafos) == 1:
                    contenido.listado.append(
                        ItemListado(letra=letra, texto=parrafos[0])
                    )
                else:
                    contenido.listado.append(
                        ItemListado(letra=letra, parrafos=parrafos)
                    )

        return contenido

    @staticmethod
    def _parse_with_requisitos(
        texto: str, req_matches: list[re.Match]
    ) -> ContenidoArticulo:
        """Parsea artículo con requisitos numerados (I.-, II.-, etc.).

        El regex PATRON_REQUISITO captura solo el marcador (número romano).
        El texto de cada requisito se extrae como bloque entre marcadores.

        Cada requisito puede contener párrafos y/o items letrados.
        """
        contenido = ContenidoArticulo()

        # Texto antes del primer requisito → párrafos de intro
        pre_text = texto[: req_matches[0].start()].strip()
        if pre_text:
            for parrafo in _split_parrafos(pre_text):
                contenido.parrafos.append(parrafo)

        # Parsear cada requisito
        for i, match in enumerate(req_matches):
            numero = match.group(1)

            # Bloque de texto = desde fin del marcador hasta inicio del siguiente
            block_start = match.end()
            block_end = (
                req_matches[i + 1].start()
                if i + 1 < len(req_matches)
                else len(texto)
            )
            full_text = texto[block_start:block_end].strip()

            requisito = RequisitoModel(numero=numero)

            # Buscar items letrados dentro del bloque
            item_matches = list(PATRON_ITEM_LETRADO.finditer(full_text))

            if item_matches:
                # Texto antes del primer item → nombre o párrafo del requisito
                pre_item = full_text[: item_matches[0].start()].strip()
                if pre_item:
                    _assign_requisito_intro(requisito, pre_item)

                # Parsear cada item
                for j, item_match in enumerate(item_matches):
                    letra = item_match.group(1)
                    item_end = (
                        item_matches[j + 1].start()
                        if j + 1 < len(item_matches)
                        else len(full_text)
                    )
                    item_texto = full_text[item_match.start() : item_end].strip()
                    item_texto = re.sub(r"^[a-z][.)]\s+", "", item_texto).strip()
                    if item_texto:
                        req_item = _parse_requisito_item(letra, item_texto)
                        requisito.items.append(req_item)
            else:
                # Sin items: solo párrafos
                for p in _split_parrafos(full_text):
                    requisito.parrafos.append(p)

            contenido.requisitos.append(requisito)

        # Detectar referencia_anexo en el último elemento
        _extract_referencia_anexo(contenido)

        return contenido

    # ───────────────────────────────────────────────────────────────────────
    # Anexos standalone
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def _detect_standalone_anexos(
        norma_base: Norma,
        articulos_contenido: dict[str, ContenidoArticulo],
        resolutivo: list[PuntoResolutivo] | None = None,
    ) -> list[AnexoStandalone]:
        """Detecta anexos referenciados y los convierte a standalone.

        Tres fuentes de información:
        1. Anexos parseados por el base parser (norma_base.anexos).
        2. Referencias a anexos en texto de artículos y referencia_anexo.
        3. Anexos con título en texto del resolutivo (Anexo I-A "Título...").

        Todos se marcan pendiente=True ya que su estructura interna
        (formularios, tablas contables) no se modela en XML aún.

        Args:
            norma_base: Norma base con posibles anexos parseados.
            articulos_contenido: Contenido estructurado de artículos.
            resolutivo: Puntos resolutivos (pueden tener títulos de anexos).

        Returns:
            Lista de AnexoStandalone deduplicados por número.
        """
        found: dict[str, AnexoStandalone] = {}

        # Fuente 1: anexos con título desde el resolutivo (mayor precisión)
        # Esto captura numeración compuesta como "I-A", "V-B" o "2 A", "2 B".
        # Para arábigos simples (1, 2, 3...) sin sufijo letra, preferimos
        # la detección por Fuentes 2/3 que usan romanos del encabezado del anexo.
        resolutivo_found: dict[str, AnexoStandalone] = {}
        has_compound = False
        if resolutivo:
            for punto in resolutivo:
                for m in PATRON_ANEXO_CON_TITULO.finditer(punto.texto):
                    num = m.group(1).upper().strip()
                    # Normalizar "2 A" → "2-A" (arábigo+espacio+letra → guión)
                    if " " in num:
                        num = num.replace(" ", "-")
                        has_compound = True
                    if "-" in num:
                        has_compound = True
                    # Limpiar newlines del título (multi-line en resolutivo)
                    titulo = " ".join(m.group(2).split())
                    resolutivo_found[num] = AnexoStandalone(
                        numero=num, titulo=titulo, pendiente=True
                    )
            # Solo usar Fuente 1 si tiene numeración compuesta O
            # si la cantidad de anexos es alta (>= 5, sugiere arábigos legítimos)
            if has_compound or len(resolutivo_found) >= 5:
                found = resolutivo_found

        # Fuente 2: anexos del base parser (si no se encontraron en resolutivo)
        if not found:
            for anexo in norma_base.anexos:
                titulo = anexo.get("titulo", "")
                numero = anexo.get("numero", "") or anexo.get("id_parte", "")
                if numero:
                    found[str(numero)] = AnexoStandalone(
                        numero=str(numero), titulo=titulo, pendiente=True
                    )

        # Fuente 3: referencias en artículos (referencia_anexo y texto)
        def _collect_text(items: list[EstructuraFuncional]) -> str:
            """Recolecta todo el texto de artículos para buscar referencias."""
            texts: list[str] = []
            for item in items:
                if item.tipo_parte == "Artículo" and item.texto:
                    texts.append(item.texto)
                _collect_text_inner = _collect_text(item.hijos)
                if _collect_text_inner:
                    texts.append(_collect_text_inner)
            return " ".join(texts)

        # Buscar en texto de artículos
        all_text = _collect_text(norma_base.estructuras)

        # También buscar en referencia_anexo de contenidos estructurados
        for cont in articulos_contenido.values():
            if cont.referencia_anexo:
                all_text += " " + cont.referencia_anexo

        # Extraer números de anexo referenciados (solo si no se tiene ya de resolutivo)
        if not found:
            for match in PATRON_ANEXO_NUMS.finditer(all_text):
                nums_str = match.group(1)
                # Separar "II, III y IV" en ["II", "III", "IV"]
                nums_str = nums_str.replace(" y ", ",")
                for num in nums_str.split(","):
                    num = num.strip()
                    if num and num not in found:
                        found[num] = AnexoStandalone(numero=num, pendiente=True)

        # Si se encontraron standalone, limpiar los anexos del base parser
        # para que no se emitan en <anexos> contenedor
        if found:
            norma_base.anexos.clear()

        # Ordenar por número romano/arábigo (soporta compuestos I-A, V-B, 2-A)
        def _sort_key(item: tuple[str, AnexoStandalone]) -> int:
            num = item[0]
            if "-" in num:
                parts = num.split("-", 1)
                base_str = parts[0]
                # Intentar arábigo primero, luego romano
                try:
                    base_val = int(base_str) * 100
                except ValueError:
                    roman_val = _roman_to_int(base_str)
                    base_val = roman_val * 100 if roman_val > 0 else 999 * 100
                suffix_val = ord(parts[1].upper()) - ord("A") if len(parts) > 1 else 0
                return base_val + suffix_val
            # Sin guión: número simple
            try:
                return int(num) * 100
            except ValueError:
                roman_val = _roman_to_int(num)
                return roman_val * 100 if roman_val > 0 else 999 * 100

        return [v for _, v in sorted(found.items(), key=_sort_key)]

    # ───────────────────────────────────────────────────────────────────────
    # Cierre (fórmula + firmante)
    # ───────────────────────────────────────────────────────────────────────

    @staticmethod
    def parse_cierre(texto: str) -> CierreSuperir | None:
        """Extrae fórmula de cierre y firmante del texto de disposiciones finales.

        Busca patrones como:
            Anótese y publíquese.
            JOSEFINA MONTENEGRO ARANEDA
            Superintendenta de Insolvencia y Reemprendimiento

        Args:
            texto: Texto de disposiciones finales / cierre.

        Returns:
            CierreSuperir con fórmula y firmante, o None si no se detecta.
        """
        if not texto or not texto.strip():
            return None

        # Extraer fórmula
        formula = ""
        formula_match = PATRON_FORMULA_CIERRE.search(texto)
        if formula_match:
            formula = formula_match.group(1).strip()
        else:
            # Buscar "ANÓTESE" como fallback
            for line in texto.split("\n"):
                stripped = line.strip().upper()
                if "ANÓTESE" in stripped or "ANOTESE" in stripped:
                    formula = line.strip()
                    break

        if not formula:
            return None

        # Extraer firmante
        firmante = _extract_firmante(texto)

        return CierreSuperir(formula=formula, firmante=firmante)


# ═══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════════


# Palabras clave de cierre que NO son nombres de personas
_CIERRE_KEYWORDS = {
    "ANÓTESE", "ANOTESE", "PUBLÍQUESE", "PUBLIQUESE",
    "NOTIFÍQUESE", "NOTIFIQUESE", "ARCHÍVESE", "ARCHIVESE",
    "DISTRIBUCIÓN", "DISTRIBUCION", "RESUELVO", "DÉJASE",
    "DEJASE", "DISPÓNGASE", "DISPONGASE", "REGÍSTRESE",
    "REGISTRESE", "COMUNÍQUESE", "COMUNIQUESE", "DERÓGUENSE",
    "DEROGUENSE",
}

# Patrón: "NOMBRE APELLIDO Cargo" en una sola línea (PDF unwrapped)
_PATRON_NOMBRE_CARGO_INLINE = re.compile(
    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,}?)\s+"
    r"((?:Superintendente|Superintendenta|Fiscal)\s.+)",
    re.IGNORECASE,
)


def _extract_firmante(texto: str) -> Firmante | None:
    """Extrae el firmante del texto de cierre.

    Maneja múltiples formatos:
    1. Nombre en línea separada + cargo en siguiente línea
    2. Nombre y cargo en misma línea (PDF unwrapped)
    3. Solo nombre en mayúsculas

    Args:
        texto: Texto del cierre / disposiciones finales.

    Returns:
        Firmante o None si no se detecta.
    """
    if not texto:
        return None

    # Intento 1: regex original (nombre en una línea, cargo en otra)
    firmante_match = PATRON_FIRMANTE.search(texto)
    if firmante_match:
        return Firmante(
            nombre=firmante_match.group(1).strip(),
            cargo=firmante_match.group(2).strip().upper(),
        )

    # Intento 2: nombre y cargo en misma línea (PDF unwrapped)
    lines = [l.strip() for l in texto.split("\n") if l.strip()]
    for line in lines:
        inline_match = _PATRON_NOMBRE_CARGO_INLINE.match(line)
        if inline_match:
            nombre = inline_match.group(1).strip()
            cargo = inline_match.group(2).strip().upper()
            # Verificar que no sea keyword de cierre
            if not any(kw in nombre.upper() for kw in _CIERRE_KEYWORDS):
                return Firmante(nombre=nombre, cargo=cargo)

    # Intento 3: heurística - línea en mayúsculas al final
    for i, line in enumerate(lines):
        if (
            line == line.upper()
            and len(line.split()) >= 2
            and not any(kw in line for kw in _CIERRE_KEYWORDS)
            and len(line) > 10
        ):
            cargo = ""
            if i + 1 < len(lines):
                cargo = lines[i + 1].upper()
            return Firmante(nombre=line, cargo=cargo)

    return None


def _split_parrafos(texto: str) -> list[str]:
    """Divide texto en párrafos por líneas en blanco o doble espacio.

    Dos modos (igual que _split_into_paragraphs del generador):
    1. Texto con newlines → split por líneas en blanco.
    2. Texto colapsado (sin newlines) → split por ". " + doble espacio + mayúscula.

    Args:
        texto: Texto con posibles líneas en blanco.

    Returns:
        Lista de párrafos no vacíos.
    """
    if not texto or not texto.strip():
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
        # Si un párrafo NO termina en puntuación de cierre (.;:)) y el siguiente
        # existe, son probablemente un corte de página, no párrafos reales.
        merged: list[str] = [parrafos[0]]
        for p in parrafos[1:]:
            prev = merged[-1]
            if prev and prev.rstrip()[-1:] not in ".;:)":
                merged[-1] = prev + " " + p
            else:
                merged.append(p)
        return merged

    # Modo 2: texto colapsado → split por ". " + doble espacio + mayúscula
    full_text = parrafos[0] if parrafos else texto.strip()
    parts = re.split(r"(?<=\.)\s{2}(?=[A-ZÁÉÍÓÚÑ])", full_text)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]

    return [full_text] if full_text else []


def _parse_item_with_alfanum_subitems(
    letra: str,
    item_block: str,
    alfanum_subs: list[re.Match],  # type: ignore[type-arg]
) -> ItemListado:
    """Parsea un item con subitems alfanuméricos intercalados (a.1, a.2...).

    Produce content_blocks con la secuencia ordenada de sublistados y
    párrafos intermedios. Cada subitem va en su propio <sublistado>
    con párrafos intercalados entre ellos.

    Patrón: NCG 20 Art 1° item A:
        Texto intro...
        a.1) Subitem uno...
        Párrafo intermedio...
        a.2) Subitem dos...

    Args:
        letra: Letra del item padre (A, B, etc.)
        item_block: Texto del item (sin marcador).
        alfanum_subs: Matches de PATRON_SUBITEM_ALFANUM.

    Returns:
        ItemListado con content_blocks para emisión intercalada.
    """
    content_blocks: list[ItemContentBlock] = []

    # Texto intro antes del primer subitem
    intro_text = item_block[: alfanum_subs[0].start()].strip()
    intro_parrafos: list[str] = []
    if intro_text:
        intro_parrafos = _split_parrafos(intro_text)

    # Procesar cada subitem y los párrafos intermedios
    for j, sm in enumerate(alfanum_subs):
        sub_id = sm.group(1)  # "a.1", "a.2", etc.

        # Determinar fin del texto de este subitem
        if j + 1 < len(alfanum_subs):
            next_sm_start = alfanum_subs[j + 1].start()
        else:
            next_sm_start = len(item_block)

        # Texto desde el fin del marcador hasta el inicio del siguiente subitem
        between = item_block[sm.end():next_sm_start].strip()

        # Separar texto del subitem de párrafos intermedios.
        # Un doble newline marca el fin del texto del subitem.
        double_nl = between.find("\n\n")
        if double_nl >= 0 and j + 1 < len(alfanum_subs):
            sub_texto = between[:double_nl].strip()
            mid_text = between[double_nl:].strip()
        else:
            # Último subitem o sin párrafos intermedios
            sub_texto = between
            mid_text = ""

        # Juntar líneas del subitem en un solo párrafo
        sub_texto = " ".join(sub_texto.split())

        # Emitir sublistado con un subitem
        if sub_texto:
            content_blocks.append(
                ItemContentBlock(
                    tipo="sublistado",
                    subitems=[SubitemModel(numero=sub_id, texto=sub_texto)],
                )
            )

        # Emitir párrafos intermedios
        if mid_text:
            for p in _split_parrafos(mid_text):
                content_blocks.append(
                    ItemContentBlock(tipo="parrafo", texto=p)
                )

    return ItemListado(
        letra=letra,
        parrafos=intro_parrafos,
        content_blocks=content_blocks,
    )


def _split_last_item_post_listado(item_texto: str) -> tuple[str, str]:
    """Separa texto del último item de un listado del párrafo post-listado.

    El base parser colapsa newlines en doble espacio. Un párrafo post-listado
    se identifica como texto después de un doble espacio que inicia con
    mayúscula y NO parece continuación del item (no es ", que", ", el", etc.).

    Args:
        item_texto: Texto del último item (ya sin prefijo "b) ").

    Returns:
        (item_text, post_text): Texto del item y texto post-listado.
        Si no hay post-listado, post_text es "".

    Ejemplo:
        "Póliza de seguro... Fomento.  Será carga del sujeto..."
        → ("Póliza de seguro... Fomento.", "Será carga del sujeto...")
    """
    # Buscar doble espacio seguido de mayúscula (posible inicio de párrafo nuevo)
    # Excluir posiciones donde la mayúscula es continuación de oración
    candidates = list(re.finditer(r"\.\s{2}([A-ZÁÉÍÓÚÑ])", item_texto))

    if not candidates:
        return item_texto, ""

    # Tomar el primer candidato que no sea continuación obvia del item
    # (el punto + doble espacio + mayúscula indica nuevo párrafo del artículo)
    for match in candidates:
        split_pos = match.start() + 1  # después del punto
        post_text = item_texto[split_pos:].strip()
        item_text = item_texto[:split_pos].strip()

        # Verificar que el post-text no es una sublista (no empieza con letra) + ...)
        if post_text and not re.match(r"^[a-z][.)]\s+", post_text):
            return item_text, post_text

    return item_texto, ""


def _assign_requisito_intro(requisito: RequisitoModel, pre_item: str) -> None:
    """Asigna texto pre-items como nombre o párrafo del requisito.

    Si el texto es una frase corta que termina en ":" (etiqueta),
    se usa como nombre del requisito. Si es largo, va como párrafo.
    """
    if (
        pre_item.endswith(":")
        and len(pre_item) < 120
        and "\n" not in pre_item.strip()
    ):
        requisito.nombre = pre_item.rstrip(":").strip()
    else:
        for p in _split_parrafos(pre_item):
            requisito.parrafos.append(p)


def _parse_requisito_item(letra: str, item_texto: str) -> RequisitoItemModel:
    """Parsea un item letrado dentro de un requisito.

    Detecta nombre (etiqueta) antes de ":" si presente.
    Soporta items multi-párrafo (e.g., item d de NCG 7).
    """
    nombre = ""
    texto_para_parsear = item_texto

    # Extraer nombre: "Ingresos: Deberá detallarse..."
    nombre_match = re.match(
        r"^([A-ZÁÉÍÓÚÑ][^:.]{1,60})[.:]\s+(.*)",
        item_texto,
        re.DOTALL,
    )
    if nombre_match:
        potential = nombre_match.group(1).strip()
        if len(potential.split()) <= 8:
            nombre = potential
            texto_para_parsear = nombre_match.group(2).strip()

    item_parrafos = _split_parrafos(texto_para_parsear)
    req_item = RequisitoItemModel(letra=letra, nombre=nombre)

    if len(item_parrafos) > 1:
        req_item.parrafos = item_parrafos
    else:
        req_item.texto = item_parrafos[0] if item_parrafos else ""

    return req_item


def _extract_referencia_anexo(contenido: ContenidoArticulo) -> None:
    """Extrae referencia_anexo del último párrafo del último requisito.

    Si el último párrafo del último requisito o último item comienza con
    "En el Anexo..." o "conforme a los Anexos...", lo extrae como
    contenido.referencia_anexo.
    """
    if not contenido.requisitos:
        return

    last_req = contenido.requisitos[-1]

    # Determinar dónde buscar la referencia_anexo
    if last_req.items:
        # Verificar el último item
        last_item = last_req.items[-1]
        if last_item.parrafos:
            source = last_item.parrafos
        elif last_item.texto:
            if PATRON_REFERENCIA_ANEXO.match(last_item.texto):
                contenido.referencia_anexo = last_item.texto
                last_req.items.pop()
            return
        else:
            return
    else:
        source = last_req.parrafos

    if source and PATRON_REFERENCIA_ANEXO.match(source[-1]):
        contenido.referencia_anexo = source.pop()


def _roman_to_int(s: str) -> int:
    """Convierte número romano a entero."""
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    prev = 0
    for char in reversed(s.upper()):
        val = values.get(char, 0)
        if val < prev:
            result -= val
        else:
            result += val
        prev = val
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACCIÓN DE RESOLUCIÓN EXENTA
# ═══════════════════════════════════════════════════════════════════════════════


def _extract_acto_administrativo(texto: str) -> ActoAdministrativo | None:
    """Detecta y extrae el acto administrativo (Resolución Exenta) del texto.

    Busca en las primeras 500 caracteres el patrón "RESOLUCIÓN EXENTA N.° XXXX".
    Si lo encuentra, extrae tipo, número y materia.

    Args:
        texto: Texto completo de la norma.

    Returns:
        ActoAdministrativo o None si no es una Resolución Exenta.
    """
    re_match = PATRON_RESOLUCION_EXENTA.search(texto[:500])
    if not re_match:
        return None

    numero = re_match.group(1)

    # Extraer materia: línea descriptiva entre organismo y SANTIAGO/VISTOS
    materia = ""
    vistos_pos = texto.upper().find("VISTOS")
    if vistos_pos < 0:
        vistos_pos = 500
    header_text = texto[:vistos_pos]

    for line in header_text.split("\n"):
        stripped = line.strip()
        # La materia suele empezar con "Aprueba", "Dicta", "Modifica"
        if stripped and re.match(
            r"(?:Aprueba|Dicta|Modifica|Establece|Regula)",
            stripped,
            re.IGNORECASE,
        ):
            materia = stripped
            break

    return ActoAdministrativo(
        tipo="RESOLUCIÓN EXENTA",
        numero=numero,
        materia=materia.upper() if materia else "",
    )


def _extract_resolutivo_y_preambulo(
    texto: str,
) -> tuple[list[PuntoResolutivo], list[str]]:
    """Extrae puntos resolutivos pre-NCG y preámbulo de la NCG.

    El resolutivo está entre "RESUELVO:" y el encabezado NCG.
    El preámbulo está entre el encabezado NCG (+ subtítulo) y el primer TÍTULO.

    Args:
        texto: Texto completo de la norma.

    Returns:
        (resolutivo, preambulo_ncg): Puntos resolutivos y párrafos del preámbulo.
    """
    resolutivo: list[PuntoResolutivo] = []
    preambulo_ncg: list[str] = []

    # Encontrar RESUELVO:
    resuelvo_match = PATRON_RESUELVO.search(texto)
    if not resuelvo_match:
        return resolutivo, preambulo_ncg

    resuelvo_start = resuelvo_match.end()

    # Encontrar encabezado NCG después de RESUELVO
    ncg_header_match = PATRON_NCG_HEADER.search(texto[resuelvo_start:])
    if not ncg_header_match:
        return resolutivo, preambulo_ncg

    ncg_header_abs = resuelvo_start + ncg_header_match.start()

    # --- Resolutivo: puntos entre RESUELVO: y encabezado NCG ---
    resuelvo_section = texto[resuelvo_start:ncg_header_abs]
    resolutivo = _parse_puntos_resolutivos(resuelvo_section)

    # --- Preámbulo NCG: texto entre encabezado NCG y primer TÍTULO ---
    # Avanzar después del encabezado NCG y posible subtítulo
    after_ncg_header = texto[ncg_header_abs:]

    # Encontrar primer TÍTULO
    titulo_match = re.search(
        r"^T[ÍI]TULO\s+[IVXLCDM\d]+",
        after_ncg_header,
        re.MULTILINE | re.IGNORECASE,
    )
    if titulo_match:
        # Texto entre encabezado NCG y primer TÍTULO
        between = after_ncg_header[: titulo_match.start()]
        # Saltar la línea del encabezado NCG y posible subtítulo
        lines = between.split("\n")
        preambulo_lines: list[str] = []
        skip_header = True
        for line in lines:
            stripped = line.strip()
            if skip_header:
                # Saltar líneas de encabezado NCG y subtítulo (SOBRE..., mayúsculas)
                if not stripped:
                    continue
                if stripped == stripped.upper() and len(stripped) > 10:
                    continue
                skip_header = False
            if stripped:
                preambulo_lines.append(stripped)

        if preambulo_lines:
            preambulo_ncg = [" ".join(preambulo_lines)]

    return resolutivo, preambulo_ncg


def _extract_resolutivo_final(texto: str) -> list[PuntoResolutivo]:
    """Extrae puntos resolutivos post-NCG (después del cuerpo normativo).

    Busca puntos numerados (2° PUBLÍQUESE..., 3° DISPÓNGASE...) entre
    el último artículo y la fórmula de cierre (ANÓTESE...).

    Args:
        texto: Texto completo de la norma.

    Returns:
        Lista de PuntoResolutivo del resolutivo final.
    """
    # Encontrar la fórmula de cierre
    anotese_match = re.search(
        r"^(AN[ÓO]TESE\b.*?)$",
        texto,
        re.MULTILINE | re.IGNORECASE,
    )
    if not anotese_match:
        return []

    # Encontrar el último artículo ANTES de la fórmula de cierre.
    # Buscar solo antes de ANÓTESE para evitar matches en anexos
    # (ej: "artículo 505" en texto de anexos con re.IGNORECASE).
    last_art_end = 0
    for match in re.finditer(
        r"^Art[ií]culo\s+\d+",
        texto[: anotese_match.start()],
        re.MULTILINE | re.IGNORECASE,
    ):
        last_art_end = match.end()

    if last_art_end == 0:
        return []

    # Buscar puntos resolutivos entre último artículo y ANÓTESE
    between = texto[last_art_end : anotese_match.start()]

    return _parse_puntos_resolutivos(between)


def _extract_distribucion(texto: str) -> str:
    """Extrae el código de distribución del texto.

    Patrón: "PVL/PCP/CVS/POR" (siglas separadas por /).
    Busca primero cerca de la fórmula de cierre (para NCGs con ANEXO después),
    luego fallback a las últimas 200 chars.

    Args:
        texto: Texto completo de la norma.

    Returns:
        Código de distribución o "" si no se encuentra.
    """
    # Buscar después de la fórmula de cierre (más robusto para NCGs con ANEXO)
    formula_pos = re.search(
        r"AN[ÓO]TESE.*?(?:ARCH[ÍI]VESE|PUBL[ÍI]QUESE)", texto, re.IGNORECASE
    )
    if formula_pos:
        after = texto[formula_pos.end() : formula_pos.end() + 500]
        match = PATRON_DISTRIBUCION.search(after)
        if match:
            return match.group(1)

    # Fallback: últimos 200 caracteres
    tail = texto[-200:]
    match = PATRON_DISTRIBUCION.search(tail)
    return match.group(1) if match else ""


def _extract_cierre_from_raw(texto: str) -> CierreSuperir | None:
    """Extrae cierre directamente del texto raw para NCGs con RE.

    El base parser puede colocar texto incorrecto en disposiciones_finales_texto
    cuando la NCG viene envuelta en Resolución Exenta (especialmente si hay
    ANEXO después del cierre). Este método busca directamente la fórmula
    de cierre y el firmante en el texto raw.

    Patrón buscado:
        ANÓTESE, PUBLÍQUESE Y ARCHÍVESE,
        HUGO SÁNCHEZ RAMÍREZ
        SUPERINTENDENTE DE INSOLVENCIA Y REEMPRENDIMIENTO

    Args:
        texto: Texto completo de la norma.

    Returns:
        CierreSuperir o None si no se puede extraer.
    """
    # Buscar fórmula de cierre en el texto raw.
    # Patrón: "ANÓTESE, PUBLÍQUESE Y ARCHÍVESE," (una línea completa)
    formula_match = re.search(
        r"(AN[ÓO]TESE[,\s]+(?:PUBL[ÍI]QUESE|NOTIF[ÍI]QUESE).*?(?:ARCH[ÍI]VESE|PUBL[ÍI]QUESE)[.,]?)",
        texto,
        re.IGNORECASE,
    )
    if not formula_match:
        return None

    formula = formula_match.group(1).strip()
    # Tomar texto después de la fórmula para buscar firmante
    after_formula = texto[formula_match.end():].strip()
    lines = after_formula.split("\n")

    # Buscar firmante: primera línea en MAYÚSCULAS (nombre), siguiente (cargo)
    nombre = ""
    cargo = ""
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # Nombre: línea en mayúsculas que no sea código de distribución
        if line.isupper() and "/" not in line and "DISTRIBUCION" not in line:
            nombre = line
            # Buscar cargo en las siguientes líneas
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith("-"):
                    if "/" not in next_line or "INSOLVENCIA" in next_line.upper():
                        cargo = next_line.upper()
                        break
            break

    if not nombre:
        return None

    firmante = Firmante(nombre=nombre, cargo=cargo)
    return CierreSuperir(formula=formula, firmante=firmante)


def _extract_destinatarios_notificacion(texto: str) -> str:
    """Extrae destinatarios de la sección DISTRIBUCIÓN del texto.

    Busca líneas con guion después de "DISTRIBUCIÓN:" / "DISTRIBUCION:".
    Ejemplo:
        DISTRIBUCION:
        -Señores/as Liquidadores/as
        -Señores/as Veedores/as
        → "Señores/as Liquidadores/as; Señores/as Veedores/as"

    Args:
        texto: Texto completo de la norma.

    Returns:
        Destinatarios separados por "; " o "" si no se encuentra.
    """
    # Buscar después de la fórmula de cierre (para NCGs con ANEXO después)
    search_region = texto
    formula_pos = re.search(
        r"AN[ÓO]TESE.*?(?:ARCH[ÍI]VESE|PUBL[ÍI]QUESE)", texto, re.IGNORECASE
    )
    if formula_pos:
        search_region = texto[formula_pos.end() : formula_pos.end() + 500]
    else:
        search_region = texto[-500:]
    match = re.search(
        r"DISTRIBUCI[ÓO]N\s*:\s*\n((?:\s*-.*\n?)+)",
        search_region,
        re.IGNORECASE,
    )
    if not match:
        return ""

    lines = match.group(1).strip().split("\n")
    destinatarios = []
    for line in lines:
        line = line.strip().lstrip("-").strip()
        if line and line.lower() != "presente":
            destinatarios.append(line)

    return "; ".join(destinatarios)


def _clean_resolutivo_from_articles(
    estructuras: list[EstructuraFuncional],
    resolutivo_final: list[PuntoResolutivo],
) -> None:
    """Limpia texto de resolutivo_final del último artículo.

    El base parser absorbe los puntos resolutivos (2° PUBLÍQUESE...,
    3° DISPÓNGASE...) como texto del último artículo del cuerpo normativo.
    Esta función los elimina.

    Args:
        estructuras: Jerarquía de EstructuraFuncional.
        resolutivo_final: Puntos resolutivos extraídos.
    """
    if not resolutivo_final:
        return

    # Encontrar el último artículo (recursivo)
    def _find_last_article(items: list[EstructuraFuncional]) -> EstructuraFuncional | None:
        last = None
        for item in items:
            if item.tipo_parte == "Artículo":
                last = item
            child_last = _find_last_article(item.hijos)
            if child_last:
                last = child_last
        return last

    last_art = _find_last_article(estructuras)
    if not last_art or not last_art.texto:
        return

    # Buscar dónde empieza el primer punto resolutivo en el texto del artículo
    # Patrón: "N° VERBO" donde N es un número del resolutivo_final
    for punto in resolutivo_final:
        # Buscar "N° VERBO" en el texto del artículo
        pattern = re.compile(
            rf"\s*{re.escape(punto.numero)}[°º]\s+{re.escape(punto.texto[:20])}",
            re.IGNORECASE,
        )
        match = pattern.search(last_art.texto)
        if match:
            # Truncar el texto del artículo antes de este punto
            last_art.texto = last_art.texto[: match.start()].strip()
            return  # Solo necesitamos encontrar el primer punto

    # Fallback: buscar cualquier "N° MAYÚSCULA" al final del texto
    fallback = re.search(
        r"\s+\d+[°º]\s+[A-ZÁÉÍÓÚÑ]{4,}",
        last_art.texto,
    )
    if fallback:
        last_art.texto = last_art.texto[: fallback.start()].strip()


def _parse_puntos_resolutivos(section: str) -> list[PuntoResolutivo]:
    """Parsea puntos resolutivos numerados de una sección de texto.

    Detecta patrones "N° VERBO..." donde N es un número y VERBO
    empieza con mayúscula (APRUÉBESE, PUBLÍQUESE, DISPÓNGASE, etc.).

    Args:
        section: Texto de la sección con puntos resolutivos.

    Returns:
        Lista de PuntoResolutivo.
    """
    puntos: list[PuntoResolutivo] = []

    matches = list(PATRON_PUNTO_RESOLUTIVO.finditer(section))
    if not matches:
        return puntos

    for i, match in enumerate(matches):
        numero = match.group(1)
        # Texto completo: desde la mayúscula hasta el siguiente punto o fin
        start = match.start() + len(match.group(0)) - 1  # posición de la mayúscula
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section)

        texto = section[start:end].strip()
        # Limpiar trailing newlines
        texto = " ".join(texto.split())

        if texto:
            puntos.append(PuntoResolutivo(numero=numero, texto=texto))

    return puntos
