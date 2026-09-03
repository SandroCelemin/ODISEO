import io
import requests
from PIL import Image, ImageOps
import streamlit as st

from db import delete_item, get_items_from_user

SUPABASE_STORAGE_BASE = "https://udmlukpnhvkedmhuvsec.supabase.co/storage/v1/object/public"


@st.cache_data(show_spinner=False)
def fetch_bytes(url: str) -> bytes | None:
    """Descarga y guarda en caché ÚNICAMENTE los bytes puros de la imagen."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        return res.content
    except Exception as e:
        print(f"Error descargando desde '{url}': {e}")
        return None


def open_image(path):
    """Construye la imagen PIL de forma segura a partir de los bytes cacheados."""
    if not path:
        return None

    path = str(path).replace("\\", "/")

    if not path.startswith("http"):
        path = path.lstrip("/")
        if not path.startswith("img_items/"):
            path = f"img_items/{path}"
        path = f"{SUPABASE_STORAGE_BASE}/{path}"

    content = fetch_bytes(path)
    if not content:
        return None

    try:
        img = Image.open(io.BytesIO(content))
        img.load()  # Forzar lectura de píxeles en memoria
        return img.convert("RGBA")
    except Exception as e:
        print(f"Error procesando imagen PIL '{path}': {e}")
        return None


@st.dialog("Vista completa de l'article", width="medium", icon=":material/visibility:")
def ampliar_imagen(ruta_imagen, item):
    img_original = open_image(item.get("image"))
    if img_original:
        st.image(img_original, use_container_width=True)
    else:
        st.error("No s'ha pogut carregar la imatge.")


def render_user_items():

    st.markdown(
        """
        <style>
        div[data-testid="stImage"] img {
            object-fit: cover;
            border-radius: 10px;
        }

        .truncate {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: block;
            max-width: 100%;
        }

        .truncate-small {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: block;
            max-width: 100%;
            font-size: 0.8rem;
            color: #888;
        }

        /* botó més net */
        div[data-testid="stButton"] > button {
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Tornar", icon=":material/arrow_left_alt:"):
        st.session_state.show_user_items = None
        st.rerun()

    st.subheader("Aquests són els teus articles publicats")

    num_columnas = 2
    filtered_items = get_items_from_user(st.session_state.user)

    for i in range(0, len(filtered_items), num_columnas):

        row = filtered_items[i : i + num_columnas]
        cols = st.columns(num_columnas, gap="medium")

        for col, item in zip(cols, row):

            with col:

                with st.container(border=True):

                    col_image, col_info = st.columns(2)

                    with col_image:

                        img_original = open_image(item.get("image"))

                        if img_original:
                            img_recortada = ImageOps.fit(img_original, (275, 200))
                            st.image(img_recortada, use_container_width=True)
                        else:
                            st.write("🖼️ *Sense imatge*")

                        if st.button(
                            "Ampliar imatge",
                            icon=":material/zoom_in:",
                            key=item["item_id"],
                            use_container_width=True,
                        ):
                            ampliar_imagen(item["image"], item)

                    with col_info:

                        st.write(f"**Tens:** {item['have']}")
                        st.write(f"**Vols:** {item['want']}")

                        if item["status"] == "active":
                            st.write("**Estat actual:** Lliure")
                        elif item["status"] == "locked":
                            st.write("**Estat actual:** Bloquejat")

                        with st.expander("Veure descripció de l'article"):
                            st.write(f"**Descripció:** {item['description']}")

                    _, col_btn = st.columns([2, 1])

                    with col_btn:

                        if st.button(
                            "Eliminar article",
                            icon=":material/delete:",
                            type="primary",
                            key=f"delete_{item['item_id']}",
                            use_container_width=True,
                        ):
                            delete_item(item["item_id"])
                            st.rerun()
