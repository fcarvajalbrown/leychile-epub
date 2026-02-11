"""
Scraper para la Biblioteca del Congreso Nacional de Chile.

Este módulo proporciona funcionalidades para extraer datos de leyes,
decretos y otras normas desde la API XML de la BCN.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import html
import logging
import re
import time
import warnings
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Config, get_config
from .exceptions import NetworkError, ParsingError, ValidationError

# Logger del módulo
logger = logging.getLogger("leychile_epub.scraper")

# Dominios permitidos para scraping
_ALLOWED_DOMAINS = {"www.leychile.cl", "leychile.cl", "www.bcn.cl", "bcn.cl"}


class BCNLawScraper:
    """Scraper para la API XML de la Biblioteca del Congreso Nacional.

    Esta clase permite extraer datos estructurados de leyes y normas
    desde la API oficial de LeyChile.

    Attributes:
        config: Configuración del scraper.
        session: Sesión HTTP con reintentos configurados.

    Example:
        >>> scraper = BCNLawScraper()
        >>> data = scraper.scrape_law("https://www.leychile.cl/Navegar?idNorma=242302")
        >>> print(data["metadata"]["title"])
        'CODIGO DEL TRABAJO'
    """

    # Namespace XML de la BCN
    NAMESPACE = {"lc": "http://www.leychile.cl/esquemas"}

    # Patrones de clasificación de texto
    PATTERNS = {
        "titulo": re.compile(r"^T[ÍI]TULO\s+[IVXLCDM]+", re.IGNORECASE),
        "capitulo": re.compile(r"^CAP[ÍI]TULO\s+[IVXLCDM]+", re.IGNORECASE),
        "libro": re.compile(r"^LIBRO\s+[IVXLCDM]+", re.IGNORECASE),
        "parrafo": re.compile(r"^P[ÁA]RRAFO\s+\d", re.IGNORECASE),
        "articulo": re.compile(r"^Art[íi]culo\s+\d", re.IGNORECASE),
        "articulo_full": re.compile(
            r"^(Art[íi]culo\s+\d+[°º]?(?:\s*(?:bis|ter|qu[aá]ter|quinquies|sexies|"
            r"septies|octies|nonies|decies))?)[.\s:\-]*(.*)$",
            re.IGNORECASE | re.DOTALL,
        ),
    }

    def __init__(self, config: Config | None = None) -> None:
        """Inicializa el scraper.

        .. deprecated:: 1.5.0
            Use :class:`BCNLawScraperV2` instead.

        Args:
            config: Configuración opcional. Si no se proporciona,
                   se usa la configuración global.
        """
        warnings.warn(
            "BCNLawScraper está deprecado. Use BCNLawScraperV2 en su lugar.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.config = config or get_config()
        self.session = self._create_session()
        logger.debug("BCNLawScraper inicializado")

    def __enter__(self) -> "BCNLawScraper":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Cierra la sesión HTTP y libera recursos."""
        if self.session:
            self.session.close()

    def _create_session(self) -> requests.Session:
        """Crea una sesión HTTP con reintentos configurados.

        Returns:
            Sesión HTTP configurada.
        """
        session = requests.Session()

        # Configurar reintentos
        retry_strategy = Retry(
            total=self.config.scraper.max_retries,
            backoff_factor=self.config.scraper.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers
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

        Args:
            url: URL completa de LeyChile.

        Returns:
            ID de la norma o None si no se encuentra.

        Example:
            >>> scraper.extract_id_norma("https://www.leychile.cl/Navegar?idNorma=242302")
            '242302'
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
        """Extrae el ID de versión desde una URL de LeyChile.

        Args:
            url: URL completa de LeyChile.

        Returns:
            ID de versión o None si no se encuentra.
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            return params.get("idVersion", [None])[0]
        except Exception:
            return None

    def get_api_url(self, id_norma: str) -> str:
        """Construye la URL de la API XML para una norma.

        Args:
            id_norma: ID de la norma.

        Returns:
            URL completa de la API.
        """
        base = self.config.scraper.base_url.rstrip("/")
        endpoint = self.config.scraper.xml_endpoint
        return f"{base}{endpoint}?opt=7&idNorma={id_norma}"

    def fetch_xml(self, url: str) -> ET.Element:
        """Obtiene y parsea el XML desde una URL.

        Args:
            url: URL del XML.

        Returns:
            Elemento raíz del XML parseado.

        Raises:
            NetworkError: Si hay problemas de conexión.
            ParsingError: Si el XML no es válido.
        """
        logger.debug(f"Fetching XML from: {url}")

        try:
            response = self.session.get(url, timeout=self.config.scraper.timeout)
            response.raise_for_status()

            # Rate limiting
            time.sleep(self.config.scraper.rate_limit_delay)

            return ET.fromstring(response.content)

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout al conectar con {url}")
            raise NetworkError(
                "Timeout al conectar con la BCN", url=url, details={"original_error": str(e)}
            ) from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Error de conexión: {e}")
            raise NetworkError(
                "No se pudo conectar con la BCN", url=url, details={"original_error": str(e)}
            ) from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP {e.response.status_code}: {url}")
            raise NetworkError(
                "Error HTTP al acceder a la BCN",
                url=url,
                status_code=e.response.status_code,
                details={"original_error": str(e)},
            ) from e
        except ET.ParseError as e:
            logger.error(f"Error parseando XML: {e}")
            raise ParsingError(
                "El XML de la BCN no es válido", details={"url": url, "original_error": str(e)}
            ) from e

    def _get_text(self, element: ET.Element, path: str) -> str:
        """Obtiene el texto de un elemento por su path.

        Args:
            element: Elemento XML raíz.
            path: XPath al elemento deseado.

        Returns:
            Texto del elemento o cadena vacía.
        """
        elem = element.find(path, self.NAMESPACE)
        if elem is not None and elem.text:
            return html.unescape(elem.text.strip())
        return ""

    def _get_all_text(self, element: ET.Element, path: str) -> list[str]:
        """Obtiene todos los textos de elementos que coinciden con el path.

        Args:
            element: Elemento XML raíz.
            path: XPath a los elementos.

        Returns:
            Lista de textos.
        """
        elements = element.findall(path, self.NAMESPACE)
        return [html.unescape(e.text.strip()) for e in elements if e.text]

    def _get_all_text_content(self, element: ET.Element) -> str:
        """Extrae todo el contenido de texto de un elemento recursivamente.

        Args:
            element: Elemento XML.

        Returns:
            Texto completo concatenado.
        """
        parts = []

        if element.text:
            parts.append(element.text)

        for child in element:
            child_text = self._get_all_text_content(child)
            if child_text:
                parts.append(child_text)
            if child.tail:
                parts.append(child.tail)

        text = "".join(parts)
        text = re.sub(r"\s+", " ", text)
        text = html.unescape(text)

        return text.strip()

    def _extract_element_text(self, element: ET.Element) -> str:
        """Extrae el texto de un elemento estructural.

        Args:
            element: Elemento XML.

        Returns:
            Texto del elemento.
        """
        texto_elem = element.find("lc:Texto", self.NAMESPACE)
        if texto_elem is not None:
            return self._get_all_text_content(texto_elem)
        return self._get_all_text_content(element)

    def _classify_text(self, text: str) -> str:
        """Clasifica un texto según su tipo estructural.

        Args:
            text: Texto a clasificar.

        Returns:
            Tipo de elemento: 'titulo', 'parrafo', 'articulo', o 'texto'.
        """
        text_clean = text.strip()

        if self.PATTERNS["titulo"].match(text_clean):
            return "titulo"
        if self.PATTERNS["capitulo"].match(text_clean):
            return "titulo"
        if self.PATTERNS["libro"].match(text_clean):
            return "titulo"
        if self.PATTERNS["parrafo"].match(text_clean):
            return "parrafo"
        if self.PATTERNS["articulo"].match(text_clean):
            return "articulo"

        return "texto"

    def _extract_metadata(self, root: ET.Element) -> dict[str, Any]:
        """Extrae los metadatos de una norma.

        Args:
            root: Elemento raíz del XML.

        Returns:
            Diccionario con los metadatos.
        """
        logger.debug("Extrayendo metadatos...")

        metadata: dict[str, Any] = {
            "title": "",
            "type": "",
            "number": "",
            "organism": "",
            "subjects": [],
            "common_name": "",
            "source": "",
            "promulgation_text": "",
            "derogation_dates": [],
        }

        metadata["title"] = self._get_text(root, ".//lc:TituloNorma")
        metadata["type"] = self._get_text(root, ".//lc:TipoNumero/lc:Tipo")
        metadata["number"] = self._get_text(root, ".//lc:TipoNumero/lc:Numero")
        metadata["organism"] = self._get_text(root, ".//lc:Organismo")
        metadata["subjects"] = self._get_all_text(root, ".//lc:Materia")
        metadata["common_name"] = self._get_text(root, ".//lc:NombreUsoComun")
        metadata["source"] = self._get_text(root, ".//lc:IdentificacionFuente")

        # Texto de promulgación
        prom = root.find(".//lc:Promulgacion", self.NAMESPACE)
        if prom is not None:
            metadata["promulgation_text"] = self._get_all_text_content(prom)

        # Fechas de derogación
        derog_dates = set()
        for elem in root.iter():
            tag = elem.tag.replace("{http://www.leychile.cl/esquemas}", "")
            if tag == "FechaDerogacion" and elem.text:
                derog_dates.add(elem.text.strip())
        metadata["derogation_dates"] = sorted(derog_dates)

        # Título por defecto si no existe
        if not metadata["title"]:
            metadata["title"] = f"{metadata['type']} {metadata['number']}"

        logger.debug(f"Metadatos extraídos: {metadata['title']}")
        return metadata

    def _extract_content(
        self, root: ET.Element, progress_callback: Callable[[float, str], None] | None = None
    ) -> list[dict[str, Any]]:
        """Extrae el contenido estructurado de la norma.

        Args:
            root: Elemento raíz del XML.
            progress_callback: Función para reportar progreso.

        Returns:
            Lista de elementos de contenido.
        """
        logger.debug("Extrayendo contenido...")
        content: list[dict[str, Any]] = []

        # Encabezado
        encabezado = root.find(".//lc:Encabezado", self.NAMESPACE)
        if encabezado is not None:
            enc_text = self._extract_element_text(encabezado)
            if enc_text:
                content.append(
                    {
                        "type": "encabezado",
                        "level": 0,
                        "text": enc_text,
                    }
                )

        # Estructuras funcionales
        estructuras = root.findall(".//lc:EstructuraFuncional", self.NAMESPACE)
        total = len(estructuras)

        current_titulo: str | None = None
        current_parrafo: str | None = None

        for i, ef in enumerate(estructuras):
            texto = self._extract_element_text(ef)
            if not texto:
                continue

            texto = texto.strip()
            element_type = self._classify_text(texto)

            if element_type == "titulo":
                current_titulo = texto
                current_parrafo = None
                content.append(
                    {
                        "type": "titulo",
                        "level": 1,
                        "text": texto,
                        "parent": None,
                    }
                )

            elif element_type == "parrafo":
                current_parrafo = texto
                content.append(
                    {
                        "type": "parrafo",
                        "level": 2,
                        "text": texto,
                        "parent": current_titulo,
                    }
                )

            elif element_type == "articulo":
                match = self.PATTERNS["articulo_full"].match(texto)

                if match:
                    article_title = match.group(1).strip()
                    article_text = match.group(2).strip()
                else:
                    article_title = texto[:50]
                    article_text = texto

                content.append(
                    {
                        "type": "articulo",
                        "level": 3,
                        "title": article_title,
                        "text": article_text,
                        "parent_titulo": current_titulo,
                        "parent_parrafo": current_parrafo,
                    }
                )

            else:
                # Texto continúa al artículo anterior o es independiente
                if content and content[-1]["type"] == "articulo":
                    content[-1]["text"] += "\n\n" + texto
                else:
                    content.append(
                        {
                            "type": "texto",
                            "level": 4,
                            "text": texto,
                        }
                    )

            # Reportar progreso
            if progress_callback and i % 50 == 0:
                progress = 0.5 + (i / total) * 0.35
                progress_callback(progress, f"Procesando elemento {i + 1} de {total}...")

        logger.info(f"Extraídos {len(content)} elementos de contenido")
        return content

    def scrape_law(
        self, url: str, progress_callback: Callable[[float, str], None] | None = None
    ) -> dict[str, Any]:
        """Extrae todos los datos de una ley desde su URL.

        Este es el método principal para obtener datos de una norma.

        Args:
            url: URL completa de LeyChile (ej: https://www.leychile.cl/Navegar?idNorma=242302)
            progress_callback: Función opcional para reportar progreso.
                              Recibe (porcentaje: float, mensaje: str).

        Returns:
            Diccionario con todos los datos de la ley:
                - metadata: Metadatos de la norma
                - content: Contenido estructurado
                - url: URL original
                - id_norma: ID de la norma
                - id_version: ID de versión (si existe)

        Raises:
            ValidationError: Si la URL no es válida.
            NetworkError: Si hay problemas de conexión.
            ParsingError: Si el XML no se puede parsear.

        Example:
            >>> scraper = BCNLawScraper()
            >>> data = scraper.scrape_law("https://www.leychile.cl/Navegar?idNorma=242302")
            >>> print(data["metadata"]["title"])
        """
        logger.info(f"Iniciando scraping de: {url}")

        # Validar y extraer ID
        id_norma = self.extract_id_norma(url)
        id_version = self.extract_id_version(url)

        if not id_norma:
            raise ValidationError(
                "No se pudo extraer el ID de la norma de la URL", field="url", value=url
            )

        if progress_callback:
            progress_callback(0.1, "Conectando con la API de LeyChile...")

        # Obtener XML
        api_url = self.get_api_url(id_norma)
        root = self.fetch_xml(api_url)

        if progress_callback:
            progress_callback(0.3, "Extrayendo metadatos...")

        # Extraer metadatos
        metadata = self._extract_metadata(root)

        if progress_callback:
            progress_callback(0.5, "Extrayendo contenido de la ley...")

        # Extraer contenido
        content = self._extract_content(root, progress_callback)

        if progress_callback:
            progress_callback(0.9, "Procesamiento completado")

        result = {
            "metadata": metadata,
            "content": content,
            "url": url,
            "id_norma": id_norma,
            "id_version": id_version,
        }

        logger.info(f"Scraping completado: {metadata['title']}")
        return result

    # Alias para compatibilidad
    scrape_full_law = scrape_law


def scrape_bcn_law(
    url: str, progress_callback: Callable[[float, str], None] | None = None
) -> dict[str, Any]:
    """Función de conveniencia para scrapear una ley.

    Args:
        url: URL de LeyChile.
        progress_callback: Callback de progreso opcional.

    Returns:
        Datos de la ley.
    """
    scraper = BCNLawScraper()
    return scraper.scrape_law(url, progress_callback)
