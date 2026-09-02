from difflib import SequenceMatcher
from rapidfuzz import fuzz, utils

def similarity(query: str, target: str) -> float:
    # utils.default_process normaliza acentos, mayúsculas y signos automáticamente
    
    # token_set_ratio ignora el orden de las palabras y duplicados
    # Ej: "bici roja" vs "roja bici de montaña" -> Coincidencia muy alta
    score = fuzz.token_set_ratio(query, target, processor=utils.default_process)
    
    return score / 100.0  # Devuelve un valor entre 0.0 y 1.0

def similarity_antiguo(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()