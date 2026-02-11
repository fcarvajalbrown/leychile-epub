"""
Parser de Texto Plano a XML para Normas Legales Chilenas.

Este módulo permite convertir texto plano de leyes, decretos, códigos y otras
normas legales chilenas al formato XML estándar definido en el esquema v1.

Uso básico:
    from text_to_xml_parser import NormaTextParser
    
    parser = NormaTextParser()
    xml_content = parser.parse_text(texto_ley, metadatos={
        'tipo': 'Ley',
        'numero': '19496',
        'titulo': 'Ley de Protección al Consumidor'
    })
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES Y ENUMERACIONES
# ═══════════════════════════════════════════════════════════════════════════════

class TipoNorma(Enum):
    """Tipos de normas legales chilenas."""
    LEY = "Ley"
    DECRETO = "Decreto"
    DECRETO_LEY = "Decreto Ley"
    DFL = "Decreto con Fuerza de Ley"
    CODIGO = "Código"
    REGLAMENTO = "Reglamento"
    RESOLUCION = "Resolución"
    AUTO_ACORDADO = "Auto Acordado"
    TRATADO = "Tratado Internacional"
    CONSTITUCION = "Constitución"


class TipoDivision(Enum):
    """Tipos de divisiones estructurales en el articulado."""
    LIBRO = "libro"
    TITULO = "titulo"
    CAPITULO = "capitulo"
    PARRAFO = "parrafo"
    SECCION = "seccion"
    ARTICULO = "articulo"


# Prioridad de divisiones (mayor número = más alto en jerarquía)
JERARQUIA_DIVISIONES = {
    TipoDivision.LIBRO: 6,
    TipoDivision.TITULO: 5,
    TipoDivision.CAPITULO: 4,
    TipoDivision.PARRAFO: 3,
    TipoDivision.SECCION: 2,
    TipoDivision.ARTICULO: 1,
}


# ═══════════════════════════════════════════════════════════════════════════════
# PATRONES REGEX
# ═══════════════════════════════════════════════════════════════════════════════

# Patrones para identificar divisiones estructurales
PATRONES_DIVISION = [
    # LIBRO
    (
        re.compile(
            r'^LIBRO\s+(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|'
            r'S[ÉE]PTIMO|OCTAVO|NOVENO|D[ÉE]CIMO|'
            r'[IVXLCDM]+|[0-9]+)',
            re.IGNORECASE | re.UNICODE
        ),
        TipoDivision.LIBRO
    ),
    # TÍTULO
    (
        re.compile(
            r'^T[ÍI]TULO\s+(PRELIMINAR|FINAL|PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|'
            r'SEXTO|S[ÉE]PTIMO|OCTAVO|NOVENO|D[ÉE]CIMO|'
            r'[IVXLCDM]+|[0-9]+)',
            re.IGNORECASE | re.UNICODE
        ),
        TipoDivision.TITULO
    ),
    # CAPÍTULO
    (
        re.compile(
            r'^CAP[ÍI]TULO\s+([IVXLCDM]+|[0-9]+|PRIMERO|SEGUNDO|TERCERO|'
            r'CUARTO|QUINTO|SEXTO|S[ÉE]PTIMO|OCTAVO|NOVENO|D[ÉE]CIMO|[ÚU]NICO)',
            re.IGNORECASE | re.UNICODE
        ),
        TipoDivision.CAPITULO
    ),
    # PÁRRAFO (como división)
    (
        re.compile(
            r'^P[ÁA]RRAFO\s+([0-9]+[º°]?|[IVXLCDM]+|PRIMERO|SEGUNDO|TERCERO|[ÚU]NICO)',
            re.IGNORECASE | re.UNICODE
        ),
        TipoDivision.PARRAFO
    ),
    # SECCIÓN (solo si comienza con la palabra "Sección")
    (
        re.compile(
            r'^SECCI[ÓO]N\s+([0-9]+[ªa]?|[IVXLCDM]+|PRIMERA|SEGUNDA|TERCERA|[ÚU]NICA)',
            re.IGNORECASE | re.UNICODE
        ),
        TipoDivision.SECCION
    ),
    # § (símbolo de párrafo/sección - tratado como PARRAFO que es su uso más común en leyes chilenas)
    (
        re.compile(
            r'^§\s*([0-9]+|[IVXLCDM]+)\.?\s*',
            re.IGNORECASE | re.UNICODE
        ),
        TipoDivision.PARRAFO  # En la práctica § se usa como párrafo en Chile
    ),
]

# Patrón para artículos numerados
# Los sufijos latinos (BIS, TER, etc.) son válidos
# Permite º entre número y sufijo (ej: Artículo 3º bis)
# NOTA: NO usa IGNORECASE - debe comenzar con mayúscula para evitar falsos positivos
# con referencias a artículos en el texto (ej: "según el artículo 5")
PATRON_ARTICULO = re.compile(
    r'^(Art[íi]culo|ART[ÍI]CULO|Art\.?)\s*'
    r'([0-9]+)\s*[º°]?\s*'
    r'([Bb][Ii][Ss]|[Tt][Ee][Rr]|[Qq][Uu][Aa][Tt][Ee][Rr]|[Qq][Uu][ÁáAa][Tt][Ee][Rr]|'
    r'[Qq][Uu][Ii][Nn][Qq][Uu][Ii][Ee][Ss]|[Ss][Ee][Xx][Ii][Ee][Ss]|'
    r'[Ss][Ee][Pp][Tt][Ii][Ee][Ss]|[Oo][Cc][Tt][Ii][Ee][Ss]|[Nn][Oo][Vv][Ii][Ee][Ss]|'
    r'[Dd][Ee][Cc][Ii][Ee][Ss]|[Uu][Nn][Dd][ÉéEe][Cc][Ii][Ee][Ss]|'
    r'[Dd][Uu][Oo][Dd][ÉéEe][Cc][Ii][Ee][Ss]|[Tt][Ee][Rr][Dd][ÉéEe][Cc][Ii][Ee][Ss])?'
    r'\s*[º°]?\s*\.?\s*[-–—.]?\s*',
    re.UNICODE
)

# Patrón específico para artículos con letra simple (Artículo 355 A.-, Artículo 5º A.-, Artículo 39-C.-)
# Requiere que la letra vaya seguida de punto, guión, o fin de encabezado
# NOTA: NO usa IGNORECASE - debe comenzar con mayúscula
PATRON_ARTICULO_LETRA = re.compile(
    r'^(Art[íi]culo|ART[ÍI]CULO|Art\.?)\s*'
    r'([0-9]+)\s*[º°]?\s*[\-–—]?\s*([A-ZÑ])\s*'  # Permite guión entre número y letra
    r'[º°]?\s*[.\-–—]',  # Debe haber punto o guión después de la letra
    re.UNICODE
)

# Patrón para artículos transitorios (PRIMERO, SEGUNDO, etc.)
# NOTA: NO usa IGNORECASE - debe comenzar con mayúscula
PATRON_ARTICULO_TRANSITORIO = re.compile(
    r'^(Art[íi]culo|ART[ÍI]CULO)\s+'
    r'([Pp][Rr][Ii][Mm][Ee][Rr][Oo]|[Ss][Ee][Gg][Uu][Nn][Dd][Oo]|[Tt][Ee][Rr][Cc][Ee][Rr][Oo]|'
    r'[Cc][Uu][Aa][Rr][Tt][Oo]|[Qq][Uu][Ii][Nn][Tt][Oo]|[Ss][Ee][Xx][Tt][Oo]|'
    r'[Ss][ÉéEe][Pp][Tt][Ii][Mm][Oo]|[Oo][Cc][Tt][Aa][Vv][Oo]|[Nn][Oo][Vv][Ee][Nn][Oo]|'
    r'[Dd][ÉéEe][Cc][Ii][Mm][Oo]|[Uu][Nn][Dd][ÉéEe][Cc][Ii][Mm][Oo]|'
    r'[Dd][Uu][Oo][Dd][ÉéEe][Cc][Ii][Mm][Oo]|[Dd][ÉéEe][Cc][Ii][Mm][Oo]\s*[Tt][Ee][Rr][Cc][Ee][Rr][Oo]|'
    r'[ÚúUu][Nn][Ii][Cc][Oo]|[Ff][Ii][Nn][Aa][Ll])\s*'
    r'(\s+[Tt][Rr][Aa][Nn][Ss][Ii][Tt][Oo][Rr][Ii][Oo])?'
    r'\s*\.?\s*[-–—.]?\s*',
    re.UNICODE
)

# Patrón para artículos transitorios numerados (Artículo 1 TRANSITORIO, etc.)
# NOTA: NO usa IGNORECASE - debe comenzar con mayúscula
PATRON_ARTICULO_TRANS_NUM = re.compile(
    r'^(Art[íi]culo|ART[ÍI]CULO)\s+([0-9]+)[º°]?\s*'
    r'([Bb][Ii][Ss]|[Tt][Ee][Rr]|[Qq][Uu][Aa][Tt][Ee][Rr])?\s*'
    r'[Tt][Rr][Aa][Nn][Ss][Ii][Tt][Oo][Rr][Ii][Oo]\s*\.?\s*[-–—.]?\s*',
    re.UNICODE
)

# Patrones para incisos y letras
PATRON_INCISO_NUMERO = re.compile(r'^(\d+)[°º]?\)\s*(.+)', re.UNICODE)
PATRON_INCISO_LETRA = re.compile(r'^([a-zñ])\)\s*(.+)', re.IGNORECASE | re.UNICODE)
PATRON_NUMERAL_ROMANO = re.compile(r'^([IVXLCDM]+)[.)\s]+(.+)', re.UNICODE)

# Patrón para detectar referencias a artículos
PATRON_REFERENCIA = re.compile(
    r'art[íi]culos?\s+([0-9]+(?:\s*(?:bis|ter|y|,|al?)\s*[0-9]*)*)',
    re.IGNORECASE | re.UNICODE
)

# Patrón para detectar falsos positivos (números que NO son artículos)
# Ej: referencias a leyes, decretos, códigos dentro del texto
PATRON_FALSO_POSITIVO_ARTICULO = re.compile(
    r'^(Ley|Decreto|DFL|D\.?L\.?|N[º°]|Código|C\.?)\s*',
    re.IGNORECASE | re.UNICODE
)


# ═══════════════════════════════════════════════════════════════════════════════
# ESTRUCTURAS DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MetadatosNorma:
    """Metadatos de una norma legal."""
    titulo: str
    tipo: str
    numero: str
    organismo: str | None = None
    materias: list[str] = field(default_factory=list)
    nombres_comunes: list[str] = field(default_factory=list)
    fecha_promulgacion: str | None = None
    fecha_publicacion: str | None = None
    fuente: str = "Texto manual"
    id_norma: str | None = None
    url_original: str | None = None


@dataclass
class ElementoContenido:
    """Elemento de contenido dentro de un artículo."""
    tipo: str  # 'parrafo', 'inciso', 'letra'
    texto: str
    numero: str | None = None


@dataclass
class Articulo:
    """Representa un artículo de la norma."""
    id: str
    numero: str
    texto: str
    contexto: str = ""
    contenido_estructurado: list[ElementoContenido] = field(default_factory=list)
    referencias: list[str] = field(default_factory=list)
    fecha_modificacion: str | None = None


@dataclass
class Division:
    """Representa una división estructural (libro, título, capítulo, etc.)."""
    id: str
    tipo: TipoDivision
    titulo: str
    texto: str
    contexto: str = ""
    hijos: list['Division | Articulo'] = field(default_factory=list)
    fecha_modificacion: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# PARSER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class NormaTextParser:
    """
    Parser para convertir texto plano de normas legales chilenas a XML.
    
    Ejemplo de uso:
        parser = NormaTextParser()
        xml = parser.parse_text(texto, metadatos={'tipo': 'Ley', 'numero': '19496'})
    """
    
    NAMESPACE = "https://leychile.cl/schema/ley/v1"
    VERSION = "1.0"
    
    def __init__(self):
        self.contador_ids = 0
    
    def _generar_id(self) -> str:
        """Genera un ID único para elementos."""
        self.contador_ids += 1
        return str(self.contador_ids)
    
    def _preprocesar_texto(self, texto: str) -> str:
        """Preprocesa el texto para normalizar formato."""
        # Normalizar saltos de línea
        texto = texto.replace('\r\n', '\n').replace('\r', '\n')
        # Eliminar líneas vacías múltiples
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        return texto.strip()
    
    def _extraer_encabezado(self, texto: str) -> tuple[str, str]:
        """
        Extrae el encabezado (preámbulo) del texto.
        Retorna (encabezado, resto_del_texto).
        """
        # Buscar el primer artículo o división
        patron_inicio_contenido = re.compile(
            r'^(ART[ÍI]CULO|Art\.?|LIBRO|T[ÍI]TULO|CAP[ÍI]TULO)\s+',
            re.IGNORECASE | re.MULTILINE
        )
        
        match = patron_inicio_contenido.search(texto)
        if match:
            encabezado = texto[:match.start()].strip()
            contenido = texto[match.start():].strip()
            return encabezado, contenido
        
        # Si no se encuentra, todo es encabezado
        return texto, ""
    
    def _identificar_division(self, linea: str) -> tuple[TipoDivision, str] | None:
        """Identifica si una línea es el inicio de una división."""
        linea_limpia = linea.strip()
        for patron, tipo in PATRONES_DIVISION:
            if patron.match(linea_limpia):
                return (tipo, linea_limpia)
        return None
    
    def _identificar_articulo(self, linea: str, linea_anterior: str = "") -> dict | None:
        """
        Identifica si una línea es el inicio de un artículo.
        linea_anterior ayuda a filtrar falsos positivos.
        
        IMPORTANTE: Solo reconoce artículos que comienzan con mayúscula
        ('Artículo', 'ARTÍCULO', 'Art.') para evitar falsos positivos
        con referencias en el texto ('artículo 5').
        """
        linea_limpia = linea.strip()
        
        # Debe empezar con mayúscula: "Artículo", "ARTÍCULO" o "Art."
        # NO coincide con "artículo" (minúscula inicial) que es una referencia
        if not (linea_limpia.startswith(('Artículo', 'ARTÍCULO', 'Articulo', 'ARTICULO', 'Art.', 'Art '))):
            return None
        
        # Primero probar artículos transitorios con texto (PRIMERO, SEGUNDO, etc.)
        match_trans = PATRON_ARTICULO_TRANSITORIO.match(linea_limpia)
        if match_trans:
            numero = match_trans.group(2).upper()
            return {
                'numero': numero,
                'texto_restante': linea_limpia[match_trans.end():].strip(),
                'transitorio': True
            }
        
        # Probar artículos transitorios numerados (Artículo 1 TRANSITORIO, etc.)
        match_trans_num = PATRON_ARTICULO_TRANS_NUM.match(linea_limpia)
        if match_trans_num:
            numero = match_trans_num.group(2)
            sufijo = match_trans_num.group(3)
            if sufijo:
                numero = f"{numero} {sufijo.upper()} TRANSITORIO"
            else:
                numero = f"{numero} TRANSITORIO"
            return {
                'numero': numero,
                'texto_restante': linea_limpia[match_trans_num.end():].strip(),
                'transitorio': True
            }
        
        # Probar artículos con letra simple (Artículo 355 A.-)
        match_letra = PATRON_ARTICULO_LETRA.match(linea_limpia)
        if match_letra:
            numero = f"{match_letra.group(2)} {match_letra.group(3).upper()}"
            return {
                'numero': numero,
                'texto_restante': linea_limpia[match_letra.end():].strip(),
                'transitorio': False
            }
        
        # Luego probar artículos numerados estándar
        match = PATRON_ARTICULO.match(linea_limpia)
        if match:
            numero = match.group(2)
            sufijo = match.group(3)
            
            if sufijo:
                # Sufijos latinos (BIS, TER, QUÁTER, etc.)
                numero = f"{numero} {sufijo.upper()}"
            
            return {
                'numero': numero,
                'texto_restante': linea_limpia[match.end():].strip(),
                'transitorio': False
            }
        return None
    
    def _estructurar_contenido_articulo(self, texto: str) -> list[ElementoContenido]:
        """Analiza el contenido de un artículo y detecta incisos, letras, etc."""
        elementos: list[ElementoContenido] = []
        lineas = texto.split('\n')
        buffer: list[str] = []
        
        for linea in lineas:
            linea_strip = linea.strip()
            if not linea_strip:
                continue
            
            # Detectar inciso numérico
            match_inciso = PATRON_INCISO_NUMERO.match(linea_strip)
            if match_inciso:
                if buffer:
                    elementos.append(ElementoContenido(
                        tipo='parrafo',
                        texto=' '.join(buffer)
                    ))
                    buffer = []
                elementos.append(ElementoContenido(
                    tipo='inciso',
                    numero=match_inciso.group(1),
                    texto=match_inciso.group(2)
                ))
                continue
            
            # Detectar letra
            match_letra = PATRON_INCISO_LETRA.match(linea_strip)
            if match_letra:
                if buffer:
                    elementos.append(ElementoContenido(
                        tipo='parrafo',
                        texto=' '.join(buffer)
                    ))
                    buffer = []
                elementos.append(ElementoContenido(
                    tipo='letra',
                    numero=match_letra.group(1).lower(),
                    texto=match_letra.group(2)
                ))
                continue
            
            # Acumular en buffer
            buffer.append(linea_strip)
        
        # Vaciar buffer final
        if buffer:
            elementos.append(ElementoContenido(
                tipo='parrafo',
                texto=' '.join(buffer)
            ))
        
        return elementos
    
    def _extraer_referencias(self, texto: str) -> list[str]:
        """Extrae referencias a otros artículos mencionados en el texto."""
        referencias = set()
        for match in PATRON_REFERENCIA.finditer(texto):
            # Extraer números de la coincidencia
            nums = re.findall(r'\d+', match.group(1))
            referencias.update(nums)
        return sorted(referencias, key=lambda x: int(x) if x.isdigit() else 0)
    
    def _parsear_contenido(self, texto: str) -> list[Division | Articulo]:
        """
        Parsea el contenido del articulado.
        Retorna una lista de divisiones y artículos.
        """
        lineas = texto.split('\n')
        elementos: list[Division | Articulo] = []
        pila_divisiones: list[Division] = []
        articulo_actual: Articulo | None = None
        buffer_texto: list[str] = []
        
        def finalizar_articulo():
            nonlocal articulo_actual, buffer_texto
            if articulo_actual:
                texto_completo = '\n'.join(buffer_texto).strip()
                articulo_actual.texto = texto_completo
                articulo_actual.contenido_estructurado = self._estructurar_contenido_articulo(texto_completo)
                articulo_actual.referencias = self._extraer_referencias(texto_completo)
                
                # Agregar al padre o a la lista principal
                if pila_divisiones:
                    pila_divisiones[-1].hijos.append(articulo_actual)
                else:
                    elementos.append(articulo_actual)
                
                articulo_actual = None
                buffer_texto = []
        
        def obtener_contexto() -> str:
            """Construye el contexto jerárquico actual."""
            if not pila_divisiones:
                return ""
            return " > ".join(d.titulo for d in pila_divisiones)
        
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            linea_strip = linea.strip()
            
            # Saltar líneas vacías
            if not linea_strip:
                if articulo_actual:
                    buffer_texto.append('')
                i += 1
                continue
            
            # ¿Es una división?
            div_info = self._identificar_division(linea_strip)
            if div_info:
                finalizar_articulo()
                tipo_div, titulo_div = div_info
                
                # Cerrar divisiones de menor o igual jerarquía
                while pila_divisiones:
                    if JERARQUIA_DIVISIONES[pila_divisiones[-1].tipo] <= JERARQUIA_DIVISIONES[tipo_div]:
                        div_cerrada = pila_divisiones.pop()
                        if pila_divisiones:
                            pila_divisiones[-1].hijos.append(div_cerrada)
                        else:
                            elementos.append(div_cerrada)
                    else:
                        break
                
                # Crear nueva división
                nueva_div = Division(
                    id=self._generar_id(),
                    tipo=tipo_div,
                    titulo=titulo_div,
                    texto=titulo_div,
                    contexto=obtener_contexto()
                )
                pila_divisiones.append(nueva_div)
                i += 1
                continue
            
            # ¿Es un artículo?
            art_info = self._identificar_articulo(linea_strip)
            if art_info:
                finalizar_articulo()
                articulo_actual = Articulo(
                    id=self._generar_id(),
                    numero=art_info['numero'],
                    texto="",
                    contexto=obtener_contexto()
                )
                if art_info['texto_restante']:
                    buffer_texto.append(linea_strip)
                else:
                    buffer_texto.append(linea_strip)
                i += 1
                continue
            
            # Texto normal
            if articulo_actual:
                buffer_texto.append(linea_strip)
            
            i += 1
        
        # Finalizar último artículo
        finalizar_articulo()
        
        # Cerrar divisiones restantes
        while pila_divisiones:
            div = pila_divisiones.pop()
            if pila_divisiones:
                pila_divisiones[-1].hijos.append(div)
            else:
                elementos.append(div)
        
        return elementos
    
    def _contar_elementos(self, elementos: list) -> dict:
        """Cuenta artículos, libros, títulos, etc."""
        contadores = {
            'articulos': 0,
            'libros': 0,
            'titulos': 0,
            'capitulos': 0
        }
        
        def contar_recursivo(elem):
            if isinstance(elem, Articulo):
                contadores['articulos'] += 1
            elif isinstance(elem, Division):
                if elem.tipo == TipoDivision.LIBRO:
                    contadores['libros'] += 1
                elif elem.tipo == TipoDivision.TITULO:
                    contadores['titulos'] += 1
                elif elem.tipo == TipoDivision.CAPITULO:
                    contadores['capitulos'] += 1
                for hijo in elem.hijos:
                    contar_recursivo(hijo)
        
        for elem in elementos:
            contar_recursivo(elem)
        
        return contadores
    
    def _elemento_a_xml(self, elem: Division | Articulo, padre: Element):
        """Convierte un elemento (División o Artículo) a XML."""
        if isinstance(elem, Articulo):
            art_elem = SubElement(padre, 'articulo')
            art_elem.set('id', elem.id)
            art_elem.set('tipo_original', 'Artículo')
            art_elem.set('numero', elem.numero)
            
            if elem.contexto:
                SubElement(art_elem, 'contexto').text = elem.contexto
            
            # Decidir si usar <texto> o <contenido>
            if len(elem.contenido_estructurado) > 1 or any(
                e.tipo in ('inciso', 'letra') for e in elem.contenido_estructurado
            ):
                contenido = SubElement(art_elem, 'contenido')
                for item in elem.contenido_estructurado:
                    if item.tipo == 'parrafo':
                        SubElement(contenido, 'parrafo').text = item.texto
                    elif item.tipo == 'inciso':
                        inciso = SubElement(contenido, 'inciso')
                        inciso.set('numero', item.numero)
                        inciso.text = item.texto
                    elif item.tipo == 'letra':
                        # Las letras van como párrafos con el formato a), b)
                        SubElement(contenido, 'parrafo').text = f"{item.numero}) {item.texto}"
            else:
                SubElement(art_elem, 'texto').text = elem.texto
            
            # Referencias
            if elem.referencias:
                refs = SubElement(art_elem, 'referencias')
                for ref in elem.referencias:
                    ref_elem = SubElement(refs, 'ref')
                    ref_elem.set('articulo', ref)
        
        elif isinstance(elem, Division):
            # Mapear tipo a nombre de elemento
            nombre_elem = {
                TipoDivision.LIBRO: 'libro',
                TipoDivision.TITULO: 'titulo',
                TipoDivision.CAPITULO: 'capitulo',
                TipoDivision.PARRAFO: 'parrafo',
                TipoDivision.SECCION: 'seccion',
            }.get(elem.tipo, 'seccion')
            
            div_elem = SubElement(padre, nombre_elem)
            div_elem.set('id', elem.id)
            div_elem.set('tipo_original', elem.tipo.value.capitalize())
            
            SubElement(div_elem, 'titulo_seccion').text = elem.titulo
            if elem.contexto:
                SubElement(div_elem, 'contexto').text = elem.contexto
            SubElement(div_elem, 'texto').text = elem.texto
            
            # Procesar hijos
            for hijo in elem.hijos:
                self._elemento_a_xml(hijo, div_elem)
    
    def parse_text(
        self,
        texto: str,
        metadatos: dict,
        estado: str = "vigente"
    ) -> str:
        """
        Convierte texto plano de una norma legal a XML.
        
        Args:
            texto: Texto plano de la norma
            metadatos: Diccionario con metadatos (tipo, numero, titulo, etc.)
            estado: Estado de vigencia ('vigente', 'derogada', 'parcial')
        
        Returns:
            String XML formateado
        """
        self.contador_ids = 0
        
        # Preprocesar
        texto = self._preprocesar_texto(texto)
        
        # Extraer encabezado y contenido
        encabezado, contenido = self._extraer_encabezado(texto)
        
        # Parsear contenido
        elementos = self._parsear_contenido(contenido) if contenido else []
        
        # Contar elementos
        contadores = self._contar_elementos(elementos)
        
        # Construir XML
        root = Element('ley')
        root.set('xmlns', self.NAMESPACE)
        root.set('version', self.VERSION)
        root.set('idioma', 'es-CL')
        root.set('tipo', metadatos.get('tipo', 'Ley'))
        root.set('numero', str(metadatos.get('numero', '')))
        root.set('estado', estado)
        root.set('generado', datetime.now().isoformat())
        
        if metadatos.get('id_norma'):
            root.set('id_norma', str(metadatos['id_norma']))
        if metadatos.get('fecha_promulgacion'):
            root.set('fecha_promulgacion', metadatos['fecha_promulgacion'])
        if metadatos.get('fecha_publicacion'):
            root.set('fecha_publicacion', metadatos['fecha_publicacion'])
        if metadatos.get('url_original'):
            root.set('url_original', metadatos['url_original'])
        
        # Metadatos
        meta_elem = SubElement(root, 'metadatos')
        SubElement(meta_elem, 'titulo').text = metadatos.get('titulo', '')
        
        ident = SubElement(meta_elem, 'identificacion')
        SubElement(ident, 'tipo').text = metadatos.get('tipo', 'Ley')
        SubElement(ident, 'numero').text = str(metadatos.get('numero', ''))
        
        if metadatos.get('organismo'):
            orgs = SubElement(meta_elem, 'organismos')
            SubElement(orgs, 'organismo').text = metadatos['organismo']
        
        if metadatos.get('materias'):
            mats = SubElement(meta_elem, 'materias')
            for mat in metadatos['materias']:
                SubElement(mats, 'materia').text = mat
        
        if metadatos.get('nombres_comunes'):
            nombres = SubElement(meta_elem, 'nombres_comunes')
            for nombre in metadatos['nombres_comunes']:
                SubElement(nombres, 'nombre').text = nombre
        
        fechas = SubElement(meta_elem, 'fechas')
        if metadatos.get('fecha_promulgacion'):
            SubElement(fechas, 'promulgacion').text = metadatos['fecha_promulgacion']
        if metadatos.get('fecha_publicacion'):
            SubElement(fechas, 'publicacion').text = metadatos['fecha_publicacion']
        
        SubElement(meta_elem, 'fuente').text = metadatos.get('fuente', 'Texto manual')
        
        # Encabezado
        SubElement(root, 'encabezado').text = encabezado
        
        # Contenido
        cont_elem = SubElement(root, 'contenido')
        cont_elem.set('total_articulos', str(contadores['articulos']))
        cont_elem.set('total_libros', str(contadores['libros']))
        cont_elem.set('total_titulos', str(contadores['titulos']))
        cont_elem.set('total_capitulos', str(contadores['capitulos']))
        
        for elem in elementos:
            self._elemento_a_xml(elem, cont_elem)
        
        # Formatear XML
        xml_str = tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ", encoding=None)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def texto_a_xml(
    texto: str,
    tipo: str,
    numero: str,
    titulo: str,
    **kwargs
) -> str:
    """
    Función de conveniencia para convertir texto a XML.
    
    Args:
        texto: Texto plano de la norma
        tipo: Tipo de norma ('Ley', 'Decreto', etc.)
        numero: Número de la norma
        titulo: Título de la norma
        **kwargs: Metadatos adicionales
    
    Returns:
        String XML
    
    Ejemplo:
        xml = texto_a_xml(
            texto_ley,
            tipo='Ley',
            numero='19496',
            titulo='Ley de Protección al Consumidor',
            organismo='MINISTERIO DE ECONOMÍA'
        )
    """
    parser = NormaTextParser()
    metadatos = {
        'tipo': tipo,
        'numero': numero,
        'titulo': titulo,
        **kwargs
    }
    return parser.parse_text(texto, metadatos)


# ═══════════════════════════════════════════════════════════════════════════════
# EJEMPLO DE USO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Texto de ejemplo
    texto_ejemplo = """
