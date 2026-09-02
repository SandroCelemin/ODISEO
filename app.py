#ACLARACIONES

#ORDEN DE LOS BOTONES EN EL MENU LATERAL

    #Abrir panel    / Cerrar panel
    
    #Iniciar sesion / Cerrar sesion
    # ---            / Usuario
    # ---            / Notificaciones
    # ---            / Cadenas
    # ---            / Crear artículo
    # ---            / Gestionar artículos

#cambiar la logica de enseñar las notificaciones

#-----------------
import streamlit as st
from db import *
from models import *
from streamlit_float import *
from PIL import Image, ImageOps

from components.header import render_header
from components.main_presentation import render_presentation
from components.auth import render_auth
from components.marketplace import render_marketplace
from components.create_item import render_create
from components.detail import render_detail
from components.user import render_user
from components.user_items import render_user_items
from components.chains import render_chains, chain_detail
from components.notifications import toast_notification, render_notifications
from components.digraph import *

from engine import find_all_chains

import sqlite3
import os
#from PIL import Image, ImageOps

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def setup_database():
    init_db()
    
setup_database()
float_init()

# 🚀 3. CACHÉ DE CONSULTAS A BD (Evita leer el disco en cada clic)
@st.cache_data(ttl=60)  # Se mantiene en RAM 60 segundos o hasta crear un ítem nuevo
def fetch_all_items():
    """
    raw_items = get_items()
    items = [row_to_item(r) for r in raw_items]
    item_dict = {x["item_id"]: x for x in items}
    return items, item_dict
    """
    items = get_items()
    item_dict = {x["item_id"]: x for x in items}
    return items, item_dict


# 🚀 4. CACHÉ DE PROCESAMIENTO DE IMÁGENES PIL
@st.cache_data(show_spinner=False)
def get_cropped_image(image_path, width=200, height=130):
    """Corta y redimensiona la imagen usando PIL guardándola en memoria RAM."""
    if not image_path:
        return None
    try:
        with Image.open(image_path) as img:
            return ImageOps.fit(img, (width, height))
    except Exception as e:
        print(f"Error processant la imatge {image_path}: {e}")
        return None

