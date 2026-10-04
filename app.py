import streamlit as st
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import re

# Diseño de la página web
st.set_page_config(page_title="Precios MIDAGRI", page_icon="🐔")
st.title("📊 Reporte de Precios de Aves")
st.write("Consulta los últimos datos oficiales del MIDAGRI en tiempo real.")

# Botón para que el usuario inicie la consulta
if st.button("Consultar Precios de Hoy"):
    
    with st.spinner('Extrayendo datos del ministerio...'):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
            }
            
            # 1. Buscar publicación
            url_base = "https://www.gob.pe/institucion/midagri/colecciones/4-boletin-diario-de-comercializacion-y-precio-de-aves"
            res_col = requests.get(url_base, headers=headers, timeout=15)
            
            if res_col.status_code != 200:
                st.error(f"El servidor de gob.pe rechazó la conexión (Código HTTP: {res_col.status_code}).")
                st.stop()
            
            sopa_col = BeautifulSoup(res_col.text, 'html.parser')
            enlace_pub = sopa_col.find('a', href=re.compile(r'informes-publicaciones'))
            
            if not enlace_pub:
                st.error("No se encontró el enlace de la publicación mensual.")
                st.stop()
                
            url_pub = enlace_pub['href']
            if not url_pub.startswith("http"): 
                url_pub = "https://www.gob.pe" + url_pub
                
            # 2. Buscar PDF (Ignorando el Organigrama)
            res_pub = requests.get(url_pub, headers=headers, timeout=15)
            sopa_pub = BeautifulSoup(res_pub.text, 'html.parser')
            
            # 🔴 SOLUCIÓN: Buscar todos los enlaces PDF en la página
            enlaces_pdf = sopa_pub.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))
            url_pdf = None
            
            for enlace in enlaces_pdf:
                href = enlace['href']
                # Si el enlace NO tiene la palabra "organigrama", ese es nuestro boletín
                if 'organigrama' not in href.lower():
                    url_pdf = href
                    break
            
            if not url_pdf:
                st.error("Se entró a la publicación, pero no se encontró el PDF del boletín.")
                st.stop()
                
            # 🔴 SOLUCIÓN: Reparar el enlace si el ministerio lo pone incompleto
            if not url_pdf.startswith("http"):
                url_pdf = "https://www.gob.pe" + url_pdf
            
            # 3. Leer PDF
            res_pdf = requests.get(url_pdf, timeout=15)
            lector = PyPDF2.PdfReader(io.BytesIO(res_pdf.content))
            
            texto_pag1 = lector.pages[0].extract_text()
            match_fecha = re.search(r'([a-záéíóú]+,\s*\d{1,2}\s*de\s*[a-záéíóú]+\s*de\s*\d{4})', texto_pag1, re.IGNORECASE)
            fecha = match_fecha.group(1).capitalize() if match_fecha else "Fecha no detectada"
            
            match_mayorista = re.search(r'S/\s*(\d+\.\d+)', texto_pag1)
            mayorista = f"S/ {match_mayorista.group(1)}" if match_mayorista else "No detectado"
            
            texto_completo = " ".join([p.extract_text() for p in lector.pages])
            texto_limpio = " ".join(texto_completo.split())
            match_granja = re.search(r'Granja[^\d]*(\d+\.\d+)[^\d]*(\d+\.\d+)[^\d]*(\d+\.\d+)', texto_limpio, re.IGNORECASE)
            granja = f"S/ {match_granja.group(3)}" if match_granja else "No detectado"

            # 4. Mostrar los resultados en la página web con diseño
            st.success("¡Datos obtenidos con éxito!")
            st.subheader(f"📅 Fecha del reporte: {fecha}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="🐔 Precio de Granja", value=f"{granja} / kg")
            with col2:
                st.metric(label="🔹 Pollo Mayorista", value=f"{mayorista} / kg")
                
            st.markdown(f"[📄 Ver PDF Original del MIDAGRI]({url_pdf})")

        except Exception as e:
            st.error(f"Ocurrió un error técnico detallado: {e}")
