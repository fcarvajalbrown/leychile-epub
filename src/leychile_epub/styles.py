"""
Estilos CSS para los ePub generados.

Este módulo contiene los estilos CSS profesionales usados
en los documentos legales generados.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

# Colores institucionales de Chile
CHILEAN_BLUE = "#0b3d91"
CHILEAN_RED = "#de1f2a"
ACCENT_GOLD = "#c9a227"

# Tamaños de fuente por preset
FONT_SIZES = {
    "small": {"base": "0.9em", "h1": "1.758em", "h2": "1.406em", "h3": "1.125em"},
    "medium": {"base": "1em", "h1": "1.953em", "h2": "1.563em", "h3": "1.25em"},
    "large": {"base": "1.1em", "h1": "2.148em", "h2": "1.719em", "h3": "1.375em"},
    "extra-large": {"base": "1.2em", "h1": "2.344em", "h2": "1.875em", "h3": "1.5em"},
}


def get_premium_css(
    font_size: str = "medium",
    line_spacing: float = 1.5,
    margin: str = "1.2em",
) -> str:
    """Genera el CSS premium para los ePub.

    Args:
        font_size: Tamaño de fuente ('small', 'medium', 'large', 'extra-large').
        line_spacing: Espaciado entre líneas.
        margin: Margen del cuerpo.

    Returns:
        CSS completo como string.
    """
    sizes = FONT_SIZES.get(font_size, FONT_SIZES["medium"])

    bg_color = "#ffffff"
    text_color = "#1a1a1a"

    return f"""
@charset "UTF-8";

/* ==========================================================================
   PREMIUM LEGAL DOCUMENT STYLESHEET
   LeyChile ePub Generator - Professional Edition
   Author: Luis Aguilera Arteaga
   ========================================================================== */

/* --------------------------------------------------------------------------
   1. ROOT VARIABLES & BASE TYPOGRAPHY
   -------------------------------------------------------------------------- */

:root {{
    --primary-color: {CHILEAN_BLUE};
    --accent-color: {CHILEAN_RED};
    --gold-accent: {ACCENT_GOLD};
    --text-color: {text_color};
    --bg-color: {bg_color};
    --border-color: #e5e5e5;
    --muted-color: #6b7280;
    --highlight-bg: #f8f9fa;
}}

body {{
    font-family: "Palatino Linotype", Palatino, "Book Antiqua", Georgia, "Times New Roman", serif;
    font-size: {sizes['base']};
    line-height: {line_spacing};
    color: var(--text-color);
    background-color: var(--bg-color);
    margin: {margin};
    padding: 0;
    text-align: justify;
    text-justify: inter-word;
    hyphens: auto;
    -webkit-hyphens: auto;
    -moz-hyphens: auto;
    orphans: 3;
    widows: 3;
    word-spacing: 0.05em;
    letter-spacing: 0.01em;
}}

/* --------------------------------------------------------------------------
   2. HEADINGS
   -------------------------------------------------------------------------- */

h1, h2, h3, h4, h5, h6 {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-weight: 600;
    line-height: 1.25;
    margin-top: 1.5em;
    margin-bottom: 0.75em;
    orphans: 4;
    widows: 4;
    page-break-after: avoid;
    -webkit-column-break-after: avoid;
    hyphens: none;
    -webkit-hyphens: none;
    -moz-hyphens: none;
    word-break: normal;
    overflow-wrap: normal;
}}

h1 {{
    font-size: {sizes['h1']};
    color: var(--primary-color);
    text-align: center;
    margin: 1.5em 0 1em 0;
    padding-bottom: 0.5em;
    border-bottom: 3px solid var(--primary-color);
    letter-spacing: 0.02em;
    text-transform: uppercase;
    page-break-before: always;
}}

h1.no-break {{
    page-break-before: auto;
}}

h2 {{
    font-size: 1.25em;
    color: var(--primary-color);
    margin: 1.5em 0 0.75em 0;
    padding-left: 0.75em;
    border-left: 4px solid var(--accent-color);
    background: linear-gradient(90deg, rgba(11,61,145,0.05) 0%, transparent 100%);
    padding: 0.5em 0.5em 0.5em 0.75em;
    page-break-inside: avoid;
    page-break-after: avoid;
    hyphens: none;
    -webkit-hyphens: none;
    -moz-hyphens: none;
}}

h3 {{
    font-size: {sizes['h3']};
    color: #2d3748;
    margin: 1.25em 0 0.5em 0;
    font-weight: 700;
}}

h4 {{
    font-size: 1.05em;
    color: #4a5568;
    font-weight: 600;
    margin: 1em 0 0.4em 0;
}}

/* --------------------------------------------------------------------------
   3. PARAGRAPHS & TEXT
   -------------------------------------------------------------------------- */

p {{
    margin: 0.6em 0;
    text-indent: 1.5em;
}}

