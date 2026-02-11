#!/usr/bin/env python3
"""
Test: Markdown → Parser → XML
Compara el XML generado desde Markdown con el XML original de la biblioteca.
"""
import re
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from leychile_epub.text_to_xml_parser import NormaTextParser


def extraer_metadatos_md(contenido: str) -> dict:
    """Extrae metadatos del frontmatter del Markdown."""
    metadatos = {
        'tipo': 'Ley',
        'numero': '',
        'titulo': '',
    }
    
    # Buscar título H1
    match_titulo = re.search(r'^#\s+(\w+)\s+(\d+)', contenido, re.MULTILINE)
    if match_titulo:
        metadatos['tipo'] = match_titulo.group(1)
        metadatos['numero'] = match_titulo.group(2)
    
    # Buscar título en negrita
    match_nombre = re.search(r'\*\*([^*]+)\*\*', contenido)
    if match_nombre:
        metadatos['titulo'] = match_nombre.group(1).strip()
    
    # Buscar fecha en frontmatter
    match_fecha = re.search(r'\*\*Fecha publicación\*\*:\s*(\d{4}-\d{2}-\d{2})', contenido)
    if match_fecha:
        metadatos['fecha_publicacion'] = match_fecha.group(1)
    
    return metadatos


def extraer_texto_md(contenido: str) -> str:
    """Extrae el texto del articulado del Markdown (sin frontmatter)."""
    # Buscar inicio del contenido real (después del segundo ---)
    partes = contenido.split('---')
    if len(partes) >= 3:
        # El contenido está después del segundo ---
        texto = '---'.join(partes[2:])
    else:
        texto = contenido
    
    # Limpiar encabezados markdown que no son divisiones legales
    texto = re.sub(r'^##\s+Encabezado\s*$', '', texto, flags=re.MULTILINE)
    
    return texto.strip()


def contar_articulos_xml(xml_str: str) -> list:
    """Cuenta artículos en un string XML."""
    import xml.etree.ElementTree as ET
    
    root = ET.fromstring(xml_str)
    articulos = []
    
    def buscar_articulos(elem):
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'articulo':
            num = elem.get('numero', '')
            articulos.append(num)
        for hijo in elem:
            buscar_articulos(hijo)
    
    buscar_articulos(root)
    return articulos


def run_md_a_xml(md_path: Path):
    """Testea la conversión de un Markdown a XML."""
    print(f"\n{'='*70}")
    print(f"📄 Testeando: {md_path.name}")
    print('='*70)
    
    # Leer Markdown
    contenido = md_path.read_text(encoding='utf-8')
    
    # Extraer metadatos y texto
    metadatos = extraer_metadatos_md(contenido)
    texto = extraer_texto_md(contenido)
    
    print("\n📋 Metadatos extraídos:")
    print(f"   - Tipo: {metadatos.get('tipo')}")
    print(f"   - Número: {metadatos.get('numero')}")
    print(f"   - Título: {metadatos.get('titulo', '')[:50]}...")
    
    # Parsear con el parser
    parser = NormaTextParser()
    xml_generado = parser.parse_text(texto, metadatos)
    
    # Contar artículos generados
    articulos = contar_articulos_xml(xml_generado)
    
    print("\n🔄 Resultado del parser:")
    print(f"   - Artículos detectados: {len(articulos)}")
    if articulos[:10]:
        print(f"   - Primeros 10: {articulos[:10]}")
    
    # Guardar XML generado para inspección
    output_path = md_path.parent.parent / 'output' / f"{md_path.stem}_from_md.xml"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(xml_generado, encoding='utf-8')
    print(f"\n💾 XML guardado en: {output_path.name}")
    
    # Comparar con original si existe
    xml_original = md_path.parent.parent / 'biblioteca_xml' / f"{md_path.stem}.xml"
    if xml_original.exists():
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(xml_original)
        root = tree.getroot()
        
        # Contar artículos originales
        arts_orig = []
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'articulo':
                arts_orig.append(elem.get('numero', ''))
        
        print("\n⚖️  Comparación con original:")
        print(f"   - Artículos original: {len(arts_orig)}")
        print(f"   - Artículos parseados: {len(articulos)}")
        diff = len(articulos) - len(arts_orig)
        status = "✅" if abs(diff) <= 2 else ("⚠️" if abs(diff) < 10 else "❌")
        print(f"   {status} Diferencia: {diff:+d}")
        
        # Artículos faltantes/extras
        set_orig = {a.upper() for a in arts_orig}
        set_parse = {a.upper() for a in articulos}
        
        faltantes = set_orig - set_parse
        extras = set_parse - set_orig
        
        if faltantes and len(faltantes) <= 5:
            print(f"   ⚠️  Faltantes: {sorted(faltantes)}")
        if extras and len(extras) <= 5:
            print(f"   ⚠️  Extras: {sorted(extras)}")
    
    return len(articulos)


def main():
    """Ejecuta tests para todos los Markdowns en normas_md/."""
    base_path = Path(__file__).parent.parent
    normas_md_path = base_path / 'normas_md'
    
    if not normas_md_path.exists():
        print("❌ Carpeta normas_md/ no encontrada")
        return
    
    md_files = list(normas_md_path.glob('*.md'))
    
    if not md_files:
        print("❌ No hay archivos .md en normas_md/")
        return
    
    print("\n" + "="*70)
    print("🧪 TEST: Markdown → Parser → XML")
    print("   Convirtiendo Markdowns a XML y comparando con originales")
    print("="*70)
    
    total_articulos = 0
    for md_file in sorted(md_files):
        total_articulos += run_md_a_xml(md_file)
    
    print(f"\n{'='*70}")
    print(f"📊 RESUMEN: {len(md_files)} archivos procesados")
    print(f"   Total artículos parseados: {total_articulos}")
    print("="*70)


if __name__ == '__main__':
    main()
