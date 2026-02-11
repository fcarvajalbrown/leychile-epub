"""
Generador de ePub v2 para normas de LeyChile.

Este módulo genera ePubs profesionales siguiendo la estructura jerárquica
oficial del XSD de la BCN: Capítulo → Título → Párrafo → Artículo.
"""

from __future__ import annotations

import html
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ebooklib import epub

from .scraper_v2 import EstructuraFuncional, Norma


@dataclass
class EPubConfig:
    """Configuración para la generación del ePub."""

    # Metadatos del ePub
    language: str = "es"
    publisher: str = "Biblioteca del Congreso Nacional de Chile"
    rights: str = "Dominio público según Ley 17.336 Art. 11"

    # Estilos y formato
    include_toc: bool = True
    include_metadata_page: bool = True
    include_derogado_markers: bool = True
    include_transitorio_markers: bool = True
    include_version_info: bool = True

    # CSS personalizado (None usa el predeterminado)
    custom_css: str | None = None


# CSS profesional para el ePub
DEFAULT_CSS = """
@charset "UTF-8";

/* ========================================
   Estilos para ePub de Leyes Chilenas
   Biblioteca del Congreso Nacional
   ======================================== */

/* Reset y base */
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.6;
    color: #1a1a1a;
    margin: 0;
    padding: 0.5em;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
}

/* Encabezados */
h1 {
    font-size: 1.8em;
    font-weight: bold;
    text-align: center;
    color: #003366;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    page-break-before: always;
    page-break-after: avoid;
    line-height: 1.3;
}

h2 {
    font-size: 1.4em;
    font-weight: bold;
    color: #003366;
    margin-top: 1.2em;
    margin-bottom: 0.6em;
    page-break-after: avoid;
    border-bottom: 1px solid #003366;
    padding-bottom: 0.3em;
}

h3 {
    font-size: 1.2em;
    font-weight: bold;
    color: #004080;
    margin-top: 1em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}

h4 {
    font-size: 1.1em;
    font-weight: bold;
    color: #005599;
    margin-top: 0.8em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
}

h5, h6 {
    font-size: 1em;
    font-weight: bold;
    color: #333;
    margin-top: 0.6em;
    margin-bottom: 0.3em;
}

/* Párrafos */
p {
    margin: 0.5em 0;
    text-indent: 1.5em;
}

p.no-indent {
    text-indent: 0;
}

/* Artículos */
.articulo {
    margin: 1em 0;
    page-break-inside: avoid;
}

.articulo-numero {
    font-weight: bold;
    color: #003366;
}

.articulo-contenido {
    margin-left: 0;
}

.articulo-contenido p:first-child {
    text-indent: 0;
}

/* Incisos y literales */
.inciso {
    margin: 0.3em 0 0.3em 1.5em;
}

.literal {
    margin: 0.2em 0 0.2em 3em;
}

.numero {
    margin: 0.2em 0 0.2em 2em;
}

/* Estados especiales */
.derogado {
    background-color: #fff3f3;
    border-left: 3px solid #cc0000;
    padding: 0.5em;
    margin: 0.5em 0;
}

.derogado::before {
    content: "DEROGADO";
    display: block;
    color: #cc0000;
    font-weight: bold;
    font-size: 0.8em;
    margin-bottom: 0.3em;
}

.transitorio {
    background-color: #f5f5dc;
    border-left: 3px solid #b8860b;
    padding: 0.5em;
    margin: 0.5em 0;
}

.transitorio::before {
    content: "DISPOSICIÓN TRANSITORIA";
    display: block;
    color: #b8860b;
    font-weight: bold;
    font-size: 0.8em;
    margin-bottom: 0.3em;
}

/* Página de título */
.titulo-pagina {
    text-align: center;
    padding-top: 2em;
}

.titulo-pagina h1 {
    font-size: 2em;
    border: none;
    page-break-before: auto;
}

.titulo-pagina .tipo-norma {
    font-size: 1.5em;
    color: #003366;
    margin: 1em 0;
}

.titulo-pagina .organismos {
    font-size: 0.9em;
    color: #666;
    margin: 1em 0;
}

.titulo-pagina .fecha {
    font-size: 1em;
    color: #333;
    margin: 0.5em 0;
}

/* Página de metadatos */
.metadatos-pagina {
    font-size: 0.95em;
}

.metadatos-pagina h2 {
    font-size: 1.3em;
    margin-top: 1em;
}

.metadatos-pagina dl {
    margin: 0.5em 0;
}

.metadatos-pagina dt {
    font-weight: bold;
    color: #003366;
    margin-top: 0.5em;
}

.metadatos-pagina dd {
    margin: 0.2em 0 0.5em 1em;
}

.metadatos-pagina .materias-list {
    list-style-type: disc;
    margin: 0.3em 0 0.3em 2em;
    padding: 0;
}

.metadatos-pagina .materias-list li {
    margin: 0.2em 0;
}

/* Encabezado de la norma */
.encabezado-norma {
    text-align: center;
    font-style: italic;
    margin: 1em 0 2em 0;
    padding: 1em;
    border-top: 1px solid #ccc;
    border-bottom: 1px solid #ccc;
}

/* Promulgación */
.promulgacion {
    margin-top: 2em;
    padding-top: 1em;
    border-top: 2px solid #003366;
}

.promulgacion h2 {
    text-align: center;
}

.firma {
    margin: 1em 0;
    text-align: right;
}

.firma-nombre {
    font-weight: bold;
}

.firma-cargo {
    font-style: italic;
    color: #666;
}

/* TOC */
.toc {
    page-break-before: always;
}

.toc h2 {
    text-align: center;
}

.toc ul {
    list-style-type: none;
    margin: 0;
    padding: 0;
}

.toc li {
    margin: 0.3em 0;
}

.toc .toc-capitulo {
    font-weight: bold;
    margin-top: 0.8em;
}

.toc .toc-titulo {
    margin-left: 1em;
}

.toc .toc-parrafo {
    margin-left: 2em;
    font-size: 0.95em;
}

.toc .toc-articulo {
    margin-left: 3em;
    font-size: 0.9em;
    color: #666;
}

/* Notas de versión */
.version-info {
    font-size: 0.8em;
    color: #666;
    text-align: right;
    margin-top: 0.3em;
}

/* Anexos */
.anexo {
    page-break-before: always;
}

/* Utilidades */
.centrado {
    text-align: center;
}

.negrita {
    font-weight: bold;
}

.cursiva {
    font-style: italic;
}

.mayusculas {
    text-transform: uppercase;
}

/* Impresión */
@media print {
    body {
        font-size: 11pt;
    }
    
    .derogado, .transitorio {
        border-left-width: 2pt;
    }
}
"""