p.no-indent, 
p:first-of-type {{
    text-indent: 0;
}}

blockquote {{
    margin: 1.5em 2em;
    padding: 1em 1.5em;
    border-left: 4px solid var(--gold-accent);
    background-color: var(--highlight-bg);
    font-style: italic;
    color: var(--muted-color);
}}

/* --------------------------------------------------------------------------
   4. LEGAL DOCUMENT STYLES
   -------------------------------------------------------------------------- */

.articulo-titulo {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 1.05em;
    font-weight: 700;
    color: var(--primary-color);
    margin: 1.5em 0 0.5em 0;
    padding: 0.4em 0;
    border-bottom: 1px solid var(--border-color);
    page-break-after: avoid;
    page-break-inside: avoid;
    hyphens: none;
    -webkit-hyphens: none;
}}

.articulo-titulo a {{
    color: inherit;
    text-decoration: none;
}}

.articulo-contenido {{
    margin: 0.5em 0 1.5em 0;
    padding-left: 0;
}}

.inciso {{
    margin: 0.4em 0 0.4em 2em;
    text-indent: 0;
    position: relative;
}}

.inciso::before {{
    content: "";
    position: absolute;
    left: -1em;
    top: 0.5em;
    width: 4px;
    height: 4px;
    background-color: var(--muted-color);
    border-radius: 50%;
}}

.letra {{
    margin: 0.3em 0 0.3em 3.5em;
    text-indent: 0;
    font-size: 0.95em;
}}

ol.legal-list {{
    counter-reset: legal-counter;
    list-style: none;
    padding-left: 2em;
    margin: 0.5em 0;
}}

ol.legal-list li {{
    counter-increment: legal-counter;
    margin: 0.4em 0;
    position: relative;
}}

ol.legal-list li::before {{
    content: counter(legal-counter) ".";
    position: absolute;
    left: -2em;
    font-weight: 600;
    color: var(--primary-color);
}}

ol.legal-list.alpha {{
    counter-reset: alpha-counter;
}}

ol.legal-list.alpha li::before {{
    content: counter(alpha-counter, lower-alpha) ")";
    counter-increment: alpha-counter;
}}

.derogado {{
    color: var(--muted-color);
    font-style: italic;
    text-decoration: line-through;
    opacity: 0.7;
}}

.derogado-notice {{
    display: inline-block;
    background-color: var(--accent-color);
    color: white;
    font-size: 0.75em;
    padding: 0.15em 0.5em;
    border-radius: 3px;
    margin-left: 0.5em;
    text-decoration: none;
    font-style: normal;
}}

/* --------------------------------------------------------------------------
   5. COVER PAGE
   -------------------------------------------------------------------------- */

.cover {{
    text-align: center;
    padding: 2em 1em;
    min-height: 90vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}}

.cover-header {{
    margin-bottom: 2em;
}}

.cover-escudo {{
    font-size: 3em;
    color: var(--primary-color);
    margin-bottom: 0.5em;
}}

.cover-republica {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 0.3em;
    color: var(--muted-color);
    margin-bottom: 0.5em;
}}

.cover-law-type {{
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 2.5em;
    font-weight: 700;
    color: var(--primary-color);
    margin: 0.5em 0;
    letter-spacing: 0.05em;
}}

.cover-law-number {{
    font-size: 3em;
    font-weight: 800;
    color: var(--accent-color);
    margin: 0.2em 0;
}}

.cover h1 {{
    font-size: 1.4em;
    color: var(--text-color);
    border: none;
    text-transform: none;
    margin: 1em 0;
    padding: 0;
    line-height: 1.4;
    page-break-before: auto;
}}

.cover-divider {{
    width: 60%;
    height: 3px;
    background: linear-gradient(90deg, transparent, var(--gold-accent), transparent);
    margin: 1.5em auto;
}}

.cover-organism {{
    font-size: 1em;
    color: var(--muted-color);
    font-style: italic;
    margin: 1em 0;
}}

.cover-subjects {{
    font-size: 0.85em;
    color: var(--primary-color);
    margin: 1em 0;
    padding: 0.75em 1.5em;
    background-color: var(--highlight-bg);
    border-radius: 4px;
    display: inline-block;
}}

.cover-metadata {{
    margin-top: 2em;
    padding: 1.5em;
    background-color: var(--highlight-bg);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    max-width: 80%;
}}

.cover-source {{
    font-size: 0.8em;
    color: var(--muted-color);
    margin: 0.5em 0;
}}

.cover-footer {{
    margin-top: auto;
    padding-top: 2em;
    font-size: 0.75em;
    color: var(--muted-color);
}}

/* --------------------------------------------------------------------------
   6. LEGAL INFO PAGE
   -------------------------------------------------------------------------- */

.legal-info {{
    padding: 1em;
}}

