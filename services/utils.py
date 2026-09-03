import streamlit as st
import io
import requests

from supabase import create_client

from difflib import SequenceMatcher
from rapidfuzz import fuzz, utils

from PIL import Image

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
    listo para operaciones de recorte (ImageOps.fit, máscaras circulares, etc.).
    """
    if not path_or_url:
        return None

    # 1. Normalizar barras de Windows
    clean_path = str(path_or_url).replace("\\", "/").strip().lstrip("/")

    # 2. Construir la URL completa de Supabase
    if clean_path.startswith("http"):
        full_url = clean_path
    else:
        if bucket_name and not clean_path.startswith(f"{bucket_name}/"):
            clean_path = f"{bucket_name}/{clean_path}"
        full_url = f"{SUPABASE_STORAGE_BASE}/{clean_path}"

    # 3. Obtener bytes de la caché
    content = fetch_bytes(full_url)
    if not content:
        return None

    # 4. Crear el objeto PIL en memoria activa
    try:
        img = Image.open(io.BytesIO(content))
        img.load()  # Forzar lectura de píxeles para evitar stream cerrado
        return img.convert("RGBA")  # Mantiene transparencias para PNGs
    except Exception as e:
        print(f"Error procesando PIL para '{full_url}': {e}")
        return None
    
def similarity_antiguo(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
