"""
Generador de ePub para legislación chilena.

Este módulo proporciona funcionalidades para crear archivos ePub
profesionales a partir de datos de leyes extraídos de la BCN.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import logging
import re
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from ebooklib import epub

from .config import Config, get_config
from .exceptions import GeneratorError, ValidationError
from .styles import get_premium_css

# Logger del módulo
logger = logging.getLogger("leychile_epub.generator")


class LawEpubGenerator:
    """Generador de ePub premium para documentos legales chilenos.

    Esta clase crea archivos ePub profesionales con:
    - Portada personalizada
    - Tabla de contenidos interactiva
    - Estilos CSS profesionales
    - Índice de artículos
    - Índice de palabras clave
    - Referencias cruzadas entre artículos
    - Metadatos completos

    Attributes:
        config: Configuración del generador.

    Example:
        >>> generator = LawEpubGenerator()
        >>> epub_path = generator.generate(law_data, output_dir="./output")
    """

    # Palabras clave legales para el índice
    LEGAL_KEYWORDS = [
        "plazo",
        "sancion",
        "multa",
        "pena",
        "prohibicion",
        "obligacion",
        "derecho",
        "deber",
        "facultad",
        "competencia",
        "jurisdiccion",
        "recurso",
        "apelacion",
        "nulidad",
        "prescripcion",
        "caducidad",
        "contrato",
        "convenio",
        "acuerdo",
        "resolucion",
        "decreto",
        "votacion",
        "eleccion",
        "escrutinio",
        "sufragio",
        "candidatura",
        "mesa",
        "vocal",
        "presidente",
        "secretario",
        "ministro",
        "tribunal",
        "juez",
        "fiscal",
        "abogado",
        "notario",
        "registro",
        "inscripcion",
        "certificado",
        "documento",
        "patrimonio",
        "propiedad",
        "dominio",
        "posesion",
        "usufructo",
        "herencia",
        "testamento",
        "sucesion",
        "donacion",
        "delito",
        "falta",
        "infraccion",
        "crimen",
        "cuasidelito",
    ]

    # Patrones para formatear títulos
    TITLE_PATTERNS = [
        (r"^(TITULO\s+[IVXLCDM]+)\s+(.+)$", r"\1<br/>\2"),
        (r"^(Titulo\s+[IVXLCDM]+)\s+(.+)$", r"\1<br/>\2"),
        (r"^(TÍTULO\s+[IVXLCDM]+)\s+(.+)$", r"\1<br/>\2"),
        (r"^(Título\s+[IVXLCDM]+)\s+(.+)$", r"\1<br/>\2"),
        (r"^(Párrafo\s+\d+[°º]?)\s+(.+)$", r"\1 – \2"),
        (r"^(PARRAFO\s+\d+[°º]?)\s+(.+)$", r"\1 – \2"),
        (r"^(Capítulo\s+[IVXLCDM]+)\s+(.+)$", r"\1<br/>\2"),
        (r"^(CAPITULO\s+[IVXLCDM]+)\s+(.+)$", r"\1<br/>\2"),
    ]

    def __init__(self, config: Config | None = None) -> None:
        """Inicializa el generador.

        Args:
            config: Configuración opcional. Si no se proporciona,
                   se usa la configuración global.
        """
        self.config = config or get_config()
        self._reset_state()
        logger.debug("LawEpubGenerator inicializado")

    def _reset_state(self) -> None:
        """Reinicia el estado interno del generador."""
        self.book: epub.EpubBook | None = None
        self.chapters: list[epub.EpubHtml] = []
        self.toc: list[Any] = []
        self.toc_sections: list[tuple[epub.EpubHtml, list[dict]]] = []
        self.article_ids: dict[str, str] = {}
        self.article_list: list[dict[str, Any]] = []
        self.keyword_index: dict[str, list[dict[str, str]]] = {}

    def generate(
        self,
        law_data: dict[str, Any],
        output_dir: str | None = None,
        filename: str | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> str:
        """Genera un archivo ePub a partir de los datos de una ley.

        Args:
            law_data: Datos de la ley (resultado de BCNLawScraper.scrape_law).
            output_dir: Directorio de salida. Por defecto usa la configuración.
            filename: Nombre del archivo. Si no se especifica, se genera automáticamente.
            progress_callback: Función para reportar progreso.

        Returns:
            Ruta al archivo ePub generado.

        Raises:
            ValidationError: Si los datos de entrada no son válidos.
            GeneratorError: Si hay problemas durante la generación.

        Example:
            >>> generator = LawEpubGenerator()
            >>> path = generator.generate(law_data, output_dir="./output")
        """
        logger.info("Iniciando generación de ePub...")

        # Validar datos de entrada
        self._validate_law_data(law_data)

        # Reiniciar estado
        self._reset_state()

        try:
            # Crear libro
            self.book = epub.EpubBook()

            metadata = law_data.get("metadata", {})
            content = law_data.get("content", [])

            if progress_callback:
                progress_callback(0.1, "Construyendo índices...")

            # Construir índices
            self._build_article_index(content)
            self._build_keyword_index(content, metadata)

            if progress_callback:
                progress_callback(0.2, "Configurando metadatos...")

            # Metadatos
            self._set_metadata(metadata, law_data)

            if progress_callback:
                progress_callback(0.3, "Aplicando estilos...")

            # CSS
            self._add_css()

            if progress_callback:
                progress_callback(0.4, "Creando portada...")

            # Portada
            self._create_cover(metadata, law_data)

            # Información legal
            self._create_legal_info_page(metadata, law_data)

            if progress_callback:
                progress_callback(0.5, "Generando capítulos...")

            # Capítulos de contenido
            self._create_chapters(content, metadata)

            if progress_callback:
                progress_callback(0.7, "Creando índices...")

            # Índices
            self._create_article_index_page()
            self._create_keyword_index_page()

            # Apéndice
            self._create_promulgation_appendix(metadata)

            if progress_callback:
                progress_callback(0.85, "Finalizando estructura...")

            # TOC y spine
            self._build_toc()
            self._set_spine()

            if progress_callback:
                progress_callback(0.9, "Escribiendo archivo...")

            # Generar ruta de salida
            output_path = self._get_output_path(metadata, output_dir, filename)

            # Escribir archivo
            epub.write_epub(str(output_path), self.book, {})

            if progress_callback:
                progress_callback(1.0, "¡Completado!")

            logger.info(f"ePub generado: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error generando ePub: {e}")
            raise GeneratorError(f"Error al generar ePub: {e}") from e

    # Alias para compatibilidad
    create_epub = generate

    def _validate_law_data(self, law_data: dict[str, Any]) -> None:
        """Valida los datos de entrada.

        Args:
            law_data: Datos a validar.

        Raises:
            ValidationError: Si los datos no son válidos.
        """
        if not isinstance(law_data, dict):
            raise ValidationError("law_data debe ser un diccionario")

        if "metadata" not in law_data:
            raise ValidationError("law_data debe contener 'metadata'")

        if "content" not in law_data:
            raise ValidationError("law_data debe contener 'content'")

    def _get_output_path(
        self,
        metadata: dict[str, Any],
        output_dir: str | None,
        filename: str | None,
    ) -> Path:
        """Genera la ruta de salida del archivo.

        Args:
            metadata: Metadatos de la ley.
            output_dir: Directorio de salida.
            filename: Nombre del archivo.

        Returns:
            Ruta completa al archivo.
        """
        # Directorio
        if output_dir:
            dir_path = Path(output_dir)
        else:
            dir_path = Path(self.config.epub.output_dir)

        dir_path.mkdir(parents=True, exist_ok=True)

        # Nombre del archivo
        if filename:
            name = filename if filename.endswith(".epub") else f"{filename}.epub"
        else:
            law_type = metadata.get("type", "Ley")
            law_number = metadata.get("number", "Unknown")
            # Sanitizar nombre
            safe_type = re.sub(r"[^\w\s-]", "", law_type).strip().replace(" ", "_")
            safe_number = re.sub(r"[^\w\s-]", "", law_number).strip().replace(" ", "_")
            name = f"{safe_type}_{safe_number}.epub"

        return dir_path / name

    def _escape_html(self, text: str) -> str:
        """Escapa caracteres HTML.

        Args:
            text: Texto a escapar.

        Returns:
            Texto con caracteres escapados.
        """
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _escape_html_preserve_links(self, text: str) -> str:
        """Escapa HTML pero preserva los links.

        Args:
            text: Texto con posibles links.

        Returns:
            Texto escapado con links preservados.
        """
        if not text:
            return ""

        link_pattern = r'(<a\s+href="[^"]*"\s+class="cross-ref">)(.*?)(</a>)'
        parts = []
        last_end = 0

        for match in re.finditer(link_pattern, text):
            before = text[last_end : match.start()]
            parts.append(self._escape_html(before))
            parts.append(match.group(1))
            parts.append(self._escape_html(match.group(2)))
            parts.append(match.group(3))
            last_end = match.end()

        parts.append(self._escape_html(text[last_end:]))
        return "".join(parts)

    def _format_section_title(self, text: str) -> str:
        """Formatea títulos de sección con separadores apropiados.

        Args:
            text: Título a formatear.

        Returns:
            Título formateado con HTML.
        """
        if not text:
            return text

        for pattern, replacement in self.TITLE_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _extract_article_id(self, article_title: str) -> str | None:
        """Extrae el ID de un artículo desde su título.

        Args:
            article_title: Título del artículo.

        Returns:
            ID del artículo o None.
        """
        if not article_title:
            return None

        match = re.search(
            r"Art[íi]culo\s+(\d+(?:\s*(?:bis|ter|qu[aá]ter|quinquies|"
            r"sexies|septies|octies|nonies|decies))?)",
            article_title,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).lower().replace(" ", "")
        return None

    def _add_cross_references(self, text: str) -> str:
        """Agrega links de referencias cruzadas entre artículos.

        Args:
            text: Texto con referencias a artículos.

        Returns:
            Texto con links HTML.
        """

        def replace_ref(match: re.Match) -> str:
            full_match = match.group(0)
            art_num = match.group(1).lower().replace(" ", "")

            if art_num in self.article_ids:
                return f'<a href="{self.article_ids[art_num]}" class="cross-ref">{full_match}</a>'
            return full_match

        pattern = (
            r"art[íi]culo\s+(\d+(?:\s*(?:bis|ter|qu[aá]ter|quinquies|"
            r"sexies|septies|octies|nonies|decies))?)"
        )
        return re.sub(pattern, replace_ref, text, flags=re.IGNORECASE)

    def _build_article_index(self, content: list[dict[str, Any]]) -> None:
        """Construye el índice de artículos.

        Args:
            content: Contenido de la ley.
        """
        logger.debug("Construyendo índice de artículos...")

        current_chapter = 0
        current_titulo: str | None = None
        current_parrafo: str | None = None

        for item in content:
            item_type = item.get("type", "")

            if item_type == "titulo":
                current_chapter += 1
                current_titulo = item.get("text", "")
                current_parrafo = None
            elif item_type == "parrafo":
                current_parrafo = item.get("text", "")
            elif item_type == "articulo":
                article_title = item.get("title", "")
                art_id = self._extract_article_id(article_title)

                if art_id:
                    if current_chapter > 0:
                        file_ref = f"titulo_{current_chapter}.xhtml#art_{art_id}"
                    else:
                        file_ref = f"intro.xhtml#art_{art_id}"

                    self.article_ids[art_id] = file_ref
                    self.article_list.append(
                        {
                            "number": art_id,
                            "title": article_title,
                            "file_ref": file_ref,
                            "parent_titulo": current_titulo,
                            "parent_parrafo": current_parrafo,
                        }
                    )

        logger.debug(f"Índice construido: {len(self.article_list)} artículos")

    def _build_keyword_index(self, content: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        """Construye el índice de palabras clave.

        Args:
            content: Contenido de la ley.
            metadata: Metadatos de la ley.
        """
        logger.debug("Construyendo índice de palabras clave...")

        current_chapter = 0

        for item in content:
            if item.get("type") == "titulo":
                current_chapter += 1
            elif item.get("type") == "articulo":
                article_title = item.get("title", "")
                article_text = item.get("text", "").lower()

                art_id = self._extract_article_id(article_title)
                if not art_id:
                    continue

                if current_chapter > 0:
                    file_ref = f"titulo_{current_chapter}.xhtml#art_{art_id}"
                else:
                    file_ref = f"intro.xhtml#art_{art_id}"

                for keyword in self.LEGAL_KEYWORDS:
                    if keyword in article_text:
                        if keyword not in self.keyword_index:
                            self.keyword_index[keyword] = []

                        if file_ref not in [x["ref"] for x in self.keyword_index[keyword]]:
                            self.keyword_index[keyword].append(
                                {
                                    "ref": file_ref,
                                    "art": art_id,
                                }
                            )

        # Agregar materias como palabras clave
        subjects = metadata.get("subjects", [])
        for subject in subjects:
            for word in subject.lower().split():
                if len(word) > 4 and word not in self.keyword_index:
                    self.keyword_index[word] = []

    def _set_metadata(self, metadata: dict[str, Any], law_data: dict[str, Any]) -> None:
        """Configura los metadatos del ePub.

        Args:
            metadata: Metadatos de la ley.
            law_data: Datos completos de la ley.
        """
        title = metadata.get("title", "Ley Chile")
        law_type = metadata.get("type", "Ley")
        law_number = metadata.get("number", "")

        full_title = f"{law_type} N° {law_number} - {title}" if law_number else title

        self.book.set_identifier(f"bcn-chile-{uuid.uuid4().hex[:8]}")
        self.book.set_title(full_title)
        self.book.set_language(self.config.epub.language)

        self.book.add_author("Biblioteca del Congreso Nacional de Chile")

        if organism := metadata.get("organism"):
            self.book.add_metadata("DC", "contributor", organism)

        self.book.add_metadata("DC", "publisher", self.config.epub.publisher)
        self.book.add_metadata("DC", "source", law_data.get("url", ""))
        self.book.add_metadata("DC", "date", datetime.now().strftime("%Y-%m-%d"))
        self.book.add_metadata("DC", "rights", "Documento publico - Republica de Chile")
        self.book.add_metadata("DC", "type", "Legislacion")
        self.book.add_metadata("DC", "format", "application/epub+zip")

        description = f"{law_type} {law_number}: {title}. Texto oficial de la Republica de Chile."
        self.book.add_metadata("DC", "description", description)

        subjects = metadata.get("subjects", [])
        unique_subjects = list(dict.fromkeys(subjects))[:5]
        for subject in unique_subjects:
            self.book.add_metadata("DC", "subject", subject)

        self.book.add_metadata("DC", "subject", "Legislacion chilena")
        self.book.add_metadata("DC", "subject", "Derecho")

    def _add_css(self) -> None:
        """Agrega los estilos CSS al ePub."""
        css_content = get_premium_css()

        nav_css = epub.EpubItem(
            uid="style_premium",
            file_name="style/premium.css",
            media_type="text/css",
            content=css_content.encode("utf-8"),
        )
        self.book.add_item(nav_css)

    def _create_chapter(
        self,
        title: str,
        filename: str,
        content: str,
        add_to_toc: bool = True,
    ) -> epub.EpubHtml:
        """Crea un capítulo del ePub.

        Args:
            title: Título del capítulo.
            filename: Nombre del archivo.
            content: Contenido HTML.
            add_to_toc: Si se agrega a la tabla de contenidos.

        Returns:
            Capítulo creado.
        """
        chapter = epub.EpubHtml(title=title, file_name=filename, lang="es")
        chapter.add_link(href="style/premium.css", rel="stylesheet", type="text/css")
        chapter.set_content(content)

        self.book.add_item(chapter)
        self.chapters.append(chapter)

        if add_to_toc:
            self.toc.append(chapter)

        return chapter

    def _create_cover(self, metadata: dict[str, Any], law_data: dict[str, Any]) -> None:
        """Crea la portada del ePub.

        Args:
            metadata: Metadatos de la ley.
            law_data: Datos completos de la ley.
        """
        title = metadata.get("title", "Ley Chile")
        law_type = metadata.get("type", "Ley")
        law_number = metadata.get("number", "")
        organism = metadata.get("organism", "")
        subjects = metadata.get("subjects", [])
        source = metadata.get("source", "")
        id_version = law_data.get("id_version", "")

        unique_subjects = list(dict.fromkeys(subjects))[:5]
        subjects_html = ""
        if unique_subjects:
            subjects_str = " | ".join([self._escape_html(s) for s in unique_subjects])
            subjects_html = f'<p class="cover-subjects">{subjects_str}</p>'

        organism_html = ""
        if organism:
            organism_html = f'<p class="cover-organism">{self._escape_html(organism)}</p>'

        version_html = ""
        if id_version:
            version_html = f'<p class="cover-source">Version: {self._escape_html(id_version)}</p>'

        source_html = ""
        if source:
            source_html = f'<p class="cover-source">Publicado en: {self._escape_html(source)}</p>'

        creator = self.config.epub.creator
        date_str = datetime.now().strftime("%d de %B de %Y")

        content = f"""