# ────── 5. INICIALIZACIÓN DE SESSION_STATE (Agrupado y limpio) ──────
def init_session_state():
    defaults = {
        "user": None,
        "user_rating": 5.0,
        
        "show_create": False,
        "show_user": None,
        "show_user_items": False,
        "show_login": False,
        "detail_item": None,
        "show_chains": False,
        "detail_chain": [],
        "show_notifications": False,
        
        "step": 0,
        "route_current_step": 0,
        "camino_resaltado": [],
        
        "have": "",
        "want": "",
        "description": "",
        "image": None,
        
        "search_text_mode": None,
        "search_text": None,
        
        "new_notifications": [0, False],
        "expand_menu": False
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# Esta función resetea los estados de session_state que enseñan las pestañas para que el cambio entre estas sea instantaneo
def reset_state_show():    
    st.session_state.show_user_items = False
    st.session_state.detail_item = None
    st.session_state.show_chains = False
    st.session_state.detail_chain = None
    st.session_state.show_notifications = False
    
    st.session_state.step = 0
    
    st.session_state.route_current_step = 0
    st.session_state.camino_resaltado = []
    
# Como la logica de enseñar "create_item" esta mas arriba del boton, cuando este se pulsa no se ejecuta esa logica
def go_to_create():
    reset_state_show()
    st.session_state.show_create = True

def close_session():
    reset_state_show()
    st.session_state.user = None
    st.session_state.user_rating = 5.0

def show_my_user():
    reset_state_show()
    st.session_state.show_user = st.session_state.user

def change_menu_state():
    st.session_state.expand_menu = not st.session_state.expand_menu

def get_menu_config():
    
    if st.session_state.expand_menu == True:
        return {
            "width": 3.5,
            "css_width": "150px",
            "cerrar_sesion": "Tancar sessió",
            "cerrar_sesion_help": "",
            "perfil": st.session_state.get("user"),
            "perfil_help": "",
            "notificaciones": "Notificacions",
            "notificaciones_help": "",
            "ver_cadenas": "Les meves cadenes",
            "ver_cadenas_help": "",
            "crear_articulo": "Crear article",
            "crear_articulo_help": "",
            "ver_articulo": "Els meus articles",
            "ver_articulo_help": "",
            "iniciar_sesion": "Iniciar sessió",
            "iniciar_sesion_help": ""
        }
    else:
        return {
            "width": 1,
            "css_width": "75px",
            "cerrar_sesion": "",
            "cerrar_sesion_help": "Tancar sessió",
            "perfil": "",
            "perfil_help": st.session_state.get("user", "Perfil"),
            "notificaciones": "",
            "notificaciones_help": "Notificacions",
            "ver_cadenas": "",
            "ver_cadenas_help": "Les meves cadenes",
            "crear_articulo": "",
            "crear_articulo_help": "Crear article",
            "ver_articulo": "",
            "ver_articulo_help": "Els meus articles",
            "iniciar_sesion": "",
            "iniciar_sesion_help": "Iniciar sessió"
        }
        
    #return menu_width
    
# ───────── NOTIFICATION TOAST ─────────
if st.session_state.user:
    toast_notification()
   
# ───────── DATA ─────────
# la funcion row_to_items deja los items igual, pero te permite escoger que filas guardar. En este caso guardamos todas, pero puede tener sentido en un futuro.
#items = [row_to_item(r) for r in get_items()]
#item_dict = {x["item_id"]: x for x in items}

# ───────── CARGA DE DATOS OPTIMIZADA (DESDE RAM CACHEADA) ─────────
items, item_dict = fetch_all_items()

# ───────── Cabecera  ─────────
render_header()

# ───────── Login de usuario o registro ─────────
if render_auth():
    st.stop()

# ───────── CREATE ─────────
if st.session_state.user and st.session_state.show_create:
    render_create(items)
    st.stop()

# ───────── Menu lateral ─────────
menu_cfg = get_menu_config()
menu_width = menu_cfg["width"]

col_menu, col_window = st.columns([menu_width, 39])

with col_menu:

    if st.session_state.expand_menu == True:
        
        # Estilo especifico para alinear los botones del menu a la izquierda cuando este se abre
        st.markdown(
            """
            <style>
            /* Estilo general para los botones de navegación (Alineados a la izquierda) */
            div[class*="st-key-menu_container"] button {
                justify-content: flex-start !important;
                text-align: left !important;
                padding-left: 15px !important;
            }
            div[class*="st-key-menu_container"] button > div {
                justify-content: flex-start !important;
                display: flex !important;
                align-items: center !important;
                width: 100% !important;
            }
            div[class*="st-key-menu_container"] button span,
            div[class*="st-key-menu_container"] button p {
                text-align: left !important;
            }
            
            /* EXCEPCIÓN: Forzamos al botón "menu" (abrir/cerrar) a ir a la derecha */
            div[class*="st-key-menu_container"] div[class*="st-key-menu"] button {
                justify-content: flex-end !important;
                padding-right: 10px !important;
                padding-left: 0px !important;
            }
            div[class*="st-key-menu_container"] div[class*="st-key-menu"] button > div {
                justify-content: flex-end !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

    with st.container(key="menu_container"):
        
        if st.session_state.expand_menu == True:
            _, col_btn_menu = st.columns(2)
            btn_menu_icon = ":material/left_panel_close:"
            
            with col_btn_menu:
                st.button(
                    "", 
                    icon=btn_menu_icon, 
                    key="menu", 
                    help="Tancar la barra lateral", 
                    type="tertiary", 
                    use_container_width=True, 
                    on_click=change_menu_state)
        
        else:
            #col_btn_menu, _ = st.columns(2)
            btn_menu_icon = ":material/left_panel_open:"
            
        #with col_btn_menu:
            st.button(
                "", 
                icon=btn_menu_icon, 
                key="menu", 
                help="Obrir la barra lateral", 
                type="tertiary", 
                use_container_width=True, 
                on_click=change_menu_state)
        
        if st.session_state.get("user") is not None: #cuando se ha iniciado sesion
            
            # Cerrar sesión (Usamos el diccionario)
            st.button(
                menu_cfg["cerrar_sesion"], 
                icon=":material/logout:", 
                key="cerrar_sesion", 
                help=menu_cfg["cerrar_sesion_help"], 
                type="tertiary", 
                use_container_width=True, 
                on_click=close_session
            )
                
            # Perfil (Usamos el diccionario)
            st.button(
                menu_cfg["perfil"], 
                icon=":material/account_circle:", 
                key="perfil", 
                help=menu_cfg["perfil_help"], 
                type="tertiary", 
                use_container_width=True, 
                on_click=show_my_user
            )
                
            # Notificaciones
            if st.session_state.new_notifications[1] == True:
                
                st.markdown(
                    """
                    <style>
                    /* Filtramos para ocultar este bloque de diseño */
                    div[data-testid="stVerticalBlock"] > div:nth-child(3):has(style) {
                        display: none !important;
                    }
                    /* Apuntamos al icono de notificaciones */
                    div[class*="st-key-notificaciones"] button [data-testid="stIconMaterial"] {
                        color: #FF4B4B !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                
                # Botón Notificaciones con unread (Usamos el diccionario)
                if st.button(
                    menu_cfg["notificaciones"], 
                    icon=":material/notifications_unread:", 
                    key="notificaciones", 
                    help=menu_cfg["notificaciones_help"], 
                    type="tertiary", 
                    use_container_width=True
                ):
                    reset_state_show()
                    st.session_state.show_notifications = True
            else:
                # Botón Notificaciones normal (Usamos el diccionario)
                if st.button(
                    menu_cfg["notificaciones"], 
                    icon=":material/notifications:", 
                    key="notificaciones", 
                    help=menu_cfg["notificaciones_help"], 
                    type="tertiary", 
                    use_container_width=True
                ):
                    reset_state_show()
                    st.session_state.show_notifications = True

            st.divider()
            
            # Ver cadenas (Usamos el diccionario)
            if st.button(
                menu_cfg["ver_cadenas"], 
                icon=":material/link_2:", 
                key="ver_cadenas", 
                help=menu_cfg["ver_cadenas_help"], 
                type="tertiary", 
                use_container_width=True
            ):
                reset_state_show()
                st.session_state.show_chains = True
                
            st.divider()
                
            # Crear item (Usamos el diccionario)
            st.button(
                menu_cfg["crear_articulo"], 
                icon=":material/box_add:", 
                key="crear_articulo", 
                help=menu_cfg["crear_articulo_help"], 
                type="tertiary", 
                use_container_width=True, 
                on_click=go_to_create
            )
                
            # Editar item (Usamos el diccionario)
            if st.button(
                menu_cfg["ver_articulo"], 
                icon=":material/box_edit:", 
                key="ver_articulo", 
                help=menu_cfg["ver_articulo_help"], 
                type="tertiary", 
                use_container_width=True
            ):
                reset_state_show()
                st.session_state.show_user_items = True
                
        else: # cuando no se ha iniciado sesion
                
            # Iniciar sesión (Usamos el diccionario)
            if st.button(
                menu_cfg["iniciar_sesion"], 
                icon=":material/login:", 
                key="iniciar_sesion", 
                help=menu_cfg["iniciar_sesion_help"], 
                type="tertiary", 
                use_container_width=True
            ):
                reset_state_show()
                st.session_state.show_login = True
                st.rerun()

        # 3. CONGELAMOS ESTE CONTENEDOR EXACTO (Esto sustituye a todo el CSS problemático)
        float_parent(css=f"position: fixed; top: 140px; left: 0px; height: calc(100vh - 140px); width: {menu_cfg['css_width']}; background-color: #f0f2f6; padding-top: 15px; border-right: 1px solid #e0e2e6; z-index: 999999;")

# ───── AREA CONTENIDO DE LA VENTANA ─────
with col_window:
        
    # ───────── DETAIL ─────────
    if st.session_state.detail_item and not st.session_state.show_create:
        #reset_state_show()
        render_detail(items)
        st.stop()

    # ───────── USER PROFILE ─────────
    if st.session_state.show_user:
        render_user(st.session_state.show_user)
        st.stop()

    # ───────── USER ITEMS ─────────
    if st.session_state.show_user_items:
        #reset_state_show()
        render_user_items()
        st.stop()
    
    # ───────── DETALLE DE CADENA ─────────
    if st.session_state.detail_chain:
        # Reiniciamos el camino resaltado en el grafo a cero
        st.session_state.camino_resaltado = []

        chain_detail(*st.session_state.detail_chain)
        st.stop()
    
    # ───────── CADENAS ─────────
    if st.session_state.show_chains:
        #reset_state_show()
        render_chains()
        st.stop()
        
    # ───────── NOTIFICATIONS ─────────
    if st.session_state.show_notifications:
        render_notifications()
        st.stop()
    
    if st.session_state.user == "Perico de los palotes":
        
        # ───────── MARKETPLACE ─────────
        #with st.container(border=True, gap="xxsmall"):
        
        #with st.expander("Visualizador de la red de CONIXBERG:"):
        col1, col2, col3 = st.columns([1,2,1])
        
        with col1:
            
            with st.container(height=350,border=True):
                pass
                
        with col2:
            
            detected_node_id = render_digraph1()
            print("sigmasigmasigmasigmasigmasigmasigmasigmasigmasigmasigmasigmasigma")
        with col3:
            
            with st.container(height=350,border=True):
            
                if detected_node_id is not None:
                    
                    node_item = item_dict[detected_node_id]
                    
                    st.write(f"### Informació del node")
                    
                    img_original = Image.open(node_item["image"])
                    img_recortada = ImageOps.fit(img_original, (200, 130)) #ImageOps.fit se encarga de que no se deforme la foto al recortarla
                    st.image(img_recortada, use_container_width=True)
                    
                    #st.write(f"Artículo: **{node_item['have']}**")
                    if st.button(
                        "Veure article",
                        key=f"detail_node{node_item['item_id']}",
                        use_container_width=True
                    ):
                        print("entro en ver")
                        st.session_state.detail_item = node_item["item_id"]
                        st.rerun()
                    
                else:
                    st.write("### Detalls")
                    st.write("Clica un node de la xarxa per veure la seva informació.")
        
    else:
        render_presentation()
        render_marketplace(items, "main")

print(round(4.22, 1))

st.stop()

cycles = find_all_chains("johnson_all", "have", items, items[0]["item_id"])

if cycles:
    
    for cycle in cycles:
        add_chains(cycle)

#print("johnson", find_all_chains("johnson", "have", items, items[0]["item_id"]))

#---------------------------------
# Ruta a la base de datos (ajusta la extensión/nombre si es diferente)
DB_PATH = "database.db"
IMG_OPT_FOLDER = "img_opt"

def optimize_single_image(image_path):
    """Abre la imagen desde disco, la recorta/optimiza y la guarda en img_opt/."""
    if not image_path or not os.path.exists(image_path):
        return "imagenes/image_not_found.png"
    
    try:
        filename = os.path.basename(image_path)
        path_opt = os.path.join(IMG_OPT_FOLDER, f"opt_{filename}")
        
        img = Image.open(image_path).convert("RGB")
        img = ImageOps.fit(img, (550, 400))
        img.save(path_opt, quality=80, optimize=True)
        
        return path_opt
    except Exception as e:
        print(f"Error optimitzant {image_path}: {e}")
        return "imagenes/image_not_found.png"

def update_all_items_images():
    # 1. Asegurar que existe la carpeta de destino
    os.makedirs(IMG_OPT_FOLDER, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 2. Obtener todos los ítems existentes
    cursor.execute("SELECT item_id, image FROM items")
    rows = cursor.fetchall()
    
    print(f"Processant {len(rows)} articles...")
    
    # 3. Optimizar y actualizar cada registro
    updated_count = 0
    for item_id, original_image_path in rows:
        path_opt = optimize_single_image(original_image_path)
        
        cursor.execute(
            "UPDATE items SET image_optimized = ? WHERE item_id = ?",
            (path_opt, item_id)
        )
        updated_count += 1

    conn.commit()
    conn.close()
    
    print(f"✅ Procés finalitzat amb èxit. {updated_count} ítems actualitzats.")

#if __name__ == "__main__":
update_all_items_images()
#-----------------------------------