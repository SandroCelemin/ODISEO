import streamlit as st
import io
import requests

from supabase import create_client

from difflib import SequenceMatcher
from rapidfuzz import fuzz, utils

from PIL import Image, ImageOps, ImageDraw, ImageEnhance, ImageFont

def similarity(query: str, target: str) -> float:
    # utils.default_process normaliza acentos, mayúsculas y signos automáticamente
    
    # token_set_ratio ignora el orden de las palabras y duplicados
    # Ej: "bici roja" vs "roja bici de montaña" -> Coincidencia muy alta
    score = fuzz.token_set_ratio(query, target, processor=utils.default_process)
    
    return score / 100.0  # Devuelve un valor entre 0.0 y 1.0


# ───────── CONEXION CON SUPABASE ─────────
# 1. Obtener credenciales desde los secrets de Streamlit
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]

# 2. Crear el cliente (esta es la variable `supabase`)
supabase = create_client(supabase_url, supabase_key)

def get_image_url(bucket_name, file_name):
    if not file_name:
        return None

    # Limpiar barras de Windows (\ -> /) y eliminar / al inicio
    clean_name = str(file_name).replace("\\", "/").strip().lstrip("/")

    # Si por error el nombre ya incluye el bucket "img_opt/", se remueve
    if clean_name.startswith(f"{bucket_name}/"):
        clean_name = clean_name.replace(f"{bucket_name}/", "", 1)

    return supabase.storage.from_(bucket_name).get_public_url(clean_name)

SUPABASE_STORAGE_BASE = "https://udmlukpnhvkedmhuvsec.supabase.co/storage/v1/object/public"

@st.cache_data(show_spinner=False)
def fetch_bytes(url: str) -> bytes | None:
    """Descarga y guarda en caché ÚNICAMENTE los bytes puros para evitar errores con PIL."""
    if not url:
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        return res.content
    except Exception as e:
        print(f"Error descargando bytes de '{url}': {e}")
        return None

def get_pil_image(path_or_url: str, bucket_name: str = None) -> Image.Image | None:
    """
    Transforma cualquier ruta o URL en un objeto PIL.Image seguro y cargado en memoria,
    utilizando get_image_url para construir la ruta de Supabase correctamente.
    """
    if not path_or_url:
        return None

    clean_path = str(path_or_url).replace("\\", "/").strip().lstrip("/")

    # 1. Obtener la URL final utilizando get_image_url o respetando si ya es web
    if clean_path.startswith("http"):
        full_url = clean_path
    else:
        if bucket_name:
            full_url = get_image_url(bucket_name, clean_path)
        else:
            # Fallback inteligente por si la ruta incluye el bucket implícito (ej: "img_opt/foto.jpg")
            parts = clean_path.split("/", 1)
            if len(parts) == 2:
                full_url = get_image_url(parts[0], parts[1])
            else:
                return None

    if not full_url:
        return None

    # 2. Obtener bytes de la caché con fetch_bytes
    content = fetch_bytes(full_url)
    if not content:
        return None

    # 3. Crear el objeto PIL en memoria activa
    try:
        img = Image.open(io.BytesIO(content))
        img.load()  # Forzar lectura de píxeles para evitar stream cerrado
        return img.convert("RGBA")  # Mantiene transparencias para PNGs
    except Exception as e:
        print(f"Error procesando PIL para '{full_url}': {e}")
        return None
        
def desvanecer_imagen(imagen_pil, factor=0.5):
    """Mezcla la foto con una capa blanca para darle efecto translúcido."""
    img_rgba = imagen_pil.convert("RGBA")
    fondo_blanco = Image.new("RGBA", img_rgba.size, (255, 255, 255, 255))
    return Image.blend(img_rgba, fondo_blanco, alpha=factor)

def agregar_insignia_reservado(img: Image.Image) -> Image.Image:
    """Añade la etiqueta 'RESERVAT' en la esquina superior derecha."""
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    ancho, alto = img.size
    margen = 10
    ancho_badge = 300  # Corregido (antes 4000)
    alto_badge = 60
    
    x1 = ancho - ancho_badge - margen
    y1 = margen
    x2 = ancho - margen
    y2 = margen + alto_badge
    
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    
    # Fondo naranja con esquinas redondeadas
    draw.rounded_rectangle([x1, y1, x2, y2], radius=4, fill=(230, 81, 0, 230))
    
    # Texto 'RESERVAT' (las coordenadas se ajustan al nuevo badge)
    draw.text((x1 + 18, y1 + 5), "RESERVAT", fill=(255, 255, 255, 255), font=font)
        
    return Image.alpha_composite(img, overlay)

def renderizar_imagen(
    file_name: str, 
    bucket_name: str = None, 
    size: tuple = (275, 200), 
    shape: str = "normal", 
    reserved: bool = False,
    crop: bool = True  # <-- Nuevo parámetro con valor por defecto True
):
    """
    Descarga, recorta (opcional), aplica filtros de estado (reservado) y pinta en Streamlit.
    """
    if not file_name:
        return

    # 1. Obtener imagen base
    img = get_pil_image(file_name, bucket_name)
    if not img:
        st.warning("No se pudo cargar la imagen.")
        return

    # 2. Recortar solo si crop=True
    if crop and size:
        img_fit = ImageOps.fit(img, size, centering=(0.5, 0.5))
    else:
        img_fit = img.copy()

    # 3. Aplicar filtros si está reservado
    if reserved:
        enhancer = ImageEnhance.Color(img_fit)
        img_fit = enhancer.enhance(0.5)               # Desaturar
        img_fit = desvanecer_imagen(img_fit, 0.5)     # Aclarar
        img_fit = agregar_insignia_reservado(img_fit) # Etiqueta

    # 4. Aplicar forma circular usando las dimensiones reales de la imagen
    if shape == "circular":
        actual_size = img_fit.size  # Se adapta al tamaño real si no se recortó
        mask = Image.new("L", actual_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, actual_size[0], actual_size[1]), fill=255)
        img_fit.putalpha(mask)

    # 5. Pintar en la interfaz
    st.image(img_fit, use_container_width=True)
    
def similarity_antiguo(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
