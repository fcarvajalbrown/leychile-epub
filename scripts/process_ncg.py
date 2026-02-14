#!/usr/bin/env python3
"""
Procesamiento batch de Normas de Carácter General (NCG) de la SUPERIR.

Descarga los PDFs, extrae texto, parsea la estructura y genera
archivos XML compatibles con el esquema ley_v1.xsd o superir_v1.xsd.

Uso:
    python scripts/process_ncg.py                           # Procesar todas (ley_v1)
    python scripts/process_ncg.py --ncg 28 27 26            # NCGs específicas
    python scripts/process_ncg.py --schema superir_v1       # Usar schema SUPERIR
    python scripts/process_ncg.py --ncg 4 6 7 --schema superir_v1  # SUPERIR para NCGs 4/6/7
    python scripts/process_ncg.py --output ./mi_dir         # Directorio personalizado
    python scripts/process_ncg.py --text-only               # Solo extraer texto

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from leychile_epub.ncg_parser import NCGParser
from leychile_epub.pdf_extractor import PDFExtractionError, PDFTextExtractor
from leychile_epub.superir_structured_parser import SuperirStructuredParser
from leychile_epub.superir_xml_generator import SuperirXMLGenerator
from leychile_epub.xml_generator import LawXMLGenerator

# ═══════════════════════════════════════════════════════════════════════════════
# CATÁLOGO ENRIQUECIDO DE NCGs
# ═══════════════════════════════════════════════════════════════════════════════

NCG_CATALOG: dict[str, dict[str, Any]] = {
    "28": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2025/12/RES_NUM_22802_AO_2025.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°28 - Procedimiento simplificado de renegociación de personas deudoras",
        "resolucion_exenta": "22802",
        "anio_resolucion": "2025",
        "fecha_publicacion": "2025-11-19",
        "materias": [
            "Renegociación",
            "Procedimiento simplificado",
            "Personas deudoras",
        ],
        "leyes_habilitantes": ["20720", "21563"],
        "deroga": ["21"],
        "modifica": [],
        "nombres_comunes": ["NCG de Renegociación Simplificada"],
        "categoria": "Renegociación",
    },
    "27": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/10/RES_NUM_13003_A_O_2024.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°27 - Cuenta definitiva de administración en procedimiento concursal de liquidación",
        "resolucion_exenta": "13003",
        "anio_resolucion": "2024",
        "fecha_publicacion": "2024-09-04",
        "materias": [
            "Cuenta definitiva",
            "Liquidación",
            "Administración concursal",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Cuenta Definitiva"],
        "categoria": "Liquidación",
    },
    "26": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2024/05/RES_NUM_6048_ANO_2024.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°26 - Requisitos para liquidación voluntaria de personas deudoras",
        "resolucion_exenta": "6048",
        "anio_resolucion": "2024",
        "fecha_publicacion": "2024-04-16",
        "materias": [
            "Liquidación voluntaria",
            "Requisitos",
            "Personas deudoras",
        ],
        "leyes_habilitantes": ["20720", "21563"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Liquidación Voluntaria"],
        "categoria": "Liquidación",
    },
    "25": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/10/RES_NUM_8322_ANO_2023.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°25 - Uso de medios electrónicos en procedimientos concursales",
        "resolucion_exenta": "8322",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-10-11",
        "materias": [
            "Medios electrónicos",
            "Procedimientos concursales",
            "Firma electrónica",
        ],
        "leyes_habilitantes": ["20720", "19799"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Medios Electrónicos"],
        "categoria": "Electrónico",
    },
    "24": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6616_ANO_2023.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°24 - Certificación de deuda en procedimiento de reorganización",
        "resolucion_exenta": "6616",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Certificación de deuda",
            "Reorganización",
            "Declaración jurada",
        ],
        "leyes_habilitantes": ["20720", "21563"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Certificación de Deuda"],
        "categoria": "Reorganización",
    },
    "23": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6624_ANO_2023.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°23 - Indicadores de desempeño de veedores y liquidadores",
        "resolucion_exenta": "6624",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Indicadores de desempeño",
            "Veedores",
            "Liquidadores",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Indicadores de Desempeño"],
        "categoria": "Desempeño",
    },
    "22": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6619_ANO_2023.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°22 - Plataforma electrónica para enajenación de activos en liquidación",
        "resolucion_exenta": "6619",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Plataforma electrónica",
            "Enajenación de activos",
            "Liquidación",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Enajenación de Activos"],
        "categoria": "Liquidación",
    },
    "20": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6617_ANO_2023.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°20 - Procedimiento de objeciones e impugnaciones de créditos",
        "resolucion_exenta": "6617",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Objeciones",
            "Impugnaciones de créditos",
            "Procedimiento concursal",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Objeciones de Créditos"],
        "categoria": "Objeciones",
    },
    "19": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6600_ANO_2023_NCG_19_CERT_DJ_REORG.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°19 - Certificación y declaración jurada en procedimiento de reorganización",
        "resolucion_exenta": "6600",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Certificación",
            "Declaración jurada",
            "Reorganización",
        ],
        "leyes_habilitantes": ["20720", "21563"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Certificación DJ Reorganización"],
        "categoria": "Reorganización",
    },
    "18": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6599_ANO_2023_NCG_18_CUENTA.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°18 - Objeción de la cuenta final de administración",
        "resolucion_exenta": "6599",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Objeción cuenta final",
            "Cuenta final de administración",
            "Liquidación",
        ],
        "leyes_habilitantes": ["20720", "21563"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Objeción Cuenta Final"],
        "categoria": "Liquidación",
    },
    "17": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6595_ANO_2023_NCG_17_NOMINACION.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°17 - Nominación y designación aleatoria de veedores y liquidadores",
        "resolucion_exenta": "6595",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Nominación",
            "Designación aleatoria",
            "Veedores y liquidadores",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Nominación Aleatoria"],
        "categoria": "Nominación",
    },
    "16": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6596_ANO_2023_NCG_16_EXAMENES.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°16 - Exámenes de conocimiento para veedores y liquidadores",
        "resolucion_exenta": "6596",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Exámenes de conocimiento",
            "Veedores",
            "Liquidadores",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Exámenes de Conocimiento"],
        "categoria": "Exámenes",
    },
    "15": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6598_ANO_2023_NCG_15_JUNTAS.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°15 - Juntas de acreedores mediante medios tecnológicos",
        "resolucion_exenta": "6598",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Juntas de acreedores",
            "Medios tecnológicos",
            "Sesiones remotas",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Juntas Remotas"],
        "categoria": "Juntas",
    },
    "14": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2023/08/RES_NUM_6597_ANO_2023_NCG_14_PUBLICACION.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°14 - Formalidades de las publicaciones en procedimientos concursales",
        "resolucion_exenta": "6597",
        "anio_resolucion": "2023",
        "fecha_publicacion": "2023-08-11",
        "materias": [
            "Publicaciones",
            "Formalidades",
            "Procedimientos concursales",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Publicaciones"],
        "categoria": "Publicación",
    },
    "10": {
        "url": "https://www.superir.gob.cl/wp-content/uploads/2020/01/NORMA-N%C2%B010.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°10 - Modifica NCG N°1 sobre garantía de fiel desempeño",
        "resolucion_exenta": "",
        "anio_resolucion": "2019",
        "fecha_publicacion": "2019-12-31",
        "materias": [
            "Garantía de fiel desempeño",
            "Modificación NCG N°1",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": ["1"],
        "nombres_comunes": ["NCG de Garantía de Desempeño (modificada)"],
        "categoria": "Garantía",
    },
    "7": {
        "url": "https://www.superir.gob.cl/wp-content/document/normas/NCG_N7_Contenidos_Obligatorios.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°7 - Forma y contenidos obligatorios de las cuentas provisorias y de la Cuenta Final de Administración",
        "resolucion_exenta": "",
        "anio_resolucion": "2014",
        "materias": [
            "Cuentas provisorias",
            "Cuenta Final de Administración",
            "Liquidación",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Cuentas de Administración"],
        "categoria": "Liquidación",
    },
    "6": {
        "url": "https://www.superir.gob.cl/wp-content/document/normas/NCG_N6_Forma_de_Otorgar.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°6 - Forma de otorgar la garantía para asegurar los pagos de acreedores de primera clase",
        "resolucion_exenta": "",
        "anio_resolucion": "2014",
        "materias": [
            "Garantía",
            "Acreedores de primera clase",
            "Procedimientos concursales",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Garantías"],
        "categoria": "Procedimiento",
    },
    "4": {
        "url": "https://www.superir.gob.cl/wp-content/document/normas/NCG_N4_Modelo_Solicitud.pdf",
        "titulo_completo": "NORMA DE CARÁCTER GENERAL N°4 - Modelo de solicitud de procedimiento concursal de reorganización",
        "resolucion_exenta": "",
        "anio_resolucion": "2014",
        "materias": [
            "Modelo de solicitud",
            "Reorganización",
        ],
        "leyes_habilitantes": ["20720"],
        "deroga": [],
        "modifica": [],
        "nombres_comunes": ["NCG de Solicitud de Reorganización"],
        "categoria": "Reorganización",
    },
}


def setup_logging(verbose: bool = False) -> None:
    """Configura logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _find_text_file(ncg_num: str) -> Path | None:
    """Busca archivo de texto pre-existente para una NCG.

    Busca en biblioteca_xml/organismos/SUPERIR/NCG/texto/NCG_{num}.txt
    """
    candidates = [
        Path("biblioteca_xml/organismos/SUPERIR/NCG/texto") / f"NCG_{ncg_num}.txt",
    ]
    for p in candidates:
        if p.exists() and p.stat().st_size > 100:
            return p
    return None