LEY NÚM. 12345

ESTABLECE NORMAS DE EJEMPLO

Teniendo presente que el H. Congreso Nacional ha dado su aprobación al siguiente

Proyecto de ley:

TÍTULO I
Disposiciones generales

Artículo 1º.- Esta es una ley de ejemplo para demostrar el funcionamiento del parser.

Artículo 2º.- Para los efectos de esta ley se entenderá por:
a) Ejemplo: algo que sirve de modelo
b) Parser: analizador sintáctico
c) XML: formato de marcado extensible

Artículo 3º.- Los derechos establecidos en esta ley son:
1) El derecho a entender el código
2) El derecho a modificarlo
3) El derecho a compartirlo

TÍTULO II
De las obligaciones

Párrafo 1º
Obligaciones generales

Artículo 4º.- Toda persona debe leer la documentación antes de usar el software.

Artículo 5º.- Se aplicarán las disposiciones del artículo 1 en lo que corresponda.
Ver también artículos 2 y 3.
"""
    
    # Parsear
    parser = NormaTextParser()
    xml_resultado = parser.parse_text(
        texto_ejemplo,
        metadatos={
            'tipo': 'Ley',
            'numero': '12345',
            'titulo': 'ESTABLECE NORMAS DE EJEMPLO',
            'organismo': 'MINISTERIO DE JUSTICIA',
            'materias': ['Ejemplo', 'Documentación'],
            'fecha_publicacion': '2026-01-12'
        }
    )
    
    print(xml_resultado)
