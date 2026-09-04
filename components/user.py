import io
import requests
from PIL import Image, ImageDraw, ImageOps
import streamlit as st

from components.marketplace import render_marketplace
from services.utils import renderizar_imagen
from db import get_items_from_user, get_user_by_username

SUPABASE_STORAGE_BASE = "https://udmlukpnhvkedmhuvsec.supabase.co/storage/v1/object/public"

IMG_FULL = "img_sistema/star_full.png"
IMG_HALF = "img_sistema/star_half.png"
IMG_EMPTY = "img_sistema/star_empty.png"


@st.cache_data(ttl=3600)
def fetch_image_bytes(url: str) -> bytes:
    """Descarga y guarda en caché únicamente los bytes puros de la imagen."""
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=5)
    res.raise_for_status()
    return res.content


def load_supabase_image(bucket_and_path):
    """Obtiene los bytes cacheados y construye la imagen PIL de forma segura."""
    if not bucket_and_path:
        return None

    path_str = str(bucket_and_path).replace("\\", "/").lstrip("/")
    url = path_str if path_str.startswith("http") else f"{SUPABASE_STORAGE_BASE}/{path_str}"

    try:
        content = fetch_image_bytes(url)
        return Image.open(io.BytesIO(content))
    except Exception as e:
        print(f"Error descargando imagen desde '{url}': {e}")
        return None


def make_circle_image(image, size=(200, 200)):
    img = ImageOps.fit(image, size, centering=(0.5, 0.5)).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    img.putalpha(mask)
    return img


def get_star_image(position, score):
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

    if not user:
        st.error("Usuari no trobat")
        return

    if st.button("Tornar", icon=":material/arrow_left_alt:"):
        st.session_state.show_user = None
        st.rerun()

    st.html("<br>")

    col_avatar, col_info = st.columns([1, 4])

    with col_avatar:
        """
        user_img_path = user.get("user_image")
        if user_img_path and not user_img_path.startswith("http") and not user_img_path.startswith("imagenes_users/"):
            user_img_path = f"imagenes_users/{user_img_path}"

        img_raw = load_supabase_image(user_img_path)

        if img_raw:
            img_circular = make_circle_image(img_raw, size=(avatar_size, avatar_size))
            st.image(img_circular)
        else:
            st.image(f"https://api.dicebear.com/7.x/bottts/svg?seed={username}", width=avatar_size)
        """
        renderizar_imagen(user.get("user_image"), "imagenes_users", (avatar_size, avatar_size), "circular", False, True)

    with col_info:
        st.header(user.get("username", username))

        col1, col2 = st.columns([1, 3])

        with col1:
            cols = st.columns(5, gap="xxsmall")
            rating = user.get("rating", 0)

            for i, col in enumerate(cols, start=1):
                star_path = get_star_image(i, rating)
                #img_star = load_supabase_image(star_path)

                with col:
                    if star_path:
                        """
                        img_recortada = ImageOps.fit(img_star, (star_size, star_size))
                        st.image(img_recortada)
                        """
                        renderizar_imagen(star_path, "img_sistema", (star_size, star_size), "normal", False, True)
                    else:
                        st.write("★")

        with col2:
            st.header(user.get("rating", 0))

    st.divider()

    user_items = get_items_from_user(username)

    tab1, tab2, tab3 = st.tabs([f"{len(user_items)} Disponibles", "Comentaris", "Més informació"])

    with tab1:
        render_marketplace(user_items, "user_items")
