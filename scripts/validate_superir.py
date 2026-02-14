#!/usr/bin/env python3
"""
Validador de NCGs SUPERIR contra superir_v1.xsd.

Valida estructura XSD, consistencia de referencias cruzadas entre NCGs,
y completitud de metadatos.

Uso:
    python scripts/validate_superir.py
    python scripts/validate_superir.py --verbose
    python scripts/validate_superir.py NCG_7.xml NCG_28.xml
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from lxml import etree

# Rutas
PROJECT_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "superir_v1.xsd"
NCG_DIR = PROJECT_ROOT / "biblioteca_xml" / "organismos" / "SUPERIR" / "NCG"
NS = "https://superir.cl/schema/norma/v1"
NSMAP = {"n": NS}


def load_schema() -> etree.XMLSchema:
    """Carga y compila el XSD."""
    schema_doc = etree.parse(str(SCHEMA_PATH))
    return etree.XMLSchema(schema_doc)


def validate_xsd(xml_path: Path, schema: etree.XMLSchema, verbose: bool = False) -> list[str]:
    """Valida un XML contra el XSD. Retorna lista de errores."""
    errors = []
    try:
        doc = etree.parse(str(xml_path))
        if not schema.validate(doc):
            for error in schema.error_log:
                errors.append(f"  XSD: línea {error.line}: {error.message}")
    except etree.XMLSyntaxError as e:
        errors.append(f"  XML malformado: {e}")
    return errors


def extract_ncg_refs(xml_path: Path) -> dict:
    """Extrae metadatos y referencias de una NCG."""
    doc = etree.parse(str(xml_path))
    root = doc.getroot()

    numero = root.get("numero", "?")
    estado = root.get("estado", "vigente")

    # ncg_referenciadas
    refs = []
    for ref in root.findall(f".//{{{NS}}}ncg_ref"):
        refs.append({
            "numero": ref.get("numero"),
            "relacion": ref.get("relacion"),
        })

    # leyes_referenciadas (verificar que no queden NCGs aquí)
    ley_refs_ncg = []
    for ref in root.findall(f".//{{{NS}}}ley_ref"):
        if ref.get("tipo") == "NCG":
            ley_refs_ncg.append(ref.get("numero"))

    # Materias
    materias = [m.text for m in root.findall(f".//{{{NS}}}materia") if m.text]

    # Contar artículos
    articulos = root.findall(f".//{{{NS}}}articulo")

    # Contar anexos
    anexos = root.findall(f"{{{NS}}}anexo")
    anexos_pendientes = [a for a in anexos if a.get("pendiente") == "true"]

    return {
        "numero": numero,
        "estado": estado,
        "ncg_refs": refs,
        "ley_refs_ncg_residuales": ley_refs_ncg,
        "materias": materias,
        "n_articulos": len(articulos),
        "n_anexos": len(anexos),
        "n_anexos_pendientes": len(anexos_pendientes),
    }


def check_cross_references(all_data: dict[str, dict]) -> list[str]:
    """Verifica consistencia bidireccional de referencias cruzadas."""
    errors = []
    ncg_numbers = {d["numero"] for d in all_data.values()}

    # Mapa inverso de relaciones
    inverse = {
        "deroga": "derogada_por",
        "derogada_por": "deroga",
        "modifica": "modificada_por",
        "modificada_por": "modifica",
        "reemplaza": "derogada_por",
    }

    for path, data in all_data.items():
        ncg_num = data["numero"]

        # Verificar ley_refs NCG residuales
        for residual in data["ley_refs_ncg_residuales"]:
            errors.append(
                f"  NCG {ncg_num}: ley_ref tipo='NCG' numero='{residual}' "
                f"debería migrar a ncg_referenciadas"
            )

        # Verificar anexos pendientes
        if data["n_anexos_pendientes"] > 0:
            errors.append(
                f"  NCG {ncg_num}: {data['n_anexos_pendientes']} anexo(s) con pendiente='true'"
            )

        # Verificar bidireccionalidad de refs que la requieren
        for ref in data["ncg_refs"]:
            ref_num = ref["numero"]
            rel = ref["relacion"]

            # Solo verificar bidireccionalidad para deroga/modifica/reemplaza
            if rel not in inverse:
                continue

            expected_inverse = inverse[rel]

            # Buscar la NCG referenciada en el corpus
            target_data = None
            for d in all_data.values():
                if d["numero"] == ref_num:
                    target_data = d
                    break

            if target_data is None:
                # NCG referenciada no está en el corpus - no es error
                continue

            # Verificar que la NCG destino tenga la referencia inversa
            has_inverse = any(
                r["numero"] == ncg_num and r["relacion"] == expected_inverse
                for r in target_data["ncg_refs"]
            )
            if not has_inverse:
                errors.append(
                    f"  NCG {ncg_num} → NCG {ref_num} ({rel}): "
                    f"falta ref inversa NCG {ref_num} → NCG {ncg_num} ({expected_inverse})"
                )

    return errors


def print_summary(all_data: dict[str, dict]) -> None:
    """Imprime resumen del corpus."""
    print("\n=== Resumen del corpus NCG SUPERIR ===\n")
    print(f"{'NCG':>5} {'Arts':>5} {'Anex':>5} {'Estado':>10} {'Refs NCG':>10}  Materias")
    print("-" * 80)

    for path in sorted(all_data.keys(), key=lambda p: int(all_data[p]["numero"])):
        d = all_data[path]
        refs_str = ", ".join(f"{r['numero']}({r['relacion'][:3]})" for r in d["ncg_refs"])
        materias_str = ", ".join(d["materias"][:2])
        if len(d["materias"]) > 2:
            materias_str += "..."
        print(
            f"{d['numero']:>5} {d['n_articulos']:>5} {d['n_anexos']:>5} "
            f"{d['estado']:>10} {refs_str:>10}  {materias_str}"
        )

    # Grafo de referencias
    print("\n=== Grafo de referencias cruzadas ===\n")
    ref_graph = defaultdict(list)
    for d in all_data.values():
        for ref in d["ncg_refs"]:
            ref_graph[d["numero"]].append((ref["numero"], ref["relacion"]))

    if ref_graph:
        for src in sorted(ref_graph.keys(), key=int):
            for dst, rel in ref_graph[src]:
                print(f"  NCG {src} --[{rel}]--> NCG {dst}")
    else:
        print("  (sin referencias cruzadas)")


def main():
    parser = argparse.ArgumentParser(description="Validador NCGs SUPERIR")
    parser.add_argument("files", nargs="*", help="Archivos específicos a validar")
    parser.add_argument("-v", "--verbose", action="store_true", help="Mostrar detalle")
    args = parser.parse_args()

    # Cargar schema
    try:
        schema = load_schema()
    except Exception as e:
        print(f"Error cargando schema {SCHEMA_PATH}: {e}")
        sys.exit(2)

    # Determinar archivos
    if args.files:
        xml_files = [NCG_DIR / f for f in args.files]
    else:
        xml_files = sorted(NCG_DIR.glob("NCG_*.xml"))

    if not xml_files:
        print("No se encontraron archivos NCG XML.")
        sys.exit(1)

    print(f"Validando {len(xml_files)} NCGs contra {SCHEMA_PATH.name}...\n")

    total_errors = 0
    all_data = {}

    for xml_path in xml_files:
        if not xml_path.exists():
            print(f"  {xml_path.name}: archivo no encontrado")
            total_errors += 1
            continue

        # Validación XSD
        xsd_errors = validate_xsd(xml_path, schema, args.verbose)

        # Extraer datos
        try:
            data = extract_ncg_refs(xml_path)
            all_data[str(xml_path)] = data
        except Exception as e:
            xsd_errors.append(f"  Error extrayendo datos: {e}")
            data = None

        if xsd_errors:
            print(f"  {xml_path.name}: {len(xsd_errors)} error(es)")
            for err in xsd_errors:
                print(err)
            total_errors += len(xsd_errors)
        elif args.verbose:
            print(f"  {xml_path.name}: OK")

    # Verificar referencias cruzadas
    print("\nVerificando referencias cruzadas...")
    ref_errors = check_cross_references(all_data)
    if ref_errors:
        print(f"  {len(ref_errors)} problema(s) de consistencia:")
        for err in ref_errors:
            print(err)
        total_errors += len(ref_errors)
    else:
        print("  Referencias cruzadas consistentes.")

    # Resumen
    if args.verbose:
        print_summary(all_data)

    # Resultado
    print(f"\n{'=' * 50}")
    if total_errors == 0:
        print(f"OK: {len(xml_files)} NCGs validadas sin errores.")
        sys.exit(0)
    else:
        print(f"ERRORES: {total_errors} problema(s) encontrado(s).")
        sys.exit(1)


if __name__ == "__main__":
    main()
