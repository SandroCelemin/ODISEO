import streamlit as st

from supabase import create_client

from difflib import SequenceMatcher
from rapidfuzz import fuzz, utils

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
    #if clean_name.startswith(f"{bucket_name}/"):
    #    clean_name = clean_name.replace(f"{bucket_name}/", "", 1)

    return supabase.storage.from_(bucket_name).get_public_url(clean_name)
    
def similarity_antiguo(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