def process_single_ncg(
    ncg_num: str,
    info: dict[str, Any],
    extractor: PDFTextExtractor,
    parser: NCGParser,
    generator: LawXMLGenerator,
    output_dir: Path,
    text_output_dir: Path | None = None,
    text_only: bool = False,
) -> bool:
    """Procesa una NCG individual.

    Returns:
        True si fue exitoso, False si falló.
    """
    url = info["url"]
    log = logging.getLogger("process_ncg")

    try:
        log.info(f"{'='*60}")
        log.info(f"Procesando NCG N°{ncg_num}")
        log.info(f"URL: {url}")

        # Primero buscar texto pre-existente (transcripciones manuales)
        text_file = _find_text_file(ncg_num)
        if text_file:
            texto = text_file.read_text(encoding="utf-8")
            log.info(f"Usando texto pre-existente: {text_file} ({len(texto):,} chars)")
        else:
            texto, pdf_path = extractor.download_and_extract(url)

        if text_output_dir:
            text_path = text_output_dir / f"NCG_{ncg_num}.txt"
            text_path.write_text(texto, encoding="utf-8")
            log.info(f"Texto guardado: {text_path}")

        if text_only:
            log.info(f"NCG N°{ncg_num}: texto extraído ({len(texto):,} chars)")
            return True

        norma = parser.parse(texto, url=url, ncg_numero=ncg_num, catalog_entry=info)

        xml_path = generator.generate(norma, str(output_dir), f"NCG_{ncg_num}")

        log.info(f"XML generado: {xml_path} ({xml_path.stat().st_size:,} bytes)")
        return True

    except PDFExtractionError as e:
        log.error(f"NCG N°{ncg_num}: Error de extracción PDF - {e}")
        return False
    except Exception as e:
        log.error(f"NCG N°{ncg_num}: Error inesperado - {e}")
        log.debug("Detalle:", exc_info=True)
        return False


