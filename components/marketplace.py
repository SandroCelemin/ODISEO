import io
import requests
import streamlit as st
#from engine import find_all_want_chains
#from engine import find_all_chains
from engine import get_items_from_have_chains
from db import delete_item, get_items_from_user, get_reserved_items, get_user_by_username
from services.search import first_distance_items

from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont

@st.cache_data(show_spinner=False)
def cargar_imagen(path):
    img = open_image(path)
    if img is None:
        return None
    return ImageOps.fit(img, (275, 200))

def reducir_opacidad(imagen_pil, opacidad):
    """
    opacidad: de 0.0 (totalment invisible) a 1.0 (totalment visible).
    0.4 deixa la imatge al 40% de visibilitat.
    """
    img_rgba = imagen_pil.convert("RGBA")
    r, g, b, a = img_rgba.split()
    
    # Reduïm el canal Alpha (transparència)
    a = a.point(lambda p: int(p * opacidad))
    img_rgba.putalpha(a)
    
    return img_rgba

def desvanecer_imagen(imagen_pil, factor):
    """
    factor: com més alt, més es desvaneix amb el fons blanc (0.5 = 50% desvanegut).
    """
    img_rgba = imagen_pil.convert("RGBA")
    fondo_blanco = Image.new("RGBA", img_rgba.size, (255, 255, 255, 255))
    
    # Barreja la foto amb una capa blanca
    return Image.blend(img_rgba, fondo_blanco, alpha=factor)

@st.cache_data(show_spinner=False)
def obtener_imagen_item(path, desaturate=False):

    img = open_image(path)
    if img is None:
        return None
    img_recortada = ImageOps.fit(img, (275, 200))
    
    if desaturate:
        enhancer = ImageEnhance.Color(img_recortada)
        img_recortada = enhancer.enhance(0.5)
        img_recortada = desvanecer_imagen(img_recortada, 0.7)

    return img_recortada

SUPABASE_STORAGE_BASE = "https://udmlukpnhvkedmhuvsec.supabase.co/storage/v1/object/public"

@st.cache_data(show_spinner=False)
def open_image(path):
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
        
"""
@st.cache_data(show_spinner=False)
def open_image(path):
    if not path:
        return None
    try:
        # Si es una URL de Supabase u otro servidor HTTP
        if str(path).startswith("http"):
            res = requests.get(path, timeout=5)
            res.raise_for_status()
            return Image.open(io.BytesIO(res.content)).convert("RGB")
        # Si es una ruta local del disco
        return Image.open(path).convert("RGB")
    except Exception:
        return None
"""
def agregar_insignia_reservado(img: Image.Image) -> Image.Image:
    """Afegeix l'etiqueta 'RESERVAT' a la cantonada superior dreta de la imatge."""
    img = img.convert("RGBA")
    
    # Capa transparent per dibuixar
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    ancho, alto = img.size
    
    # Coordenades de l'etiqueta (cantonada superior dreta)
    margen = 20
    ancho_badge, alto_badge = 280, 60
    x1 = ancho - ancho_badge - margen
    y1 = margen
    x2 = ancho - margen
    y2 = margen + alto_badge
    
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 35)
    except OSError:
        font = ImageFont.load_default()
    
    # 1. Dibuixar fons taronja amb cantonades arrodonides
    draw.rounded_rectangle([x1, y1, x2, y2], radius=8, fill=(230, 81, 0, 230))
    
    # 2. Escriure el text 'RESERVAT'
    draw.text((x1 + 15, y1 + 8), "RESERVAT", fill=(255, 255, 255, 255), font=font)
        
    # Combinar capa i retornar la imatge
    imagen_final = Image.alpha_composite(img, overlay)
    return imagen_final.convert("RGB")

# 🚀 OPTIMITZACIÓ: Utilitzar un fragment perquè només es torni a renderitzar la quadrícula
@st.fragment
def render_grid_con_paginacion(filtered_items, num_columnas):
    total_items = len(filtered_items)
    items_to_show = filtered_items[:st.session_state.items_limit]

    reserved_ids = get_reserved_items(items_to_show)

    # ───── GRID ─────
    for i in range(0, len(items_to_show), num_columnas):
        row = items_to_show[i:i + num_columnas]
        cols = st.columns(num_columnas)

        for col, item in zip(cols, row):
            reserved = (item["item_id"] in reserved_ids)
            locked_or_reserved = (item['status'] == "locked" or reserved == 1)

            with col:
                # ───── IMATGE ─────
                #st.write(item)
                #path, optimized = ((item["image_optimized"], True) if item["image_optimized"] else (item["image"], False))
                path = item.get("image_optimized") or item.get("image")
                
                if path:
                    # Obté la imatge directament de la memòria cau RAM
                    
                    #if optimized:
                    img = open_image(path)
                    
                    if img is not None:
                        if locked_or_reserved:
                            enhancer = ImageEnhance.Color(img)
                            img = enhancer.enhance(0.5)
                            img = desvanecer_imagen(img, 0.5)
                            img = agregar_insignia_reservado(img)
                        """
                        else:
                            img = obtener_imagen_item(path, locked_or_reserved)
                        """
                        st.image(img, use_container_width=True)

                # ───── TEXT ─────
                user = get_user_by_username(item["user"])
                
                st.subheader(f"**{item['have']}**")
                st.write(f":grey[{user['username']}] ★ {user['rating']}")
                
                # ───── BOTÓ VEURE ─────
                if st.button("Veure", key=f"detail_{item['item_id']}", use_container_width=True):
                    st.session_state.detail_item = item["item_id"]
                    st.rerun()

    # ───── BOTÓ DE PAGINACIÓ ─────
    if st.session_state.items_limit < total_items:
        st.html("<br>")
        st.caption(f"Mostrant **{len(items_to_show)}** de **{total_items}** articles disponibles")

        def show_more():
            st.session_state.items_limit += num_columnas * 3

        st.button(
            "Mostrar més articles", 
            icon=":material/arrow_downward:", 
            key="load_more_items", 
            on_click=show_more
        )