<div class="cover">
    <div class="cover-header">
        <p class="cover-escudo">&#9733;</p>
        <p class="cover-republica">Republica de Chile</p>
    </div>
    
    <p class="cover-law-type">{self._escape_html(law_type)}</p>
    <p class="cover-law-number">N° {self._escape_html(law_number)}</p>
    
    <div class="cover-divider"></div>
    
    <h1 class="no-break">{self._escape_html(title)}</h1>
    
    {organism_html}
    {subjects_html}
    
    <div class="cover-metadata">
        {version_html}
        {source_html}
        <p class="cover-source">Fuente: Biblioteca del Congreso Nacional de Chile</p>
    </div>
    
    <div class="cover-footer">
        <p>Documento generado el {date_str}</p>
        <p>Generado en base a la ultima version de la ley por {self._escape_html(creator)}</p>
    </div>
</div>
"""
        self._create_chapter("Portada", "cover.xhtml", content, add_to_toc=False)

    def _create_legal_info_page(self, metadata: dict[str, Any], law_data: dict[str, Any]) -> None:
        """Crea la página de información legal.

        Args:
            metadata: Metadatos de la ley.
            law_data: Datos completos de la ley.
        """
        law_type = metadata.get("type", "Ley")
        law_number = metadata.get("number", "")
        title = metadata.get("title", "")
        organism = metadata.get("organism", "")
        source = metadata.get("source", "")
        subjects = metadata.get("subjects", [])
        derogation_dates = metadata.get("derogation_dates", [])

        unique_subjects = list(dict.fromkeys(subjects))[:8]
        subjects_str = (
            ", ".join([self._escape_html(s) for s in unique_subjects])
            if unique_subjects
            else "No especificadas"
        )

        timeline_items = ""
        if derogation_dates:
            dates_str = " | ".join([self._escape_html(d) for d in derogation_dates[:5]])
            timeline_items = (
                f'<tr><td>Modificaciones</td><td class="compact-text">{dates_str}</td></tr>'
            )

        creator = self.config.epub.creator

        content = f"""
