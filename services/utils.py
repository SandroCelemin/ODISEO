import streamlit as st
import io
import requests

from supabase import create_client
from rapidfuzz import fuzz, utils
from PIL import Image, ImageOps, ImageDraw, ImageEnhance, ImageFont

def similarity(query: str, target: str) -> float:
    score = fuzz.token_set_ratio(query, target, processor=utils.default_process)
    return score / 100.0


# ───────── CONEXION CON SUPABASE ─────────
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase = create_client(supabase_url, supabase_key)

SUPABASE_STORAGE_BASE = "https://udmlukpnhvkedmhuvsec.supabase.co/storage/v1/object/public"

def get_image_url(bucket_name, file_name):
    if not file_name:
        return None

    clean_name = str(file_name).replace("\\", "/").strip().lstrip("/")
    if clean_name.startswith(f"{bucket_name}/"):
        clean_name = clean_name.replace(f"{bucket_name}/", "", 1)

    return supabase.storage.from_(bucket_name).get_public_url(clean_name)


@st.cache_data(show_spinner=False, max_entries=300, ttl=3600)
def fetch_bytes(url: str) -> bytes | None:
    """Descarga y guarda en caché únicamente los bytes puros."""
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
    ancho_badge = 300
    alto_badge = 60
    
    x1 = ancho - ancho_badge - margen
    y1 = margen
    x2 = ancho - margen
    y2 = margen + alto_badge
    
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    
    draw.rounded_rectangle([x1, y1, x2, y2], radius=8, fill=(230, 81, 0, 230))
    
    centro_x = (x1 + x2) / 2
    centro_y = (y1 + y2) / 2
    draw.text((centro_x, centro_y), "RESERVAT", fill=(255, 255, 255, 255), font=font, anchor="mm")
        
    return Image.alpha_composite(img, overlay)


# ───────── PROCESAMIENTO Y CACHÉ FINAL DE IMAGEN ─────────
@st.cache_data(show_spinner=False, max_entries=200, ttl=3600)
def get_processed_image(
    file_name: str, 
    bucket_name: str = None, 
    size: tuple = (275, 200), 
    shape: str = "normal", 
    reserved: bool = False,
    crop: bool = True
) -> Image.Image | None:
    """
    Descarga, recorta y procesa la imagen GUARDANDO EL RESULTADO EN CACHÉ.
    Evita que PIL vuelva a procesar la imagen cada vez que el usuario hace clic.
    """
    if not file_name:
        return None

    clean_path = str(file_name).replace("\\", "/").strip().lstrip("/")

    if clean_path.startswith("http"):
        full_url = clean_path
    else:
        bucket = bucket_name
        path = clean_path
        if not bucket:
            parts = clean_path.split("/", 1)
            if len(parts) == 2:
                bucket, path = parts[0], parts[1]
            else:
                return None
        full_url = get_image_url(bucket, path)

    if not full_url:
        return None

    content = fetch_bytes(full_url)
    if not content:
        return None

    try:
        img = Image.open(io.BytesIO(content))
        img.load()

        # 1. Recortar/Redimensionar primero (Reduce trabajo de procesamiento posterior)
        if crop and size:
            img = ImageOps.fit(img, size, centering=(0.5, 0.5))

        # 2. Solo convertir a RGBA si el formato o los filtros lo exigen
        if reserved or shape == "circular":
            img = img.convert("RGBA")

        # 3. Aplicar filtro de reservado
        if reserved:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(0.5)
            img = desvanecer_imagen(img, 0.5)
            img = agregar_insignia_reservado(img)

        # 4. Aplicar forma circular
        if shape == "circular":
            actual_size = img.size
            mask = Image.new("L", actual_size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, actual_size[0], actual_size[1]), fill=255)
            img.putalpha(mask)

        return img

    except Exception as e:
        print(f"Error procesando PIL para '{full_url}': {e}")
        return None


def renderizar_imagen(
    file_name: str, 
    bucket_name: str = None, 
    size: tuple = (275, 200), 
    shape: str = "normal", 
    reserved: bool = False,
    crop: bool = True
):
    """Pinta directamente en Streamlit la imagen procesada obtenida desde la caché."""
    img_fit = get_processed_image(file_name, bucket_name, size, shape, reserved, crop)
    if not img_fit:
        st.warning("No se pudo cargar la imagen.")
        return

    st.image(img_fit, use_container_width=True)


def similarity_antiguo(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
