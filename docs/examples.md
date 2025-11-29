# 📋 Ejemplos de Uso

Esta página contiene ejemplos prácticos de uso de LeyChile ePub Generator.

## Ejemplos del CLI

### Leyes Más Buscadas

```bash
# Constitución Política de la República
leychile-epub https://www.leychile.cl/Navegar?idNorma=242302 -o ./constitucional/

# Código Civil
leychile-epub https://www.leychile.cl/Navegar?idNorma=172986 -o ./codigos/

# Código Penal
leychile-epub https://www.leychile.cl/Navegar?idNorma=1984 -o ./codigos/

# Código del Trabajo
leychile-epub https://www.leychile.cl/Navegar?idNorma=207436 -o ./laboral/

# Código de Procedimiento Civil
leychile-epub https://www.leychile.cl/Navegar?idNorma=22740 -o ./procesal/

# Código de Procedimiento Penal
leychile-epub https://www.leychile.cl/Navegar?idNorma=176595 -o ./procesal/

# Código Tributario
leychile-epub https://www.leychile.cl/Navegar?idNorma=6374 -o ./tributario/

# Código de Aguas
leychile-epub https://www.leychile.cl/Navegar?idNorma=5605 -o ./recursos/

# Código Sanitario
leychile-epub https://www.leychile.cl/Navegar?idNorma=5595 -o ./salud/

# Código de Minería
leychile-epub https://www.leychile.cl/Navegar?idNorma=29668 -o ./mineria/
```

### Leyes Laborales

```bash
# Crear directorio
mkdir -p ./biblioteca/laboral

# Descargar leyes
leychile-epub https://www.leychile.cl/Navegar?idNorma=207436 -o ./biblioteca/laboral/  # Código del Trabajo
leychile-epub https://www.leychile.cl/Navegar?idNorma=30667 -o ./biblioteca/laboral/   # Ley de Accidentes del Trabajo
leychile-epub https://www.leychile.cl/Navegar?idNorma=141344 -o ./biblioteca/laboral/  # Ley de Subcontratación
```

### Procesamiento Masivo

Crea un archivo `biblioteca_legal.txt`:

```text
# Códigos fundamentales
https://www.leychile.cl/Navegar?idNorma=172986
https://www.leychile.cl/Navegar?idNorma=1984
https://www.leychile.cl/Navegar?idNorma=207436

# Leyes electorales
https://www.leychile.cl/Navegar?idNorma=242302

# Leyes tributarias
https://www.leychile.cl/Navegar?idNorma=6374
```

Ejecuta:

```bash
leychile-epub --batch biblioteca_legal.txt -o ./biblioteca_completa/
```

## Ejemplos de Python

### Script Básico

```python
#!/usr/bin/env python3
"""
Script básico para generar un ePub de una ley chilena.
"""
from leychile_epub import BCNLawScraper, LawEpubGenerator

def main():
    url = "https://www.leychile.cl/Navegar?idNorma=242302"
    
    # Extraer datos
    scraper = BCNLawScraper()
    print("Extrayendo datos de la ley...")
    law_data = scraper.scrape_law(url)
    
    # Mostrar información
    metadata = law_data.get("metadata", {})
    print(f"Ley: {metadata.get('type')} {metadata.get('number')}")
    print(f"Título: {metadata.get('title')}")
    
    # Generar ePub
    generator = LawEpubGenerator()
    print("Generando ePub...")
    epub_path = generator.generate(law_data, output_dir="./output")
    
    print(f"✅ ePub generado: {epub_path}")

if __name__ == "__main__":
    main()
```

### Biblioteca Legal Personal

```python
#!/usr/bin/env python3
"""
Crea una biblioteca legal personal con múltiples leyes.
"""
from pathlib import Path
from leychile_epub import BCNLawScraper, LawEpubGenerator, NetworkError

# Leyes a descargar organizadas por categoría
LEYES = {
    "constitucional": [
        "https://www.leychile.cl/Navegar?idNorma=242302",  # Constitución
    ],
    "civil": [
        "https://www.leychile.cl/Navegar?idNorma=172986",  # Código Civil
    ],
    "penal": [
        "https://www.leychile.cl/Navegar?idNorma=1984",    # Código Penal
    ],
    "laboral": [
        "https://www.leychile.cl/Navegar?idNorma=207436",  # Código del Trabajo
    ],
}

def crear_biblioteca(base_dir: str = "./mi_biblioteca"):
    scraper = BCNLawScraper()
    generator = LawEpubGenerator()
    
    for categoria, urls in LEYES.items():
        output_dir = Path(base_dir) / categoria
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📂 Categoría: {categoria}")
        
        for url in urls:
            try:
                print(f"  ⏳ Procesando: {url}")
                law_data = scraper.scrape_law(url)
                epub_path = generator.generate(law_data, output_dir=str(output_dir))
                print(f"  ✅ Generado: {epub_path}")
            except NetworkError as e:
                print(f"  ❌ Error de red: {e}")
            except Exception as e:
                print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    crear_biblioteca()
```