def process_single_ncg_superir(
    ncg_num: str,
    info: dict[str, Any],
    extractor: PDFTextExtractor,
    parser: SuperirStructuredParser,
    generator: SuperirXMLGenerator,
    output_dir: Path,
    text_output_dir: Path | None = None,
    text_only: bool = False,
) -> bool:
    """Procesa una NCG con pipeline SUPERIR (superir_v1.xsd).

    Returns:
        True si fue exitoso, False si falló.
    """
    url = info["url"]
    log = logging.getLogger("process_ncg")

    try:
        log.info(f"{'='*60}")
        log.info(f"Procesando NCG N°{ncg_num} [schema: superir_v1]")
        log.info(f"URL: {url}")

        # Buscar texto pre-existente
        text_file = _find_text_file(ncg_num)
        if text_file:
            texto = text_file.read_text(encoding="utf-8")
            log.info(f"Usando texto pre-existente: {text_file} ({len(texto):,} chars)")
        else:
            texto, pdf_path = extractor.download_and_extract(url)

        if text_output_dir:
            text_path = text_output_dir / f"NCG_{ncg_num}.txt"
            text_path.write_text(texto, encoding="utf-8")
            log.info(f"Texto guardado: {text_path}")

        if text_only:
            log.info(f"NCG N°{ncg_num}: texto extraído ({len(texto):,} chars)")
            return True

        # Pipeline SUPERIR: parse → NormaSuperir → XML superir_v1.xsd
        norma_superir = parser.parse(texto, url=url, doc_numero=ncg_num, catalog_entry=info)

        xml_str = generator.generate(norma_superir)

        # Guardar XML
        xml_filename = f"NCG_{ncg_num}_superir.xml"
        xml_path = output_dir / xml_filename
        xml_path.write_text(xml_str, encoding="utf-8")

        log.info(f"XML generado: {xml_path} ({xml_path.stat().st_size:,} bytes)")
        return True

    except PDFExtractionError as e:
        log.error(f"NCG N°{ncg_num}: Error de extracción PDF - {e}")
        return False
    except Exception as e:
        log.error(f"NCG N°{ncg_num}: Error inesperado - {e}")
        log.debug("Detalle:", exc_info=True)
        return False


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal."""
    arg_parser = argparse.ArgumentParser(
        description="Procesar NCGs de la SUPERIR: PDF → texto → XML"
    )
    arg_parser.add_argument(
        "--ncg",
        nargs="+",
        help="Números de NCG a procesar (ej: 28 27 26). Si no se especifica, procesa todas.",
    )
    arg_parser.add_argument(
        "--output",
        "-o",
        default="biblioteca_xml/organismos/SUPERIR/NCG",
        help="Directorio de salida para XMLs (default: biblioteca_xml/organismos/SUPERIR/NCG)",
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
        "--schema",
        choices=["ley_v1", "superir_v1"],
        default="ley_v1",
        help="Schema XSD a usar: ley_v1 (default) o superir_v1 (semántica SUPERIR)",
    )
    arg_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Logging detallado",
    )

    args = arg_parser.parse_args(argv)
    setup_logging(args.verbose)
    log = logging.getLogger("process_ncg")

    # Determinar qué NCGs procesar
    if args.ncg:
        ncgs_to_process = {n: NCG_CATALOG[n] for n in args.ncg if n in NCG_CATALOG}
        missing = [n for n in args.ncg if n not in NCG_CATALOG]
        if missing:
            log.warning(f"NCGs no encontradas en catálogo: {missing}")
    else:
        ncgs_to_process = NCG_CATALOG

    if not ncgs_to_process:
        log.error("No hay NCGs para procesar.")
        return 1

    # Crear directorios
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    text_output_dir = None
    if args.save_text or args.text_only:
        text_output_dir = output_dir / "texto"
        text_output_dir.mkdir(parents=True, exist_ok=True)

    # Inicializar componentes
    extractor = PDFTextExtractor(cache_dir=args.pdf_cache)
    use_superir = args.schema == "superir_v1"

    if use_superir:
        superir_parser = SuperirStructuredParser()
        superir_generator = SuperirXMLGenerator()
        log.info(f"Procesando {len(ncgs_to_process)} NCGs [schema: superir_v1.xsd]")
    else:
        ncg_parser = NCGParser()
        ley_generator = LawXMLGenerator()
        log.info(f"Procesando {len(ncgs_to_process)} NCGs [schema: ley_v1.xsd]")

    log.info(f"Salida: {output_dir.absolute()}")

    exitosas = 0
    fallidas = 0
    errores: list[str] = []

    for ncg_num, info in sorted(ncgs_to_process.items(), key=lambda x: int(x[0])):
        if use_superir:
            ok = process_single_ncg_superir(
                ncg_num=ncg_num,
                info=info,
                extractor=extractor,
                parser=superir_parser,
                generator=superir_generator,
                output_dir=output_dir,
                text_output_dir=text_output_dir,
                text_only=args.text_only,
            )
        else:
            ok = process_single_ncg(
                ncg_num=ncg_num,
                info=info,
                extractor=extractor,
                parser=ncg_parser,
                generator=ley_generator,
                output_dir=output_dir,
                text_output_dir=text_output_dir,
                text_only=args.text_only,
            )
        if ok:
            exitosas += 1
        else:
            fallidas += 1
            errores.append(ncg_num)

    # Resumen
    log.info(f"\n{'='*60}")
    log.info(f"RESUMEN: {exitosas} exitosas, {fallidas} fallidas de {len(ncgs_to_process)}")
    if errores:
        log.info(f"NCGs con error: {', '.join(errores)}")
    log.info(f"Archivos en: {output_dir.absolute()}")

    return 1 if fallidas > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