<div class="legal-info-compact">
    <h1 class="no-break info-title">Ficha del Documento</h1>
    
    <table class="info-table-compact">
        <tr><td class="label">Tipo</td><td>{self._escape_html(law_type)} N° {self._escape_html(law_number)}</td></tr>
        <tr><td class="label">Titulo</td><td class="compact-text">{self._escape_html(title)}</td></tr>
        <tr><td class="label">Organismo</td><td>{self._escape_html(organism) if organism else "—"}</td></tr>
        <tr><td class="label">Publicacion</td><td>{self._escape_html(source) if source else "—"}</td></tr>
        <tr><td class="label">Materias</td><td class="compact-text">{subjects_str}</td></tr>
        {timeline_items}
    </table>
    
    <p class="legal-disclaimer">Generado en base a la ultima version de la ley por {self._escape_html(creator)}.<br/>Para efectos legales, consulte la fuente oficial en la BCN.</p>
</div>
"""
        self._create_chapter("Informacion del Documento", "legal_info.xhtml", content)

    def _create_chapters(self, content: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
        """Crea los capítulos de contenido.

        Args:
            content: Contenido de la ley.
            metadata: Metadatos de la ley.
        """
        if not content:
            self._create_empty_chapter(metadata)
            return

        current_titulo: dict | None = None
        current_titulo_content: list[dict] = []
        chapter_count = 0
        pre_titulo_content: list[dict] = []

        for item in content:
            item_type = item.get("type", "")

            if item_type == "encabezado":
                chapter = self._create_encabezado_chapter(item)
                self.toc.append(chapter)

            elif item_type == "titulo":
                # Guardar capítulo anterior si existe
                if current_titulo and current_titulo_content:
                    chapter = self._create_titulo_chapter(
                        current_titulo, current_titulo_content, chapter_count
                    )
                    self.toc_sections.append((chapter, current_titulo_content))
                    chapter_count += 1
                elif not current_titulo and pre_titulo_content:
                    chapter = self._create_intro_chapter(pre_titulo_content, metadata)
                    self.toc.append(chapter)
                    pre_titulo_content = []

                current_titulo = item
                current_titulo_content = []

            else:
                if current_titulo is None:
                    pre_titulo_content.append(item)
                else:
                    current_titulo_content.append(item)

        # Último capítulo
        if current_titulo and current_titulo_content:
            chapter = self._create_titulo_chapter(
                current_titulo, current_titulo_content, chapter_count
            )
            self.toc_sections.append((chapter, current_titulo_content))

        if pre_titulo_content and not current_titulo:
            chapter = self._create_general_chapter(pre_titulo_content, metadata)
            self.toc.append(chapter)

    def _create_encabezado_chapter(self, item: dict[str, Any]) -> epub.EpubHtml:
        """Crea el capítulo de encabezado.

        Args:
            item: Datos del encabezado.

        Returns:
            Capítulo creado.
        """
        text = item.get("text", "Encabezado")
        content = f"""
