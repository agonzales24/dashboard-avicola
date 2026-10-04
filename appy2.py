import io
import re
import requests
from bs4 import BeautifulSoup
import PyPDF2
import streamlit as st

# Configuración de la página en Streamlit
st.set_page_config(
    page_title="Reporte MIDAGRI - Precio de Aves", page_icon="📊", layout="centered"
)


# Función para extraer los datos (optimizada sin Selenium)
@st.cache_data(
    ttl=3600
)  # Cachea los resultados por 1 hora para no sobrecargar la web del ministerio
def obtener_datos_midagri():
  url_coleccion = "https://www.gob.pe/institucion/midagri/colecciones/4-boletin-diario-de-comercializacion-y-precio-de-aves"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  # 1. Obtener la página de la colección
  response = requests.get(url_coleccion, headers=headers)
  if response.status_code != 200:
    return None, None, None, "No se pudo acceder a la colección del MIDAGRI."

  soup = BeautifulSoup(response.text, "html.parser")

  # Buscar el enlace de la primera publicación (mes más reciente)
  publicacion_link = None
  for a in soup.find_all("a", href=True):
    if "Boletin de comercializacion" in a.text or "boletin-diario" in a["href"]:
      publicacion_link = "https://www.gob.pe" + a["href"]
      break

  if not publicacion_link:
    # Intento alternativo buscando enlaces directos
    for a in soup.select("a.link-item"):
      publicacion_link = "https://www.gob.pe" + a["href"]
      break

  if not publicacion_link:
    return (
        None,
        None,
        None,
        "No se pudo encontrar el enlace de la última publicación.",
    )

  # 2. Entrar a la página de la publicación para buscar el PDF
  resp_pub = requests.get(publicacion_link, headers=headers)
  soup_pub = BeautifulSoup(resp_pub.text, "html.parser")

  url_del_pdf = None
  for a in soup_pub.find_all("a", href=True):
    if ".pdf" in a["href"].lower() or "descargar" in a.text.lower():
      href = a["href"]
      url_del_pdf = href if href.startswith("http") else "https://www.gob.pe" + href
      break

  if not url_del_pdf:
    return None, None, None, "No se pudo hallar el enlace de descarga del PDF."

  # 3. Descargar y leer el PDF en memoria
  resp_pdf = requests.get(url_del_pdf)
  if resp_pdf.status_code == 200:
    archivo_pdf = io.BytesIO(resp_pdf.content)
    lector = PyPDF2.PdfReader(archivo_pdf)

    # Extraer fecha y precio mayorista (Página 1)
    texto_primera_pagina = lector.pages[0].extract_text()

    match_fecha = re.search(
        r"([a-záéíóú]+,\s*\d{1,2}\s*de\s*[a-záéíóú]+\s*de\s*\d{4})",
        texto_primera_pagina,
        re.IGNORECASE,
    )
    fecha_boletin = (
        match_fecha.group(1).capitalize()
        if match_fecha
        else "Fecha no detectada"
    )

    match_mayorista = re.search(r"S/\s*(\d+\.\d+)", texto_primera_pagina)
    precio_mayorista = (
        f"S/ {match_mayorista.group(1)}" if match_mayorista else "No detectado"
    )

    # Extraer precio de Granja
    texto_completo = " ".join(
        [pagina.extract_text() for pagina in lector.pages]
    )
    texto_limpio = " ".join(texto_completo.split())

    match_granja = re.search(
        r"Granja[^\d]*(\d+\.\d+)[^\d]*(\d+\.\d+)[^\d]*(\d+\.\d+)",
        texto_limpio,
        re.IGNORECASE,
    )
    precio_granja = (
        f"S/ {match_granja.group(3)}" if match_granja else "No detectado"
    )

    return fecha_boletin, precio_mayorista, precio_granja, url_del_pdf

  return None, None, None, "Error al descargar el archivo PDF."


# Interfaz en Streamlit
st.title("📊 Reporte de Precios - MIDAGRI")
st.markdown("Consulta en tiempo real el boletín diario de comercialización de aves.")

if st.button("🔄 Cargar / Actualizar Datos"):
  with st.spinner(
      "Conectando con MIDAGRI y procesando el último boletín en PDF..."
  ):
    fecha, mayorista, granja, pdf_url = obtener_datos_midagri()

    if fecha:
      st.success("¡Datos obtenidos exitosamente!")

      st.markdown(f"### 📅 Fecha del Boletín: *{fecha}*")

      # Visualización en columnas tipo tarjeta
      col1, col2 = st.columns(2)

      with col1:
        st.metric(
            label="Pollo al por mayor (Promedio)",
            value=f"{mayorista} / kg",
            delta="Mayorista",
        )

      with col2:
        st.metric(
            label="Precio de Granja (Día actual)",
            value=f"{granja} / kg",
            delta="Granja",
        )

      st.markdown("---")
      st.markdown(
          f"📄 **[Descargar / Ver PDF Original del MIDAGRI]({pdf_url})**",
          unsafe_allow_html=True,
      )
    else:
      st.error(f"❌ Ocurrió un error: {pdf_url}")
else:
  st.info(
      "Haz clic en el botón de arriba para buscar y analizar el boletín más"
      " reciente."
  )
