from difflib import SequenceMatcher
from rapidfuzz import fuzz, utils

def similarity(query: str, target: str) -> float:
    # utils.default_process normaliza acentos, mayúsculas y signos automáticamente
    
    # token_set_ratio ignora el orden de las palabras y duplicados
    # Ej: "bici roja" vs "roja bici de montaña" -> Coincidencia muy alta
    score = fuzz.token_set_ratio(query, target, processor=utils.default_process)
    
    return score / 100.0  # Devuelve un valor entre 0.0 y 1.0

def get_image(bucket_name, file_name):
    
    return image_opt_url = supabase.storage.from_(bucket_name).get_public_url(file_name)

def get_image_url(bucket_name, file_name):
    return supabase.storage.from_(bucket_name).get_public_url(file_name)


SUPABASE_STORAGE_BASE = "https://udmlukpnhvkedmhuvsec.supabase.co/storage/v1/object/public"

@st.cache_data(show_spinner=False)
def open_image(path, bucket_name):
    if not path:
        return None
    
    # 1. Arreglar barras de Windows (\ -> /)
    path = str(path).replace("\\", "/")

    # 2. Convertir la ruta de la DB en URL pública de Supabase
    if not path.startswith("http"):
        path = path.lstrip("/")
        path = f"{SUPABASE_STORAGE_BASE}/{path}"

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(path, headers=headers, timeout=5)
        res.raise_for_status()
        return Image.open(io.BytesIO(res.content)).convert("RGB")
    except Exception as e:
        print(f"Error cargando '{path}': {e}")
        return None

@st.cache_data(ttl=3600)
def fetch_image_bytes(url: str) -> bytes:
    """Descarga y guarda en caché únicamente los bytes puros de la imagen."""
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=5)
    res.raise_for_status()
    return res.content

def similarity_antiguo(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