<div class="encabezado">
    <p>{self._escape_html(text)}</p>
</div>
"""
        return self._create_chapter("Encabezado", "encabezado.xhtml", content, add_to_toc=False)

    def _create_intro_chapter(
        self, content: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> epub.EpubHtml:
        """Crea el capítulo introductorio.

        Args:
            content: Contenido del capítulo.
            metadata: Metadatos de la ley.

        Returns:
            Capítulo creado.
        """
        html_parts = [
            '<a href="#main-content" class="skip-link">Saltar al contenido principal</a>\n',
            '<main id="main-content" role="main">\n',
            '<h1 class="no-break">Disposiciones Preliminares</h1>\n',
        ]

        for item in content:
            html_parts.append(self._render_content_item(item))

        html_parts.append("</main>\n")

        chapter = epub.EpubHtml(
            title="Disposiciones Preliminares",
            file_name="intro.xhtml",
            lang="es",
        )
        chapter.add_link(href="style/premium.css", rel="stylesheet", type="text/css")
        chapter.set_content("".join(html_parts))

        self.book.add_item(chapter)
        self.chapters.append(chapter)

        return chapter

    def _create_titulo_chapter(
        self,
        titulo: dict[str, Any],
        content: list[dict[str, Any]],
        index: int,
    ) -> epub.EpubHtml:
        """Crea un capítulo de título.

        Args:
            titulo: Datos del título.
            content: Contenido del capítulo.
            index: Índice del capítulo.

        Returns:
            Capítulo creado.
        """
        titulo_text = titulo.get("text", f"Titulo {index + 1}")
        formatted_title = self._format_section_title(titulo_text)
        short_title = titulo_text[:50] + "..." if len(titulo_text) > 50 else titulo_text

        html_parts = [
            '<a href="#main-content" class="skip-link">Saltar al contenido principal</a>\n',
            '<main id="main-content" role="main">\n',
            f'<article role="article" aria-labelledby="titulo-{index + 1}">\n',
            f'<h1 id="titulo-{index + 1}">{formatted_title}</h1>\n',
        ]

        for item in content:
            html_parts.append(self._render_content_item(item))

        if len(html_parts) == 4:
            html_parts.append('<p class="no-indent">Sin contenido adicional.</p>\n')

        html_parts.append("</article>\n")
        html_parts.append("</main>\n")

        chapter = epub.EpubHtml(
            title=short_title,
            file_name=f"titulo_{index + 1}.xhtml",
            lang="es",
        )
        chapter.add_link(href="style/premium.css", rel="stylesheet", type="text/css")
        chapter.set_content("".join(html_parts))

        self.book.add_item(chapter)
        self.chapters.append(chapter)

        return chapter

    def _create_general_chapter(
        self,
        content: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> epub.EpubHtml:
        """Crea un capítulo general.

        Args:
            content: Contenido del capítulo.
            metadata: Metadatos de la ley.

        Returns:
            Capítulo creado.
        """
        title = metadata.get("title", "Contenido")

        html_parts = [
            '<a href="#main-content" class="skip-link">Saltar al contenido principal</a>\n',
            '<main id="main-content" role="main">\n',
            f"<h1>{self._escape_html(title)}</h1>\n",
        ]

        for item in content:
            html_parts.append(self._render_content_item(item))

        html_parts.append("</main>\n")

        chapter = epub.EpubHtml(
            title=title[:50],
            file_name="contenido.xhtml",
            lang="es",
        )
        chapter.add_link(href="style/premium.css", rel="stylesheet", type="text/css")
        chapter.set_content("".join(html_parts))

        self.book.add_item(chapter)
        self.chapters.append(chapter)

        return chapter

    def _create_empty_chapter(self, metadata: dict[str, Any]) -> None:
        """Crea un capítulo vacío cuando no hay contenido.

        Args:
            metadata: Metadatos de la ley.
        """
        title = metadata.get("title", "Documento")

        content = f"""