### Con Interfaz de Usuario (Click)

```python
#!/usr/bin/env python3
"""
CLI personalizado con Click.
"""
import click
from leychile_epub import BCNLawScraper, LawEpubGenerator

@click.command()
@click.argument("url")
@click.option("-o", "--output", default=".", help="Directorio de salida")
@click.option("-v", "--verbose", is_flag=True, help="Modo verbose")
def generar_epub(url: str, output: str, verbose: bool):
    """Genera un ePub desde una URL de LeyChile."""
    scraper = BCNLawScraper()
    generator = LawEpubGenerator()
    
    if verbose:
        click.echo(f"URL: {url}")
        click.echo(f"Output: {output}")
    
    with click.progressbar(length=100, label="Generando ePub") as bar:
        def update(progress, message):
            bar.update(int(progress * 100) - bar.pos)
        
        law_data = scraper.scrape_law(url)
        bar.update(30)
        
        epub_path = generator.generate(
            law_data, 
            output_dir=output,
            progress_callback=update
        )
    
    click.echo(f"\n✅ Generado: {epub_path}")

if __name__ == "__main__":
    generar_epub()
```

### Servidor Web Simple (Flask)

```python
#!/usr/bin/env python3
"""
Servidor web simple para generar ePubs.
"""
from flask import Flask, request, send_file, render_template_string
from leychile_epub import BCNLawScraper, LawEpubGenerator
import tempfile
import os

app = Flask(__name__)
scraper = BCNLawScraper()
generator = LawEpubGenerator()

HTML = """
<!DOCTYPE html>
<html>
<head><title>LeyChile ePub Generator</title></head>
<body>
    <h1>🇨🇱 LeyChile ePub Generator</h1>
    <form action="/generate" method="post">
        <label>URL de LeyChile:</label><br>
        <input type="url" name="url" size="60" required><br><br>
        <button type="submit">Generar ePub</button>
    </form>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/generate", methods=["POST"])
def generate():
    url = request.form.get("url")
    if not url:
        return "URL requerida", 400
    
    try:
        law_data = scraper.scrape_law(url)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = generator.generate(law_data, output_dir=tmpdir)
            return send_file(
                epub_path,
                as_attachment=True,
                download_name=os.path.basename(epub_path)
            )
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
```

### Análisis de Leyes

```python
#!/usr/bin/env python3
"""
Analiza el contenido de una ley.
"""
from leychile_epub import BCNLawScraper
from collections import Counter

def analizar_ley(url: str):
    scraper = BCNLawScraper()
    law_data = scraper.scrape_law(url)
    
    metadata = law_data.get("metadata", {})
    content = law_data.get("content", [])
    
    # Contar tipos de elementos
    tipos = Counter(item.get("type") for item in content)
    
    # Contar artículos
    articulos = [item for item in content if item.get("type") == "articulo"]
    
    print("=" * 50)
    print(f"📋 {metadata.get('type')} {metadata.get('number')}")
    print(f"📝 {metadata.get('title')}")
    print("=" * 50)
    print(f"\n📊 Estadísticas:")
    print(f"  - Títulos: {tipos.get('titulo', 0)}")
    print(f"  - Párrafos: {tipos.get('parrafo', 0)}")
    print(f"  - Artículos: {len(articulos)}")
    print(f"\n📂 Materias:")
    for subject in metadata.get("subjects", [])[:5]:
        print(f"  - {subject}")

if __name__ == "__main__":
    analizar_ley("https://www.leychile.cl/Navegar?idNorma=242302")
```

## Integración con Otros Servicios

### Guardar en Google Drive

```python
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from leychile_epub import BCNLawScraper, LawEpubGenerator

# Autenticación
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# Generar ePub
scraper = BCNLawScraper()
generator = LawEpubGenerator()
law_data = scraper.scrape_law("https://www.leychile.cl/Navegar?idNorma=242302")
epub_path = generator.generate(law_data)

# Subir a Drive
file = drive.CreateFile({"title": epub_path.split("/")[-1]})
file.SetContentFile(epub_path)
file.Upload()
print(f"Subido a Google Drive: {file['id']}")
```

### Enviar por Email

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from leychile_epub import BCNLawScraper, LawEpubGenerator

def enviar_ley_por_email(url: str, destinatario: str):
    # Generar ePub
    scraper = BCNLawScraper()
    generator = LawEpubGenerator()
    law_data = scraper.scrape_law(url)
    epub_path = generator.generate(law_data)
    
    # Crear email
    msg = MIMEMultipart()
    msg["Subject"] = f"Ley: {law_data['metadata']['title'][:50]}"
    msg["From"] = "tu@email.com"
    msg["To"] = destinatario
    
    # Adjuntar ePub
    with open(epub_path, "rb") as f:
        part = MIMEBase("application", "epub+zip")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={epub_path.split('/')[-1]}")
        msg.attach(part)
    
    # Enviar
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("tu@email.com", "tu_password")
        server.send_message(msg)
```
