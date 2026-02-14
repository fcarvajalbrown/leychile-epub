#!/usr/bin/env python3
"""
Procesamiento batch de Instructivos de la SUPERIR.

Descarga los PDFs, extrae texto, parsea la estructura y genera
archivos XML compatibles con el esquema ley_v1.xsd.

Fuentes:
  Página 1: https://www.superir.gob.cl/biblioteca-digital/instructivo-ley-20-720/
  Página 2: https://www.superir.gob.cl/biblioteca-digital/instructivo-ley-20-720/instructivo-ley-20-720-2/

Uso:
    python scripts/process_instructivos.py                    # Procesar todos
    python scripts/process_instructivos.py --id 2024_INST_5   # Procesar uno específico
    python scripts/process_instructivos.py --text-only         # Solo extraer texto

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from leychile_epub.instructivo_parser import InstructivoParser
from leychile_epub.pdf_extractor import PDFExtractionError, PDFTextExtractor
from leychile_epub.xml_generator import LawXMLGenerator

# ═══════════════════════════════════════════════════════════════════════════════
# CATÁLOGO DE INSTRUCTIVOS SUPERIR (Ley 20.720)
# ═══════════════════════════════════════════════════════════════════════════════
#
# 22 documentos en total:
#   Página 1 (2023-2026): 12 instructivos
#   Página 2 (2015-2021): 10 instructivos
#

INSTRUCTIVO_CATALOG: dict[str, dict[str, Any]] = {
    # ─── Página 1: 2023-2026 ─────────────────────────────────────────────
    "2026_COMPL_SQ_8": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2026/01/RES_NUM_999_A_O_2026.pdf",
        "titulo_completo": "Resolución complementaria Instructivo SQ N°8 - Prelación de créditos y distribución de fondos",
        "resolucion_exenta": "999",
        "fecha_publicacion": "2026-01-16",
        "materias": [
            "Prelación de créditos",
            "Distribución de fondos",
            "Interpretación administrativa",
        ],
        "nombres_comunes": ["Complemento Instructivo SQ 8"],
        "categoria": "Liquidación",
        "doc_numero": "complementario",
    },
    "2025_INST_1_FIANZAS": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2025/09/RES_NUM_15573_AÑO_2025.pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°1/2025 - Fianzas, preferencias y contragarantías en liquidación",
        "resolucion_exenta": "15573",
        "fecha_publicacion": "2025-08-19",
        "materias": [
            "Fianzas",
            "Preferencias",
            "Contragarantías",
            "Liquidación",
        ],
        "nombres_comunes": ["Instructivo de Fianzas y Preferencias"],
        "categoria": "Liquidación",
        "doc_numero": "1",
    },
    "2025_MODIF_INST_1": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2025/04/RES_NUM_7164_2025.pdf",
        "titulo_completo": "Resolución que modifica Instructivo SUPERIR N°1/2024 - Cese de liquidadores y sustitutos",
        "resolucion_exenta": "7164",
        "fecha_publicacion": "2025-04-22",
        "materias": [
            "Cese de liquidadores",
            "Liquidadores sustitutos",
            "Artículo 38",
        ],
        "nombres_comunes": ["Modificación Instructivo Cese Liquidadores"],
        "categoria": "Liquidación",
        "doc_numero": "modif_1",
    },
    "2024_INST_6": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/11/RES_NUM_16245_A_O_2024.pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°6 - Finiquitos laborales electrónicos y firma electrónica en el procedimiento concursal de liquidación",
        "resolucion_exenta": "16245",
        "fecha_publicacion": "2024-11-04",
        "materias": [
            "Finiquitos laborales electrónicos",
            "Firma electrónica",
            "Procedimiento concursal de liquidación",
        ],
        "nombres_comunes": ["Instructivo de Finiquitos Electrónicos"],
        "categoria": "Liquidación",
        "doc_numero": "6",
    },
    "2024_INST_5": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/10/RES_NUM_14477_A_O_2024.pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°5 - Incautación, conservación y entrega de bienes en procedimientos concursales de liquidación ordinaria y simplificada",
        "resolucion_exenta": "14477",
        "fecha_publicacion": "2024-10-03",
        "materias": [
            "Incautación de bienes",
            "Conservación de bienes",
            "Entrega de bienes",
            "Inventario de bienes",
            "Procedimiento concursal de liquidación",
            "Liquidación simplificada",
            "Remuneraciones inembargables",
            "Documentación contable",
        ],
        "nombres_comunes": [
            "Instructivo de Incautación y Conservación de Bienes",
            "Instructivo de Incautación de Bienes",
        ],
        "categoria": "Liquidación",
        "doc_numero": "5",
    },
    "2024_INST_4": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/09/RES_NUM_13139_AO_2024.pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°4 - Instrucciones sobre hechos relevantes que deben informar los sujetos fiscalizados a la Superintendencia de Insolvencia y Reemprendimiento",
        "resolucion_exenta": "13139",
        "fecha_publicacion": "2024-09-05",
        "materias": [
            "Hechos relevantes",
            "Sujetos fiscalizados",
            "Obligación de informar",
            "Implicancia concursal",
            "Implicancia penal",
            "Inhabilidades sobrevinientes",
            "Procedimiento administrativo sancionatorio",
        ],
        "nombres_comunes": [
            "Instructivo de Hechos Relevantes",
            "Instructivo de Reporte de Hechos Relevantes",
        ],
        "categoria": "Fiscalización",
        "doc_numero": "4",
    },
    "2024_INST_3": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/08/RES_NUM_12473_AO_2024.pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°3 - Instrucciones a los Veedores y Veedoras en el Procedimiento Concursal de Reorganización Judicial, de Reorganización Simplificada y de Reorganización Extrajudicial",
        "resolucion_exenta": "12473",
        "fecha_publicacion": "2024-08-26",
        "materias": [
            "Veedores",
            "Reorganización judicial",
            "Reorganización simplificada",
            "Reorganización extrajudicial",
            "Nómina de créditos reconocidos",
            "Informe del veedor",
            "Cuenta mensual",
            "Cuenta final de gestión",
            "Acuerdo de reorganización",
            "Protección financiera concursal",
        ],
        "nombres_comunes": [
            "Instructivo de Veedores",
            "Instructivo de Veedores en Reorganización",
        ],
        "categoria": "Reorganización",
        "doc_numero": "3",
    },
    "2024_INST_2": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/08/RES_NUM_11679_AO_2024.pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°2 - Instrucciones a los Síndicos y Ex Síndicos en Aplicación de Sobreseimiento Definitivo y Sobreseimiento Temporal en los Procedimientos de Quiebras Vigentes Regidos por el Libro IV del Código de Comercio",
        "resolucion_exenta": "11679",
        "fecha_publicacion": "2024-08-13",
        "materias": [
            "Síndicos",
            "Sobreseimiento definitivo",
            "Sobreseimiento temporal",
            "Quiebras vigentes",
            "Libro IV del Código de Comercio",
            "Cuenta definitiva de administración",
            "Fondos disponibles",
            "Gestiones pendientes",
        ],
        "nombres_comunes": [
            "Instructivo de Síndicos",
            "Instructivo de Sobreseimientos en Quiebras",
        ],
        "categoria": "Liquidación",
        "doc_numero": "2",
    },
    "2024_INST_1": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/04/RES_NUM_4389_ANO_2024.pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°1 - Instrucciones a Liquidadores que Cesen Anticipadamente en el Cargo, a Liquidadores Suplentes y a Liquidadores que Asuman la Titularidad del Cargo, Conforme al Artículo 38 de la Ley N.° 20.720",
        "resolucion_exenta": "4389",
        "fecha_publicacion": "2024-04-04",
        "materias": [
            "Cese anticipado de liquidadores",
            "Liquidadores suplentes",
            "Liquidador titular",
            "Cuenta final de administración",
            "Entrega de antecedentes y fondos",
            "Denuncia o querella penal",
            "Procedimiento administrativo sancionatorio",
            "Artículo 38 Ley 20.720",
        ],
        "nombres_comunes": [
            "Instructivo de Cese de Liquidadores",
            "Instructivo de Liquidadores Suplentes",
        ],
        "categoria": "Liquidación",
        "doc_numero": "1",
    },
    "2024_MODIF_HONORARIOS": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/02/RES_NUM_2549_ANO_2024.pdf",
        "titulo_completo": "Resolución Modificatoria - Modifica Resolución Exenta N.° 9074 que Fijó el Texto Refundido del Instructivo SUPERIR N.° 1 que Regula el Pago de Honorarios con Cargo al Presupuesto de la Superintendencia",
        "resolucion_exenta": "2549",
        "fecha_publicacion": "2024-02-28",
        "materias": [
            "Pago de honorarios",
            "Presupuesto SUPERIR",
            "Declaraciones juradas",
            "Documentos electrónicos",
            "Firma electrónica avanzada",
            "Ley 21.582 supresión notarios",
            "Modificación instructivo",
        ],
        "nombres_comunes": [
            "Modificación Instructivo Honorarios 2024",
            "Resolución Modificatoria Honorarios",
        ],
        "categoria": "Honorarios",
        "doc_numero": "modif_honorarios_2024",
    },
    "2023_MODIF_HONORARIOS": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/11/RES_NUM_9074_A_O_2023.pdf",
        "titulo_completo": "Resolución que modifica instructivo de pago de honorarios (octubre 2023)",
        "resolucion_exenta": "9074",
        "fecha_publicacion": "2023-11-03",
        "materias": [
            "Pago de honorarios",
            "Modificación",
        ],
        "nombres_comunes": ["Modificación Instructivo Honorarios 2023"],
        "categoria": "Honorarios",
        "doc_numero": "modif_honorarios_2023",
    },
    "2023_INST_HONORARIOS": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/10/RES_NUM_8725_ANO_2023.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°1/2023 - Pago de honorarios con cargo al presupuesto SUPERIR (art. 40)",
        "resolucion_exenta": "8725",
        "fecha_publicacion": "2023-10-24",
        "materias": [
            "Pago de honorarios",
            "Presupuesto SUPERIR",
            "Artículo 40",
        ],
        "nombres_comunes": ["Instructivo de Honorarios"],
        "categoria": "Honorarios",
        "doc_numero": "1",
    },
    # ─── Página 2: 2015-2021 ─────────────────────────────────────────────
    "2021_INST_1_REEMBOLSO": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2021/06/INSTRUCTIVO-SUPERIR-N%C2%B01..pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°1/2021 - Reembolso de gastos de administración en micro y pequeña empresa",
        "resolucion_exenta": "",
        "fecha_publicacion": "2021-06-18",
        "materias": [
            "Reembolso de gastos",
            "Micro y pequeña empresa",
            "Ley 21.354",
        ],
        "nombres_comunes": ["Instructivo de Reembolso MYPE"],
        "categoria": "Liquidación",
        "doc_numero": "1",
    },
    "2020_MODIF_OBLIG": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2020/06/INSTRUCTIVO-SUPERIR-N%C2%B01..pdf",
        "titulo_completo": "INSTRUCTIVO SUPERIR N°1/2020 - Modifica obligaciones generales de sujetos fiscalizados",
        "resolucion_exenta": "",
        "fecha_publicacion": "2020-06-26",
        "materias": [
            "Obligaciones generales",
            "Sujetos fiscalizados",
            "Modificación",
        ],
        "nombres_comunes": ["Modificación Instructivo Obligaciones"],
        "categoria": "Fiscalización",
        "doc_numero": "1",
    },
    "2018_INST_3_HONORARIOS": {
        "url": "https://www.superir.gob.cl/wp-content/document/biblioteca_digital/instructivos/ley-20.720/Instructivo_3.DE.16.11.18.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°3/2018 - Pago de honorarios de liquidadores con cargo al presupuesto",
        "resolucion_exenta": "",
        "fecha_publicacion": "2018-11-16",
        "materias": [
            "Pago de honorarios",
            "Liquidadores",
        ],
        "nombres_comunes": ["Instructivo Honorarios 2018"],
        "categoria": "Honorarios",
        "doc_numero": "3",
    },
    "2018_INST_2_ENAJENACION": {
        "url": "https://www.superir.gob.cl/wp-content/document/biblioteca_digital/instructivos/ley-20.720/Instructivo_2.DE.20.06.18.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°2/2018 - Enajenación de activos en procedimientos concursales",
        "resolucion_exenta": "",
        "fecha_publicacion": "2018-06-20",
        "materias": [
            "Enajenación de activos",
            "Procedimientos concursales",
        ],
        "nombres_comunes": ["Instructivo de Enajenación"],
        "categoria": "Liquidación",
        "doc_numero": "2",
    },
    "2018_INST_1_HONORARIOS": {
        "url": "https://www.superir.gob.cl/wp-content/document/biblioteca_digital/instructivos/ley-20.720/Instructivo_1_15.01.18.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°1/2018 - Modificación del pago de honorarios de liquidadores",
        "resolucion_exenta": "",
        "fecha_publicacion": "2018-01-15",
        "materias": [
            "Pago de honorarios",
            "Modificación",
            "Liquidadores",
        ],
        "nombres_comunes": ["Instructivo Honorarios 2018 v1"],
        "categoria": "Honorarios",
        "doc_numero": "1",
    },
    "2016_INST_2_INSUF_BIENES": {
        "url": "https://www.superir.gob.cl/wp-content/document/biblioteca_digital/instructivos/ley-20.720/Instructivo_2_02.11.16.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°2/2016 - Concepto de insuficiencia de bienes (art. 267)",
        "resolucion_exenta": "",
        "fecha_publicacion": "2016-11-02",
        "materias": [
            "Insuficiencia de bienes",
            "Artículo 267",
        ],
        "nombres_comunes": ["Instructivo de Insuficiencia de Bienes"],
        "categoria": "Liquidación",
        "doc_numero": "2",
    },
    "2016_INST_1_TRANSFRONTERIZO": {
        "url": "https://www.superir.gob.cl/wp-content/document/biblioteca_digital/instructivos/ley-20.720/Instructivo_1_06.07.16.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°1/2016 - Procedimiento de insolvencia transfronteriza",
        "resolucion_exenta": "",
        "fecha_publicacion": "2016-07-06",
        "materias": [
            "Insolvencia transfronteriza",
            "Procedimiento internacional",
        ],
        "nombres_comunes": ["Instructivo de Insolvencia Transfronteriza"],
        "categoria": "Internacional",
        "doc_numero": "1",
    },
    "2015_INST_3_CREDITOS": {
        "url": "https://www.superir.gob.cl/wp-content/document/biblioteca_digital/instructivos/ley-20.720/instructivo_3_v2.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°3/2015 - Prelación de créditos, actualización y reparto de fondos",
        "resolucion_exenta": "",
        "fecha_publicacion": "2015-10-06",
        "materias": [
            "Prelación de créditos",
            "Actualización",
            "Reparto de fondos",
        ],
        "nombres_comunes": ["Instructivo de Prelación de Créditos"],
        "categoria": "Liquidación",
        "doc_numero": "3",
    },
    "2015_INST_2_CONTABLE": {
        "url": "https://www.superir.gob.cl/wp-content/document/biblioteca_digital/instructivos/ley-20.720/instructivo_2_v2.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°2/2015 - Aspectos contables y financieros de administración concursal",
        "resolucion_exenta": "",
        "fecha_publicacion": "2015-10-06",
        "materias": [
            "Aspectos contables",
            "Administración concursal",
            "Aspectos financieros",
        ],
        "nombres_comunes": ["Instructivo Contable Concursal"],
        "categoria": "Contabilidad",
        "doc_numero": "2",
    },
    "2015_INST_1_OBLIGACIONES": {
        "url": "https://www.superir.gob.cl/wp-content/document/biblioteca_digital/instructivos/ley-20.720/instructivo_1_v2.pdf",
        "titulo_completo": "INSTRUCTIVO SIR N°1/2015 - Obligaciones generales y especiales de sujetos fiscalizados",
        "resolucion_exenta": "",
        "fecha_publicacion": "2015-10-06",
        "materias": [
            "Obligaciones generales",
            "Obligaciones especiales",
            "Sujetos fiscalizados",
        ],
        "nombres_comunes": ["Instructivo de Obligaciones"],
        "categoria": "Fiscalización",
        "doc_numero": "1",
    },
}


def markdown_to_plain_text(md_text: str) -> str:
    """Convierte markdown de instructivo a texto plano para el parser.

    Elimina formato markdown preservando la estructura textual que
    el parser SUPERIR necesita (VISTOS, CONSIDERANDO, RESUELVO,
    Título, Artículo, etc.).
    """
    lines = md_text.split("\n")
    result: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Eliminar separadores horizontales
        if re.match(r"^-{3,}$", stripped):
            continue

        # Eliminar blockquotes (notas al pie) - quitar solo el marcador ">"
        if stripped.startswith("> "):
            stripped = stripped[2:]

        # Headers markdown → texto plano (sin #)
        header_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if header_match:
            stripped = header_match.group(2).strip()
            # Limpiar guion decorativo en títulos: "Título I - Nombre" → "Título I Nombre"
            stripped = re.sub(r"^(T[ií]tulo\s+[IVXLCDM]+)\s*-\s*", r"\1 ", stripped)
            stripped = re.sub(
                r"^(Párrafo\s+[IVXLCDM]+)\s*-\s*", r"\1 ", stripped, flags=re.IGNORECASE
            )

        # Eliminar bold markers **texto**
        stripped = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)

        # Eliminar italic markers *texto*
        stripped = re.sub(r"\*(.+?)\*", r'"\1"', stripped)

        # Quitar items markdown con guion "- item" → "item"
        if re.match(r"^- ", stripped):
            stripped = stripped[2:]

        result.append(stripped)

    return "\n".join(result)


def setup_logging(verbose: bool = False) -> None:
    """Configura logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def process_single_instructivo(
    inst_id: str,
    info: dict[str, Any],
    extractor: PDFTextExtractor,
    parser: InstructivoParser,
    generator: LawXMLGenerator,
    output_dir: Path,
    text_output_dir: Path | None = None,
    text_only: bool = False,
    text_override_dir: Path | None = None,
) -> bool:
    """Procesa un Instructivo individual.

    Args:
        text_override_dir: Directorio con archivos .md o .txt de texto
            limpio. Si existe un archivo {inst_id}.md o {inst_id}.txt,
            se usa en lugar de descargar y extraer el PDF.

    Returns:
        True si fue exitoso, False si falló.
    """
    url = info["url"]
    log = logging.getLogger("process_instructivos")

    try:
        log.info(f"{'='*60}")
        log.info(f"Procesando: {inst_id}")
        log.info(f"URL: {url}")

        # Intentar usar texto override (limpio, corregido manualmente)
        texto = None
        if text_override_dir:
            for ext in (".md", ".txt"):
                override_path = text_override_dir / f"{inst_id}{ext}"
                if override_path.exists():
                    raw = override_path.read_text(encoding="utf-8")
                    if ext == ".md":
                        texto = markdown_to_plain_text(raw)
                    else:
                        texto = raw
                    log.info(f"Usando texto override: {override_path}")
                    break

        # Fallback: descargar PDF y extraer texto
        if texto is None:
            texto, pdf_path = extractor.download_and_extract(url)

        if text_output_dir:
            text_path = text_output_dir / f"{inst_id}.txt"
            text_path.write_text(texto, encoding="utf-8")
            log.info(f"Texto guardado: {text_path}")

        if text_only:
            log.info(f"{inst_id}: texto extraído ({len(texto):,} chars)")
            return True

        doc_numero = info.get("doc_numero", "")
        norma = parser.parse(texto, url=url, doc_numero=doc_numero, catalog_entry=info)

        # Usar el ID como nombre de archivo
        safe_id = inst_id.replace("/", "_")
        xml_path = generator.generate(norma, str(output_dir), f"INST_{safe_id}")

        log.info(f"XML generado: {xml_path} ({xml_path.stat().st_size:,} bytes)")
        return True

    except PDFExtractionError as e:
        log.error(f"{inst_id}: Error de extracción PDF - {e}")
        return False
    except Exception as e:
        log.error(f"{inst_id}: Error inesperado - {e}")
        log.debug("Detalle:", exc_info=True)
        return False


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal."""
    arg_parser = argparse.ArgumentParser(
        description="Procesar Instructivos de la SUPERIR: PDF → texto → XML"
    )
    arg_parser.add_argument(
        "--id",
        nargs="+",
        help="IDs de instructivos a procesar. Si no se especifica, procesa todos.",
    )
    arg_parser.add_argument(
        "--output",
        "-o",
        default="biblioteca_xml/organismos/SUPERIR/Instructivo",
        help="Directorio de salida para XMLs",
    )
    arg_parser.add_argument(
        "--pdf-cache",
        default=".pdf_cache",
        help="Directorio para cachear PDFs descargados (default: .pdf_cache)",
    )
    arg_parser.add_argument(
        "--text-only",
        action="store_true",
        help="Solo extraer texto (no generar XML)",
    )
    arg_parser.add_argument(
        "--save-text",
        action="store_true",
        help="Guardar también el texto extraído en archivos .txt",
    )
    arg_parser.add_argument(
        "--text-override-dir",
        default="biblioteca_xml/organismos/SUPERIR/Instructivo/texto_override",
        help=(
            "Directorio con archivos .md/.txt de texto limpio. "
            "Si existe {id}.md o {id}.txt, se usa en vez del PDF."
        ),
    )
    arg_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Logging detallado",
    )

    args = arg_parser.parse_args(argv)
    setup_logging(args.verbose)
    log = logging.getLogger("process_instructivos")

    # Determinar qué instructivos procesar
    if args.id:
        to_process = {i: INSTRUCTIVO_CATALOG[i] for i in args.id if i in INSTRUCTIVO_CATALOG}
        missing = [i for i in args.id if i not in INSTRUCTIVO_CATALOG]
        if missing:
            log.warning(f"IDs no encontrados en catálogo: {missing}")
    else:
        to_process = INSTRUCTIVO_CATALOG

    if not to_process:
        log.error("No hay instructivos para procesar.")
        return 1

    # Crear directorios
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    text_output_dir = None
    if args.save_text or args.text_only:
        text_output_dir = output_dir / "texto"
        text_output_dir.mkdir(parents=True, exist_ok=True)

    # Directorio de text overrides (texto limpio corregido manualmente)
    text_override_dir = Path(args.text_override_dir)
    if text_override_dir.exists():
        overrides = list(text_override_dir.glob("*.md")) + list(text_override_dir.glob("*.txt"))
        if overrides:
            log.info(f"Text overrides encontrados: {len(overrides)} archivos en {text_override_dir}")

    # Inicializar componentes
    extractor = PDFTextExtractor(cache_dir=args.pdf_cache)
    parser = InstructivoParser()
    generator = LawXMLGenerator()

    # Procesar
    log.info(f"Procesando {len(to_process)} Instructivos de la SUPERIR")
    log.info(f"Salida: {output_dir.absolute()}")

    exitosas = 0
    fallidas = 0
    errores: list[str] = []

    for inst_id, info in to_process.items():
        ok = process_single_instructivo(
            inst_id=inst_id,
            info=info,
            extractor=extractor,
            parser=parser,
            generator=generator,
            output_dir=output_dir,
            text_output_dir=text_output_dir,
            text_only=args.text_only,
            text_override_dir=text_override_dir if text_override_dir.exists() else None,
        )
        if ok:
            exitosas += 1
        else:
            fallidas += 1
            errores.append(inst_id)

    # Resumen
    log.info(f"\n{'='*60}")
    log.info(f"RESUMEN: {exitosas} exitosas, {fallidas} fallidas de {len(to_process)}")
    if errores:
        log.info(f"Con error: {', '.join(errores)}")
    log.info(f"Archivos en: {output_dir.absolute()}")

    return 1 if fallidas > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
