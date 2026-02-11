"""
Test del Parser de Texto a XML vs XMLs de la Biblioteca.

Este script compara los resultados del parser con los XMLs originales
de la biblioteca para identificar discrepancias y áreas de mejora.
"""

import sys
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from leychile_epub.text_to_xml_parser import NormaTextParser

# Configuración
BIBLIOTECA_PATH = Path(__file__).parent.parent / "biblioteca_xml"
NS = {"ley": "https://leychile.cl/schema/ley/v1"}


def extraer_texto_plano_de_xml(xml_path: Path) -> tuple[str, dict, dict]:
    """
    Extrae el texto plano de un XML de la biblioteca.
    Retorna (texto_plano, metadatos, estadisticas_originales)
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Extraer metadatos del atributo raíz
    metadatos = {
        'tipo': root.get('tipo', ''),
        'numero': root.get('numero', ''),
        'id_norma': root.get('id_norma', ''),
    }
    
    # Extraer título de metadatos
    titulo_elem = root.find('.//ley:metadatos/ley:titulo', NS)
    if titulo_elem is not None:
        metadatos['titulo'] = titulo_elem.text or ''
    
    # Extraer encabezado
    encabezado_elem = root.find('.//ley:encabezado', NS)
    encabezado = encabezado_elem.text if encabezado_elem is not None else ''
    
    # Estadísticas originales
    contenido_elem = root.find('.//ley:contenido', NS)
    stats_originales = {
        'total_articulos': int(contenido_elem.get('total_articulos', 0)) if contenido_elem is not None else 0,
        'total_libros': int(contenido_elem.get('total_libros', 0)) if contenido_elem is not None else 0,
        'total_titulos': int(contenido_elem.get('total_titulos', 0)) if contenido_elem is not None else 0,
        'total_capitulos': int(contenido_elem.get('total_capitulos', 0)) if contenido_elem is not None else 0,
    }
    
    # Extraer texto de todos los elementos en orden
    textos = [encabezado] if encabezado else []
    
    def extraer_textos_recursivo(elem):
        # Buscar texto directo del elemento
        texto_elem = elem.find('ley:texto', NS)
        if texto_elem is not None and texto_elem.text:
            textos.append(texto_elem.text)
        
        # Buscar contenido estructurado de artículos (párrafos, incisos)
        contenido_art = elem.find('ley:contenido', NS)
        if contenido_art is not None:
            partes = []
            for child in contenido_art:
                if child.text:
                    partes.append(child.text)
            if partes:
                textos.append('\n'.join(partes))
        
        # Recurrir a hijos estructurales EN ORDEN
        for child in elem:
            tag_local = child.tag.replace('{' + NS['ley'] + '}', '')
            if tag_local in ['libro', 'titulo', 'capitulo', 'parrafo', 'seccion', 'articulo']:
                extraer_textos_recursivo(child)
    
    if contenido_elem is not None:
        extraer_textos_recursivo(contenido_elem)
    
    texto_plano = '\n\n'.join(textos)
    return texto_plano, metadatos, stats_originales


def analizar_estructura_xml(xml_path: Path) -> dict:
    """
    Analiza la estructura de un XML existente.
    Retorna estadísticas detalladas.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    stats = {
        'articulos': [],
        'divisiones': defaultdict(list),
        'incisos': 0,
        'parrafos_internos': 0,
    }
    
    def analizar_recursivo(elem, contexto=""):
        tag_local = elem.tag.replace('{' + NS['ley'] + '}', '')
        
        if tag_local == 'articulo':
            numero = elem.get('numero', '')
            stats['articulos'].append(numero)
            
            # Contar incisos
            for _inciso in elem.findall('.//ley:inciso', NS):
                stats['incisos'] += 1

            # Contar párrafos internos
            contenido = elem.find('ley:contenido', NS)
            if contenido is not None:
                for _parr in contenido.findall('ley:parrafo', NS):
                    stats['parrafos_internos'] += 1
        
        elif tag_local in ['libro', 'titulo', 'capitulo', 'parrafo', 'seccion']:
            titulo_sec = elem.find('ley:titulo_seccion', NS)
            titulo_text = titulo_sec.text if titulo_sec is not None else ''
            stats['divisiones'][tag_local].append(titulo_text)
        
        # Recurrir
        for child in elem:
            analizar_recursivo(child, contexto)
    
    contenido = root.find('.//ley:contenido', NS)
    if contenido is not None:
        analizar_recursivo(contenido)
    
    return stats