<h1 class="no-break">{self._escape_html(title)}</h1>
<p class="no-indent">No se pudo extraer el contenido de este documento.</p>
<p class="no-indent">Por favor, verifique la URL proporcionada e intente nuevamente.</p>
"""
        self._create_chapter(title, "contenido.xhtml", content)

    def _render_content_item(self, item: dict[str, Any]) -> str:
        """Renderiza un elemento de contenido a HTML.

        Args:
            item: Elemento a renderizar.

        Returns:
            HTML del elemento.
        """
        item_type = item.get("type", "")

        if item_type == "parrafo":
            parrafo_text = item.get("text", "")
            formatted_parrafo = self._format_section_title(parrafo_text)
            return f"<h2>{formatted_parrafo}</h2>\n"

        elif item_type == "articulo":
            return self._render_article(item)

        elif item_type == "texto":
            text = item.get("text", "")
            if text:
                return f"<p>{self._escape_html(text)}</p>\n"

        return ""

    def _render_article(self, item: dict[str, Any]) -> str:
        """Renderiza un artículo a HTML.

        Args:
            item: Datos del artículo.

        Returns:
            HTML del artículo.
        """
        article_title = item.get("title", "")
        article_text = item.get("text", "")

        art_id = self._extract_article_id(article_title)
        is_derogado = "derogad" in article_text.lower() if article_text else False

        html = ""

        if article_title:
            if art_id:
                if is_derogado:
                    html += f'<h3 id="art_{art_id}" class="articulo-titulo derogado">'
                    html += f"{self._escape_html(article_title)}"
                    html += '<span class="derogado-notice">DEROGADO</span></h3>\n'
                else:
                    html += f'<h3 id="art_{art_id}" class="articulo-titulo">'
                    html += f"{self._escape_html(article_title)}</h3>\n"
            else:
                html += f'<h3 class="articulo-titulo">{self._escape_html(article_title)}</h3>\n'

        if article_text and not is_derogado:
            formatted_text = self._format_article_content(article_text)
            html += f'<div class="articulo-contenido">{formatted_text}</div>\n'

        return html

    def _format_article_content(self, text: str) -> str:
        """Formatea el contenido de un artículo.

        Args:
            text: Texto del artículo.

        Returns:
            HTML formateado.
        """
        if not text:
            return "<p></p>"

        text_with_refs = self._add_cross_references(text)
        paragraphs = text_with_refs.split("\n\n")
        formatted_parts = []
        in_inciso_list = False
        in_letra_list = False

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            is_inciso = re.match(r"^(\d+)[°º.)\-]\s*(.*)$", para)
            is_letra = re.match(r"^([a-z])[.)]\s+(.*)$", para)

            if is_inciso:
                if in_letra_list:
                    formatted_parts.append("</ol>")
                    in_letra_list = False
                if not in_inciso_list:
                    formatted_parts.append('<ol class="legal-list" role="list">')
                    in_inciso_list = True
                content = is_inciso.group(2) or ""
                escaped = self._escape_html_preserve_links(content)
                formatted_parts.append(f"<li>{escaped}</li>")

            elif is_letra:
                if not in_letra_list:
                    if not in_inciso_list:
                        formatted_parts.append('<ol class="legal-list" role="list">')
                        in_inciso_list = True
                    formatted_parts.append('<ol class="legal-list alpha" role="list">')
                    in_letra_list = True
                content = is_letra.group(2) or ""
                escaped = self._escape_html_preserve_links(content)
                formatted_parts.append(f"<li>{escaped}</li>")

            else:
                if in_letra_list:
                    formatted_parts.append("</ol>")
                    in_letra_list = False
                if in_inciso_list:
                    formatted_parts.append("</ol>")
                    in_inciso_list = False
                escaped = self._escape_html_preserve_links(para)
                formatted_parts.append(f"<p>{escaped}</p>")

        if in_letra_list:
            formatted_parts.append("</ol>")
        if in_inciso_list:
            formatted_parts.append("</ol>")

        if not formatted_parts:
            return f"<p>{self._escape_html_preserve_links(text_with_refs)}</p>"

        return "\n".join(formatted_parts)

    def _create_article_index_page(self) -> None:
        """Crea la página de índice de artículos."""
        if not self.article_list:
            return

        # Agrupar artículos por título
        grouped_articles: dict[str, list[dict]] = {}
        for art in self.article_list:
            titulo = art.get("parent_titulo", "Sin Titulo") or "Sin Titulo"
            if titulo not in grouped_articles:
                grouped_articles[titulo] = []
            grouped_articles[titulo].append(art)

        sections_html = []
        for titulo, articles in grouped_articles.items():
            items_html = []
            for art in articles:
                items_html.append(
                    f'<li><a href="{art["file_ref"]}">'
                    f'<span class="art-num">Art. {art["number"]}</span></a></li>'
                )

            titulo_str = titulo or "Disposiciones Generales"
            section_title = titulo_str[:60] + "..." if len(titulo_str) > 60 else titulo_str

            sections_html.append(
                f"""
            <div class="index-section">
                <h3>{self._escape_html(section_title)}</h3>
                <ul class="index-list">
                    {"".join(items_html)}
                </ul>
            </div>
            """
            )

        content = f"""