.legal-info h1 {{
    page-break-before: auto;
}}

.info-section {{
    margin: 1.5em 0;
    padding: 1em;
    background-color: var(--highlight-bg);
    border-radius: 6px;
    border-left: 4px solid var(--primary-color);
}}

.info-section h3 {{
    margin-top: 0;
    color: var(--primary-color);
}}

.info-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
}}

.info-table td {{
    padding: 0.5em;
    border-bottom: 1px solid var(--border-color);
    vertical-align: top;
}}

.info-table td:first-child {{
    font-weight: 600;
    width: 35%;
    color: var(--primary-color);
}}

.legal-info-compact {{
    padding: 1em;
    max-width: 100%;
}}

.legal-info-compact .info-title {{
    font-size: 1.4em;
    margin-bottom: 0.8em;
    page-break-before: auto;
}}

.info-table-compact {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9em;
    margin: 0.5em 0;
}}

.info-table-compact td {{
    padding: 0.4em 0.5em;
    border-bottom: 1px solid var(--border-color);
    vertical-align: top;
}}

.info-table-compact td.label {{
    font-weight: 600;
    width: 25%;
    color: var(--primary-color);
    white-space: nowrap;
}}

.info-table-compact .compact-text {{
    font-size: 0.95em;
    line-height: 1.3;
}}

.legal-disclaimer {{
    font-size: 0.8em;
    color: var(--muted-color);
    font-style: italic;
    margin-top: 1em;
    text-align: center;
    text-indent: 0;
}}

/* --------------------------------------------------------------------------
   7. ARTICLE INDEX
   -------------------------------------------------------------------------- */

.article-index {{
    padding: 1em;
}}

.article-index h1 {{
    page-break-before: auto;
}}

.index-section {{
    margin: 1.5em 0;
}}

.index-section h3 {{
    color: var(--primary-color);
    border-bottom: 2px solid var(--border-color);
    padding-bottom: 0.3em;
}}

.index-list {{
    list-style: none;
    padding: 0;
    margin: 0;
    column-count: 2;
    column-gap: 2em;
}}

.index-list li {{
    margin: 0.3em 0;
    padding: 0.2em 0;
    break-inside: avoid;
}}

.index-list a {{
    color: var(--text-color);
    text-decoration: none;
    display: block;
    padding: 0.2em 0.5em;
    border-radius: 3px;
    transition: background-color 0.2s;
}}

.index-list a:hover {{
    background-color: var(--highlight-bg);
}}

.index-list .art-num {{
    font-weight: 600;
    color: var(--primary-color);
}}

/* --------------------------------------------------------------------------
   8. ENCABEZADO
   -------------------------------------------------------------------------- */

.encabezado {{
    text-align: center;
    margin: 2em 1em;
    padding: 1.5em;
    background: linear-gradient(135deg, rgba(11,61,145,0.05) 0%, rgba(222,31,42,0.03) 100%);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    font-style: italic;
    color: var(--muted-color);
}}

.encabezado p {{
    text-indent: 0;
    margin: 0;
    line-height: 1.8;
}}

/* --------------------------------------------------------------------------
   9. CROSS-REFERENCES
   -------------------------------------------------------------------------- */

a {{
    color: var(--primary-color);
    text-decoration: none;
}}

a:hover {{
    text-decoration: underline;
}}

.cross-ref {{
    color: var(--primary-color);
    text-decoration: none;
    border-bottom: 1px dotted var(--primary-color);
    padding-bottom: 1px;
}}

.cross-ref:hover {{
    background-color: rgba(11,61,145,0.1);
    border-bottom-style: solid;
}}

.back-link {{
    font-size: 0.8em;
    color: var(--muted-color);
    margin-left: 0.5em;
}}

/* --------------------------------------------------------------------------
   10. KEYWORD INDEX
   -------------------------------------------------------------------------- */

.keyword-index {{
    padding: 1em;
}}

.keyword-index h1 {{
    page-break-before: auto;
}}

.index-intro {{
    font-style: italic;
    color: var(--muted-color);
    margin-bottom: 1.5em;
    text-indent: 0;
}}

.keyword-section {{
    margin: 1em 0;
}}

.keyword-letter {{
    font-size: 1.3em;
    color: var(--primary-color);
    border-bottom: 2px solid var(--primary-color);
    padding-bottom: 0.2em;
    margin-bottom: 0.5em;
}}

.keyword-entry {{
    margin: 0.3em 0;
    text-indent: 0;
    font-size: 0.95em;
}}

.keyword-entry a {{
    color: var(--primary-color);
}}

.keyword-entry a:hover {{
    text-decoration: underline;
}}

/* --------------------------------------------------------------------------
   11. APPENDIX
   -------------------------------------------------------------------------- */

.appendix {{
    padding: 1em;
}}