def render_marketplace(items, mode): #mode pot ser "suggestions" (per a create_item) o "main" (per a la marketplace)

    # ───── CONTROL DE PAGINACIÓ (15 en 15) ─────
    if "items_limit" not in st.session_state:
        st.session_state.items_limit = 15

    st.markdown(
        """
        <style>
        div[data-testid="stImage"] img {
            
            object-fit: cover;
            border-radius: 10px;
        }

        /* botó més net */
        div[data-testid="stButton"] > button {
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ───── ACTIVE STATE ─────
    if mode == "main":
        search = st.session_state.get("search_text", "") #search_text és el text de la barra de cerca
        intent = st.session_state.get("search_text_mode", "neutral")
        
        if search and st.session_state.search_text != "":
            st.header("Articles que et poden interessar aconseguir segons la teva cerca")
            """
            if st.session_state.search_text_mode == "want":
                st.subheader(f"Articles que et poden interessar aconseguir segons la teva cerca")
            else:
                st.subheader(f"Articles que podries aconseguir ")
            """
        else:
            st.header("Troba el que busques")
        
    elif mode == "suggestions_have":
        search = st.session_state.get("have_input", "") 
        intent = "have"
        
    elif mode == "suggestions_want":
        search = st.session_state.get("want_input", "")
        intent = "want"
        
    elif mode == "user_items":
        search = None
        intent = "want"
        st.header("Articles publicats")
        
    st.html("<br>")
        
    """
    # fallback segur
    if "search_text" not in st.session_state:
        search = st.session_state.get("search", "")

    if "search_text_mode" not in st.session_state:
        intent = st.session_state.get("intent", "neutral")
    """

    # ───── FILTRE ─────
    if search:
        if intent == "have":
            filtered_items = get_items_from_have_chains(items, search, intent)
        elif intent == "want":
            filtered_items = first_distance_items(items, search, intent)
    else:
        filtered_items = first_distance_items(items, search, intent)
    
    if mode == "main" or mode == "user_items":
        num_columnas = 5
    else:
        num_columnas = 3
    
    # Comprovació per no mostrar els articles de l'usuari fora del perfil de l'usuari
    if st.session_state.user and mode != "user_items":
        filtered_items = [
            item for item in filtered_items 
            if item["user"] != st.session_state.user
        ]
        
    # ───── INICIALITZAR LÍMIT D'ARTICLES ─────
    if "items_limit" not in st.session_state:
        st.session_state.items_limit = num_columnas * 3

    # Crida al fragment aïllat
    render_grid_con_paginacion(filtered_items, num_columnas)
    """
    # ───── APLICAR LÍMIT D'ARTICLES A MOSTRAR ─────
    #st.session_state.items_limit = num_columnas*3
    total_items = len(filtered_items)
    items_to_show = filtered_items[:st.session_state.items_limit]
    
    def show_more():
        st.session_state.items_limit += num_columnas*3
    
    # ───── GRID ─────
    for i in range(0, len(items_to_show), num_columnas):
        
        row = items_to_show[i:i + num_columnas]
        cols = st.columns(num_columnas)

        for col, item in zip(cols, row):

            reserved = is_item_accepted_in_any_chain(item["item_id"])

            with col:

                # ───── IMATGE ─────
                if item["image"]:
                    # Convertim a RGB directament per evitar l'error de mode
                    #img_original = Image.open(item["image"]).convert("RGB")
                    #img_recortada = ImageOps.fit(img_original, (275, 200)) #ImageOps.fit s'encarrega que no es deformi la foto en retallar-la
                    img_recortada = cargar_imagen(item["image"]) # Millora d'optimització
                    
                    # Si està bloquejat o reservat, apliquem desaturació i transparència
                    if item['status'] == "locked" or reserved == 1:
                        enhancer = ImageEnhance.Color(img_recortada)
                        img_recortada = enhancer.enhance(0.5)
                        
                        # Aplicar desvanegut sobre fons blanc
                        img_recortada = desvanecer_imagen(img_recortada, 0.7)
                        
                    st.image(img_recortada, use_container_width=True)
                    
                # ───── TEXT ─────

                # 1. Primer la màxima prioritat: Està bloquejat definitivament a la DB?
                if item['status'] == "locked":
                    st.write(f"**{item['have']}** :red[No disponible]")

                # 2. Segona prioritat: Està actiu però algú ha acceptat en alguna cadena?
                elif reserved == 1:
                    st.write(f"**{item['have']}** :orange[Reservat]")

                # 3. Estat normal: Actiu i sense reserves
                else:
                    st.write(f"**{item['have']}**")
                
                # ───── BOTÓ FULL WIDTH ─────
                if st.button(
                    "Veure",
                    key=f"detail_{item['item_id']}",
                    use_container_width=True
                ):
                    print("entro en ver")
                    st.session_state.detail_item = item["item_id"]
                    st.rerun()
                    
    # ───── BOTÓ DE PAGINACIÓ "MOSTRAR MÉS" ─────
    if st.session_state.items_limit < total_items:
        #st.divider()
        st.html("<br>")
        st.caption(f"Mostrant **{len(items_to_show)}** de **{total_items}** articles disponibles")
        
        st.button("Mostrar més articles", icon=":material/arrow_downward:", key="load_more_items", on_click=show_more)
    """
