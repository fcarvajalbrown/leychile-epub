"""
Interfaz web (Streamlit) para LeyChile ePub Generator.

Ejecutar con:
    streamlit run app.py

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import tempfile
from pathlib import Path

import streamlit as st

from leychile_epub import __version__
from leychile_epub.exceptions import LeyChileError
from leychile_epub.generator_v2 import EPubGeneratorV2
from leychile_epub.scraper_v2 import BCNLawScraperV2

st.set_page_config(
    page_title="LeyChile ePub Generator",
    page_icon="📚",
    layout="centered",
)

st.title("📚 LeyChile ePub Generator")
st.caption(f"v{__version__} — Genera ePub profesionales de legislación chilena")

url = st.text_input(
    "URL de LeyChile",
    placeholder="https://www.leychile.cl/Navegar?idNorma=242302",
    help="Pega la URL de cualquier norma de leychile.cl o bcn.cl",
)

if st.button("Generar ePub", type="primary", disabled=not url):
    with st.status("Generando ePub...", expanded=True) as status:
        try:
            st.write("Extrayendo datos de la BCN...")
            scraper = BCNLawScraperV2()
            norma = scraper.scrape(url)

            if not norma:
                st.error("No se pudo obtener datos de la norma.")
                st.stop()

            titulo = norma.titulo_completo
            st.write(f"Norma encontrada: **{titulo}**")

            st.write("Generando ePub profesional...")
            generator = EPubGeneratorV2()

            with tempfile.TemporaryDirectory() as tmpdir:
                filename = norma.nombre_archivo + ".epub"
                output_path = Path(tmpdir) / filename
                epub_path = generator.generate(norma, output_path)

                epub_bytes = epub_path.read_bytes()
                size_kb = len(epub_bytes) / 1024

            status.update(label="ePub generado", state="complete", expanded=True)

            st.success(f"**{titulo}** — {size_kb:.1f} KB")
            st.download_button(
                label=f"Descargar {filename}",
                data=epub_bytes,
                file_name=filename,
                mime="application/epub+zip",
            )

        except LeyChileError as e:
            status.update(label="Error", state="error")
            st.error(f"Error: {e.message}")
        except Exception as e:
            status.update(label="Error", state="error")
            st.error(f"Error inesperado: {e}")

with st.expander("Información"):
    st.markdown(
        """
        **Fuente**: [Biblioteca del Congreso Nacional de Chile](https://www.bcn.cl/leychile)

        Acepta URLs de:
        - `leychile.cl` — ej: `https://www.leychile.cl/Navegar?idNorma=242302`
        - `bcn.cl` — ej: `https://www.bcn.cl/leychile/navegar?idNorma=242302`
        """
    )
