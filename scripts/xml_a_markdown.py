#!/usr/bin/env python3
"""
Extrae el texto de XMLs de la biblioteca y los convierte a formato Markdown
para testear el parser con input en MD.
"""
import xml.etree.ElementTree as ET
from pathlib import Path


def xml_a_markdown(xml_path: Path) -> str:
    """Convierte un XML de la biblioteca a formato Markdown."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Manejar namespace
    ns = {'ley': 'https://leychile.cl/schema/ley/v1'}
    
    def find_elem(parent, tag):
        """Busca elemento con o sin namespace."""
        elem = parent.find(f'ley:{tag}', ns)
        if elem is None:
            elem = parent.find(tag)
        return elem
    
    def findall_elem(parent, tag):
        """Busca todos los elementos con o sin namespace."""
        elems = parent.findall(f'ley:{tag}', ns)
        if not elems:
            elems = parent.findall(tag)
        return elems
    
    md_lines = []
    
    # Título de la norma
    metadatos = find_elem(root, 'metadatos')
    titulo = ''
    if metadatos is not None:
        titulo_elem = find_elem(metadatos, 'titulo')
        if titulo_elem is not None and titulo_elem.text:
            titulo = titulo_elem.text.strip()
    
    tipo = root.get('tipo', 'Ley')
    numero = root.get('numero', '')
    
    md_lines.append(f"# {tipo} {numero}")
    md_lines.append("")
    if titulo:
        md_lines.append(f"**{titulo}**")
        md_lines.append("")
    
    # Metadatos
    md_lines.append("---")
    md_lines.append(f"- **Tipo**: {tipo}")
    md_lines.append(f"- **Número**: {numero}")
    fecha_pub = root.get('fecha_publicacion')
    if fecha_pub:
        md_lines.append(f"- **Fecha publicación**: {fecha_pub}")
    md_lines.append("---")
    md_lines.append("")
    
    # Encabezado
    encabezado = find_elem(root, 'encabezado')
    if encabezado is not None and encabezado.text:
        md_lines.append("## Encabezado")
        md_lines.append("")
        md_lines.append(encabezado.text.strip())
        md_lines.append("")
    
    def get_tag_local(elem):
        """Obtiene el tag sin namespace."""
        tag = elem.tag
        if '}' in tag:
            tag = tag.split('}')[1]
        return tag
    
    def procesar_elemento(elem, nivel=2):
        """Procesa un elemento y sus hijos recursivamente."""
        lines = []
        tag = get_tag_local(elem)
        
        # Divisiones estructurales
        if tag in ('libro', 'titulo', 'capitulo', 'parrafo', 'seccion'):
            titulo_sec = find_elem(elem, 'titulo_seccion')
            texto_elem = find_elem(elem, 'texto')
            
            # Determinar el nivel de encabezado
            niveles = {'libro': 2, 'titulo': 3, 'capitulo': 4, 'parrafo': 5, 'seccion': 5}
            nivel_h = min(niveles.get(tag, nivel), 6)
            
            if titulo_sec is not None and titulo_sec.text:
                lines.append(f"{'#' * nivel_h} {titulo_sec.text.strip()}")
                lines.append("")
            elif texto_elem is not None and texto_elem.text:
                texto = texto_elem.text.strip()
                if len(texto) < 150:
                    lines.append(f"{'#' * nivel_h} {texto}")
                    lines.append("")
            
            # Procesar hijos
            for hijo in elem:
                hijo_tag = get_tag_local(hijo)
                if hijo_tag not in ('titulo_seccion', 'texto', 'contexto'):
                    lines.extend(procesar_elemento(hijo, nivel_h + 1))
        
        elif tag == 'articulo':
            texto_elem = find_elem(elem, 'texto')
            contenido_elem = find_elem(elem, 'contenido')
            
            if texto_elem is not None and texto_elem.text:
                texto = texto_elem.text.strip()
                lines.append(texto)
                lines.append("")
            elif contenido_elem is not None:
                for p in contenido_elem:
                    if p.text:
                        lines.append(p.text.strip())
                lines.append("")
        
        return lines
    
    # Procesar contenido
    contenido = find_elem(root, 'contenido')
    if contenido is not None:
        for elem in contenido:
            md_lines.extend(procesar_elemento(elem))
    
    return '\n'.join(md_lines)


def main():
    """Convierte XMLs seleccionados a Markdown."""
    base_path = Path(__file__).parent.parent
    biblioteca_path = base_path / 'biblioteca_xml'
    output_path = base_path / 'trabajo' / 'normas_md'
    output_path.mkdir(exist_ok=True)
    
    # Normas a convertir (selección diversa)
    normas = [
        'ley_19628_proteccion_datos.xml',
        'ley_19880_procedimiento_administrativo.xml',
        'ley_20730_lobby.xml',
        'ley_19496_consumidor.xml',
        'ley_18046_sociedades_anonimas.xml',
        'constitucion.xml',
    ]
    
    for norma in normas:
        xml_path = biblioteca_path / norma
        if xml_path.exists():
            md_content = xml_a_markdown(xml_path)
            md_filename = norma.replace('.xml', '.md')
            md_path = output_path / md_filename
            md_path.write_text(md_content, encoding='utf-8')
            
            print(f"✅ Creado: {md_path.name}")
            lineas = md_content.split('\n')
            print(f"   Total líneas: {len(lineas)}")
            print("   Primeras líneas:")
            for line in lineas[:10]:
                print(f"   | {line[:70]}")
            print()
        else:
            print(f"❌ No encontrado: {norma}")


if __name__ == '__main__':
    main()
