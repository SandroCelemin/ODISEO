import streamlit as st
from PIL import Image, ImageOps, ImageDraw

from db import get_user_by_username, get_items_from_user
from components.marketplace import render_marketplace

# Base URL para el bucket de Supabase Storage (ajusta el nombre del bucket si no es 'img_opt')
SUPABASE_STORAGE_BASE = "https://udmlukpnhvkedmhuvsec.supabase.co/storage/v1/object/public/imagenes_users"

#@st.cache_data(ttl=3600)
def load_supabase_image(bucket_and_path):
    """Descarga e interpreta cualquier imagen guardada en Supabase Storage."""
    if not bucket_and_path:
        return None
        
    path_str = str(bucket_and_path).replace("\\", "/").lstrip("/")
    
    if not path_str.startswith("http"):
        url = f"{SUPABASE_STORAGE_BASE}/{path_str}"
    else:
        url = path_str

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        return Image.open(io.BytesIO(res.content))
    except Exception as e:
        print(f"Error descargando imagen desde '{url}': {e}")
        return None
        
def make_circle_image(image, size=(200, 200)):
    # 1. Redimensionar i enquadrar perquè no es deformi
    img = ImageOps.fit(image, size, centering=(0.5, 0.5)).convert("RGBA")
    
    # 2. Crear una màscara en blanc i negre (L) amb un cercle blanc
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    
    # 3. Aplicar la màscara com a canal Alfa (transparència)
    img.putalpha(mask)
    return img

IMG_FULL = "img_sistema/star_full.png"
IMG_HALF = "img_sistema/star_half.png"
IMG_EMPTY = "img_sistema/star_empty.png"

def get_star_image(position, score):
    """
    Determina quina imatge d'estrella utilitzar per a la posició (1 a 5) donada la puntuació.
    """
    diff = float(score) - (position - 1)
    
    if diff >= 0.75:
        return IMG_FULL
    elif diff >= 0.25:
        return IMG_HALF
    else:
        return IMG_EMPTY

def render_user(username):
    
    avatar_size = 250
    star_size = 50
    user = get_user_by_username(username)
    
    if st.button("Tornar", icon=":material/arrow_left_alt:"):
        st.session_state.show_user = None
        st.rerun()
    
    st.html("<br>")
    
    col_avatar, col_info = st.columns([1,4])
    
    with col_avatar:
        """
        img_path = user["user_image"]
        
        img_original = Image.open(img_path)
        img_circular = make_circle_image(img_original, size=(avatar_size, avatar_size))
        st.image(img_circular)
        """
        
        img_raw = load_supabase_image(user.get("user_image"))
        
        if img_raw:
            img_circular = make_circle_image(img_raw, size=(avatar_size, avatar_size))
            st.image(img_circular)
        else:
            st.image("https://api.dicebear.com/7.x/bottts/svg?seed=" + username, width=avatar_size)
        
    with col_info:
        
        st.header(user["username"])

        col1, col2 = st.columns([1,3])
        
        with col1:
            
            cols = st.columns(5, gap="xxsmall")
            rating = user["rating"]
            
            for i, col in enumerate(cols, start=1):
                star_path = get_star_image(i, rating)
                
                img_star = load_supabase_image(star_path)
                img_recortada = ImageOps.fit(img_star, (star_size, star_size))

                with col:
                    st.image(img_recortada)
                    
        with col2:
            st.header(user["rating"])
        
    st.divider()
    
    user_items = get_items_from_user(username)
    
    tab1, tab2, tab3 = st.tabs([f"{len(user_items)} Disponibles", "Comentaris", "Més informació"])

    with tab1:
        
        render_marketplace(user_items, "user_items")
