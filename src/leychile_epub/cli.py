"""
Interfaz de línea de comandos para LeyChile ePub Generator.

Uso:
    python -m leychile_epub https://www.leychile.cl/Navegar?idNorma=242302
    python -m leychile_epub --batch urls.txt -o ./output

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import BCNLawScraper, Config, LawEpubGenerator, __version__
from .exceptions import LeyChileError


def create_parser() -> argparse.ArgumentParser:
    """Crea el parser de argumentos.

    Returns:
        Parser configurado.
    """
    parser = argparse.ArgumentParser(
        prog="leychile-epub",
        description="🇨🇱 Generador de ePub para legislación chilena",
        epilog="Ejemplo: %(prog)s https://www.leychile.cl/Navegar?idNorma=242302",
    )

    parser.add_argument(
        "url",
        nargs="?",
        help="URL de LeyChile a convertir",
    )

    parser.add_argument(
        "-b",
        "--batch",
        metavar="FILE",
        help="Archivo con lista de URLs (una por línea)",
    )

    parser.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        default=".",
        help="Directorio de salida (default: directorio actual)",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Modo silencioso (sin output en consola)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Modo verbose (más información)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def print_progress(progress: float, message: str) -> None:
    """Imprime el progreso en la consola.

    Args:
        progress: Progreso de 0 a 1.
        message: Mensaje a mostrar.
    """
    bar_width = 30
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)
    percent = int(progress * 100)
    print(f"\r[{bar}] {percent}% - {message}", end="", flush=True)
    if progress >= 1:
        print()


def process_url(
    url: str,
    output_dir: str,
    quiet: bool = False,
    verbose: bool = False,
) -> Optional[str]:
    """Procesa una URL y genera el ePub.

    Args:
        url: URL de LeyChile.
        output_dir: Directorio de salida.
        quiet: Modo silencioso.
        verbose: Modo verbose.

    Returns:
        Ruta al ePub generado o None si hubo error.
    """
    scraper = BCNLawScraper()
    generator = LawEpubGenerator()

    callback = None if quiet else print_progress

    try:
        if not quiet:
            print(f"\n📚 Procesando: {url}")

        # Scraping
        if verbose and not quiet:
            print("  → Extrayendo datos de la BCN...")

        law_data = scraper.scrape_law(url, progress_callback=callback if not verbose else None)

        if not law_data:
            if not quiet:
                print("  ❌ No se pudo obtener datos de la ley")
            return None

        title = law_data.get("metadata", {}).get("title", "Desconocido")
        if verbose and not quiet:
            print(f"  → Ley encontrada: {title}")

        # Generación
        if verbose and not quiet:
            print("  → Generando ePub...")

        epub_path = generator.generate(
            law_data,
            output_dir=output_dir,
            progress_callback=callback if not verbose else None,
        )

        if not quiet:
            print(f"  ✅ Generado: {epub_path}")

        return epub_path

    except LeyChileError as e:
        if not quiet:
            print(f"  ❌ Error: {e.message}")
        return None
    except Exception as e:
        if not quiet:
            print(f"  ❌ Error inesperado: {e}")
        return None


def process_batch(
    batch_file: str,
    output_dir: str,
    quiet: bool = False,
    verbose: bool = False,
) -> tuple[int, int]:
    """Procesa un archivo con múltiples URLs.

    Args:
        batch_file: Ruta al archivo con URLs.
        output_dir: Directorio de salida.
        quiet: Modo silencioso.
        verbose: Modo verbose.

    Returns:
        Tupla (exitosos, fallidos).
    """
    path = Path(batch_file)

    if not path.exists():
        print(f"❌ Archivo no encontrado: {batch_file}")
        return 0, 0

    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    if not urls:
        print("❌ No se encontraron URLs en el archivo")
        return 0, 0

    if not quiet:
        print(f"\n📋 Procesando {len(urls)} URLs...")

    success = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        if not quiet:
            print(f"\n[{i}/{len(urls)}]", end="")

        result = process_url(url, output_dir, quiet, verbose)

        if result:
            success += 1
        else:
            failed += 1

    return success, failed


def main(argv: Optional[List[str]] = None) -> int:
    """Función principal del CLI.

    Args:
        argv: Argumentos de línea de comandos (opcional).

    Returns:
        Código de salida (0 = éxito, 1 = error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Validar argumentos
    if not args.url and not args.batch:
        parser.print_help()
        return 1

    # Crear directorio de salida
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        print("=" * 50)
        print("🇨🇱 LeyChile ePub Generator")
        print(f"   Versión: {__version__}")
        print("   Autor: Luis Aguilera Arteaga")
        print("=" * 50)

    try:
        if args.batch:
            # Modo batch
            success, failed = process_batch(
                args.batch,
                str(output_dir),
                args.quiet,
                args.verbose,
            )

            if not args.quiet:
                print("\n" + "=" * 50)
                print(f"📊 Resumen: {success} exitosos, {failed} fallidos")
                print("=" * 50)

            return 0 if failed == 0 else 1

        else:
            # Modo individual
            result = process_url(
                args.url,
                str(output_dir),
                args.quiet,
                args.verbose,
            )

            return 0 if result else 1

    except KeyboardInterrupt:
        if not args.quiet:
            print("\n\n⚠️ Operación cancelada por el usuario")
        return 130


if __name__ == "__main__":
    sys.exit(main())
