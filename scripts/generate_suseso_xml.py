#!/usr/bin/env python3
"""Genera XML del Compendio SUSESO desde los archivos descargados.

Lee la estructura de `biblioteca_suseso/indice_general.json` y los archivos .txt
de cada libro para generar un XML validado contra `schemas/compendio_v1.xsd`.

Uso:
    python scripts/generate_suseso_xml.py                  # Generar XML completo
    python scripts/generate_suseso_xml.py --libro 1        # Solo Libro I
    python scripts/generate_suseso_xml.py --validar        # Solo validar existente
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

NAMESPACE = "https://leychile.cl/schema/compendio/v1"
NSMAP = {None: NAMESPACE}
SCHEMA_PATH = Path("schemas/compendio_v1.xsd")
INPUT_DIR = Path("biblioteca_suseso")
OUTPUT_PATH = INPUT_DIR / "compendio_suseso.xml"
SOURCE_URL = "https://www.suseso.cl/620/w3-propertyname-785.html"

NUMEROS_ROMANOS = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
    6: "VI", 7: "VII", 8: "VIII",
}


# ---------------------------------------------------------------------------
# Parsing de archivos .txt
# ---------------------------------------------------------------------------


def _nombre_archivo(numero: str, titulo: str) -> str:
    """Genera nombre de archivo (mismo algoritmo que download_suseso.py)."""
    t = titulo.lower()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"\s+", "_", t.strip())
    t = t[:60]
    if numero:
        return f"{numero}_{t}"
    return t


def leer_contenido_txt(libro_dir: Path, numero: str, titulo: str) -> tuple[list[str], list[str]]:
    """Lee un archivo .txt y retorna (párrafos, referencias_raw).

    Separa el contenido en párrafos de texto y la sección de referencias legales.
    """
    nombre = _nombre_archivo(numero, titulo)
    txt_path = libro_dir / f"{nombre}.txt"

    if not txt_path.exists():
        return [], []

    text = txt_path.read_text(encoding="utf-8")

    # Saltar encabezado (título + línea de ===)
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("===") or line.startswith("---"):
            start = i + 1
            break
    if start == 0 and len(lines) > 1:
        start = 1  # Al menos saltar la primera línea (título)

    body = "\n".join(lines[start:]).strip()

    # Ignorar nodos estructurales
    if body == "(Nodo estructural - ver subnodos)":
        return [], []

    # Separar referencias legales
    parrafos_raw: str
    refs_raw: str = ""
    if "Referencias legales:" in body:
        parts = body.split("Referencias legales:", 1)
        parrafos_raw = parts[0].strip()
        refs_raw = parts[1].strip()
    else:
        parrafos_raw = body

    # Dividir en párrafos (separados por línea vacía)
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", parrafos_raw) if p.strip()]

    # Parsear referencias individuales
    referencias: list[str] = []
    if refs_raw:
        # Las referencias están separadas por " - " precedido de ciertos patrones
        refs_text = refs_raw.strip()
        # Separar por " - " cuando va seguido de una referencia legal
        ref_items = re.split(r"\s*-\s+(?=(?:DFL|Ley|D\.?[SL]|Código|Art))", refs_text)
        for item in ref_items:
            item = item.strip().rstrip("-").strip()
            if item:
                referencias.append(item)

    return parrafos, referencias


def parsear_referencia(ref_text: str) -> dict[str, str]:
    """Parsea una referencia textual en atributos estructurados.

    Ejemplos:
        "Ley 18.833, artículo 1" → {tipo: "Ley", numero: "18.833", articulo: "1"}
        "DFL 1 de 2000 Minjus, artículo 545 (del art. 2)" → {tipo: "DFL", numero: "1", articulo: "545"}
        "Ley 19.378" → {tipo: "Ley", numero: "19.378"}
    """
    result: dict[str, str] = {"texto": ref_text}

    # Extraer tipo de norma
    tipo_match = re.match(
        r"^(Ley|DFL|D\.?L\.?|D\.?S\.?|Código\s+\w+|NCG)\s+", ref_text, re.IGNORECASE
    )
    if tipo_match:
        result["tipo"] = tipo_match.group(1)

    # Extraer número
    num_match = re.match(
        r"^(?:Ley|DFL|D\.?L\.?|D\.?S\.?|NCG)\s+N?°?\s*([\d.,]+)",
        ref_text, re.IGNORECASE,
    )
    if num_match:
        result["numero"] = num_match.group(1).rstrip(".,")

    # Extraer artículo
    art_match = re.search(r"artículo\s+([\d\w°.-]+)", ref_text, re.IGNORECASE)
    if art_match:
        result["articulo"] = art_match.group(1).rstrip(".,")

    return result


# ---------------------------------------------------------------------------
# Generación XML
# ---------------------------------------------------------------------------


def crear_compendio_xml(
    indice: dict,
    input_dir: Path,
    libros_filtro: list[int] | None = None,
) -> etree._Element:
    """Genera el árbol XML completo del compendio."""
    root = etree.Element(
        f"{{{NAMESPACE}}}compendio",
        nsmap=NSMAP,
        attrib={
            "organismo": "SUSESO",
            "ley_base": "18.833",
            "version": "1.0",
            "generado": datetime.now(timezone.utc).isoformat(),
            "fuente": SOURCE_URL,
        },
    )

    # Metadatos
    meta = etree.SubElement(root, f"{{{NAMESPACE}}}metadatos")
    etree.SubElement(meta, f"{{{NAMESPACE}}}titulo").text = (
        "Compendio de Normas que regulan a las Cajas de Compensación de Asignación Familiar"
    )
    etree.SubElement(meta, f"{{{NAMESPACE}}}organismo").text = (
        "Superintendencia de Seguridad Social"
    )
    ley_base = etree.SubElement(
        meta, f"{{{NAMESPACE}}}ley_base",
        attrib={"tipo": "Ley", "numero": "18.833"},
    )
    ley_base.text = "Ley N° 18.833"

    # Libros
    libros_dict = indice.get("libros", {})
    for num_str in sorted(libros_dict.keys(), key=int):
        num = int(num_str)
        if libros_filtro and num not in libros_filtro:
            continue

        libro_data = libros_dict[num_str]
        libro_dir = input_dir / f"libro_{num}"
        romano = NUMEROS_ROMANOS.get(num, str(num))

        libro_elem = etree.SubElement(
            root,
            f"{{{NAMESPACE}}}libro",
            attrib={
                "numero": romano,
                "titulo": libro_data.get("titulo", ""),
                "id": f"libro-{num}",
            },
        )

        # Contenido propio del libro (si tiene)
        _agregar_contenido_nodo(
            libro_elem, libro_dir,
            libro_data.get("numero", str(num)),
            libro_data.get("titulo", ""),
        )

        # Secciones hijas
        for hijo in libro_data.get("hijos", []):
            _agregar_seccion(libro_elem, hijo, libro_dir)

    return root


def _agregar_seccion(parent: etree._Element, nodo: dict, libro_dir: Path) -> None:
    """Agrega recursivamente una sección y sus hijas al XML."""
    numero = nodo.get("numero", "")
    titulo = nodo.get("titulo", "")
    sec_id = f"sec-{numero}" if numero else f"sec-{nodo.get('pvid', '')}"

    sec_elem = etree.SubElement(
        parent,
        f"{{{NAMESPACE}}}seccion",
        attrib={
            "numero": numero,
            "titulo": titulo,
            "id": sec_id,
        },
    )

    # Contenido propio
    _agregar_contenido_nodo(sec_elem, libro_dir, numero, titulo)

    # Secciones hijas (recursivo)
    for hijo in nodo.get("hijos", []):
        _agregar_seccion(sec_elem, hijo, libro_dir)


def _agregar_contenido_nodo(
    elem: etree._Element, libro_dir: Path, numero: str, titulo: str
) -> None:
    """Agrega <contenido> y <referencias> a un elemento si el .txt tiene datos."""
    parrafos, referencias = leer_contenido_txt(libro_dir, numero, titulo)

    if parrafos:
        contenido = etree.SubElement(elem, f"{{{NAMESPACE}}}contenido")
        for p in parrafos:
            parrafo_elem = etree.SubElement(contenido, f"{{{NAMESPACE}}}parrafo")
            parrafo_elem.text = p

    if referencias:
        refs_elem = etree.SubElement(elem, f"{{{NAMESPACE}}}referencias")
        for ref_text in referencias:
            parsed = parsear_referencia(ref_text)
            attrib: dict[str, str] = {}
            if "tipo" in parsed:
                attrib["tipo"] = parsed["tipo"]
            if "numero" in parsed:
                attrib["numero"] = parsed["numero"]
            if "articulo" in parsed:
                attrib["articulo"] = parsed["articulo"]

            ref_elem = etree.SubElement(refs_elem, f"{{{NAMESPACE}}}ref", attrib=attrib)
            ref_elem.text = ref_text


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------


def validar_xml(xml_path: Path, schema_path: Path) -> bool:
    """Valida un archivo XML contra el schema XSD."""
    schema_doc = etree.parse(str(schema_path))
    schema = etree.XMLSchema(schema_doc)

    doc = etree.parse(str(xml_path))

    if schema.validate(doc):
        print(f"  Validación OK contra {schema_path}")
        return True
    else:
        print(f"  ERROR de validación contra {schema_path}:")
        for error in schema.error_log:
            print(f"    Línea {error.line}: {error.message}")
        return False


# ---------------------------------------------------------------------------
# Estadísticas
# ---------------------------------------------------------------------------


def contar_elementos(root: etree._Element) -> dict[str, int]:
    """Cuenta elementos en el XML generado."""
    ns = f"{{{NAMESPACE}}}"
    stats = {
        "libros": len(root.findall(f"{ns}libro")),
        "secciones": len(root.findall(f".//{ns}seccion")),
        "secciones_con_contenido": len(
            [s for s in root.findall(f".//{ns}seccion") if s.find(f"{ns}contenido") is not None]
        ),
        "parrafos": len(root.findall(f".//{ns}parrafo")),
        "referencias": len(root.findall(f".//{ns}ref")),
    }
    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera XML del Compendio SUSESO desde archivos descargados"
    )
    parser.add_argument(
        "--libro",
        type=int,
        nargs="*",
        help="Número(s) de libro a incluir (1-8). Sin argumento = todos.",
    )
    parser.add_argument(
        "--validar",
        action="store_true",
        help="Solo validar el XML existente sin regenerar.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_DIR,
        help=f"Directorio de entrada (default: {INPUT_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Archivo de salida (default: {OUTPUT_PATH})",
    )
    args = parser.parse_args()

    # Solo validar
    if args.validar:
        if not args.output.exists():
            print(f"Error: {args.output} no existe")
            sys.exit(1)
        ok = validar_xml(args.output, SCHEMA_PATH)
        sys.exit(0 if ok else 1)

    # Verificar input
    indice_path = args.input / "indice_general.json"
    if not indice_path.exists():
        print(f"Error: No se encontró {indice_path}")
        print("Ejecuta primero: python scripts/download_suseso.py")
        sys.exit(1)

    with open(indice_path, encoding="utf-8") as f:
        indice = json.load(f)

    libros_filtro = args.libro
    if libros_filtro:
        print(f"Generando XML para libro(s): {libros_filtro}")
    else:
        print("Generando XML para los 8 libros")

    # Generar XML
    root = crear_compendio_xml(indice, args.input, libros_filtro)

    # Escribir
    tree = etree.ElementTree(root)
    etree.indent(tree, space="  ")
    tree.write(
        str(args.output),
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    )
    print(f"XML generado: {args.output}")

    # Estadísticas
    stats = contar_elementos(root)
    print(f"  Libros: {stats['libros']}")
    print(f"  Secciones: {stats['secciones']}")
    print(f"  Secciones con contenido: {stats['secciones_con_contenido']}")
    print(f"  Párrafos: {stats['parrafos']}")
    print(f"  Referencias: {stats['referencias']}")

    # Validar
    print()
    validar_xml(args.output, SCHEMA_PATH)


if __name__ == "__main__":
    main()
