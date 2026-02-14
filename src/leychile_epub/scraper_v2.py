"""
Scraper v2 para la Biblioteca del Congreso Nacional de Chile.

Este módulo implementa un parser que sigue fielmente el esquema XSD oficial
de LeyChile (EsquemaIntercambioNorma-v1-0.xsd).

Estructura del XML según el esquema:
- Norma (raíz)
  - Identificador (TiposNumeros, Organismos, fechas)
  - Metadatos (TituloNorma, Materias, NombresUsoComun, etc.)
  - Encabezado (texto preámbulo)
  - EstructurasFuncionales (jerarquía de artículos/agrupadores)
    - EstructuraFuncional (tipoParte: Capítulo, Título, Párrafo, Artículo, etc.)
      - Texto
      - Metadatos (NombreParte, TituloParte, Materias)
      - EstructurasFuncionales (anidadas recursivamente)
  - Promulgacion (texto final)
  - Anexos

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import html
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Config, get_config
from .exceptions import NetworkError, ParsingError, ValidationError

logger = logging.getLogger("leychile_epub.scraper")

# Namespace XML oficial de LeyChile
NS = {"lc": "http://www.leychile.cl/esquemas"}

# Dominios permitidos para scraping
_ALLOWED_DOMAINS = {"www.leychile.cl", "leychile.cl", "www.bcn.cl", "bcn.cl"}


@dataclass
class NormaIdentificador:
    """Identificación de la norma según el esquema XSD."""

    tipo: str = ""
    numero: str = ""
    organismos: list[str] = field(default_factory=list)
    fecha_promulgacion: str = ""
    fecha_publicacion: str = ""


@dataclass
class NormaMetadatos:
    """Metadatos de la norma según el esquema XSD."""

    titulo: str = ""
    materias: list[str] = field(default_factory=list)
    conceptos: list[str] = field(default_factory=list)
    nombres_uso_comun: list[str] = field(default_factory=list)
    paises_tratado: list[str] = field(default_factory=list)
    tipo_tratado: str = ""
    fecha_tratado: str = ""
    fecha_derogacion: str = ""
    identificacion_fuente: str = ""
    numero_fuente: str = ""
    leyes_referenciadas: list[str] = field(default_factory=list)


@dataclass
class EstructuraFuncional:
    """Representa una estructura funcional (artículo o agrupador) según el esquema XSD.

    Attributes:
        id_parte: Identificador único de la BCN
        tipo_parte: Tipo de estructura (Artículo, Capítulo, Título, Párrafo, etc.)
        texto: Contenido textual
        nombre_parte: Número/nombre del artículo (ej: "1", "2 bis")
        titulo_parte: Título del agrupador (ej: "CAPÍTULO I DISPOSICIONES GENERALES")
        fecha_version: Fecha de última modificación
        derogado: Si está derogado
        transitorio: Si es transitorio
        materias: Materias asociadas a esta parte
        hijos: Estructuras funcionales anidadas
        nivel: Nivel de profundidad en la jerarquía (0=raíz)
    """

    id_parte: str = ""
    tipo_parte: str = ""
    texto: str = ""
    nombre_parte: str = ""
    titulo_parte: str = ""
    fecha_version: str = ""
    derogado: bool = False
    transitorio: bool = False
    materias: list[str] = field(default_factory=list)
    hijos: list["EstructuraFuncional"] = field(default_factory=list)
    nivel: int = 0


@dataclass
class Norma:
    """Representa una norma completa según el esquema XSD de LeyChile.

    Esta es la estructura principal que contiene todos los datos
    de una ley, decreto u otra norma jurídica.
    """

    # Atributos de la raíz Norma
    norma_id: str = ""
    es_tratado: bool = False
    fecha_version: str = ""
    schema_version: str = ""
    derogado: bool = False

    # Componentes estructurales
    identificador: NormaIdentificador = field(default_factory=NormaIdentificador)
    metadatos: NormaMetadatos = field(default_factory=NormaMetadatos)
    encabezado_texto: str = ""
    encabezado_derogado: bool = False
    vistos_texto: str = ""
    considerandos_texto: str = ""
    estructuras: list[EstructuraFuncional] = field(default_factory=list)
    promulgacion_texto: str = ""
    promulgacion_derogado: bool = False
    disposiciones_finales_texto: str = ""
    anexos: list[dict[str, Any]] = field(default_factory=list)

    # Metadatos adicionales
    url_original: str = ""
    id_version: str = ""

    @property
    def titulo_completo(self) -> str:
        """Genera el título completo de la norma."""
        if self.metadatos.titulo:
            return self.metadatos.titulo
        return f"{self.identificador.tipo} {self.identificador.numero}"

    @property
    def nombre_archivo(self) -> str:
        """Genera un nombre de archivo seguro."""
        tipo = self.identificador.tipo.replace(" ", "_")
        numero = self.identificador.numero.replace(" ", "_").replace("/", "-")
        return f"{tipo}_{numero}"


class BCNXMLParser:
    """Parser XML que sigue el esquema XSD oficial de LeyChile.

    Este parser implementa la especificación completa del esquema
    EsquemaIntercambioNorma-v1-0.xsd para extraer datos estructurados.
    """

    def __init__(self) -> None:
        self.ns = NS

    def parse(self, root: ET.Element) -> Norma:
        """Parsea el elemento raíz XML y retorna una Norma completa.

        Args:
            root: Elemento raíz <Norma> del XML.

        Returns:
            Objeto Norma con todos los datos estructurados.
        """
        norma = Norma()

        # Atributos de la raíz
        norma.norma_id = root.get("normaId", "")
        norma.es_tratado = root.get("esTratado", "") == "tratado"
        norma.fecha_version = root.get("fechaVersion", "")
        norma.schema_version = root.get("SchemaVersion", "")
        norma.derogado = root.get("derogado", "") == "derogado"

        # Parsear componentes
        norma.identificador = self._parse_identificador(root)
        norma.metadatos = self._parse_metadatos(root)
        norma.encabezado_texto, norma.encabezado_derogado = self._parse_encabezado(root)
        norma.estructuras = self._parse_estructuras_funcionales(root)
        norma.promulgacion_texto, norma.promulgacion_derogado = self._parse_promulgacion(root)
        norma.anexos = self._parse_anexos(root)

        return norma

    def _get_text(self, element: ET.Element | None) -> str:
        """Extrae y limpia el texto de un elemento."""
        if element is None:
            return ""

        # Obtener todo el texto recursivamente
        parts = []
        if element.text:
            parts.append(element.text)

        for child in element:
            # Saltar elementos binarios (imágenes)
            if "ArchivoBinario" in child.tag:
                continue
            child_text = self._get_text(child)
            if child_text:
                parts.append(child_text)
            if child.tail:
                parts.append(child.tail)

        text = "".join(parts)
        text = html.unescape(text)
        # Normalizar espacios pero preservar saltos de línea significativos
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    def _parse_identificador(self, root: ET.Element) -> NormaIdentificador:
        """Parsea el elemento Identificador."""
        ident = NormaIdentificador()

        id_elem = root.find("lc:Identificador", self.ns)
        if id_elem is None:
            return ident

        # Fechas de los atributos
        ident.fecha_promulgacion = id_elem.get("fechaPromulgacion", "")
        ident.fecha_publicacion = id_elem.get("fechaPublicacion", "")

        # Tipo y número (puede haber múltiples TipoNumero)
        tipo_numero = id_elem.find(".//lc:TipoNumero", self.ns)
        if tipo_numero is not None:
            tipo_elem = tipo_numero.find("lc:Tipo", self.ns)
            numero_elem = tipo_numero.find("lc:Numero", self.ns)
            ident.tipo = self._get_text(tipo_elem)
            ident.numero = self._get_text(numero_elem)

        # Organismos
        for org in id_elem.findall(".//lc:Organismo", self.ns):
            org_text = self._get_text(org)
            if org_text:
                ident.organismos.append(org_text)

        return ident

    def _parse_metadatos(self, root: ET.Element) -> NormaMetadatos:
        """Parsea el elemento Metadatos de la norma."""
        meta = NormaMetadatos()

        meta_elem = root.find("lc:Metadatos", self.ns)
        if meta_elem is None:
            return meta

        # Título
        titulo_elem = meta_elem.find("lc:TituloNorma", self.ns)
        meta.titulo = self._get_text(titulo_elem)

        # Materias
        for materia in meta_elem.findall(".//lc:Materia", self.ns):
            mat_text = self._get_text(materia)
            if mat_text:
                meta.materias.append(mat_text)

        # Nombres de uso común
        for nombre in meta_elem.findall(".//lc:NombreUsoComun", self.ns):
            nom_text = self._get_text(nombre)
            if nom_text:
                meta.nombres_uso_comun.append(nom_text)

        # Tratados
        for pais in meta_elem.findall(".//lc:PaisTratado", self.ns):
            pais_text = self._get_text(pais)
            if pais_text:
                meta.paises_tratado.append(pais_text)

        tipo_tratado = meta_elem.find("lc:TipoTratado", self.ns)
        meta.tipo_tratado = self._get_text(tipo_tratado)

        fecha_tratado = meta_elem.find("lc:FechaTratado", self.ns)
        meta.fecha_tratado = self._get_text(fecha_tratado)

        # Derogación
        fecha_derog = meta_elem.find("lc:FechaDerogacion", self.ns)
        meta.fecha_derogacion = self._get_text(fecha_derog)

        # Fuente
        fuente = meta_elem.find("lc:IdentificacionFuente", self.ns)
        meta.identificacion_fuente = self._get_text(fuente)

        num_fuente = meta_elem.find("lc:NumeroFuente", self.ns)
        meta.numero_fuente = self._get_text(num_fuente)

        return meta

    def _parse_encabezado(self, root: ET.Element) -> tuple[str, bool]:
        """Parsea el elemento Encabezado."""
        enc_elem = root.find("lc:Encabezado", self.ns)
        if enc_elem is None:
            return "", False

        texto_elem = enc_elem.find("lc:Texto", self.ns)
        texto = self._get_text(texto_elem)
        derogado = enc_elem.get("derogado", "") == "derogado"

        return texto, derogado

    def _parse_estructuras_funcionales(
        self, root: ET.Element, nivel: int = 0
    ) -> list[EstructuraFuncional]:
        """Parsea recursivamente las EstructurasFuncionales.

        Esta es la parte más importante del parser, ya que maneja
        la jerarquía anidada de Capítulos > Títulos > Párrafos > Artículos.
        """
        estructuras: list[EstructuraFuncional] = []

        # Buscar el contenedor de estructuras
        container = root.find("lc:EstructurasFuncionales", self.ns)

        if container is None:
            return estructuras

        # Iterar sobre cada EstructuraFuncional
        for ef_elem in container.findall("lc:EstructuraFuncional", self.ns):
            ef = self._parse_estructura_funcional(ef_elem, nivel)
            estructuras.append(ef)

        return estructuras

    def _parse_estructura_funcional(self, ef_elem: ET.Element, nivel: int) -> EstructuraFuncional:
        """Parsea una única EstructuraFuncional y sus hijos."""
        ef = EstructuraFuncional()
        ef.nivel = nivel

        # Atributos
        ef.id_parte = ef_elem.get("idParte", "")
        ef.tipo_parte = html.unescape(ef_elem.get("tipoParte", ""))
        ef.fecha_version = ef_elem.get("fechaVersion", "")
        ef.derogado = ef_elem.get("derogado", "") == "derogado"
        ef.transitorio = ef_elem.get("transitorio", "") == "transitorio"

        # Texto
        texto_elem = ef_elem.find("lc:Texto", self.ns)
        ef.texto = self._get_text(texto_elem)

        # Metadatos de la parte
        meta_elem = ef_elem.find("lc:Metadatos", self.ns)
        if meta_elem is not None:
            nombre_elem = meta_elem.find("lc:NombreParte", self.ns)
            if nombre_elem is not None and nombre_elem.get("presente", "") == "si":
                ef.nombre_parte = self._get_text(nombre_elem).strip()

            titulo_elem = meta_elem.find("lc:TituloParte", self.ns)
            if titulo_elem is not None and titulo_elem.get("presente", "") == "si":
                ef.titulo_parte = self._get_text(titulo_elem).strip()

            # Materias específicas de esta parte
            for materia in meta_elem.findall(".//lc:Materia", self.ns):
                mat_text = self._get_text(materia)
                if mat_text:
                    ef.materias.append(mat_text)

        # Parsear hijos recursivamente
        ef.hijos = self._parse_estructuras_funcionales(ef_elem, nivel + 1)

        return ef

    def _parse_promulgacion(self, root: ET.Element) -> tuple[str, bool]:
        """Parsea el elemento Promulgacion."""
        prom_elem = root.find("lc:Promulgacion", self.ns)
        if prom_elem is None:
            return "", False

        texto_elem = prom_elem.find("lc:Texto", self.ns)
        texto = self._get_text(texto_elem)
        derogado = prom_elem.get("derogado", "") == "derogado"

        return texto, derogado

    def _parse_anexos(self, root: ET.Element) -> list[dict[str, Any]]:
        """Parsea los Anexos de la norma."""
        anexos: list[dict[str, Any]] = []

        anexos_container = root.find("lc:Anexos", self.ns)
        if anexos_container is None:
            return anexos

        for anexo_elem in anexos_container.findall("lc:Anexo", self.ns):
            anexo: dict[str, Any] = {
                "id_parte": anexo_elem.get("idParte", ""),
                "fecha_version": anexo_elem.get("fechaVersion", ""),
                "derogado": anexo_elem.get("derogado", "") == "derogado",
                "transitorio": anexo_elem.get("transitorio", "") == "transitorio",
                "titulo": "",
                "materias": [],
                "texto": "",
            }

            # Metadatos del anexo
            meta_elem = anexo_elem.find("lc:Metadatos", self.ns)
            if meta_elem is not None:
                titulo_elem = meta_elem.find("lc:Titulo", self.ns)
                anexo["titulo"] = self._get_text(titulo_elem)

                for materia in meta_elem.findall(".//lc:Materia", self.ns):
                    mat_text = self._get_text(materia)
                    if mat_text:
                        anexo["materias"].append(mat_text)

            # Texto del anexo
            texto_elem = anexo_elem.find("lc:Texto", self.ns)
            anexo["texto"] = self._get_text(texto_elem)

            anexos.append(anexo)

        return anexos


class BCNLawScraperV2:
    """Scraper v2 para la API XML de la Biblioteca del Congreso Nacional.

    Esta versión usa el parser XSD oficial para extraer datos
    con la estructura jerárquica correcta.

    Example:
        >>> with BCNLawScraperV2() as scraper:
        ...     norma = scraper.scrape("https://www.leychile.cl/Navegar?idNorma=1058072")
        ...     print(norma.titulo_completo)
    """

    def __init__(self, config: Config | None = None) -> None:
        """Inicializa el scraper.

        Args:
            config: Configuración opcional.
        """
        self.config = config or get_config()
        self.session = self._create_session()
        self.parser = BCNXMLParser()
        logger.debug("BCNLawScraperV2 inicializado")

    def __enter__(self) -> "BCNLawScraperV2":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Cierra la sesión HTTP y libera recursos."""
        if self.session:
            self.session.close()

    def _create_session(self) -> requests.Session:
        """Crea una sesión HTTP con reintentos configurados."""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.config.scraper.max_retries,
            backoff_factor=self.config.scraper.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update(
            {
                "User-Agent": self.config.scraper.user_agent,
                "Accept": "application/xml, text/xml, */*",
                "Accept-Language": "es-CL,es;q=0.9",
            }
        )

        return session

    def _validate_url(self, url: str) -> None:
        """Valida que la URL pertenezca a un dominio permitido.

        Args:
            url: URL a validar.

        Raises:
            ValidationError: Si la URL no es de un dominio permitido.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValidationError(
                "La URL debe usar protocolo HTTP o HTTPS",
                field="url",
                value=url,
            )
        hostname = parsed.hostname or ""
        if hostname not in _ALLOWED_DOMAINS:
            raise ValidationError(
                f"Dominio no permitido: {hostname}. "
                f"Solo se permiten: {', '.join(sorted(_ALLOWED_DOMAINS))}",
                field="url",
                value=url,
            )

    def extract_id_norma(self, url: str) -> str | None:
        """Extrae el ID de la norma desde una URL de LeyChile.

        Soporta múltiples formatos de URL:
        - https://www.leychile.cl/Navegar?idNorma=242302
        - https://www.bcn.cl/leychile/navegar?idNorma=242302
        - https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma=242302
        """
        try:
            self._validate_url(url)
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return params.get("idNorma", [None])[0]
        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"Error extrayendo idNorma de {url}: {e}")
            return None

    def extract_id_version(self, url: str) -> str | None:
        """Extrae el ID de versión desde una URL."""
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return params.get("idVersion", [None])[0]
        except Exception:
            return None

    def get_xml_url(self, id_norma: str) -> str:
        """Construye la URL del XML para una norma."""
        base = self.config.scraper.base_url.rstrip("/")
        endpoint = self.config.scraper.xml_endpoint
        return f"{base}{endpoint}?opt=7&idNorma={id_norma}"

    def fetch_xml(self, url: str) -> ET.Element:
        """Obtiene y parsea el XML desde la API.

        Raises:
            NetworkError: Si hay problemas de conexión.
            ParsingError: Si el XML no es válido.
        """
        logger.debug(f"Obteniendo XML: {url}")

        try:
            response = self.session.get(url, timeout=self.config.scraper.timeout)
            response.raise_for_status()
            time.sleep(self.config.scraper.rate_limit_delay)
            return ET.fromstring(response.content)

        except requests.exceptions.Timeout as e:
            raise NetworkError(
                "Timeout al conectar con la BCN", url=url, details={"original_error": str(e)}
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(
                "No se pudo conectar con la BCN", url=url, details={"original_error": str(e)}
            ) from e
        except requests.exceptions.HTTPError as e:
            raise NetworkError(
                "Error HTTP al acceder a la BCN",
                url=url,
                status_code=e.response.status_code,
                details={"original_error": str(e)},
            ) from e
        except ET.ParseError as e:
            raise ParsingError(
                "El XML de la BCN no es válido", details={"url": url, "original_error": str(e)}
            ) from e

    def scrape(
        self, url: str, progress_callback: Callable[[float, str], None] | None = None
    ) -> Norma:
        """Extrae todos los datos de una norma desde su URL.

        Args:
            url: URL de LeyChile con el parámetro idNorma.
            progress_callback: Función para reportar progreso (0.0-1.0, mensaje).

        Returns:
            Objeto Norma con todos los datos estructurados.

        Raises:
            ValidationError: Si la URL no contiene idNorma válido.
            NetworkError: Si hay problemas de conexión.
            ParsingError: Si el XML no se puede procesar.
        """
        logger.info(f"Iniciando scraping: {url}")

        # Extraer IDs
        id_norma = self.extract_id_norma(url)
        id_version = self.extract_id_version(url)

        if not id_norma:
            raise ValidationError(
                "No se pudo extraer el ID de la norma de la URL", field="url", value=url
            )

        if progress_callback:
            progress_callback(0.1, "Conectando con LeyChile...")

        # Obtener XML
        xml_url = self.get_xml_url(id_norma)
        root = self.fetch_xml(xml_url)

        if progress_callback:
            progress_callback(0.3, "Parseando estructura XML...")

        # Parsear
        norma = self.parser.parse(root)
        norma.url_original = url
        norma.id_version = id_version or ""

        if progress_callback:
            progress_callback(1.0, "Completado")

        logger.info(f"Scraping completado: {norma.titulo_completo}")
        return norma

    def scrape_to_dict(
        self, url: str, progress_callback: Callable[[float, str], None] | None = None
    ) -> dict[str, Any]:
        """Versión que retorna diccionario para compatibilidad con v1.

        Este método convierte la Norma a un formato compatible con
        el generador de ePub existente.
        """
        norma = self.scrape(url, progress_callback)
        return self._norma_to_dict(norma)

    def _norma_to_dict(self, norma: Norma) -> dict[str, Any]:
        """Convierte una Norma a diccionario compatible con el generador."""
        # Metadatos en formato v1
        metadata = {
            "title": norma.metadatos.titulo or norma.titulo_completo,
            "type": norma.identificador.tipo,
            "number": norma.identificador.numero,
            "organism": norma.identificador.organismos[0] if norma.identificador.organismos else "",
            "organisms": norma.identificador.organismos,
            "subjects": norma.metadatos.materias,
            "common_names": norma.metadatos.nombres_uso_comun,
            "source": norma.metadatos.identificacion_fuente,
            "source_number": norma.metadatos.numero_fuente,
            "promulgation_date": norma.identificador.fecha_promulgacion,
            "publication_date": norma.identificador.fecha_publicacion,
            "version_date": norma.fecha_version,
            "derogated": norma.derogado,
            "is_treaty": norma.es_tratado,
            "promulgation_text": norma.promulgacion_texto,
        }

        # Contenido estructurado
        content = []

        # Encabezado
        if norma.encabezado_texto:
            content.append(
                {
                    "type": "encabezado",
                    "text": norma.encabezado_texto,
                    "derogado": norma.encabezado_derogado,
                }
            )

        # Estructuras funcionales (aplanadas pero con jerarquía)
        self._flatten_estructuras(norma.estructuras, content, parent_chain=[])

        # Promulgación
        if norma.promulgacion_texto:
            content.append(
                {
                    "type": "promulgacion",
                    "text": norma.promulgacion_texto,
                    "derogado": norma.promulgacion_derogado,
                }
            )

        # Anexos
        for anexo in norma.anexos:
            content.append(
                {
                    "type": "anexo",
                    "titulo": anexo["titulo"],
                    "text": anexo["texto"],
                    "materias": anexo["materias"],
                    "derogado": anexo["derogado"],
                }
            )

        return {
            "metadata": metadata,
            "content": content,
            "estructuras": norma.estructuras,  # Estructura jerárquica completa
            "url": norma.url_original,
            "id_norma": norma.norma_id,
            "id_version": norma.id_version,
        }

    def _flatten_estructuras(
        self,
        estructuras: list[EstructuraFuncional],
        content: list[dict[str, Any]],
        parent_chain: list[str],
    ) -> None:
        """Aplana la jerarquía de estructuras manteniendo contexto de padres."""
        for ef in estructuras:
            tipo = ef.tipo_parte.lower()

            # Determinar el título a mostrar
            if ef.titulo_parte:
                display_title = ef.titulo_parte
            elif ef.nombre_parte:
                display_title = f"{ef.tipo_parte} {ef.nombre_parte}"
            else:
                display_title = ef.tipo_parte

            item: dict[str, Any] = {
                "type": tipo if tipo in ["artículo", "articulo"] else ef.tipo_parte.lower(),
                "tipo_parte": ef.tipo_parte,
                "id_parte": ef.id_parte,
                "nivel": ef.nivel,
                "text": ef.texto,
                "nombre_parte": ef.nombre_parte,
                "titulo_parte": ef.titulo_parte,
                "display_title": display_title,
                "fecha_version": ef.fecha_version,
                "derogado": ef.derogado,
                "transitorio": ef.transitorio,
                "materias": ef.materias,
                "parent_chain": list(parent_chain),
                "tiene_hijos": len(ef.hijos) > 0,
            }

            # Clasificar tipo para el generador
            tipo_lower = ef.tipo_parte.lower()
            if "artículo" in tipo_lower or "articulo" in tipo_lower:
                item["type"] = "articulo"
                item["title"] = f"Artículo {ef.nombre_parte}" if ef.nombre_parte else "Artículo"
            elif "capítulo" in tipo_lower or "capitulo" in tipo_lower:
                item["type"] = "capitulo"
            elif "título" in tipo_lower or "titulo" in tipo_lower:
                item["type"] = "titulo"
            elif "párrafo" in tipo_lower or "parrafo" in tipo_lower:
                item["type"] = "parrafo"
            elif "libro" in tipo_lower:
                item["type"] = "libro"

            content.append(item)

            # Procesar hijos con la cadena de padres actualizada
            if ef.hijos:
                new_chain = parent_chain + [display_title]
                self._flatten_estructuras(ef.hijos, content, new_chain)


# Función de conveniencia
def scrape_law_v2(
    url: str, progress_callback: Callable[[float, str], None] | None = None
) -> dict[str, Any]:
    """Función de conveniencia para scrapear una ley con el parser v2.

    Args:
        url: URL de LeyChile.
        progress_callback: Callback de progreso opcional.

    Returns:
        Diccionario con datos de la ley.
    """
    scraper = BCNLawScraperV2()
    return scraper.scrape_to_dict(url, progress_callback)
