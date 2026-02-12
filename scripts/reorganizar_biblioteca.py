#!/usr/bin/env python3
"""
Reorganiza la estructura de carpetas de biblioteca_xml/.

Mueve los archivos XML existentes a una estructura organizada
por tipo de norma e institución emisora.

Estructura final:
  biblioteca_xml/
    leyes/              # Leyes nacionales
    codigos/            # Códigos (Civil, Penal, etc.)
    decretos/           # Decretos, DL, DFL
    auto_acordados/     # Autos acordados
    constitucion/       # Constitución
    organismos/
      SUPERIR/
        NCG/            # Normas de Carácter General
        Instructivo/    # Instructivos

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import logging
import shutil
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("reorganizar")

# Mapeo de tipo XML → carpeta destino
TIPO_TO_DIR: dict[str, str] = {
    "Ley": "leyes",
    "Decreto": "decretos",
    "Decreto Ley": "decretos",
    "Decreto con Fuerza de Ley": "decretos",
    "Código": "codigos",
    "Reglamento": "decretos",
    "Resolución": "decretos",
    "Auto Acordado": "auto_acordados",
    "Constitución": "constitucion",
    "Tratado Internacional": "leyes",
    "Norma de Carácter General": "organismos/SUPERIR/NCG",
    "Instructivo": "organismos/SUPERIR/Instructivo",
}

# Namespace del XML
NS = "https://leychile.cl/schema/ley/v1"


def classify_xml(xml_path: Path) -> str:
    """Clasifica un XML en la carpeta destino correcta.

    Usa una combinación de nombre de archivo y metadatos XML.
    Prioriza el nombre de archivo para códigos y constitución,
    ya que su tipo legal puede diferir del nombre común.
    """
    name = xml_path.stem.lower()

    # 1. Clasificación por nombre de archivo (override)
    if name == "constitucion":
        return "constitucion"
    if name.startswith("codigo_"):
        return "codigos"
    if name == "indice":
        return ""  # Skip index files
    if name.startswith("ncg_"):
        # NCGs de la CMF u otros organismos → carpeta general
        return "organismos/CMF/NCG"

    # 2. Clasificación por tipo XML
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        tipo = root.get("tipo", "")
    except ET.ParseError:
        logger.warning(f"No se pudo parsear: {xml_path}")
        return ""

    return TIPO_TO_DIR.get(tipo, "")


def reorganize(base_dir: Path, dry_run: bool = False) -> None:
    """Reorganiza los XMLs en la estructura por tipo.

    Args:
        base_dir: Directorio base (biblioteca_xml/).
        dry_run: Si True, solo muestra qué haría sin mover archivos.
    """
    # Encontrar todos los XML en el directorio raíz (no en subdirectorios ya organizados)
    xml_files = list(base_dir.glob("*.xml"))
    logger.info(f"Encontrados {len(xml_files)} archivos XML en {base_dir}")

    # Crear subdirectorios
    if not dry_run:
        all_dirs = set(TIPO_TO_DIR.values()) | {"organismos/CMF/NCG"}
        for subdir in all_dirs:
            (base_dir / subdir).mkdir(parents=True, exist_ok=True)

    moved = 0
    skipped = 0

    for xml_path in sorted(xml_files):
        target_dir = classify_xml(xml_path)
        if not target_dir:
            logger.warning(f"  Sin clasificación: {xml_path.name}")
            skipped += 1
            continue

        target_path = base_dir / target_dir / xml_path.name

        if dry_run:
            logger.info(f"  [DRY] {xml_path.name} → {target_dir}/")
        else:
            shutil.move(str(xml_path), str(target_path))
            logger.info(f"  {xml_path.name} → {target_dir}/")
        moved += 1

    logger.info(f"\nMovidos: {moved}, Omitidos: {skipped}")


def migrate_ncg(base_dir: Path, ncg_dir: Path, dry_run: bool = False) -> None:
    """Mueve NCGs generadas de normas_ncg/ a la nueva estructura."""
    if not ncg_dir.exists():
        logger.info(f"No existe {ncg_dir}, omitiendo migración NCG")
        return

    target = base_dir / "organismos" / "SUPERIR" / "NCG"
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    ncg_xmls = list(ncg_dir.glob("NCG_*.xml"))
    logger.info(f"Migrando {len(ncg_xmls)} NCGs de {ncg_dir} → {target}")

    for xml_path in sorted(ncg_xmls):
        target_path = target / xml_path.name
        if dry_run:
            logger.info(f"  [DRY] {xml_path.name}")
        else:
            shutil.copy2(str(xml_path), str(target_path))
            logger.info(f"  {xml_path.name}")


def main() -> int:
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Reorganizar biblioteca XML")
    parser.add_argument(
        "--base-dir",
        default="biblioteca_xml",
        help="Directorio base de la biblioteca (default: biblioteca_xml)",
    )
    parser.add_argument(
        "--ncg-dir",
        default="biblioteca_xml/organismos/SUPERIR/NCG",
        help="Directorio con NCGs (default: biblioteca_xml/organismos/SUPERIR/NCG)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo mostrar cambios sin ejecutar",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir)
    ncg_dir = Path(args.ncg_dir)

    if not base_dir.exists():
        logger.error(f"No existe {base_dir}")
        return 1

    # 1. Reorganizar XMLs existentes por tipo
    logger.info("=" * 60)
    logger.info("FASE 1: Reorganizar XMLs existentes por tipo")
    logger.info("=" * 60)
    reorganize(base_dir, dry_run=args.dry_run)

    # 2. Migrar NCGs
    logger.info("\n" + "=" * 60)
    logger.info("FASE 2: Migrar NCGs generadas")
    logger.info("=" * 60)
    migrate_ncg(base_dir, ncg_dir, dry_run=args.dry_run)

    # 3. Resumen
    if not args.dry_run:
        logger.info("\n" + "=" * 60)
        logger.info("Estructura final:")
        for subdir in sorted(set(TIPO_TO_DIR.values())):
            dir_path = base_dir / subdir
            if dir_path.exists():
                count = len(list(dir_path.glob("*.xml")))
                if count > 0:
                    logger.info(f"  {subdir}/: {count} archivos")

    return 0


if __name__ == "__main__":
    sys.exit(main())