def comparar_resultados(original: dict, parseado: dict) -> dict:
    """Compara estadísticas del original vs parseado."""
    comparacion = {}
    
    # Comparar conteos
    for key in ['total_articulos', 'total_libros', 'total_titulos', 'total_capitulos']:
        orig_val = original.get(key, 0)
        # El parseado viene de contar elementos
        if key == 'total_articulos':
            parse_val = len(parseado.get('articulos', []))
        elif key == 'total_libros':
            parse_val = len(parseado.get('divisiones', {}).get('libro', []))
        elif key == 'total_titulos':
            parse_val = len(parseado.get('divisiones', {}).get('titulo', []))
        elif key == 'total_capitulos':
            parse_val = len(parseado.get('divisiones', {}).get('capitulo', []))
        else:
            parse_val = 0
        
        comparacion[key] = {
            'original': orig_val,
            'parseado': parse_val,
            'diferencia': parse_val - orig_val,
            'match': orig_val == parse_val
        }
    
    return comparacion


def run_test_archivo(xml_path: Path, verbose: bool = True) -> dict:
    """
    Testea un archivo XML comparando con el parser.
    """
    print(f"\n{'='*70}")
    print(f"📄 Testeando: {xml_path.name}")
    print('='*70)
    
    resultado = {
        'archivo': xml_path.name,
        'exito': False,
        'errores': [],
        'comparacion': {},
        'detalles': {}
    }
    
    try:
        # 1. Extraer texto y metadatos del original
        texto_plano, metadatos, stats_orig = extraer_texto_plano_de_xml(xml_path)
        
        print("\n📊 Estadísticas ORIGINALES:")
        print(f"   - Artículos: {stats_orig['total_articulos']}")
        print(f"   - Libros: {stats_orig['total_libros']}")
        print(f"   - Títulos: {stats_orig['total_titulos']}")
        print(f"   - Capítulos: {stats_orig['total_capitulos']}")
        
        # 2. Analizar estructura detallada del original
        stats_detalle_orig = analizar_estructura_xml(xml_path)
        
        print("\n📋 Divisiones en original:")
        for tipo, items in stats_detalle_orig['divisiones'].items():
            print(f"   - {tipo}: {len(items)}")
        print(f"   - Incisos: {stats_detalle_orig['incisos']}")
        print(f"   - Párrafos internos: {stats_detalle_orig['parrafos_internos']}")
        
        # 3. Parsear el texto
        parser = NormaTextParser()
        xml_generado = parser.parse_text(texto_plano, metadatos)
        
        # 4. Analizar el XML generado
        root_generado = ET.fromstring(xml_generado)
        
        # Contar elementos en el generado (puede tener o no namespace)
        stats_parseado = {
            'articulos': [],
            'divisiones': defaultdict(list),
            'incisos': 0,
            'parrafos_internos': 0,
        }
        
        def contar_en_generado(elem):
            # Obtener tag sin namespace
            tag = elem.tag
            if '}' in tag:
                tag = tag.split('}')[1]
            
            if tag == 'articulo':
                stats_parseado['articulos'].append(elem.get('numero', ''))
                # Buscar incisos (con o sin namespace)
                for inciso in list(elem.iter()):
                    inciso_tag = inciso.tag.split('}')[-1] if '}' in inciso.tag else inciso.tag
                    if inciso_tag == 'inciso':
                        stats_parseado['incisos'] += 1
                # Buscar contenido
                for child in elem:
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if child_tag == 'contenido':
                        for subchild in child:
                            subtag = subchild.tag.split('}')[-1] if '}' in subchild.tag else subchild.tag
                            if subtag == 'parrafo':
                                stats_parseado['parrafos_internos'] += 1
                        
            elif tag in ['libro', 'titulo', 'capitulo', 'parrafo', 'seccion']:
                # Buscar titulo_seccion
                titulo_text = ''
                for child in elem:
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if child_tag == 'titulo_seccion' and child.text:
                        titulo_text = child.text
                        break
                stats_parseado['divisiones'][tag].append(titulo_text)
            
            for child in elem:
                contar_en_generado(child)
        
        # Buscar contenido (con o sin namespace)
        contenido_gen = None
        for child in root_generado:
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if child_tag == 'contenido':
                contenido_gen = child
                break
        
        if contenido_gen is not None:
            contar_en_generado(contenido_gen)
        
        print("\n🔄 Estadísticas PARSEADAS:")
        print(f"   - Artículos: {len(stats_parseado['articulos'])}")
        for tipo, items in stats_parseado['divisiones'].items():
            print(f"   - {tipo}: {len(items)}")
        print(f"   - Incisos: {stats_parseado['incisos']}")
        print(f"   - Párrafos internos: {stats_parseado['parrafos_internos']}")
        
        # 5. Comparar
        print("\n⚖️  COMPARACIÓN:")
        
        # Artículos
        art_orig = len(stats_detalle_orig['articulos'])
        art_parse = len(stats_parseado['articulos'])
        diff_art = art_parse - art_orig
        status_art = "✅" if diff_art == 0 else ("⚠️" if abs(diff_art) < 5 else "❌")
        print(f"   {status_art} Artículos: {art_orig} orig vs {art_parse} parsed (diff: {diff_art:+d})")
        
        # Divisiones
        for tipo in ['libro', 'titulo', 'capitulo', 'parrafo', 'seccion']:
            orig_count = len(stats_detalle_orig['divisiones'].get(tipo, []))
            parse_count = len(stats_parseado['divisiones'].get(tipo, []))
            diff = parse_count - orig_count
            status = "✅" if diff == 0 else ("⚠️" if abs(diff) < 3 else "❌")
            if orig_count > 0 or parse_count > 0:
                print(f"   {status} {tipo.capitalize()}: {orig_count} orig vs {parse_count} parsed (diff: {diff:+d})")
        
        # Incisos
        diff_inc = stats_parseado['incisos'] - stats_detalle_orig['incisos']
        status_inc = "✅" if diff_inc == 0 else ("⚠️" if abs(diff_inc) < 10 else "❌")
        print(f"   {status_inc} Incisos: {stats_detalle_orig['incisos']} orig vs {stats_parseado['incisos']} parsed (diff: {diff_inc:+d})")
        
        # Guardar resultados
        resultado['exito'] = abs(diff_art) <= 2
        resultado['detalles'] = {
            'articulos_original': art_orig,
            'articulos_parseado': art_parse,
            'divisiones_original': {k: len(v) for k, v in stats_detalle_orig['divisiones'].items()},
            'divisiones_parseado': {k: len(v) for k, v in stats_parseado['divisiones'].items()},
            'incisos_original': stats_detalle_orig['incisos'],
            'incisos_parseado': stats_parseado['incisos'],
        }
        
        # Detectar artículos faltantes o extras (comparación case-insensitive)
        arts_orig_set = {a.upper() for a in stats_detalle_orig['articulos']}
        arts_parse_set = {a.upper() for a in stats_parseado['articulos']}
        
        faltantes = arts_orig_set - arts_parse_set
        extras = arts_parse_set - arts_orig_set
        
        if faltantes and len(faltantes) <= 10:
            print(f"\n   ⚠️  Artículos NO detectados: {sorted(faltantes)[:10]}")
        if extras and len(extras) <= 10:
            print(f"   ⚠️  Artículos EXTRA detectados: {sorted(extras)[:10]}")
        
        resultado['faltantes'] = list(faltantes)[:20]
        resultado['extras'] = list(extras)[:20]
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        resultado['errores'].append(str(e))
    
    return resultado


