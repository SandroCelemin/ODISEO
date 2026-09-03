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
    return supabase.storage.from_(bucket_name).get_public_url(file_name)

def similarity_antiguo(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