<div class="article-index">
    <h1 class="no-break">Indice de Articulos</h1>
    <p class="no-indent">Total de articulos: {len(self.article_list)}</p>
    {"".join(sections_html)}
</div>
"""
        self._create_chapter("Indice de Articulos", "article_index.xhtml", content)

    def _create_keyword_index_page(self) -> None:
        """Crea la página de índice de palabras clave."""
        if not self.keyword_index:
            return

        sorted_keywords = sorted(
            [(k, v) for k, v in self.keyword_index.items() if v],
            key=lambda x: x[0],
        )

        if not sorted_keywords:
            return

        current_letter = ""
        sections_html = []

        for keyword, refs in sorted_keywords:
            first_letter = keyword[0].upper()
            if first_letter != current_letter:
                if current_letter:
                    sections_html.append("</div>")
                current_letter = first_letter
                sections_html.append(
                    f'<div class="keyword-section"><h3 class="keyword-letter">{current_letter}</h3>'
                )

            refs_html = ", ".join([f'<a href="{r["ref"]}">Art. {r["art"]}</a>' for r in refs[:8]])
            sections_html.append(
                f'<p class="keyword-entry"><strong>{keyword.capitalize()}</strong>: {refs_html}</p>'
            )

        if sections_html:
            sections_html.append("</div>")

        content = f"""