def main():
    """Ejecuta tests en múltiples archivos de la biblioteca."""
    
    # Seleccionar archivos para test (diversidad de estructuras)
    archivos_test = [
        "ley_19628_proteccion_datos.xml",   # Ley simple con títulos
        "ley_19496_consumidor.xml",         # Ley con párrafos estructurales
        "dl_825_iva.xml",                   # Decreto ley con párrafos
        "codigo_penal.xml",                 # Código con libros
        "constitucion.xml",                 # Constitución con capítulos
        "codigo_comercio.xml",              # Código extenso
        "ley_20730_lobby.xml",              # Ley con incisos
        "codigo_civil.xml",                 # Código civil extenso
        "ley_19880_procedimiento_administrativo.xml",  # Ley administrativa
        "ley_18046_sociedades_anonimas.xml", # Ley comercial
    ]
    
    resultados = []
    
    print("\n" + "="*70)
    print("🧪 TEST DEL PARSER DE TEXTO A XML")
    print("   Comparando resultados del parser con XMLs de la biblioteca")
    print("="*70)
    
    for archivo in archivos_test:
        path = BIBLIOTECA_PATH / archivo
        if path.exists():
            resultado = run_test_archivo(path)
            resultados.append(resultado)
        else:
            print(f"\n⚠️  Archivo no encontrado: {archivo}")
    
    # Resumen final
    print("\n" + "="*70)
    print("📊 RESUMEN DE TESTS")
    print("="*70)
    
    exitosos = sum(1 for r in resultados if r['exito'])
    total = len(resultados)
    
    print(f"\n✅ Exitosos: {exitosos}/{total}")
    print(f"❌ Con problemas: {total - exitosos}/{total}")
    
    # Identificar patrones de problemas
    print("\n📋 Patrones identificados:")
    
    total_art_diff = 0
    problemas_divisiones = defaultdict(int)
    
    for r in resultados:
        if 'detalles' in r:
            d = r['detalles']
            total_art_diff += abs(d.get('articulos_parseado', 0) - d.get('articulos_original', 0))
            
            for tipo in ['libro', 'titulo', 'capitulo', 'parrafo', 'seccion']:
                orig = d.get('divisiones_original', {}).get(tipo, 0)
                parse = d.get('divisiones_parseado', {}).get(tipo, 0)
                if orig != parse:
                    problemas_divisiones[tipo] += 1
    
    print(f"   - Diferencia total en artículos: {total_art_diff}")
    for tipo, count in problemas_divisiones.items():
        print(f"   - Problemas con {tipo}: {count} archivos")
    
    return resultados


if __name__ == "__main__":
    results = main()