class EPubGeneratorV2:
    """Generador de ePub v2 con soporte para estructura jerárquica."""

    # Mapeo de tipos de parte a niveles de encabezado HTML
    HEADING_LEVELS = {
        "Capítulo": "h2",
        "Título": "h3",
        "Párrafo": "h4",
        "Artículo": "h5",
    }

    # Mapeo de tipos de parte a clases CSS para TOC
    TOC_CLASSES = {
        "Capítulo": "toc-capitulo",
        "Título": "toc-titulo",
        "Párrafo": "toc-parrafo",
        "Artículo": "toc-articulo",
    }

    def __init__(self, config: EPubConfig | None = None):
        """
        Inicializa el generador.

        Args:
            config: Configuración del ePub. Si es None, usa valores predeterminados.
        """
        self.config = config or EPubConfig()
        self._book: epub.EpubBook | None = None
        self._chapters: list[epub.EpubHtml] = []
        self._toc_items: list[tuple | epub.Link | epub.EpubHtml] = []
        self._spine: list[str | epub.EpubHtml] = ["nav"]
        self._chapter_counter = 0

    def generate(self, norma: Norma, output_path: str | Path) -> Path:
        """
        Genera el ePub a partir de los datos de la norma.

        Args:
            norma: Datos de la norma parseada.
            output_path: Ruta donde guardar el ePub.

        Returns:
            Path del archivo generado.
        """
        output_path = Path(output_path)

        # Inicializar libro
        self._init_book(norma)

        # Agregar CSS
        self._add_styles()

        # Generar páginas
        self._add_title_page(norma)

        if self.config.include_metadata_page:
            self._add_metadata_page(norma)

        # Agregar encabezado si existe
        if norma.encabezado_texto:
            self._add_encabezado(norma)

        # Agregar contenido estructurado
        self._add_estructuras(norma.estructuras)

        # Agregar promulgación si existe
        if norma.promulgacion_texto:
            self._add_promulgacion(norma)

        # Configurar TOC y spine
        self._finalize_book()

        # Guardar
        epub.write_epub(str(output_path), self._book, {})

        return output_path

    def _init_book(self, norma: Norma) -> None:
        """Inicializa el libro ePub con metadatos."""
        self._book = epub.EpubBook()
        self._chapters = []
        self._toc_items = []
        self._spine = ["nav"]
        self._chapter_counter = 0

        # Identificador único
        book_id = f"leychile-{norma.norma_id}-{uuid.uuid4().hex[:8]}"
        self._book.set_identifier(book_id)

        # Título
        titulo = f"{norma.identificador.tipo} {norma.identificador.numero}"
        self._book.set_title(titulo)

        # Idioma
        self._book.set_language(self.config.language)

        # Autores/Organismos
        for org in norma.identificador.organismos:
            self._book.add_author(org)

        # Metadatos adicionales
        self._book.add_metadata("DC", "publisher", self.config.publisher)
        self._book.add_metadata("DC", "rights", self.config.rights)
        self._book.add_metadata("DC", "date", norma.fecha_version or "")
        self._book.add_metadata("DC", "description", norma.titulo_completo)

        # Materias como subjects
        for materia in norma.metadatos.materias:
            self._book.add_metadata("DC", "subject", materia)

    def _add_styles(self) -> None:
        """Agrega los estilos CSS al libro."""
        css_content = self.config.custom_css or DEFAULT_CSS

        css_item = epub.EpubItem(
            uid="style_main",
            file_name="styles/main.css",
            media_type="text/css",
            content=css_content.encode("utf-8"),
        )
        self._book.add_item(css_item)

    def _create_chapter(
        self,
        title: str,
        content: str,
        filename: str | None = None,
    ) -> epub.EpubHtml:
        """Crea un capítulo HTML."""
        self._chapter_counter += 1

        if filename is None:
            filename = f"chapter_{self._chapter_counter:03d}.xhtml"

        chapter = epub.EpubHtml(
            title=title,
            file_name=filename,
            lang=self.config.language,
        )
        chapter.set_content(content)
        chapter.add_item(self._book.get_item_with_id("style_main"))

        self._book.add_item(chapter)
        self._chapters.append(chapter)
        self._spine.append(chapter)

        return chapter

    def _add_title_page(self, norma: Norma) -> None:
        """Agrega la página de título."""
        tipo_numero = f"{norma.identificador.tipo} {norma.identificador.numero}"
        organismos = "<br/>".join(html.escape(o) for o in norma.identificador.organismos)

        fechas_html = ""
        if norma.identificador.fecha_promulgacion:
            fechas_html += (
                f'<p class="fecha">Promulgación: {html.escape(norma.identificador.fecha_promulgacion)}</p>\n'
            )
        if norma.identificador.fecha_publicacion:
            fechas_html += (
                f'<p class="fecha">Publicación: {html.escape(norma.identificador.fecha_publicacion)}</p>\n'
            )
        if norma.fecha_version:
            fechas_html += f'<p class="fecha">Última modificación: {html.escape(norma.fecha_version)}</p>\n'

        estado = ""
        if norma.derogado:
            estado = (
                '<p style="color: #cc0000; font-weight: bold; margin-top: 1em;">NORMA DEROGADA</p>'
            )

        content = f"""

<html xmlns="http://www.w3.org/1999/xhtml" lang="es">
<head>
    <title>{html.escape(tipo_numero)}</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    <div class="titulo-pagina">
        <p class="tipo-norma">{html.escape(tipo_numero)}</p>
        <h1>{html.escape(norma.titulo_completo)}</h1>
        <p class="organismos">{organismos}</p>
        {fechas_html}
        {estado}
    </div>
</body>
</html>"""

        chapter = self._create_chapter(tipo_numero, content, "titulo.xhtml")
        self._toc_items.append(chapter)

    def _add_metadata_page(self, norma: Norma) -> None:
        """Agrega la página de metadatos."""
        materias_html = ""
        if norma.metadatos.materias:
            materias_items = "\n".join(
                f"        <li>{html.escape(m)}</li>" for m in norma.metadatos.materias
            )
            materias_html = f"""
    <dt>Materias</dt>
    <dd>
        <ul class="materias-list">
{materias_items}
        </ul>
    </dd>"""

        # Nombres de uso común
        nombres_html = ""
        if norma.metadatos.nombres_uso_comun:
            nombres_items = "\n".join(
                f"        <li>{html.escape(n)}</li>" for n in norma.metadatos.nombres_uso_comun
            )
            nombres_html = f"""
    <dt>Nombres de uso común</dt>
    <dd>
        <ul class="materias-list">
{nombres_items}
        </ul>
    </dd>"""

        content = f"""

<html xmlns="http://www.w3.org/1999/xhtml" lang="es">
<head>
    <title>Información de la Norma</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    <div class="metadatos-pagina">
        <h2>Información de la Norma</h2>
        
        <h3>Identificación</h3>
        <dl>
            <dt>Tipo</dt>
            <dd>{html.escape(norma.identificador.tipo)}</dd>
            
            <dt>Número</dt>
            <dd>{html.escape(norma.identificador.numero)}</dd>
            
            <dt>ID Norma BCN</dt>
            <dd>{html.escape(norma.norma_id)}</dd>
        </dl>
        
        <h3>Organismos</h3>
        <dl>
            <dt>Organismo(s) responsable(s)</dt>
            <dd>{"<br/>".join(html.escape(o) for o in norma.identificador.organismos)}</dd>
        </dl>
        
        <h3>Fechas</h3>
        <dl>
            <dt>Fecha de promulgación</dt>
            <dd>{html.escape(norma.identificador.fecha_promulgacion or "No disponible")}</dd>
            
            <dt>Fecha de publicación</dt>
            <dd>{html.escape(norma.identificador.fecha_publicacion or "No disponible")}</dd>
            
            <dt>Versión del texto</dt>
            <dd>{html.escape(norma.fecha_version or "No disponible")}</dd>
        </dl>
        
        <h3>Clasificación</h3>
        <dl>{materias_html}{nombres_html}
        </dl>
        
        <h3>Estado</h3>
        <dl>
            <dt>Estado de vigencia</dt>
            <dd>{"Derogada" if norma.derogado else "Vigente"}</dd>
        </dl>
        
        <p class="no-indent" style="margin-top: 2em; font-size: 0.8em; color: #666;">
            <em>Fuente: Biblioteca del Congreso Nacional de Chile (www.leychile.cl)</em><br>
            <em>Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")}</em>
        </p>
    </div>
</body>
</html>"""

        chapter = self._create_chapter("Información de la Norma", content, "metadatos.xhtml")
        self._toc_items.append(chapter)

    def _add_encabezado(self, norma: Norma) -> None:
        """Agrega el encabezado de la norma."""
        content = f"""

<html xmlns="http://www.w3.org/1999/xhtml" lang="es">
<head>
    <title>Encabezado</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    <div class="encabezado-norma">
        {self._format_texto(norma.encabezado_texto)}
    </div>
</body>
</html>"""

        self._create_chapter("Encabezado", content, "encabezado.xhtml")

    def _add_estructuras(self, estructuras: list[EstructuraFuncional]) -> None:
        """Agrega las estructuras funcionales al ePub."""
        # Crear un capítulo para cada estructura de nivel superior (típicamente Capítulos)
        for estructura in estructuras:
            self._add_estructura_capitulo(estructura)

    def _add_estructura_capitulo(self, estructura: EstructuraFuncional) -> None:
        """Agrega una estructura de nivel superior como capítulo."""
        titulo = self._get_titulo_estructura(estructura)
        content_body = self._render_estructura(estructura, is_root=True)

        # Asegurar que siempre haya contenido
        if not content_body.strip():
            content_body = "<p><em>(Sin contenido)</em></p>"

        content = f"""

<html xmlns="http://www.w3.org/1999/xhtml" lang="es">
<head>
    <title>{html.escape(titulo)}</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
{content_body}
</body>
</html>"""

        chapter = self._create_chapter(titulo, content)

        # Construir TOC jerárquico
        toc_entry = self._build_toc_entry(estructura, chapter)
        self._toc_items.append(toc_entry)

    def _render_estructura(
        self,
        estructura: EstructuraFuncional,
        is_root: bool = False,
    ) -> str:
        """Renderiza una estructura funcional a HTML."""
        html_parts: list[str] = []

        # Determinar clase CSS adicional
        css_classes: list[str] = []
        if self.config.include_derogado_markers and estructura.derogado:
            css_classes.append("derogado")
        if self.config.include_transitorio_markers and estructura.transitorio:
            css_classes.append("transitorio")

        class_attr = f' class="{" ".join(css_classes)}"' if css_classes else ""

        # Título/encabezado
        titulo = self._get_titulo_estructura(estructura)
        heading = self.HEADING_LEVELS.get(estructura.tipo_parte, "h5")

        if estructura.tipo_parte == "Artículo":
            # Formato especial para artículos
            html_parts.append(f'<div class="articulo"{class_attr}>')
            html_parts.append(
                f'<p><span class="articulo-numero">Artículo {html.escape(estructura.nombre_parte or "")}</span></p>'
            )
            html_parts.append('<div class="articulo-contenido">')

            if estructura.texto:
                html_parts.append(self._format_texto(estructura.texto))

            html_parts.append("</div>")

            # Info de versión
            if self.config.include_version_info and estructura.fecha_version:
                html_parts.append(
                    f'<p class="version-info">Última modificación: {estructura.fecha_version}</p>'
                )

            html_parts.append("</div>")
        else:
            # Formato para capítulos, títulos, párrafos
            wrapper_start = f"<section{class_attr}>" if css_classes else ""
            wrapper_end = "</section>" if css_classes else ""

            if wrapper_start:
                html_parts.append(wrapper_start)

            html_parts.append(f"<{heading}>{html.escape(titulo)}</{heading}>")

            if estructura.texto:
                html_parts.append(self._format_texto(estructura.texto))

            # Renderizar hijos
            for hijo in estructura.hijos:
                html_parts.append(self._render_estructura(hijo))

            if wrapper_end:
                html_parts.append(wrapper_end)

        return "\n".join(html_parts)

    def _get_titulo_estructura(self, estructura: EstructuraFuncional) -> str:
        """Obtiene el título formateado de una estructura."""
        if estructura.tipo_parte == "Artículo":
            return f"Artículo {estructura.nombre_parte or ''}"

        if estructura.titulo_parte:
            return estructura.titulo_parte

        if estructura.nombre_parte:
            return estructura.nombre_parte

        return f"{estructura.tipo_parte} {estructura.id_parte}"

    def _format_texto(self, texto: str) -> str:
        """Formatea el texto con párrafos y estructura."""
        if not texto:
            return ""

        # Escapar HTML
        texto = html.escape(texto)

        # Dividir en párrafos
        parrafos = texto.split("\n\n")

        html_parts: list[str] = []

        for parrafo in parrafos:
            parrafo = parrafo.strip()
            if not parrafo:
                continue

            # Detectar incisos (comienzan con letras minúsculas seguidas de .)
            if re.match(r"^[a-z]\)\s", parrafo):
                html_parts.append(f'<p class="literal">{parrafo}</p>')
            # Detectar numerales (comienzan con números seguidos de . o ))
            elif re.match(r"^\d+[\.\)]\s", parrafo):
                html_parts.append(f'<p class="numero">{parrafo}</p>')
            # Detectar incisos con guión
            elif parrafo.startswith("-"):
                html_parts.append(f'<p class="inciso">{parrafo}</p>')
            else:
                # Párrafo normal - reemplazar saltos de línea simples con <br/>
                parrafo = parrafo.replace("\n", "<br/>\n")
                html_parts.append(f"<p>{parrafo}</p>")

        return "\n".join(html_parts)

    def _build_toc_entry(
        self,
        estructura: EstructuraFuncional,
        chapter: epub.EpubHtml,
    ) -> tuple | epub.Link:
        """Construye una entrada de TOC con sub-items."""
        titulo = self._get_titulo_estructura(estructura)

        # Si no tiene hijos, retornar link simple
        if not estructura.hijos:
            return epub.Link(chapter.file_name, titulo, chapter.id)

        # Filtrar hijos que aparecerán en TOC (no artículos individuales si son muchos)
        hijos_toc = []
        for hijo in estructura.hijos:
            if hijo.tipo_parte in ("Capítulo", "Título", "Párrafo"):
                # Crear sub-entrada
                hijo_titulo = self._get_titulo_estructura(hijo)
                hijo_anchor = f"{chapter.file_name}#{self._make_anchor(hijo)}"
                hijos_toc.append(epub.Link(hijo_anchor, hijo_titulo, f"toc_{hijo.id_parte}"))

        # Si hay sub-items, crear sección con hijos
        if hijos_toc:
            section = epub.Section(titulo)
            return (section, [epub.Link(chapter.file_name, titulo, chapter.id)] + hijos_toc)

        return epub.Link(chapter.file_name, titulo, chapter.id)

    def _make_anchor(self, estructura: EstructuraFuncional) -> str:
        """Crea un anchor ID para una estructura."""
        tipo = estructura.tipo_parte.lower().replace("á", "a").replace("í", "i")
        return f"{tipo}_{estructura.id_parte}"

    def _add_promulgacion(self, norma: Norma) -> None:
        """Agrega la página de promulgación."""
        content = f"""

<html xmlns="http://www.w3.org/1999/xhtml" lang="es">
<head>
    <title>Promulgación</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    <div class="promulgacion">
        <h2>Promulgación</h2>
        {self._format_texto(norma.promulgacion_texto)}
    </div>
</body>
</html>"""

        chapter = self._create_chapter("Promulgación", content, "promulgacion.xhtml")
        self._toc_items.append(chapter)

    def _finalize_book(self) -> None:
        """Finaliza la configuración del libro."""
        # Configurar TOC
        self._book.toc = self._toc_items

        # Agregar navegación
        self._book.add_item(epub.EpubNcx())
        self._book.add_item(epub.EpubNav())

        # Configurar spine
        self._book.spine = self._spine


def generate_epub(
    norma: Norma,
    output_path: str | Path,
    config: EPubConfig | None = None,
) -> Path:
    """
    Función de conveniencia para generar un ePub.

    Args:
        norma: Datos de la norma.
        output_path: Ruta de salida.
        config: Configuración opcional.

    Returns:
        Path del archivo generado.
    """
    generator = EPubGeneratorV2(config)
    return generator.generate(norma, output_path)
