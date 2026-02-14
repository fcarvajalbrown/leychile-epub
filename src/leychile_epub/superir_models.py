"""Modelos de datos específicos para normas SUPERIR.

Dataclasses que representan la estructura semántica de NCGs e Instructivos
de la Superintendencia de Insolvencia y Reemprendimiento, complementando
el modelo Norma genérico con campos estructurados del dominio.

El schema de referencia es superir_v1.xsd.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from leychile_epub.scraper_v2 import Norma


@dataclass
class ConsiderandoItem:
    """Un considerando individual numerado.

    Ejemplo:
        1° Que, el artículo 54° de la Ley ordena que...
        → ConsiderandoItem(numero=1, texto="Que, el artículo 54° de la Ley ordena que...")
    """

    numero: int
    texto: str


@dataclass
class Firmante:
    """Persona que firma la norma.

    Ejemplo:
        JOSEFINA MONTENEGRO ARANEDA
        Superintendenta de Insolvencia y Reemprendimiento
        → Firmante(nombre="JOSEFINA MONTENEGRO ARANEDA",
                   cargo="SUPERINTENDENTA DE INSOLVENCIA Y REEMPRENDIMIENTO")
    """

    nombre: str
    cargo: str


@dataclass
class CierreSuperir:
    """Cierre estructurado de una norma SUPERIR.

    Separa la fórmula de cierre ("Anótese y publíquese.") del firmante.
    Incluye opcionalmente código de distribución interna.
    """

    formula: str
    firmante: Firmante | None = None
    distribucion: str = ""
    destinatarios_notificacion: str = ""


@dataclass
class ActoAdministrativo:
    """Resolución Exenta que envuelve una NCG.

    Usado cuando la NCG se aprueba mediante un acto administrativo formal.
    Ejemplo: Resolución Exenta N.° 6597 que aprueba NCG N.° 14.
    """

    tipo: str  # "RESOLUCIÓN EXENTA"
    numero: str  # "6597"
    materia: str  # "APRUEBA LA NORMA DE CARÁCTER GENERAL N.° 14..."


@dataclass
class PuntoResolutivo:
    """Punto del resolutivo de un acto administrativo.

    Ejemplo:
        1) APRUÉBESE la siguiente Norma de Carácter General...
        → PuntoResolutivo(numero="1", texto="APRUÉBESE la siguiente...")
    """

    numero: str
    texto: str


@dataclass
class SubitemModel:
    """Subitem dentro de un item de listado.

    Soporta subitems numerados (romanos) y letrados.

    Ejemplo numerado:
        i. Los postulantes a integrar la Nómina...
        → SubitemModel(numero="i", texto="Los postulantes a integrar la Nómina...")

    Ejemplo letrado:
        a) aquellos que proporcionan evidencia...
        → SubitemModel(letra="a", texto="aquellos que proporcionan evidencia...")
    """

    numero: str = ""  # "i", "ii", "iii", "iv", "v"
    letra: str = ""  # "a", "b", "c"
    texto: str = ""


@dataclass
class ItemContentBlock:
    """An ordered content element within a complex item.

    Supports interleaved sublistados and paragraphs within an item,
    as seen in NCG 20 Art 1° item A (a.1 → parrafo → a.2).

    Attributes:
        tipo: "parrafo" or "sublistado"
        texto: Text content (for parrafo blocks)
        subitems: Subitems (for sublistado blocks)
    """

    tipo: str  # "parrafo" or "sublistado"
    texto: str = ""  # for parrafo
    subitems: list[SubitemModel] = field(default_factory=list)  # for sublistado


@dataclass
class ItemListado:
    """Item de un listado dentro de un artículo.

    Soporta items simples (solo texto) y complejos (con subitems).

    Ejemplo simple:
        a) Vale vista o boleta bancaria...
        → ItemListado(letra="a", texto="Vale vista o boleta bancaria...")

    Ejemplo numerado:
        1. Que se encuentre debidamente incorporado...
        → ItemListado(numero="1", texto="Que se encuentre debidamente incorporado...")

    Ejemplo complejo con subitems:
        a) Veedores Concursales: Deberán presentarse...
           i. Los postulantes...  ii. Aquellos que integren...
        → ItemListado(letra="a", nombre="Veedores Concursales",
                      parrafos=["Deberán presentarse..."],
                      subitems=[SubitemModel("i", "Los postulantes..."), ...])

    Ejemplo complejo con subitems y párrafos post-sublistado (NCG 19 Art 1° E):
        E.- Deberán constar los "Hechos Posteriores"...
            a) aquellos que proporcionan evidencia...
            b) aquellos que proporcionan evidencia...
            Estos hechos posteriores pueden referirse...
        → ItemListado(letra="E", parrafos=["Deberán constar..."],
                      subitems=[SubitemModel(letra="a", ...)],
                      parrafos_post=["Estos hechos posteriores..."])

    Ejemplo complejo con subitems intercalados (NCG 20 Art 1° A):
        A. Constatar e informar...
           a.1) Lo anterior deberá...
           En caso de que...
           a.2) En caso de haberse...
        → ItemListado(letra="A", content_blocks=[...])
    """

    letra: str = ""
    numero: str = ""
    nombre: str = ""
    texto: str = ""  # Simple text content (backward compatible)
    parrafos: list[str] = field(default_factory=list)  # Complex: paragraphs before sublistado
    subitems: list[SubitemModel] = field(default_factory=list)  # Complex: nested subitems
    parrafos_post: list[str] = field(default_factory=list)  # Paragraphs after sublistado
    content_blocks: list[ItemContentBlock] = field(default_factory=list)  # Interleaved content


@dataclass
class RequisitoItemModel:
    """Item letrado dentro de un requisito (I, II, III...).

    Ejemplo simple:
        a) Ingresos: Deberá detallarse cada cuenta...
        → RequisitoItemModel(letra="a", nombre="Ingresos", texto="Deberá detallarse...")

    Ejemplo complejo (multi-párrafo):
        d) Provisión para Gastos Finales: <parrafo1> <parrafo2>
        → RequisitoItemModel(letra="d", nombre="Provisión para Gastos Finales",
                             parrafos=["<parrafo1>", "<parrafo2>"])
    """

    letra: str
    nombre: str = ""
    texto: str = ""  # Items simples (una sola oración)
    parrafos: list[str] = field(default_factory=list)  # Items complejos (multi-párrafo)


@dataclass
class RequisitoModel:
    """Requisito numerado con romanos (I, II, III) dentro de un artículo.

    Ejemplo:
        I.- Tener una carátula...
        → RequisitoModel(numero="I", parrafos=["Tener una carátula..."])

    Un requisito puede contener solo párrafos (III, IV, V) o
    párrafos + items letrados (I, II).
    """

    numero: str
    nombre: str = ""
    parrafos: list[str] = field(default_factory=list)
    items: list[RequisitoItemModel] = field(default_factory=list)


@dataclass
class AnexoStandalone:
    """Anexo standalone a nivel raíz (pendiente de modelado detallado).

    Usado cuando el anexo es un formulario complejo cuya estructura
    interna no se modela en XML (se marca pendiente="true").

    Ejemplo:
        <anexo numero="I" titulo="Modelo de presentación..." pendiente="true"/>
    """

    numero: str
    titulo: str = ""
    pendiente: bool = True


@dataclass
class ContenidoArticulo:
    """Contenido estructurado de un artículo SUPERIR.

    Un artículo puede tener párrafos de texto libre, listados letrados,
    incisos numerados, requisitos (I-V) y referencias a anexos.
    """

    parrafos: list[str] = field(default_factory=list)
    listado: list[ItemListado] = field(default_factory=list)
    parrafos_post: list[str] = field(default_factory=list)
    incisos: list[str] = field(default_factory=list)
    requisitos: list[RequisitoModel] = field(default_factory=list)
    referencia_anexo: str = ""


@dataclass
class NormaSuperir:
    """Modelo enriquecido para normas SUPERIR (NCGs e Instructivos).

    Usa composición: envuelve el modelo Norma genérico y agrega campos
    estructurados específicos del dominio SUPERIR.

    Attributes:
        norma_base: Modelo Norma genérico con datos básicos.
        considerandos: Lista de considerandos individuales numerados.
        cierre: Cierre estructurado (fórmula + firmante).
        articulos_epigrafe: Mapeo de número de artículo a su epígrafe.
            Ejemplo: {"1": "Modelo", "2": "Ámbito de aplicación"}
        articulos_contenido: Mapeo de número de artículo a contenido estructurado.
            Solo se popula para artículos con listados u otra estructura especial.
    """

    norma_base: Norma
    considerandos: list[ConsiderandoItem] = field(default_factory=list)
    cierre: CierreSuperir | None = None
    articulos_epigrafe: dict[str, str] = field(default_factory=dict)
    articulos_contenido: dict[str, ContenidoArticulo] = field(default_factory=dict)
    formula_dictacion: str = ""
    anexos_standalone: list[AnexoStandalone] = field(default_factory=list)
    # Nuevos campos para NCGs envueltas en Resolución Exenta
    acto_administrativo: ActoAdministrativo | None = None
    resolutivo: list[PuntoResolutivo] = field(default_factory=list)
    preambulo_ncg: list[str] = field(default_factory=list)
    resolutivo_final: list[PuntoResolutivo] = field(default_factory=list)