<div class="keyword-index">
    <h1 class="no-break">Indice de Materias</h1>
    <p class="index-intro">Referencias a los principales conceptos juridicos contenidos en esta norma.</p>
    {"".join(sections_html)}
</div>
"""
        self._create_chapter("Indice de Materias", "keyword_index.xhtml", content)

    def _create_promulgation_appendix(self, metadata: dict[str, Any]) -> None:
        """Crea el apéndice de promulgación.

        Args:
            metadata: Metadatos de la ley.
        """
        promulgation = metadata.get("promulgation_text", "")
        if not promulgation:
            return

        content = f"""
<div class="appendix">
    <h1 class="no-break">Anexo</h1>
    <h2>Texto de Promulgacion</h2>
    <blockquote class="promulgation-text">{self._escape_html(promulgation)}</blockquote>
</div>
"""
        self._create_chapter("Anexo: Texto de Promulgacion", "anexo_promulgacion.xhtml", content)

    def _build_toc(self) -> None:
        """Construye la tabla de contenidos."""
        toc_items = list(self.toc)

        for chapter, content in self.toc_sections:
            sub_items: list[Any] = []
            for item in content:
                if item.get("type") == "parrafo":
                    parrafo_text = item.get("text", "")
                    if parrafo_text:
                        short_text = (
                            parrafo_text[:40] + "..." if len(parrafo_text) > 40 else parrafo_text
                        )
                        sub_items.append(
                            epub.Link(
                                chapter.file_name,
                                short_text,
                                f"{chapter.id}_{len(sub_items)}",
                            )
                        )

            if sub_items:
                toc_items.append((chapter, sub_items))
            else:
                toc_items.append(chapter)

        self.book.toc = tuple(toc_items)
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

    def _set_spine(self) -> None:
        """Configura el spine del ePub."""
        self.book.spine = ["nav"] + self.chapters


def generate_law_epub(
    law_data: dict[str, Any],
    output_path: str | None = None,
    config: Config | None = None,
) -> str:
    """Función de conveniencia para generar un ePub.

    Args:
        law_data: Datos de la ley.
        output_path: Ruta de salida (directorio o archivo).
        config: Configuración opcional.

    Returns:
        Ruta al archivo generado.
    """
    generator = LawEpubGenerator(config)

    if output_path:
        path = Path(output_path)
        if path.suffix == ".epub":
            return generator.generate(law_data, output_dir=str(path.parent), filename=path.name)
        else:
            return generator.generate(law_data, output_dir=output_path)

    return generator.generate(law_data)
