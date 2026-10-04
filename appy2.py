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


# Función optimizada y robusta para extraer los datos
@st.cache_data(ttl=3600)
def obtener_datos_midagri():
  url_coleccion = "https://www.gob.pe/institucion/midagri/colecciones/4-boletin-diario-de-comercializacion-y-precio-de-aves"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      )
  }

  try:
    # 1. Obtener la página principal de la colección
    response = requests.get(url_coleccion, headers=headers, timeout=10)
    if response.status_code != 200:
      return (
          None,
          None,
          None,
          f"Error al conectar con la web (Código HTTP: {response.status_code})",
      )

    soup = BeautifulSoup(response.text, "html.parser")

    # Buscar enlaces que lleven a la publicación mensual o diaria
    publicacion_link = None
    for a in soup.find_all("a", href=True):
      texto_enlace = a.get_text().lower()
      href = a["href"]
      if (
          "boletín de comercialización" in texto_enlace
          or "comercializacion y precios de aves" in texto_enlace
      ):
        publicacion_link = (
            href if href.startswith("http") else "https://www.gob.pe" + href
        )
        break

    # Si no encuentra por texto exacto, buscar cualquier enlace de la colección de boletines
    if not publicacion_link:
      for a in soup.find_all("a", href=True):
        if "/informes-publicaciones/" in a["href"]:
          href = a["href"]
          publicacion_link = (
              href if href.startswith("http") else "https://www.gob.pe" + href
          )
          break

    if not publicacion_link:
      return (
          None,
          None,
          None,
          "No se pudo encontrar el enlace de la última publicación en el"
          " MIDAGRI.",
      )

    # 2. Entrar a la página de la publicación específica
    resp_pub = requests.get(publicacion_link, headers=headers, timeout=10)
    if resp_pub.status_code != 200:
      return (
          None,
          None,
          None,
          "No se pudo acceder a la página interna de la publicación.",
      )

    soup_pub = BeautifulSoup(resp_pub.text, "html.parser")

    # 3. Buscar el enlace directo al archivo PDF dentro de la publicación
    url_del_pdf = None
    for a in soup_pub.find_all("a", href=True):
      href = a["href"]
      if ".pdf" in href.lower() or "descargar" in a.get_text().lower():
        url_del_pdf = (
            href if href.startswith("http") else "https://www.gob.pe" + href
        )
        break

    if not url_del_pdf:
      return (
          None,
          None,
          None,
          "No se halló el enlace de descarga del PDF en la página de la"
          " publicación.",
      )

    # 4. Descargar y procesar el PDF en memoria
    resp_pdf = requests.get(url_del_pdf, timeout=15)
    if resp_pdf.status_code == 200:
      archivo_pdf = io.BytesIO(resp_pdf.content)
      lector = PyPDF2.PdfReader(archivo_pdf)

      if len(lector.pages) == 0:
        return None, None, None, "El archivo PDF descargado está vacío."

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

    return None, None, None, "Falla al descargar el contenido del archivo PDF."

  except Exception as e:
    return None, None, None, f"Ocurrió un error técnico: {str(e)}"


# Interfaz visual en Streamlit
st.title("📊 Reporte de Precios - MIDAGRI")
st.markdown(
    "Visualiza de forma rápida los datos actualizados del boletín de"
    " comercialización de aves."
)

if st.button("🔄 Cargar / Actualizar Datos"):
  with st.spinner("Conectando con el MIDAGRI y analizando el último boletín..."):
    fecha, mayorista, granja, pdf_url = obtener_datos_midagri()

    # Validación de que se obtuvo la información correctamente y no un mensaje de error
    if fecha and not pdf_url.startswith(
        ("Error", "No", "Falla", "Ocurrió")
    ):
      st.success("¡Datos obtenidos correctamente!")

      st.markdown(f"### 📅 Fecha del Boletín: *{fecha}*")

      # Tarjetas de métricas
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
          f"📄 **[Descargar o Ver PDF Original]({pdf_url})**",
          unsafe_allow_html=True,
      )
    else:
      st.error(f"❌ {pdf_url}")
else:
  st.info("Presiona el botón superior para realizar la consulta en línea.")