.appendix h1 {{
    page-break-before: auto;
    font-size: 1.5em;
}}

.appendix h2 {{
    font-size: 1.2em;
    margin-top: 0.5em;
}}

.promulgation-text {{
    font-size: 0.9em;
    line-height: 1.6;
    font-style: italic;
    margin: 1em 0;
    padding: 1em;
    background-color: var(--highlight-bg);
    border-left: 3px solid var(--muted-color);
}}

/* --------------------------------------------------------------------------
   12. NAVIGATION & TOC
   -------------------------------------------------------------------------- */

nav#toc {{
    padding: 1em;
}}

nav#toc h1 {{
    page-break-before: auto;
}}

nav#toc ol {{
    list-style-type: none;
    padding-left: 0;
}}

nav#toc li {{
    margin: 0.5em 0;
}}

nav#toc a {{
    color: var(--text-color);
    text-decoration: none;
    display: block;
    padding: 0.3em 0;
}}

nav#toc a:hover {{
    color: var(--primary-color);
}}

nav#toc ol ol {{
    padding-left: 1.5em;
    margin-top: 0.3em;
}}

nav#toc ol ol li {{
    font-size: 0.95em;
}}

nav#toc ol ol ol {{
    font-size: 0.9em;
}}

/* --------------------------------------------------------------------------
   13. DARK MODE
   -------------------------------------------------------------------------- */

@media (prefers-color-scheme: dark) {{
    :root {{
        --primary-color: #4a90d9;
        --accent-color: #ff6b6b;
        --gold-accent: #ffd93d;
        --text-color: #e8e6e0;
        --bg-color: #1a1a1a;
        --border-color: #3d3d3d;
        --muted-color: #9ca3af;
        --highlight-bg: #2d2d2d;
    }}
    
    body {{
        background-color: var(--bg-color);
        color: var(--text-color);
    }}
    
    h1, h2 {{
        color: var(--primary-color);
    }}
    
    .cover-escudo {{
        color: var(--gold-accent);
    }}
    
    .encabezado {{
        background: linear-gradient(135deg, rgba(74,144,217,0.1) 0%, rgba(255,107,107,0.05) 100%);
    }}
    
    .info-section {{
        background-color: var(--highlight-bg);
    }}
    
    .cover-metadata {{
        background-color: var(--highlight-bg);
    }}
}}

/* --------------------------------------------------------------------------
   14. SEPIA MODE
   -------------------------------------------------------------------------- */

body.sepia {{
    --primary-color: #5c4033;
    --accent-color: #8b4513;
    --text-color: #3d2914;
    --bg-color: #f4ecd8;
    --border-color: #d4c4a8;
    --highlight-bg: #ebe3d1;
    background-color: var(--bg-color);
    color: var(--text-color);
}}

/* --------------------------------------------------------------------------
   15. PRINT STYLES
   -------------------------------------------------------------------------- */

@media print {{
    body {{
        font-size: 11pt;
        line-height: 1.4;
        color: #000000;
        background: #ffffff;
    }}
    
    h1 {{
        page-break-before: always;
        color: #000000;
    }}
    
    h1.no-break {{
        page-break-before: auto;
    }}
    
    .articulo-titulo {{
        page-break-after: avoid;
    }}
    
    .articulo-contenido {{
        page-break-inside: avoid;
    }}
    
    .cover {{
        page-break-after: always;
    }}
    
    a {{
        color: #000000;
        text-decoration: underline;
    }}
    
    .cross-ref {{
        border-bottom: none;
    }}
}}

/* --------------------------------------------------------------------------
   16. ACCESSIBILITY
   -------------------------------------------------------------------------- */

@media (prefers-contrast: high) {{
    :root {{
        --text-color: #000000;
        --bg-color: #ffffff;
        --border-color: #000000;
        --primary-color: #000080;
        --accent-color: #800000;
    }}
    
    a, .cross-ref {{
        text-decoration: underline;
    }}
    
    h1, h2, h3 {{
        border-width: 2px;
    }}
}}

@media (prefers-reduced-motion: reduce) {{
    * {{
        transition: none !important;
        animation: none !important;
    }}
}}

a:focus, 
button:focus {{
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
}}

.sr-only {{
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}}

.skip-link {{
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--primary-color);
    color: white;
    padding: 8px;
    z-index: 100;
}}

.skip-link:focus {{
    top: 0;
}}

/* --------------------------------------------------------------------------
   17. RESPONSIVE
   -------------------------------------------------------------------------- */

@media screen and (max-width: 600px) {{
    body {{
        margin: 0.5em;
    }}
    
    h1 {{
        font-size: 1.5em;
    }}
    
    h2 {{
        font-size: 1.25em;
    }}
    
    .cover-law-number {{
        font-size: 2em;
    }}
    
    .index-list {{
        column-count: 1;
    }}
}}
"""
